import time
from pathlib import Path
from typing import Optional
import asyncio

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

loader = Loader(".", verbose=False)
GRADIENT =  Gradient(
    (0.0, "midnightblue"),
    (0.45, "darkslateblue"),
    (1, "white"),         # a bright star / streak
    (0.55, "darkslateblue"),
    (0.8, "indigo"),
    quality=200
)



class EphemerisesDownloadScreen(ModalScreen):
    CSS_PATH = "../css/screens/ephemerisesDownloadScreenTcss.tcss"

    BINDINGS = [
        Binding("ctrl+c", "cancel", "Cancel", show=True, priority=True)
    ]

    def __init__(self, file_name: str, download_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.download_url = loader.build_url(file_name)
        self.file_path = download_dir.joinpath(file_name)
        self._worker: Optional[Worker] = None

    def compose(self) -> ComposeResult:
        vertical_group = VerticalGroup(
            ProgressBar(id="progress", gradient=GRADIENT),
            Label("", id="status"),
            Button("[b]START DOWNLOAD[b]", id="start", variant="error"),
            id = "vertical_group"
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
            self._worker = self.run_worker(self._download_bsp, thread=True, exclusive=True, exit_on_error=False)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.CANCELLED:
            self.notify("Download cancelled.", severity="information")
        elif event.state == WorkerState.ERROR:
            self.notify(f"Download failed.\nError: {event.worker.error}", severity="error")

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
                self.app.call_from_thread(
                    status_widget.update,
                    f"🛰️ Fetching from [bold][italic]NASA JBL[/italic][/bold] server...\n"
                    f"(0/{round(total_bytes*0.000001, 2)} bytes)"
                )
                self.app.call_from_thread(progress_bar.update, total=total_bytes, progress=0)

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
                            f"🛰️ Fetching from [bold][italic]NASA JBL[/italic][/bold] server...\n"
                            f"({round(downloaded_bytes*0.000001, 2)}/{round(total_bytes*0.000001, 2)} Mb)"
                        )

                    # Check if worker cancelled
                    if self._worker.is_cancelled:
                        return

            self.app.call_from_thread(status_widget.update, "✅ Downloaded successfully!")
            time.sleep(2)
            self.dismiss(self.file_path)

    def action_cancel(self):
        if self._worker is not None:
            self._worker.cancel()
            self.app.notify("Download cancelled.", severity="information", timeout=1)
            self._worker.wait()
            self.dismiss()
