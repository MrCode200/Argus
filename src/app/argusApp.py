import asyncio
import math
from pathlib import Path
from typing import Optional

from geopy import Location
from skyfield.units import Angle, Distance
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, VerticalGroup, Container, ScrollableContainer, Center
from textual.widgets import Footer, Header, Label, Button, TabbedContent
from textual.worker import Worker, WorkerState
from textual_image.widget import Image

from config.config import settings, app_state
from src.app.screens import PromptEyesLocationScreen, FilteredFilePickerScreen, EphemerisesDownloadScreen, \
    ConfirmationScreen
from src.app.screens.dynamicConfigScreen import DynamicConfigScreen
from src.app.screens.filteredFilePickerScreen import FilteredDirectoryTree
from src.app.screens.promptEyesLocationScreen import geolocator
from src.app.widgets import ImageDisplay
from src.constants import AngleUnit, DistanceUnit, CARDINAL_DIRECTIONS_CIRCLE_PATH, RED_DOT_PATH, \
    CARDINAL_DIRECTIONS_COORDINATES
from src.locator import get_relative_altazd
from src.utils import format_delta

# --- Constants ---
EXAMPLE_IMAGE_PATH: Path = Path(".").parent.parent.joinpath("assets/interstellarObjectImages/example.jpg").resolve()

# TODO: Every Base Screen should be interactable/callable from main screen (? is this good design?)
# TODO: Add slider to time.now() + deltaTime
## Tracking Display Settings
# TODO: Toggleable If for altazd values should be calculated through average of n values or based on last value

