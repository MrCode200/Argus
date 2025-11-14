from textual.binding import Binding
from textual.containers import HorizontalGroup, VerticalGroup, Container
from textual.screen import ModalScreen
from textual.widgets import Label, Input, Button
from textual.app import ComposeResult

class InputPromptScreen(ModalScreen[str]):
    BINDINGS = [
        Binding("ctrl+c", "cancel", "Cancel", show=True, priority=True),
        Binding("enter", "submit", "Submit", show=True, priority=True),
    ]

    CSS_PATH = "../css/screens/inputPromptScreenTcss.tcss"

    def __init__(self, title: str, prompt: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.prompt = prompt

    def compose(self) -> ComposeResult:
        with VerticalGroup():
            yield Label(self.title)
            with Container(id="input_container"):
                yield Input(placeholder=self.prompt)
            with HorizontalGroup():
                yield Button("Submit", variant="success", id="submit_btn")
                yield Button("Cancel", variant="error", id="cancel_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "submit_btn":
            self.action_submit()
            return

        self.action_cancel()

    def action_submit(self) -> None:
        self.dismiss(self.query_one(Input).value)

    def action_cancel(self) -> None:
        self.dismiss(None)