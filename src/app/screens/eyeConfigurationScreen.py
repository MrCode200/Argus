import json
import logging
import socket
import time
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Static, LoadingIndicator
from textual.worker import get_current_worker

from config.config import app_state, settings
from src.utils import validate_ip
from .inputPromptScreen import InputPromptScreen
from ...constants import EyeActions, DeviceInfo

logger = logging.getLogger("argus.app")


class EyeConfigurationScreen(ModalScreen):
    CSS_PATH = "../css/screens/eyeConfigurationScreenTcss.tcss"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loading_start_time: Optional[float] = None

    def compose(self) -> ComposeResult:
        with Container(id="main"):
            # Header Section
            yield Label("--- EYE CONFIGURATION ---", id="title_lbl")

            with Vertical(id="connection_info"):
                yield Label("Connection Status", id="connection_header")
                yield Label(
                    f"Network: {app_state.network_identifier or 'Not configured'}",
                    id="network_identifier_lbl"
                )
                yield Static("", id="connection_status_lbl")

            with Vertical(id="device_info_section"):
                yield Label("Device Information", id="device_info_header")
                yield Label("Device: Not connected", id="device_name_lbl")
                yield Label("Degrees per step: N/A", id="degrees_per_step_lbl")

            with Container(id="loading_container"):
                yield LoadingIndicator(id="loading_indicator")
                yield Label("Connecting...", id="loading_text")

            with Horizontal(id="action_buttons"):
                yield Button("Connect", id="connect_disconnect_btn", variant="success")
                yield Button("Calibrate", id="calibrate_btn", variant="primary", disabled=True)

            yield Button("Exit", id="exit_btn", variant="error")

    def on_mount(self) -> None:
        """Update UI based on current connection state"""
        self.query_one("#loading_container").display = False
        self.update_ui_state()

    def show_loading(self, message: str = "Connecting...") -> None:
        """Show loading indicator with custom message"""
        loading_container = self.query_one("#loading_container")
        loading_text = self.query_one("#loading_text", Label)

        self._loading_start_time = time.time()
        loading_text.update(message)
        loading_container.display = True

        self.query_one("#connect_disconnect_btn", Button).disabled = True
        self.query_one("#calibrate_btn", Button).disabled = True
        self.query_one("#exit_btn", Button).disabled = True

    def hide_loading(self) -> None:
        """Hide loading indicator"""
        loading_container = self.query_one("#loading_container")
        loading_container.display = False

        if self._loading_start_time is not None:
            elapsed = time.time() - self._loading_start_time
            logger.debug(f"Loading operation took {elapsed:.2f} seconds")
            self._loading_start_time = None

        self.query_one("#connect_disconnect_btn", Button).disabled = False
        self.query_one("#exit_btn", Button).disabled = False
        if self.app.connected:
            self.query_one("#calibrate_btn", Button).disabled = False

    def update_ui_state(self) -> None:
        """Update all UI elements based on connection state"""
        connect_btn = self.query_one("#connect_disconnect_btn", Button)
        calibrate_btn = self.query_one("#calibrate_btn", Button)
        status_lbl = self.query_one("#connection_status_lbl", Static)
        device_name_lbl = self.query_one("#device_name_lbl", Label)
        degrees_lbl = self.query_one("#degrees_per_step_lbl", Label)
        network_lbl = self.query_one("#network_identifier_lbl", Label)

        if self.app.connected:
            # Update connection button
            connect_btn.label = "Disconnect"
            connect_btn.variant = "error"

            # Enable calibration
            calibrate_btn.disabled = False

            # Update status
            status_lbl.update("● Connected")
            status_lbl.add_class("connected")
            status_lbl.remove_class("disconnected")

            # Update network identifier
            network_lbl.update(f"Network: {app_state.network_identifier}")

            # Update device info if available
            if hasattr(self.app, 'device_info') and self.app.device_info:
                device_name_lbl.update(f"Device: {self.app.device_info.name}")
                degrees_lbl.update(f"Degrees per step: {self.app.device_info.degrees_per_step}°")
            else:
                device_name_lbl.update("Device: Connected (info pending)")
                degrees_lbl.update("Degrees per step: Loading...")
        else:
            # Update connection button
            connect_btn.label = "Connect"
            connect_btn.variant = "success"

            # Disable calibration
            calibrate_btn.disabled = True

            # Update status
            status_lbl.update("○ Disconnected")
            status_lbl.add_class("disconnected")
            status_lbl.remove_class("connected")

            # Update network identifier
            network_lbl.update(f"Network: {app_state.network_identifier or 'Not configured'}")

            # Clear device info
            device_name_lbl.update("Device: Not connected")
            degrees_lbl.update("Degrees per step: N/A")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "connect_disconnect_btn":
                self.action_connect_to_eye()
            case "calibrate_btn":
                self.action_calibrate_eye()
            case "exit_btn":
                self.dismiss()

    def action_connect_to_eye(self) -> None:
        if self.app.connected:
            # Disconnect from eye (this is fast, can be synchronous)
            self.show_loading("Disconnecting...")

            try:
                self.app.client.close()
                self.app.connected = False
                self.app.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.app.device_info = None  # Clear device info

                self.notify("Disconnected from EYE", severity="information")
                logger.info(f"Disconnected from EYE: network_identifier={app_state.network_identifier}")
            except Exception as e:
                logger.error("Error disconnecting", exc_info=e)
                self.notify("Error during disconnect", severity="error")
            finally:
                self.hide_loading()
                # Update UI
                self.update_ui_state()
        else:
            # Show connection dialog
            self.app.push_screen(
                InputPromptScreen(
                    "Enter Network Identifier (format: IP:PORT or HOSTNAME:PORT)",
                    "Enter IP/MAC Address or Hostname with port...",
                    default_value=app_state.network_identifier if app_state.network_identifier else None,
                ),
                callback=self.handle_connect_to_eye
            )

    def action_calibrate_eye(self) -> None:
        if not self.app.connected:
            self.notify("Cannot calibrate: Not connected to EYE", severity="warning")
            return

        try:
            self.app.client.send(json.dumps({"action": EyeActions.CALIBRATE}).encode())
            self.notify("Calibration command sent", severity="information")
            logger.info("Calibration command sent to EYE")
        except Exception as e:
            logger.error("Error sending calibration command", exc_info=e)
            self.notify("Failed to send calibration command", severity="error")

    # --- Connection to Eye Handling (Using run_worker) ---
    async def handle_connect_to_eye(self, result: Optional[str] = None) -> None:
        if result is None:
            return

        try:
            ip, port = result.split(":")
            port = int(port)

        except ValueError as e:
            if "not enough values to unpack (expected 2, got 1)" in str(e):
                self.notify("Invalid format: Use IP:PORT (e.g., 192.168.1.100:8080)", severity="error")
            elif "invalid literal for int() with base 10:" in str(e):
                self.notify("Invalid port: Port must be a number", severity="error")
            else:
                logger.debug(f"Error while splitting network_identifier: {e}", exc_info=e)
                self.notify("Invalid network identifier format", severity="error")
                if settings.dev.get_value("raise_on_error"):
                    raise
            return

        # Run connection in background worker
        self.run_worker(
            self.connect_to_eye_worker(ip, port, result),
            name="eye_connection",
            thread=True,
            exclusive=True
        )

    async def connect_to_eye_worker(self, ip: str, port: int, network_identifier: str) -> None:
        """Worker function that runs in background thread"""
        worker = get_current_worker()

        # Show loading indicator
        if not worker.is_cancelled:
            self.app.call_from_thread(self.show_loading, "Connecting...")

        try:
            # Step 1: Resolve hostname
            if worker.is_cancelled:
                return

            resolved_ip = self._resolve_hostname(ip)
            if resolved_ip is None:
                self.app.call_from_thread(self.hide_loading)
                return

            # Step 2: Connect to socket
            if worker.is_cancelled:
                return

            self.app.call_from_thread(self.show_loading, f"Connecting to {resolved_ip}:{port}...")
            success, error_msg = self._connect_socket(resolved_ip, port)

            if not success:
                self.app.call_from_thread(self.hide_loading)
                self.app.call_from_thread(self.notify, error_msg, severity="error")
                logger.warning(f"Couldn't connect to {resolved_ip}:{port}")
                return

            # Step 3: Get device info
            if worker.is_cancelled:
                return

            self.app.call_from_thread(self.show_loading, "Getting device info...")
            device_info = self._get_device_info()

            if device_info is None:
                # Failed to get device info, close connection
                self.app.client.close()
                self.app.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.app.call_from_thread(self.hide_loading)
                self.app.call_from_thread(
                    self.notify,
                    "Connected but failed to get device info",
                    severity="error"
                )
                return

            # Success!
            if worker.is_cancelled:
                return

            self.app.connected = True
            self.app.device_info = device_info

            # Save network identifier
            app_state.network_identifier = network_identifier
            app_state.save()

            logger.info(
                f"Connected to EYE: network_identifier={resolved_ip}:{port}; "
                f"Device: {device_info.name}; "
                f"Degrees/step: {device_info.degrees_per_step}"
            )

            # Update UI on main thread
            self.app.call_from_thread(self.hide_loading)
            self.app.call_from_thread(self.update_ui_state)
            self.app.call_from_thread(
                self.notify,
                f"Connected to {device_info.name}",
                severity="success"
            )

        except Exception as e:
            logger.error("Unexpected error in connection worker", exc_info=e)
            self.app.call_from_thread(self.hide_loading)
            self.app.call_from_thread(
                self.notify,
                f"Unexpected error: {str(e)}",
                severity="error"
            )
            if settings.dev.get_value("raise_on_error"):
                raise

    def _resolve_hostname(self, ip: str) -> Optional[str]:
        """Resolve hostname to IP (blocking operation)"""
        try:
            match validate_ip(ip):
                case "invalid":
                    resolved = socket.gethostbyname(ip)
                    return resolved
                case _:
                    return ip
        except socket.gaierror as e:
            logger.error(f"Couldn't resolve hostname: {ip}", exc_info=e)
            self.app.call_from_thread(
                self.notify,
                f"Failed to resolve hostname: {ip}",
                severity="error"
            )
            if settings.dev.get_value("raise_on_error"):
                raise
            return None

    def _connect_socket(self, ip: str, port: int) -> tuple[bool, Optional[str]]:
        """Connect socket (blocking operation)"""
        try:
            # Set timeout for connection
            self.app.client.settimeout(10.0)  # 10 second timeout
            self.app.client.connect((ip, port))
            logger.debug(f"Socket connected to {ip}:{port}")
            return True, None
        except ConnectionRefusedError as e:
            logger.error(f"Connection refused: {ip}:{port}", exc_info=e)
            error_msg = f"Connection refused by {ip}:{port}"
            if settings.dev.get_value("raise_on_error"):
                raise
            return False, error_msg
        except TimeoutError as e:
            logger.error(f"Connection timeout: {ip}:{port}", exc_info=e)
            error_msg = f"Connection timeout to {ip}:{port}"
            if settings.dev.get_value("raise_on_error"):
                raise
            return False, error_msg
        except Exception as e:
            logger.error(f"Connection error: {ip}:{port}", exc_info=e)
            error_msg = f"Connection failed: {str(e)}"
            if settings.dev.get_value("raise_on_error"):
                raise
            return False, error_msg

    def _get_device_info(self) -> Optional[DeviceInfo]:
        """Get device info from connected socket (blocking operation)"""
        try:
            # Request device info
            logger.debug("Requesting device info from EYE")
            self.app.client.send(json.dumps({"action": EyeActions.GET_DEVICE_INFO}).encode())

            # Set timeout for receiving
            self.app.client.settimeout(5.0)  # 5 second timeout for response

            # Receive device info
            logger.debug("Waiting to receive device info")
            device_data = json.loads(self.app.client.recv(1024))
            device_info = DeviceInfo(*device_data)

            # Reset timeout (or set to None for blocking)
            self.app.client.settimeout(None)

            return device_info

        except TimeoutError as e:
            logger.error("Timeout waiting for device info", exc_info=e)
            if settings.dev.get_value("raise_on_error"):
                raise
            return None
        except Exception as e:
            logger.error("Error getting device info", exc_info=e)
            if settings.dev.get_value("raise_on_error"):
                raise
            return None