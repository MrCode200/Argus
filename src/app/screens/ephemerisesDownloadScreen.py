import logging
import time
from pathlib import Path
from typing import Optional

import requests
from skyfield.api import Loader
from textual.app import ComposeResult
from textual.binding import Binding
from textual.color import Gradient
from textual.containers import VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import ProgressBar, Button, Label, Footer
from textual.worker import Worker
from textual.worker import WorkerState

from config.config import settings

loader = Loader(".", verbose=False)

logger = logging.getLogger("argus.app")

# Galactic core gradient - from center outward to void (REVERSED)
NEBULA_GRADIENT = Gradient(
    (0.0, "#f6e6ff"),  # Brighter pale purple-white
    (0.12, "#d79af6"),  # Brighter lavender
    (0.25, "#b56af0"),  # More luminous bright purple
    (0.4, "#8440d0"),  # Brighter violet
    (0.6, "#4a46c2"),  # Brighter royal purple (vs darkslateblue)
    (0.8, "#3a34a0"),  # Brightened deep purple
    (1.0, "#101a80"),  # Brighter midnight blue
    quality=1000
)
STATUS_TEXT: dict[float, str] = {
    0.00: "🛰️ Linking to [bold][italic]NASA JBL[/italic][/bold] server… initializing deep-space feed.",
    0.1: "🕳️ Tracking black-hole drift patterns…",
    0.2: "🌞 Estimating solar flare timelines…",
    0.3: "🪐 Scanning rogue planetary orbits…",
    0.4: "🌌 Probing dark-matter pockets…",
    0.5: "⚛️ Reading gamma-burst echoes…",
    0.6: "🛰️ Syncing pulsar navigation grids…",
    0.7: "⏳ Measuring expansion drift…",
    0.8: "☄️ Sampling comet-trail signatures…",
    0.9: "🪞 Detecting neutron-star ripples…",
    1.00: "✅ Download complete.",
}


class EphemerisesDownloadScreen(ModalScreen[Path | None]):
    CSS_PATH = "../css/screens/ephemerisesDownloadScreenTcss.tcss"

    BINDINGS = [
        Binding("ctrl+c", "cancel", "Cancel", show=True, priority=True)
    ]

    def __init__(self, file_name: str, download_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.file_name = file_name
        self.download_url = loader.build_url(file_name)
        self.file_path = download_dir.joinpath(file_name)
        self._worker: Optional[Worker] = None

    def compose(self) -> ComposeResult:
        vertical_group = VerticalGroup(
            ProgressBar(id="progress", gradient=NEBULA_GRADIENT),
            Label("", id="status"),
            Button("[b]START DOWNLOAD[b]", id="start", variant="error"),
            id="vertical_group"
        )
        vertical_group.border_title = "BSP Downloader"
        yield vertical_group
        yield Footer()

    def on_mount(self):
        self.query_one("#start").animate("opacity", value=0, duration=0)
        self.query_one("#start").animate("opacity", value=1, duration=2)
        vertical_group = self.query_one("#vertical_group", VerticalGroup)
        vertical_group.animate("opacity", value=0, duration=0)
        vertical_group.animate("opacity", value=1, duration=0.5)

    async def on_button_pressed(self, event: Button.Pressed):
        event.stop()

        if event.button.id == "start":
            event.button.disabled = True

            if self._worker is not None:
                self._worker.cancel()
            self._worker = self.run_worker(self._download_bsp, thread=True, exclusive=True,
                                           exit_on_error=settings.dev.get_value("raise_on_error"))

            event.button.disabled = False

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.CANCELLED:
            self.notify("Download cancelled.", severity="information")
            logger.info("Download cancelled.")
        elif event.state == WorkerState.ERROR:
            self.notify(f"Download failed.\nError: {event.worker.error}", severity="error")
            logger.error(f"Download failed.\nError: {event.worker.error}", exc_info=event.worker.error)

    def _get_status_text(self) -> str:
        # Sort keys to ensure correct ordering
        keys = sorted(STATUS_TEXT.keys())
        percent = self.query_one("#progress", ProgressBar).percentage

        chosen_key = 0.0
        for k in keys:
            if k <= percent:
                chosen_key = k
            else:
                break

        return STATUS_TEXT[chosen_key]

    def _download_bsp(self) -> Optional[Path]:
        progress_bar = self.query_one("#progress", ProgressBar)
        status_widget = self.query_one("#status", Label)

        chunk_size = 64 * 1024
        downloaded_bytes = 0

        with requests.get(self.download_url, stream=True) as r:
            r.raise_for_status()
            total_bytes = int(r.headers.get("Content-Length"))

            if total_bytes is None:
                self.app.call_from_thread(status_widget.update, "🛰️❓ Downloading (unknown size)...")
            else:
                self.app.call_from_thread(progress_bar.update, total=total_bytes, progress=0)
                self.app.call_from_thread(
                    status_widget.update,
                    f"{STATUS_TEXT[0]}\n"
                    f"(0/{round(total_bytes * 0.000001, 2)} bytes)"
                )

            with open(self.file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded_bytes += len(chunk)

                    if total_bytes:
                        self.app.call_from_thread(progress_bar.update, progress=downloaded_bytes)
                        self.app.call_from_thread(
                            status_widget.update,
                            f"{self.app.call_from_thread(self._get_status_text)}\n"
                            f"({round(downloaded_bytes * 0.000001, 2)}/{round(total_bytes * 0.000001, 2)} MB)"
                        )

                    # Check if worker cancelled
                    if self._worker.is_cancelled:
                        return

            logger.info(f"Download {self.file_name} completed.")
            self.app.call_from_thread(status_widget.update, STATUS_TEXT[1])
            time.sleep(2)
            self.app.call_from_thread(self.dismiss, self.file_path)

    def action_cancel(self):
        if self._worker is not None:
            self._worker.cancel()
            self._worker.wait()
            self.dismiss()
