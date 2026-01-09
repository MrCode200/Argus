import logging
import re
from typing import TypeVar, get_origin, Literal

from pydantic import BaseModel
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalGroup, Center, Container, HorizontalGroup, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Label, Checkbox, Switch, Select, Input, Button

from config.config import ConfigFieldMeta, get_config_fields, settings
from src.validation import validate_locationiq_key

logger = logging.getLogger("argus.app")

T = TypeVar('T')


class DynamicConfigScreen(ModalScreen):
    """Dynamic configuration editor that adapts to field types."""
    CSS_PATH = "../css/screens/dynamicConfigScreen.tcss"

    BINDINGS = [
        Binding("ctrl+c", "cancel", "Cancel", show=True, priority=True),
        Binding("ctrl+S", "submit", "Submit", show=True, priority=True),
        Binding("ctrl+r", "reset", "Reset", show=True, priority=True),
    ]

    def __init__(self, config_models: list[BaseModel]):
        super().__init__()
        self.config_models = config_models
        self.sections = self._extract_fields()

    def _extract_fields(self) -> dict[str, list[ConfigFieldMeta]]:
        sections: dict[str, list[ConfigFieldMeta]] = {}

        for config_model in self.config_models:
            fields: list[ConfigFieldMeta] = get_config_fields(config_model, connector="-")
            sections[config_model.__class__.__name__] = fields

        return sections

    def compose(self) -> ComposeResult:
        with Container(id="container-main"):
            with ScrollableContainer(id="config-scrollable-container"):
                for section_name, fields in self.sections.items():
                    with Container(classes="section-container", id=f"section-container-{section_name}"):

                        for field in fields:
                            # Wrap each field in a horizontal container
                            with Container(classes="field-row", id=f"field-row-{field.pathed_name}"):
                                yield Label(field.display_name, classes="field-label")

                                if field.is_bool:
                                    yield Switch(field.value, id=f"field-checkbox-{field.pathed_name}",
                                                 tooltip=field.description)
                                elif field.is_float:
                                    yield Input(str(field.value), id=f"field-input-{field.pathed_name}", type="number",
                                                tooltip=field.description)
                                elif field.is_int:
                                    yield Input(str(field.value), id=f"field-input-{field.pathed_name}", type="integer",
                                                tooltip=field.description)
                                elif field.is_choice:
                                    yield Select.from_values(field.choices, id=f"field-select-{field.pathed_name}",
                                                             value=field.value)
                                elif field.is_str:
                                    yield Input(str(field.value), id=f"field-input-{field.pathed_name}", type="text",
                                                tooltip=field.description)

            with HorizontalGroup(id="horizontal-group-buttons"):
                yield Button("Save", id="save-button", variant="success")
                yield Button("Reset", id="reset-button", variant="error")
                yield Button("Close", id="close-button", variant="primary")

    def on_mount(self):
        for container in self.query(".section-container"):
            # Set Section name
            section_name = container.id.replace("section-container-", "")
            section_display_name: str = ' '.join(re.findall('[A-Z][^A-Z]*', section_name))
            container.border_title = f"[b i]--- {section_display_name} ---[/b i]"

            # Set Section height
            num_fields = len(container.query(".field-row"))
            container.styles.height = 3 * num_fields

        self.query_one("#container-main", Container).border_title = "Config"


    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "reset-button":
            self.action_reset()
        elif event.button.id == "close-button":
            self.action_cancel()

    @staticmethod
    def get_widget_name(field_meta: ConfigFieldMeta) -> str:
        if field_meta.is_bool:
            return "checkbox"
        elif (field_meta.is_int or
              field_meta.is_float or
              field_meta.is_str):
            return "input"
        elif field_meta.is_choice:
            return "select"


    def action_save(self, _recall_on_error: bool = True):
        previous_state = self.config_models.copy()
        try:
            for section in self.query(".section-container"):
                section_name = section.id.replace("section-container-", "")

                for field_meta in self.sections[section_name]:
                    field_name = field_meta.pathed_name

                    widget_name = self.get_widget_name(field_meta)
                    if not widget_name:
                        self.notify("Field Meta Type Not Supported", severity="error")
                        return

                    field_value = self.query_one(f"#field-{widget_name}-{field_name}").value

                    model = field_meta.model
                    while "-" in field_name:
                        field_name = field_name.split("-", 1)[1]

                    # Convert field value to correct type from inputs
                    if field_meta.is_int:
                        field_value = int(field_value)
                    elif field_meta.is_float:
                        field_value = float(field_value)
                    model.__setattr__(field_name, field_value)

        except Exception as e:
            self.notify(f"Failed to save config: {e}", severity="error")
            self.config_models = previous_state
            if _recall_on_error:
                self.action_save(_recall_on_error=False)

        # ---------------
        # Entangled to the config.py code! :'((
        # ---------------
        if not validate_locationiq_key(settings.env.LOCATIONIQ_API_KEY):
            self.notify("Invalid LocationIQ API key.\nCanceling save. ಠ╭╮ಠ", severity="error")
            return

        try:
            settings.save()
            self.notify("Config Saved")
        except Exception as e:
            self.notify(f"Failed to save config: {e}", severity="error")
            logger.error(f"Failed to save config: {e}")

    def action_reset(self):
        for section in self.query(".section-container"):
            section_name = section.id.replace("section-container-", "")
            for field_meta in self.sections[section_name]:
                field_name = field_meta.pathed_name
                if "LOCATIONIQ_API_KEY" in field_name:
                    continue

                widget_name = self.get_widget_name(field_meta)
                if not widget_name:
                    self.notify("Field Meta Type Not Supported", severity="error")
                    return

                default_value = field_meta.default
                if widget_name == "input":
                    default_value = str(default_value)
                self.query_one(f"#field-{widget_name}-{field_name}").value = default_value

        self.notify("Config Reset, to save press the Save button", severity="information")

    def action_cancel(self):
        self.dismiss(None)

if __name__ == '__main__':
    from config.config import settings, get_config_fields, ConfigFieldMeta

    app = DynamicConfigScreen([settings.units])
    print(app.sections["UnitsConfig"][0].__dict__)
