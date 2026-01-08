from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, Center
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Footer
from pathlib import Path
from textual_image.widget import Image

class ConfirmationScreen(ModalScreen[Button.Pressed]):
    """Screen with a dialog."""
    BINDINGS = [
        Binding("enter", "press_green_btn", "Submit", show=True, priority=True),
        Binding("ctrl+c", "press_red_btn", "Cancel", show=True, priority=True),
    ]
    CSS_PATH = "../css/screens/confirmationScreenTcss.tcss"

    def __init__(
            self,
            title: str,
            prompt: str,
            green_btn_lbl: str,
            red_btn_lbl: str,
            image_path: Optional[Path] = None,
    ):
        """
        Args:
            prompt (str): The message to display.
            green_btn_lbl (str): The label for the green button.
            red_btn_lbl (str): The label for the red button.
            image_path (Optional[Path]): The path to the image to display.

        Note:
            The green button id="green_btn" and the red button id="red_btn".
        """
        super().__init__()
        self.title = title
        self.prompt = prompt
        self.green_btn_lbl = green_btn_lbl
        self.red_btn_lbl = red_btn_lbl
        self.image_path = image_path

    def compose(self) -> ComposeResult:
        with Center(id="dialog"):
            yield Label(self.title, id="title", variant="accent")

            if self.image_path:
                with Center(id="image-center"):
                    yield Image(self.image_path, id="image")

            yield Label(self.prompt, id="prompt")

            yield HorizontalGroup(
                Button(self.red_btn_lbl, variant="error", id="red_btn"),
                Button(self.green_btn_lbl, variant="success", id="green_btn")
            )

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event)

    def action_press_green_btn(self):
        self.query_one("#green_btn", Button).press()

    def action_press_red_btn(self):
        self.query_one("#red_btn", Button).press()
