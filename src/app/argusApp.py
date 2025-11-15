import asyncio
from pathlib import Path
from typing import Optional
import time

from geopy import Location
from skyfield.units import Angle, Distance
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Footer, Header, Input, Label, Button, DataTable
from textual.worker import Worker, WorkerState

from src.app.screens.filteredFilePickerScreen import FilteredDirectoryTree
from src.locator import get_relative_altazd

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
        self.target_body: Optional[str] = None
        self._worker: Optional[Worker] = None
        self.debug_mode: bool = debug_mode

    def compose(self) -> ComposeResult:
        yield Header(True)
        yield Label("Enter Interstellar Object Name: ", variant="accent")
        with HorizontalGroup():
            yield Input(placeholder="ex. Moon",
                        tooltip="The name can be found on NASA maybe")  # Change width so btn fits
            yield Button("Start", variant="error", id="start")
        with VerticalGroup():
            yield Label("Address: ", id="address_lbl")
            yield Label("Latitude: ", id="latitude_lbl")
            yield Label("Longitude: ", id="longitude_lbl")
            yield Label("Target Body: ", id="target_body_lbl")
            yield Label("Altitude: ", id="altitude_lbl")
            yield Label("Azimuth: ", id="azimuth_lbl")
            yield Label("Distance: ", id="distance_lbl")
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        if not self.user_location and not self.debug_mode:
            self.push_screen(PromptEyesLocationScreen())

        self.theme = "flexoki"
        self.title = "ARGUS"

    def on_button_pressed(self, event: Button.Pressed):
        event.stop()

        if event.button.id == "start":
            if self._worker is not None and self._worker.is_running:
                return

            if self.user_location is None or self.ephemeris_file is None or self.target_body is None:
                self.app.notify("Please select a location, ephemeris file, and target body.", severity="error")
                return

            self._worker = self.run_worker(self._get_altazd, exclusive=True, exit_on_error=self.debug_mode)

    # --- Handle AltAz logic ---
    async def _get_altazd(
            self,
            refresh_rate: int = 0.1
    ) -> None:
        """
        :param refresh_rate: The refresh rate in seconds
        """
        altitude_lbl = self.query_one("#altitude_lbl", Label)
        azimuth_lbl = self.query_one("#azimuth_lbl", Label)
        distance_lbl = self.query_one("#distance_lbl", Label)

        old_alt: Optional[Angle] = None
        old_az: Optional[Angle] = None
        old_d: Optional[Distance] = None

        while True:
            if self._worker is not None and self._worker.is_cancelled:
                return

            alt, az, d = await asyncio.to_thread(
                get_relative_altazd,
                self.target_body,
                self.user_location.latitude,
                self.user_location.longitude,
                str(self.ephemeris_file)
            )

            # Calculate changes and format with colors
            if old_alt is not None:
                alt_change = alt.degrees - old_alt.degrees
                az_change = az.degrees - old_az.degrees
                d_change = d.km - old_d.km

                # Format with color based on direction
                alt_delta = f"[green]↑ +{alt_change:.4f}°[/green]" if alt_change > 0 else f"[red]↓ {alt_change:.4f}°[/red]" if alt_change < 0 else "[dim]→ 0°[/dim]"
                az_delta = f"[green]↑ +{az_change:.4f}°[/green]" if az_change > 0 else f"[red]↓ {az_change:.4f}°[/red]" if az_change < 0 else "[dim]→ 0°[/dim]"
                d_delta = f"[green]↑ +{d_change:.2f} km[/green]" if d_change > 0 else f"[red]↓ {d_change:.2f} km[/red]" if d_change < 0 else "[dim]→ 0 km[/dim]"

                altitude_lbl.update(f"Altitude: {alt} | {alt_delta}[dim]/{refresh_rate}sec[/dim]")
                azimuth_lbl.update(f"Azimuth: {az} | {az_delta}[dim]/{refresh_rate}sec[/dim]")
                distance_lbl.update(f"Distance: {d} | {d_delta}[dim]/{refresh_rate}sec[/dim]")
            else:
                # First iteration - no delta yet
                altitude_lbl.update(f"Altitude: {alt} | [dim]—[/dim]")
                azimuth_lbl.update(f"Azimuth: {az} | [dim]—[/dim]")
                distance_lbl.update(f"Distance: {d} | [dim]—[/dim]")

            old_alt = alt
            old_az = az
            old_d = d

            await asyncio.sleep(refresh_rate)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.CANCELLED:
            self.notify("AltAz calculation cancelled.", severity="information")
        elif event.state == WorkerState.ERROR:
            self.notify(f"AltAz calculation failed.\nError: {event.worker.error}", severity="error")

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
            callback=self.reload_file_picker
        )
        # get active file picker screen and reload

    def reload_file_picker(self, *args, **kwargs):
        self.screen_stack[-1].query_one("#dir-tree", FilteredDirectoryTree).reload()

    def handle_file_picker_result(self, result: dict[str, str | Path] | None) -> None:
        if result is None:
            return

        ephemeris_file = result["path"]
        target_body = result["target_body"]

        if isinstance(ephemeris_file, Path):
            self.ephemeris_file = ephemeris_file
            self.target_body = target_body
            self.query_one("#target_body_lbl", Label).update(f"Target Body: {target_body}")
            self.app.notify(f"Selected ephemeris file: {ephemeris_file}\n"
                            f"Target body: {target_body}")

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