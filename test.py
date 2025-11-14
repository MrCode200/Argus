from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button
from textual.containers import Container, Vertical
from textual.binding import Binding


class NotificationApp(App):
    """Example app showing different notification types."""

    CSS = """
    Screen {
        align: center middle;
    }

    Vertical {
        width: 60;
        height: auto;
        border: round $primary;
        padding: 2 4;
        background: $surface;
    }

    Button {
        width: 100%;
        margin: 1 0;
    }

    /* Customize toast appearance (optional) */
    Toast.-information {
        background: $primary-darken-2;
        border: solid $primary;
    }

    Toast.-warning {
        background: $warning-darken-2;
        border: solid $warning;
    }

    Toast.-error {
        background: $error-darken-2;
        border: solid $error;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "show_quit_message", "Attempt Quit", show=False),
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("i", "info_notification", "Info", show=True),
        Binding("w", "warning_notification", "Warning", show=True),
        Binding("e", "error_notification", "Error", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Button("Show Info Notification", id="info-btn")
            yield Button("Show Warning Notification", id="warning-btn", variant="warning")
            yield Button("Show Error Notification", id="error-btn", variant="error")
            yield Button("Show Custom Notification", id="custom-btn", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "info-btn":
            self.action_info_notification()
        elif event.button.id == "warning-btn":
            self.action_warning_notification()
        elif event.button.id == "error-btn":
            self.action_error_notification()
        elif event.button.id == "custom-btn":
            self.action_custom_notification()

    def action_show_quit_message(self) -> None:
        """Show notification when user tries to quit with Ctrl+C."""
        self.notify(
            "Use [b]Ctrl+Q[/b] to quit the application",
            title="Wrong Key Combination",
            severity="warning",
            timeout=5
        )

    def action_info_notification(self) -> None:
        """Show an information notification."""
        self.notify(
            "This is a simple information message",
            title="Information",
            severity="information"
        )

    def action_warning_notification(self) -> None:
        """Show a warning notification."""
        self.notify(
            "Something might need your [b]attention[/b]!",
            title="Warning",
            severity="warning",
            timeout=8
        )

    def action_error_notification(self) -> None:
        """Show an error notification with longer timeout."""
        self.notify(
            "An [b]error[/b] has occurred! Check the logs.",
            title="Error",
            severity="error",
            timeout=10
        )

    def action_custom_notification(self) -> None:
        """Show notification with Rich markup and no title."""
        self.notify(
            "[italic]You can use [b]Rich markup[/b] in notifications![/italic] "
            "🎉 [green]Colors[/green], [yellow]styles[/yellow], and [blue]emojis[/blue] work too!",
            title=""  # Empty title for no title bar
        )


if __name__ == "__main__":
    app = NotificationApp()
    app.run()