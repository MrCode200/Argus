from typing import Literal, Optional

from textual.widgets import Static, Label
from textual.app import ComposeResult

class StatusIndicator(Static):
    """A status indicator widget showing system state."""
    status_colors = {
        "active": "green",
        "inactive": "dim",
        "error": "red",
        "warning": "yellow"
    }

    def __init__(self, label: str, status: str = "inactive", **kwargs) -> None:
        super().__init__(**kwargs)
        self.label_text = label
        self.status = status

    def compose(self) -> ComposeResult:
        color = self.status_colors.get(self.status)
        yield Label(f"[{color}]● {self.label_text}[/]", id=f"status_{self.id}")

    def update_status(self, status: Literal['active', 'inactive', 'error', 'warning'], label: Optional[str] = None) -> None:
        """Update status: 'active', 'inactive', 'error', 'warning'"""
        self.label_text = label if label is not None else self.label_text
        self.status = status

        color = self.status_colors.get(status)
        label = self.query_one(Label)
        label.update(f"[{color}]● {self.label_text}[/]")
