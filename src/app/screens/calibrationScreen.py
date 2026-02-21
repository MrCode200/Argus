import json
import logging
import time
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Button, ProgressBar
from textual.reactive import reactive

from ..widgets import StatusIndicator
from ...constants import EyeActions

logger = logging.getLogger("argus.app")


class CalibrationScreen(ModalScreen):
    """Simple calibration progress screen"""

    CSS_PATH = "../css/screens/calibrationScreenTcss.tcss"

    accuracy = reactive(0)
    elapsed = reactive(0.0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_time = None
        self._timer = None

    def compose(self) -> ComposeResult:
        with Container(id="cal_container"):
            yield Label("Magnetometer Calibration", id="cal_title")

            # Progress bar
            with Container(id="data_container"):
                yield Label("Accuracy: ░░░", id="cal_accuracy")

                # Timer
                yield Label("Elapsed: 00:00", id="cal_timer")

                # Data display
                yield Label("Heading: ---°", id="cal_heading")
                yield Label("Mag: (---, ---, ---)", id="cal_mag")

    def on_mount(self) -> None:
        """Start timer and send calibration command"""
        self._start_time = time.time()
        self._timer = self.set_interval(0.1, self._update_elapsed_timer)

        # Send calibration command
        try:
            self.app.client.send(json.dumps({"action": EyeActions.CALIBRATE}).encode())
            logger.info("Calibration started")
        except Exception as e:
            logger.error(f"Error starting calibration: {e}")

    def _update_elapsed_timer(self) -> None:
        """Update elapsed time"""
        if self._start_time:
            self.elapsed = time.time() - self._start_time

    def watch_elapsed(self, elapsed: float) -> None:
        """Update timer display"""
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        self.query_one("#cal_timer", Label).update(f"Elapsed: {minutes:02d}:{seconds:02d}")

    def watch_accuracy(self, accuracy: int) -> None:
        """Update progress bar and accuracy label"""
        cal_bar = "█" * accuracy + "░" * (3 - accuracy)
        self.query_one("#cal_accuracy", Label).update(f"Accuracy: {cal_bar}")

    def update_data(self, data: dict) -> None:
        """
        Update calibration data from EYE
        Expected: {"accuracy": 0-3, "heading": float, "mag": [x,y,z], "status": str}
        """
        if "accuracy" in data:
            self.accuracy = data["accuracy"]

        if "heading" in data and "direction" in data:
            heading = data["heading"]
            direction = data["direction"]
            self.query_one("#cal_heading", Label).update(f"Heading: {heading:.1f}° ({direction})")

        if "mag" in data:
            x, y, z = data["mag"]
            self.query_one("#cal_mag", Label).update(f"Mag: ({x:.1f}, {y:.1f}, {z:.1f})")

        # Check if complete
        if data.get("status") == "calibrated":
            self.query_one("#cal_cancel", Button).label = "Close"
            self.query_one("#cal_cancel", Button).variant = "success"
            if self._timer:
                self._timer.stop()
            self.notify("Calibration complete!", severity="success")
            self.app.query_one("#calibration-status-indicator", StatusIndicator).update_status('active', 'Calibrated')