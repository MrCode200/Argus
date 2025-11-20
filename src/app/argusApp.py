import asyncio
import math
from pathlib import Path
from typing import Optional

from geopy import Location
from skyfield.units import Angle, Distance
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, VerticalGroup, Container, ScrollableContainer, Center, Right, Horizontal
from textual.widgets import Footer, Header, Label, Button, TabbedContent
from textual.worker import Worker, WorkerState
from textual_image.widget import Image

from config.settings import settings
from src.app.screens import PromptEyesLocationScreen, FilteredFilePickerScreen, EphemerisesDownloadScreen, \
    ConfirmationScreen
from src.app.screens.filteredFilePickerScreen import FilteredDirectoryTree
from src.app.screens.promptEyesLocationScreen import geolocator
from src.app.widgets import ImageDisplay
from src.locator import get_relative_altazd

# --- Constants ---
CARDINAL_DIRECTIONS_CIRCLE_PATH: Path = Path(".").parent.parent.joinpath(
    "assets/ui/ColoredCardinalDirectionsCircle.png").resolve()
RED_DOT_PATH: Path = Path(".").parent.parent.joinpath("assets/ui/RedCross.png").resolve()
EXAMPLE_IMAGE_PATH: Path = Path(".").parent.parent.joinpath("assets/interstellarObjectImages/example.jpg").resolve()

# P(x, y)
CARDINAL_RED_CROSS_COORDINATES: dict[str, tuple[int, int]] = {
    "CENTER": (46, -27),
    "N": (46, -47),
    "E": (86, -27),
    "S": (46, -7),
    "W": (6, -27)
}

# TODO: Every Base Screen should be interactable/callable from main screen (? is this good design?)
# TODO: Option to continue from last session
## Tracking Display Settings -> TODO: Settings class
# TODO: Add slider to time.now() + deltaTime
# TODO: Add Option to change Units for altazd (deg, rad, def)
# TODO: Add Option to change Refresh Rate ->
# TODO: Togglable If for altazd values should be calculated through average of n values or based on last value
# TODO: Add option to display = False/true for TrackingDisplay altazd

