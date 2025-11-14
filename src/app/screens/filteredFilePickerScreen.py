import os
from pathlib import Path
from typing import Iterable, Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, HorizontalGroup
from textual.screen import ModalScreen
from textual.suggester import SuggestFromList
from textual.widgets import DirectoryTree, Button, Footer, Label, Input

from src.app.screens.inputPromptScreen import InputPromptScreen


class FilteredDirectoryTree(DirectoryTree):
    """DirectoryTree with search filtering capability."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_query = ""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        if self.search_query == "":
            return paths

        return [path for path in paths if self.search_query.lower() in path.name.lower()]

    def set_search_query(self, query: str):
        self.search_query = query
        self.reload()


class FilteredFilePickerScreen(ModalScreen[Path | None]):
    """Modal screen with DirectoryTree for selecting a directory or file."""

    BINDINGS = [
        Binding("ctrl+c", "cancel", "Cancel", show=True, priority=True),
        Binding("ctrl+a", "add", "Add", show=True, priority=True),
        Binding("ctrl+s", "select", "Select", show=True, priority=True),
        Binding("ctrl+f", "focus_search", "Search", show=True, priority=True),
    ]

    CSS_PATH = "../css/screens/filteredFilePickerScreenTcss.tcss"

    def __init__(
            self,
            path: str | Path = ".",
            title: str = "[u]Select File[/u]",
            add_file_callback: Callable[[str], None] = None,
            **kwargs
    ):
        """
        Args:
            path: Starting directory path
            title: Title for the dialog
            add_file_callback: Callback function to add a file (if not None will add a button to add a file)
        """
        super().__init__(**kwargs)
        self.path: Path = Path(path) if isinstance(path, str) else path
        self.dialog_title = title
        self.selected_path: Path | None = None
        self.add_file_callback = add_file_callback

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.dialog_title, id="title")
            yield Input(
                placeholder="🔍 Type to search files and directories...",
                suggester=SuggestFromList(os.listdir(self.path), case_sensitive=False),
                id="search-input"
            )
            yield FilteredDirectoryTree(self.path, id="dir-tree")

            yield Label("", id="status-bar")
            with HorizontalGroup(id="button-container"):
                yield Button("Cancel", variant="error", id="cancel")
                if self.add_file_callback:
                    yield Button("Add", variant="success", id="Add")
                yield Button("Select", variant="primary", id="select")

        yield Footer()

    def on_mount(self) -> None:
        """Focus search input when screen loads. And update bindings if add_file_callback is not None"""
        self.query_one("#search-input", Input).focus()
        if self.add_file_callback:
            for b in FilteredDirectoryTree.BINDINGS:
                if b.key == "ctrl+a":
                    b.show = True
                    b.priority = True

    def on_unmount(self):
        if not self.add_file_callback:
            return

        for b in FilteredDirectoryTree.BINDINGS:
            if b.key == "ctrl+a":
                b.show = False
                b.priority = False

    def on_input_changed(self):
        self.query_one("#dir-tree", FilteredDirectoryTree).set_search_query(self.query_one("#search-input", Input).value)

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.selected_path = event.path
        self.query_one("#status-bar", Label).update(f"Selected: {event.path.name}")
        event.stop()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()

        if event.button.id == "select":
            self.action_select()
        elif event.button.id == "Add":
            self.action_add()
        elif event.button.id == "cancel":
            self.action_cancel()

    def action_add(self):
        self.app.push_screen(
            InputPromptScreen(
                title="EFD\n(Ephemeris File Downloader)",
                prompt="Enter ephemeris file name",
            ),
            callback=self.add_file_callback
        )

    def action_select(self) -> None:
        """Select the current path and close the modal."""
        if self.selected_path:
            self.dismiss(self.selected_path)
        else:
            self.app.notify(
                "Please [b]select a file or directory[/b] from the tree before confirming. "
                "Use [i]arrow keys[/i] to navigate or [b]ESC[/b] to cancel.",
                title="⚠️  No Selection Made",
                severity="warning",
                timeout=6
            )

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()
