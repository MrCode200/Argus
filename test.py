# skyfield_textual_download.py
from pathlib import Path
import requests

from skyfield.api import Loader
from textual import work
from textual.app import App, ComposeResult
from textual.worker import get_current_worker
from textual.widgets import ProgressBar, Button, Static
from textual.containers import Vertical

# adjust this directory for your cache
DATA_DIR = Path(".") / ".skyfield-data"
loader = Loader(str(DATA_DIR), verbose=False)  # verbose=False avoids terminal prints

FILE_NAME = "de421.bsp"  # example; replace with the BSP you want

class DownloaderApp(App):
    CSS = """
    ProgressBar { height: 1 }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Skyfield BSP downloader", id="title"),
            ProgressBar(id="progress"),
            Button("Start download", id="start"),
            Static("", id="status"),
        )

    async def on_button_pressed(self, event) -> None:
        if event.button.id == "start":
            # start the threaded worker; exclusive=True ensures one at a time
            self.run_worker(self._download_bsp, thread=True, exclusive=True)

    @work(thread=True, exclusive=True)
    def _download_bsp(self, **kwargs) -> Path:
        """Thread worker that downloads the file and updates the Textual ProgressBar."""
        self.app.notify(
            str(kwargs)
        )
        filename = kwargs.get("filename", FILE_NAME)
        prog = self.query_one("#progress", ProgressBar)
        status = self.query_one("#status", Static)

        # 1) figure out where Skyfield would fetch it, and local path
        url = loader.build_url(filename)
        local_path = Path(loader.path_to(filename))

        # make sure directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # 2) stream download with requests
        # If server provides Content-Length we can show absolute progress; otherwise show indeterminate.
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total = r.headers.get("Content-Length")
            if total is None:
                # Indeterminate: set no total (Textual ProgressBar will show indeterminate)
                total_bytes = None
                self.call_from_thread(status.update, "Downloading (unknown size)...")
                self.call_from_thread(prog.reset)  # enter indeterminate style
            else:
                total_bytes = int(total)
                # ProgressBar expects total as integer
                self.call_from_thread(prog.update, total=total_bytes, progress=0)
                self.call_from_thread(status.update, f"Downloading {filename} ({total_bytes} bytes)...")

            downloaded = 0
            chunk_size = 32 * 1024  # 32 KiB
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    # update progress in UI thread
                    if total_bytes is not None:
                        # set exact value
                        self.call_from_thread(prog.update, progress=downloaded)
                    else:
                        # for indeterminate, you can optionally show an updating counter
                        self.call_from_thread(status.update, f"Downloaded {downloaded} bytes...")

                    # check worker cancellation
                    worker = get_current_worker()
                    if worker is not None and worker.is_cancelled:
                        # cleanup partial file and exit
                        try:
                            f.close()
                            local_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        self.call_from_thread(status.update, "Cancelled.")
                        return Path()  # empty
        # 3) Finished — ensure ProgressBar shows completion
        if total_bytes is not None:
            self.call_from_thread(prog.update, progress=total_bytes)
        self.call_from_thread(status.update, f"Downloaded to {local_path}")
        # Return the path (accessible as worker.result if needed)
        return local_path

    def on_worker_state_changed(self, event) -> None:
        """Optional: log worker lifecycle changes"""
        self.log(event)

if __name__ == "__main__":
    DownloaderApp().run()