class ArgusApp(App):
    DEFAULT_FULL_EPHEMERIS_FILE: str = "de421.bsp"
    CSS_PATH = "css/app.tcss"

    BINDINGS = [
        Binding("ctrl+a", "change_address", "Change Address", show=True, priority=True),
        Binding("ctrl+b", "open_picker", "Open Picker", show=True),
        Binding("ctrl+s", "tracking_display_settings", "Tracking Display Settings", show=True)
    ]

    # --- Initialization ---
    def __init__(self):
        super().__init__()
        self.user_location: Optional[Location] = None
        self.ephemeris_file: Optional[Path] = None
        self.celestial_body: Optional[str] = None
        self._worker: Optional[Worker] = None

    def compose(self) -> ComposeResult:
        yield Header(True)
        with HorizontalGroup(id="main_horizontal_group"):
            with Container(id="stat-container"):
                yield Button("Start", variant="error", id="start")
                with VerticalGroup():
                    yield Label("Address: ", id="address_lbl")
                    yield Label("Latitude: ", id="latitude_lbl")
                    yield Label("Longitude: ", id="longitude_lbl")
                    yield Label("OFFSET_X: ", id="offset_x")
                    yield Label("OFFSET_Y: ", id="offset_y")

            with Container(id="image-container"):
                with TabbedContent("Cardinal Directions", "Celestial Body"):
                    with Center(id="compass-overlay-center-container"):
                        yield ImageDisplay(
                            CARDINAL_DIRECTIONS_CIRCLE_PATH,
                            id="cardinal-directions-image",
                            resize=(96, 96)
                        )
                        yield ImageDisplay(
                            RED_DOT_PATH,
                            id="red-cross-image",
                            resize=(6, 6),
                        )
                    with ScrollableContainer(id="celestial-body-image-scroll-container"):
                        yield Image(EXAMPLE_IMAGE_PATH, id="celestial-body-image")
                with Center(id="celestial-body-center-container"):
                    yield Label("Celestial Body: ", id="celestial-body-lbl", variant="accent")
                yield Label("Altitude: ", id="altitude_lbl", variant="primary", classes="pos_data_lbl")
                yield Label("Azimuth: ", id="azimuth_lbl", variant="primary", classes="pos_data_lbl")
                yield Label("Distance: ", id="distance_lbl", variant="secondary", classes="pos_data_lbl")

        yield Footer()

    def on_mount(self) -> None:
        self.theme = "flexoki"
        self.title = "ARGUS"

        if not settings.config_dev.get_value("display_image_container"):
            self.query_one("#image-container", Container).display = False

        if not settings.config_dev.get_value("auto_continue"):
            self.push_screen(
                ConfirmationScreen(
                    "Continue from last session?",
                    "Continue",
                    "Cancel"
                ),
                callback=self.continue_from_last_session
            )
        else:
            self.continue_from_last_session(Button.Pressed(Button(id="green_btn")))

    # --- Event Handlers ---
    def on_button_pressed(self, event: Button.Pressed):
        event.stop()

        if event.button.id == "start":
            self._handle_start_button()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        image_container = self.query_one("#image-container", Container)

        if event.tab.id == "--content-tab-tab-2":
            image_container.add_class("celestial-tab-active")
        else:
            image_container.remove_class("celestial-tab-active")

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.CANCELLED:
            self.notify("AltAz calculation cancelled.", severity="information")
            self.query_one("#red-cross-image", ImageDisplay).offset = CARDINAL_RED_CROSS_COORDINATES["CENTER"]
        elif event.state == WorkerState.ERROR:
            self.notify(f"AltAz calculation failed.\nError: {event.worker.error}", severity="error")
            self.query_one("#red-cross-image", ImageDisplay).offset = CARDINAL_RED_CROSS_COORDINATES["CENTER"]

    # --- Actions (Keybindings) ---
    def action_change_address(self):
        self.push_screen(
            PromptEyesLocationScreen(),
            callback=self.handle_location_result
        )

    def action_open_picker(self) -> None:
        self.push_screen(
            FilteredFilePickerScreen(path="./ephemerises", add_file_callback=self.download_ephemeris_file),
            callback=self.handle_file_picker_result
        )

    # --- Session Management ---
    def continue_from_last_session(self, event: Button.Pressed):
        last_ephemeris_file = settings.hidden_config.last_ephemeris_file
        last_celestial_body = settings.hidden_config.last_celestial_body
        last_address = settings.hidden_config.last_address

        if event.button.id == "green_btn" and (last_ephemeris_file and last_celestial_body):
            self.handle_file_picker_result({
                "path": Path(last_ephemeris_file),
                "target_body": last_celestial_body
            })

        if (
            (last_address is None or event.button.id == "red_btn") and
            settings.config_dev.get_value("force_push_screens", ignore_debug_mode=True)
        ):
            self.push_screen(PromptEyesLocationScreen())
        elif last_address is not None and event.button.id == "green_btn":
            self.handle_location_result(geolocator.geocode(last_address))

    # --- Location Handling ---
    def handle_location_result(self, result: Optional[Location] = None) -> None:
        if not isinstance(result, Location):
            return

        self.user_location = result
        self.query_one("#address_lbl", Label).update("Address: " + str(self.user_location))
        self.query_one("#latitude_lbl", Label).update("Latitude: " + str(self.user_location.latitude))
        self.query_one("#longitude_lbl", Label).update("Longitude: " + str(self.user_location.longitude))

    # --- File Picker Handling ---
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

    def reload_file_picker(self, *args, **kwargs):
        self.screen_stack[-1].query_one("#dir-tree", FilteredDirectoryTree).reload()

    def handle_file_picker_result(self, result: dict[str, str | Path] | None) -> None:
        if result is None:
            return

        if self._worker is not None and self._worker.is_running:
            self._worker.cancel()
            self.query_one("#altitude_lbl", Label).update("Altitude: ")
            self.query_one("#azimuth_lbl", Label).update("Azimuth: ")
            self.query_one("#distance_lbl", Label).update("Distance: ")

        ephemeris_file = result["path"]
        celestial_body = result["target_body"]

        if isinstance(ephemeris_file, Path):
            self.ephemeris_file = ephemeris_file
            self.celestial_body = celestial_body
            self.query_one("#celestial-body-lbl", Label).update(f" Celestial Body: {celestial_body} ")
            self.app.notify(f"Selected ephemeris file: {ephemeris_file}\n"
                            f" Celestial body: {celestial_body} ")

    # --- Tracking Display ---
    def toggle_display_tracking_data(self):
        altitude_lbl = self.query_one("#altitude_lbl", Label)
        azimuth_lbl = self.query_one("#azimuth_lbl", Label)
        distance_lbl = self.query_one("#distance_lbl", Label)

        show = settings.display_tracking_data and not altitude_lbl.display
        hide = not settings.display_tracking_data and altitude_lbl.display

        if show or hide:
            altitude_lbl.display = show
            azimuth_lbl.display = show
            distance_lbl.display = show

    # --- AltAzD Calculation & Compass ---
    def _handle_start_button(self):
        if self._worker is not None and self._worker.is_running:
            return

        if self.user_location is None or self.ephemeris_file is None or self.celestial_body is None:
            self.app.notify(
                "Please select a location, ephemeris file, and celestial body (￢︿̫̿￢☆).",
                severity="error"
            )
            return

        full_ephemeris_path = self.ephemeris_file.parent / self.DEFAULT_FULL_EPHEMERIS_FILE
        if not full_ephemeris_path.exists():
            self.app.notify(
                f"Missing full ephemeris file (￣ε(#￣)☆╰╮o(￣皿￣///).\n"
                f"Download {self.DEFAULT_FULL_EPHEMERIS_FILE}!",
                severity="error"
            )
            return

        self._worker = self.run_worker(
            self._get_altazd,
            exclusive=True,
            exit_on_error=settings.config_dev.get_value("exit_on_worker_error")
        )
        self.query_one("#image-container", Container).display = True

    async def _get_altazd(self, refresh_rate: float = 0.1) -> None:
        """Continuously update altitude, azimuth, and distance values."""
        altitude_lbl = self.query_one("#altitude_lbl", Label)
        azimuth_lbl = self.query_one("#azimuth_lbl", Label)
        distance_lbl = self.query_one("#distance_lbl", Label)

        old_alt: Optional[Angle] = None
        old_az: Optional[Angle] = None
        old_d: Optional[Distance] = None

        full_bsp = str(self.ephemeris_file.parent / self.DEFAULT_FULL_EPHEMERIS_FILE)
        target_bsp = str(self.ephemeris_file)

        while True:
            if self._worker is not None and self._worker.is_cancelled:
                return

            alt, az, d = await asyncio.to_thread(
                get_relative_altazd,
                self.celestial_body,
                self.user_location.latitude,
                self.user_location.longitude,
                full_bsp_file=full_bsp,
                target_bsp_file=target_bsp
            )

            self._update_tracking_labels(
                altitude_lbl, azimuth_lbl, distance_lbl,
                alt, az, d,
                old_alt, old_az, old_d,
                refresh_rate
            )

            old_alt, old_az, old_d = alt, az, d
            self._update_compass(alt, az)

            await asyncio.sleep(refresh_rate)

    def _update_tracking_labels(
        self,
        altitude_lbl: Label, azimuth_lbl: Label, distance_lbl: Label,
        alt: Angle, az: Angle, d: Distance,
        old_alt: Optional[Angle], old_az: Optional[Angle], old_d: Optional[Distance],
        refresh_rate: float
    ) -> None:
        """Update the tracking labels with current and delta values."""
        if old_alt is not None:
            alt_delta = self._format_delta(alt.degrees - old_alt.degrees, "°")
            az_delta = self._format_delta(az.degrees - old_az.degrees, "°")
            d_delta = self._format_delta(d.km - old_d.km, "km")

            altitude_lbl.update(f"Altitude: {alt} | {alt_delta} [dim]/{refresh_rate}s[/dim]")
            azimuth_lbl.update(f"Azimuth: {az} | {az_delta} [dim]/{refresh_rate}s[/dim]")
            distance_lbl.update(f"Distance: {d} | {d_delta} [dim]/{refresh_rate}s[/dim]")
        else:
            altitude_lbl.update(f"Altitude: {alt} | [dim]—[/dim]")
            azimuth_lbl.update(f"Azimuth: {az} | [dim]—[/dim]")
            distance_lbl.update(f"Distance: {d} | [dim]—[/dim]")

    def _update_compass(self, alt: Angle, az: Angle):
        alt_rad = math.radians(abs(alt.degrees))  # 0° = horizon, 90° = zenith

        # 0° = North, 90° = East, 180° = South, 270° = West
        # 90° = North, 0° = East, 270° = South, 180° = West
        az_rad = math.radians((360 - (az.degrees - 90)) % 360)

        cx, cy = CARDINAL_RED_CROSS_COORDINATES["CENTER"]

        minor_radius: int = abs(cx - CARDINAL_RED_CROSS_COORDINATES["E"][0])
        major_radius: int = abs(cy - CARDINAL_RED_CROSS_COORDINATES["N"][1])

        # Calculate distance from center based on altitude
        # At 90° altitude (zenith), radius_factor = 0 (at center)
        # At 0° altitude (horizon), radius_factor = 1 (at edge)
        radius_factor = math.cos(alt_rad)

        effective_minor = minor_radius * radius_factor
        effective_major = major_radius * radius_factor

        # Get current radius length for new Ellipse for Azimuth
        az_r = ((effective_minor * effective_major) /
                math.sqrt(
                    (effective_minor * math.sin(az_rad)) ** 2 +
                    (effective_major * math.cos(az_rad)) ** 2
                )
                )

        dx = az_r * math.cos(az_rad)  # cos for x in math coords
        dy = az_r * math.sin(az_rad)  # sin for y in math coords

        offset_x = cx + dx
        offset_y = cy - dy  # Subtract because screen y is inverted
        self.query_one("#red-cross-image", ImageDisplay).offset = (offset_x, offset_y)

        self.query_one("#offset_x", Label).update(f"OFFSET_X: {offset_x}; OFFSET_Y: {offset_y} ")
        self.query_one("#offset_y", Label).update(f"dx: {dx}; dy: {dy} ")

    # --- Utilities ---
    def _format_delta(self, change: float, unit: str) -> str:
        """Format a change value with color and arrow."""
        change = round(change, 4)
        if change > 0:
            return f"[green]↑ +{change:.4f}{unit}[/green]"
        elif change < 0:
            return f"[red]↓ {change:.4f}{unit}[/red]"
        else:
            return f"[dim]→ 0{unit}[/dim]"