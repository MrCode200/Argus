from textual.widgets import Static, Label
from textual.app import ComposeResult

class StatusIndicator(Static):
    """A status indicator widget showing system state."""

    def __init__(self, label: str, status: str = "inactive", **kwargs) -> None:
        super().__init__(**kwargs)
        self.label_text = label
        self.status = status

    def compose(self) -> ComposeResult:
        yield Label(f"● {self.label_text}", id=f"status_{self.id}")

    def set_status(self, status: str) -> None:
        """Update status: 'active', 'inactive', 'error', 'warning'"""
        self.status = status
        status_colors = {
            "active": "green",
            "inactive": "dim",
            "error": "red",
            "warning": "yellow"
        }
        color = status_colors.get(status, "dim")
        label = self.query_one(Label)
        label.update(f"[{color}]●[/] {self.label_text}")
