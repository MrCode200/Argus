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
from ..widgets import StatusIndicator
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
        self.app.query_one("#connected-status-indicator", StatusIndicator).update_status('warning', 'Connecting...')

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
            self.app.query_one("#connected-status-indicator", StatusIndicator).update_status('active', 'Connected')
        else:
            self.app.query_one("#connected-status-indicator", StatusIndicator).update_status('error', 'Disconnected')

    def update_ui_state(self) -> None:
        """Update all UI elements based on connection state"""
        connect_btn = self.query_one("#connect_disconnect_btn", Button)
        calibrate_btn = self.query_one("#calibrate_btn", Button)
        status_lbl = self.query_one("#connection_status_lbl", Static)
        device_name_lbl = self.query_one("#device_name_lbl", Label)
        degrees_lbl = self.query_one("#degrees_per_step_lbl", Label)
        network_lbl = self.query_one("#network_identifier_lbl", Label)

        if self.app.connected:
            connect_btn.label = "Disconnect"
            connect_btn.variant = "error"
            calibrate_btn.disabled = False
            status_lbl.update("● Connected")
            status_lbl.add_class("connected")
            status_lbl.remove_class("disconnected")
            network_lbl.update(f"Network: {app_state.network_identifier}")

            if hasattr(self.app, 'device_info') and self.app.device_info:
                device_name_lbl.update(f"Device: {self.app.device_info.name}")
                degrees_lbl.update(f"Degrees per step: {self.app.device_info.degrees_per_step}°")
            else:
                device_name_lbl.update("Device: Connected (info pending)")
                degrees_lbl.update("Degrees per step: Loading...")
        else:
            connect_btn.label = "Connect"
            connect_btn.variant = "success"
            calibrate_btn.disabled = True
            status_lbl.update("○ Disconnected")
            status_lbl.add_class("disconnected")
            status_lbl.remove_class("connected")
            network_lbl.update(f"Network: {app_state.network_identifier or 'Not configured'}")
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
            self.show_loading("Disconnecting...")
            try:
                self.app.client.close()
                self.app.connected = False
                self.app.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.app.device_info = None
                self.notify("Disconnected from EYE", severity="information")
                logger.info(f"Disconnected from EYE: network_identifier={app_state.network_identifier}")
            except Exception as e:
                logger.error("Error disconnecting", exc_info=e)
                self.notify("Error during disconnect", severity="error")
            finally:
                self.hide_loading()
                self.update_ui_state()
        else:
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

        from .calibrationScreen import CalibrationScreen

        cal_screen = CalibrationScreen()
        self.app.push_screen(cal_screen)
        self.run_worker(self._receive_calibration_data(cal_screen), name="calibration_receiver", thread=True)

    async def _receive_calibration_data(self, cal_screen) -> None:
        """Receive calibration data and update screen"""
        try:
            self.app.client.settimeout(0.5)
            while True:
                try:
                    data = self.app.client.recv(1024)
                    if not data:
                        break
                    cal_data = json.loads(data.decode())
                    self.app.call_from_thread(cal_screen.update_data, cal_data)
                    if cal_data.get("status") == "calibrated":
                        break
                except socket.timeout:
                    continue
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.error(f"Error receiving calibration data: {e}")
        finally:
            try:
                self.app.client.settimeout(None)
            except:
                pass

    async def handle_connect_to_eye(self, result: Optional[str] = None) -> None:
        if result is None:
            return

        try:
            ip, port = result.split(":")
            port = int(port)
        except ValueError as e:
            if "not enough values to unpack" in str(e):
                self.notify("Invalid format: Use IP:PORT (e.g., 192.168.1.100:8080)", severity="error")
            elif "invalid literal for int()" in str(e):
                self.notify("Invalid port: Port must be a number", severity="error")
            else:
                logger.debug(f"Error while splitting network_identifier: {e}", exc_info=e)
                self.notify("Invalid network identifier format", severity="error")
                if settings.dev.get_value("raise_on_error"):
                    raise
            return

        self.run_worker(self.connect_to_eye_worker(ip, port, result), name="eye_connection", thread=True,
                        exclusive=True)

    async def connect_to_eye_worker(self, ip: str, port: int, network_identifier: str) -> None:
        worker = get_current_worker()
        if not worker.is_cancelled:
            self.app.call_from_thread(self.show_loading, "Connecting...")

        try:
            if worker.is_cancelled:
                return
            resolved_ip = self._resolve_hostname(ip)
            if resolved_ip is None:
                self.app.call_from_thread(self.hide_loading)
                return

            if worker.is_cancelled:
                return
            self.app.call_from_thread(self.show_loading, f"Connecting to {resolved_ip}:{port}...")
            success, error_msg = self._connect_socket(resolved_ip, port)

            if not success:
                self.app.call_from_thread(self.hide_loading)
                self.app.call_from_thread(self.notify, error_msg, severity="error")
                logger.warning(f"Couldn't connect to {resolved_ip}:{port}")
                return

            if worker.is_cancelled:
                return
            self.app.call_from_thread(self.show_loading, "Getting device info...")
            device_info = self._get_device_info()

            if device_info is None:
                self.app.client.close()
                self.app.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.app.call_from_thread(self.hide_loading)
                self.app.call_from_thread(self.notify, "Connected but failed to get device info", severity="error")
                return

            if worker.is_cancelled:
                return

            self.app.connected = True
            self.app.device_info = device_info
            app_state.network_identifier = network_identifier
            app_state.save()

            logger.info(
                f"Connected to EYE: network_identifier={resolved_ip}:{port}; Device: {device_info.name}; Degrees/step: {device_info.degrees_per_step}")

            self.app.call_from_thread(self.hide_loading)
            self.app.call_from_thread(self.update_ui_state)
            self.app.call_from_thread(self.notify, f"Connected to {device_info.name}", severity="success")

        except Exception as e:
            logger.error("Unexpected error in connection worker", exc_info=e)
            self.app.call_from_thread(self.hide_loading)
            self.app.call_from_thread(self.notify, f"Unexpected error: {str(e)}", severity="error")
            if settings.dev.get_value("raise_on_error"):
                raise

    def _resolve_hostname(self, ip: str) -> Optional[str]:
        try:
            match validate_ip(ip):
                case "invalid":
                    return socket.gethostbyname(ip)
                case _:
                    return ip
        except socket.gaierror as e:
            logger.error(f"Couldn't resolve hostname: {ip}", exc_info=e)
            self.app.call_from_thread(self.notify, f"Failed to resolve hostname: {ip}", severity="error")
            if settings.dev.get_value("raise_on_error"):
                raise
            return None

    def _connect_socket(self, ip: str, port: int) -> tuple[bool, Optional[str]]:
        try:
            self.app.client.settimeout(10.0)
            self.app.client.connect((ip, port))
            logger.debug(f"Socket connected to {ip}:{port}")
            return True, None
        except ConnectionRefusedError as e:
            logger.error(f"Connection refused: {ip}:{port}", exc_info=e)
            if settings.dev.get_value("raise_on_error"):
                raise
            return False, f"Connection refused by {ip}:{port}"
        except TimeoutError as e:
            logger.error(f"Connection timeout: {ip}:{port}", exc_info=e)
            if settings.dev.get_value("raise_on_error"):
                raise
            return False, f"Connection timeout to {ip}:{port}"
        except Exception as e:
            logger.error(f"Connection error: {ip}:{port}", exc_info=e)
            if settings.dev.get_value("raise_on_error"):
                raise
            return False, f"Connection failed: {str(e)}"

    def _get_device_info(self) -> Optional[DeviceInfo]:
        try:
            logger.debug("Requesting device info from EYE")
            self.app.client.send(json.dumps({"action": EyeActions.GET_DEVICE_INFO}).encode())
            self.app.client.settimeout(5.0)
            logger.debug("Waiting to receive device info")
            device_data = json.loads(self.app.client.recv(1024))
            self.notify(str(device_data))
            device_info = DeviceInfo(device_data["device"], device_data["degrees_per_step"])
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