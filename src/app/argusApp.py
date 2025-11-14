from pathlib import Path
from typing import Optional

from geopy import Location
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Footer, Header, Input, Label, Button, DataTable
from textual.worker import Worker

EXAMPLE_IMG_PATH: Path = Path("example.jpg")

from src.app.screens import PromptEyesLocationScreen, FilteredFilePickerScreen, EphemerisesDownloadScreen


class ArgusApp(App):
    CSS_PATH = "css/app.tcss"

    BINDINGS = [
        Binding("ctrl+a", "change_address", "Change Address", show=True, priority=True),
        Binding("ctrl+b", "open_picker", "Open Picker", show=True),
    ]

    def __init__(self, debug_mode: bool = False):
        super().__init__()
        self.user_location: Optional[Location] = None
        self.ephemeris_file: Optional[Path] = None
        self.debug_mode: bool = debug_mode

    def compose(self) -> ComposeResult:
        yield Header(True)
        yield Label("Enter Interstellar Object Name: ", variant="accent")
        with HorizontalGroup():
            yield Input(placeholder="ex. Moon",
                        tooltip="The name can be found on NASA maybe")  # Change width so btn fits
            yield Button("Submit", variant="error", id="submit")
        with VerticalGroup():
            yield Label("Address: ", id="address_lbl")
            yield Label("Latitude: ", id="latitude_lbl")
            yield Label("Longitude: ", id="longitude_lbl")
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        if not self.user_location and not self.debug_mode:
            self.push_screen(PromptEyesLocationScreen())

        self.theme = "flexoki"
        self.title = "ARGUS"

    def on_button_pressed(self, event: Button.Pressed):
        event.stop()

        if event.button.id == "submit":
            self.action_open_picker()

    # --- Handles File Picker logic ---
    def action_open_picker(self) -> None:
        self.push_screen(
            FilteredFilePickerScreen(path="./ephemerises", add_file_callback=self.download_ephemeris_file),
            callback=self.handle_file_picker_result
        )

    def download_ephemeris_file(self, file_name: str):
        if not file_name:
            return

        file_name = file_name.strip()
        if not file_name.endswith(".bsp"):
            file_name += ".bsp"
        self.app.push_screen(
            EphemerisesDownloadScreen(
                file_name=file_name,
                download_dir=Path("./ephemerises"),
            ),
        )
        # get active file picker screen and reload

    def handle_file_picker_result(self, result: Optional[Path] = None) -> None:
        if isinstance(result, Path):
            self.ephemeris_file = result
            self.app.notify(f"Selected ephemeris file: {result}")

    # --- Handles Location logic ---
    def action_change_address(self):
        self.push_screen(
            PromptEyesLocationScreen(),
            callback=self.handle_location_result
        )

    def handle_location_result(self, result: Optional[Location] = None) -> None:
        if isinstance(result, Location):
            self.user_location = result
            self.query_one("#address_lbl", Label).update("Address: " + str(self.user_location))
            self.query_one("#latitude_lbl", Label).update("Latitude: " + str(self.user_location.latitude))
            self.query_one("#longitude_lbl", Label).update("Longitude: " + str(self.user_location.longitude))