class ArgusApp(App):
    """
    Main application for tracking celestial bodies.

    Displays altitude, azimuth, and distance to selected celestial bodies
    using ephemeris data, with a visual compass overlay.
    """

    DEFAULT_FULL_EPHEMERIS_FILE: str = "de421.bsp"
    CSS_PATH = "css/app.tcss"

    BINDINGS = [
        Binding("ctrl+a", "change_address", "Change Address", show=True, priority=True),
        Binding("ctrl+b", "open_picker", "Open Picker", show=True),
        Binding("ctrl+d", "toggle_display_data", "Toggle Display Data", show=True),
        Binding("ctrl+s", "open_config", "config", show=True)
    ]

    # --- Initialization ---
    def __init__(self):
        """Initialize the application with default state and load unit settings."""
        super().__init__()
        self.user_location: Optional[Location] = None
        self.ephemeris_file: Optional[Path] = None
        self.celestial_body: Optional[str] = None
        self._worker: Optional[Worker] = None

        self._load_unit_settings()

    def _load_unit_settings(self) -> None:
        """Load and cache unit settings from config for tracking display."""
        self.alt_unit = AngleUnit.from_key(settings.units.altitude.unit)
        self.alt_dec = settings.units.altitude.decimals
        self.az_unit = AngleUnit.from_key(settings.units.azimuth.unit)
        self.az_dec = settings.units.azimuth.decimals
        self.d_unit = DistanceUnit.from_key(settings.units.distance.unit)
        self.d_dec = settings.units.distance.decimals

    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
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
        """Initialize application state after mounting."""
        self.theme = "flexoki"
        self.title = "ARGUS"

        if not settings.dev.get_value("display_image_container"):
            self.query_one("#image-container", Container).display = False

        if not settings.dev.get_value("auto_continue"):
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
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        event.stop()

        if event.button.id == "start":
            self._handle_start_button()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Handle tab switching to update CSS classes for layout adjustments."""
        image_container = self.query_one("#image-container", Container)

        if event.tab.id == "--content-tab-tab-2":
            image_container.add_class("celestial-tab-active")
        else:
            image_container.remove_class("celestial-tab-active")

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes and reset compass on cancellation or error."""
        match event.state:
            case WorkerState.CANCELLED:
                self.notify("AltAz calculation cancelled.", severity="information")
            case WorkerState.ERROR:
                self.notify(f"AltAz calculation failed.\nError: {event.worker.error}", severity="error")
            case _:
                return

        self.query_one("#red-cross-image", ImageDisplay).offset = CARDINAL_DIRECTIONS_COORDINATES.CENTER

    # --- Actions (Keybindings) ---
    def action_change_address(self) -> None:
        """Open the address/location selection screen."""
        self.push_screen(
            PromptEyesLocationScreen(),
            callback=self.handle_location_result
        )

    def action_open_picker(self) -> None:
        """Open the ephemeris file picker screen."""
        self.push_screen(
            FilteredFilePickerScreen(path="./ephemerises", add_file_callback=self.download_ephemeris_file),
            callback=self.handle_file_picker_result
        )

    def action_open_config(self) -> None:
        """Open the configuration screen."""
        self.push_screen(
            DynamicConfigScreen(
                [settings.units, settings.tracking, settings.dev]
            ),
            callback=self.handle_config_result
        )

    def handle_config_result(self, result: dict[str, str | Path] | None) -> None:
        """
        Process configuration result and update application state.
        """
        self._load_unit_settings()
        self.action_toggle_display_data(display=settings.tracking.display_data)

    def action_toggle_display_data(self, display: Optional[bool] = None) -> None:
        """
        Toggle or set the visibility of tracking data labels.

        If display is None, toggles the current state and saves to config.
        If display is provided, sets the state without saving (assumes caller handles save).

        Args:
            display: If None, toggles current state. If bool, sets to that value.
        """
        if display is None:
            # Toggle mode: flip the value and persist
            settings.tracking.display_data = not settings.tracking.display_data
            display = settings.tracking.display_data
            settings.save()
        else:
            # Explicit set mode: caller is responsible for saving
            settings.tracking.display_data = display

        self.query_one("#celestial-body-center-container", Center).display = display
        self.query_one("#altitude_lbl", Label).display = display
        self.query_one("#azimuth_lbl", Label).display = display
        self.query_one("#distance_lbl", Label).display = display

    # --- Session Management ---
    def continue_from_last_session(self, event: Button.Pressed) -> None:
        """
        Handle continuation from last session based on user confirmation.

        Args:
            event: Button press event from confirmation dialog.
                   green_btn = continue, red_btn = start fresh.
        """
        last_ephemeris_file = app_state.last_ephemeris_file
        last_celestial_body = app_state.last_celestial_body
        last_address = app_state.last_address

        if event.button.id == "green_btn" and (last_ephemeris_file and last_celestial_body):
            self.handle_file_picker_result({
                "path": last_ephemeris_file,
                "target_body": last_celestial_body
            })

        if (
                (last_address is None or event.button.id == "red_btn") and
                settings.dev.get_value("force_push_screens", ignore_debug_mode=True)
        ):
            self.push_screen(PromptEyesLocationScreen())
        elif last_address is not None and event.button.id == "green_btn":
            self.handle_location_result(geolocator.geocode(last_address))

    # --- Location Handling ---
    def handle_location_result(self, result: Optional[Location] = None) -> None:
        """
        Process location selection result and update UI.

        Args:
            result: Geopy Location object or None if selection was cancelled.
        """
        if not isinstance(result, Location):
            return

        self.user_location = result
        app_state.last_address = result.address
        app_state.save()

        self.query_one("#address_lbl", Label).update("Address: " + str(self.user_location))
        self.query_one("#latitude_lbl", Label).update("Latitude: " + str(self.user_location.latitude))
        self.query_one("#longitude_lbl", Label).update("Longitude: " + str(self.user_location.longitude))

    # --- File Picker Handling ---
    def download_ephemeris_file(self, file_name: str) -> None:
        """
        Initiate download of an ephemeris file.

        Args:
            file_name: Name of the ephemeris file to download (with or without .bsp extension).
        """
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

    def reload_file_picker(self, *args, **kwargs) -> None:
        """Reload the file picker directory tree after a download completes."""
        self.screen_stack[-1].query_one("#dir-tree", FilteredDirectoryTree).reload()

    def handle_file_picker_result(self, result: dict[str, str | Path] | None) -> None:
        """
        Process ephemeris file selection and update application state.

        Args:
            result: Dictionary with 'path' and 'target_body' keys, or None if cancelled.
        """
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

            app_state.last_ephemeris_file = ephemeris_file
            app_state.last_celestial_body = celestial_body

            app_state.save()

            self.query_one("#celestial-body-lbl", Label).update(f" Celestial Body: {celestial_body} ")
            self.app.notify(f"Selected ephemeris file: {ephemeris_file}\n"
                            f" Celestial body: {celestial_body} ")

    # --- Tracking Display ---
    def toggle_display_tracking_data(self) -> None:
        """
        Sync tracking label visibility with settings.

        Shows or hides labels based on settings.display_tracking_data value.
        """
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
    def _handle_start_button(self) -> None:
        """
        Validate requirements and start the celestial body tracking worker.

        Checks for location, ephemeris file, and celestial body selection
        before starting the background tracking task.
        """
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
            exit_on_error=settings.dev.get_value("exit_on_worker_error")
        )
        self.query_one("#image-container", Container).display = True

    async def _get_altazd(self, refresh_rate: float = 0.1) -> None:
        """
        Continuously calculate and update altitude, azimuth, and distance.

        Runs in a background worker, updating the UI at the specified refresh rate.

        Args:
            refresh_rate: Update interval in seconds.
        """
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
        """
        Update tracking labels with current values and delta changes.

        Args:
            alt: Current altitude angle.
            az: Current azimuth angle.
            d: Current distance.
            old_alt: Previous altitude for delta calculation.
            old_az: Previous azimuth for delta calculation.
            old_d: Previous distance for delta calculation.
            refresh_rate: Current refresh rate for display.
        """
        alt_val = self.alt_unit.get_value(alt)
        az_val = self.az_unit.get_value(az)
        d_val = self.d_unit.get_value(d)

        if old_alt is not None:
            old_alt_val = self.alt_unit.get_value(old_alt)
            old_az_val = self.az_unit.get_value(old_az)
            old_d_val = self.d_unit.get_value(old_d)

            alt_delta = format_delta(alt_val - old_alt_val, self.alt_unit.symbol, self.alt_dec)
            az_delta = format_delta(az_val - old_az_val, self.az_unit.symbol, self.az_dec)
            d_delta = format_delta(d_val - old_d_val, self.d_unit.symbol, self.d_dec)

            altitude_lbl.update(
                f"Altitude: {alt_val:.{self.alt_dec}f}{self.alt_unit.symbol} | {alt_delta} [dim]/{refresh_rate}s[/dim]")
            azimuth_lbl.update(
                f"Azimuth: {az_val:.{self.az_dec}f}{self.az_unit.symbol} | {az_delta} [dim]/{refresh_rate}s[/dim]")
            distance_lbl.update(f"Distance: {d_val:.{self.d_dec}f} | {d_delta} [dim]/{refresh_rate}s[/dim]")
        else:
            altitude_lbl.update(f"Altitude: {alt_val:.4f}{self.alt_unit.symbol} | [dim]—[/dim]")
            azimuth_lbl.update(f"Azimuth: {az_val:.4f}{self.az_unit.symbol} | [dim]—[/dim]")
            distance_lbl.update(f"Distance: {d_val:.4f}{self.d_unit.symbol} | [dim]—[/dim]")

    def _update_compass(self, alt: Angle, az: Angle) -> None:
        """
        Update the compass overlay marker position based on celestial body position.

        Converts altitude and azimuth to screen coordinates on an elliptical compass,
        where altitude determines distance from center and azimuth determines angle.

        Args:
            alt: Altitude angle (0° = horizon, 90° = zenith).
            az: Azimuth angle (0° = North, 90° = East, 180° = South, 270° = West).
        """
        alt_rad = math.radians(abs(alt.degrees))

        # Convert azimuth to screen coordinates
        az_rad = math.radians((360 - (az.degrees - 90)) % 360)

        cx, cy = CARDINAL_DIRECTIONS_COORDINATES.CENTER

        minor_radius: int = abs(cx - CARDINAL_DIRECTIONS_COORDINATES.EAST.x)
        major_radius: int = abs(cy - CARDINAL_DIRECTIONS_COORDINATES.NORTH.y)

        # At 90° altitude (zenith), radius_factor = 0 (at center)
        # At 0° altitude (horizon), radius_factor = 1 (at edge)
        radius_factor = math.cos(alt_rad)

        effective_minor = minor_radius * radius_factor
        effective_major = major_radius * radius_factor

        # Calculate radius for current azimuth on the ellipse
        az_r = ((effective_minor * effective_major) /
                math.sqrt(
                    (effective_minor * math.sin(az_rad)) ** 2 +
                    (effective_major * math.cos(az_rad)) ** 2
                )
                )

        dx = az_r * math.cos(az_rad)
        dy = az_r * math.sin(az_rad)

        offset_x = cx + dx
        offset_y = cy - dy  # Subtract because screen y is inverted
        self.query_one("#red-cross-image", ImageDisplay).offset = (offset_x, offset_y)

        self.query_one("#offset_x", Label).update(f"OFFSET_X: {offset_x}; OFFSET_Y: {offset_y} ")
        self.query_one("#offset_y", Label).update(f"dx: {dx}; dy: {dy} ")