from pathlib import Path

from PIL import Image
from rich_pixels import Pixels
from textual.widgets import Static


class ImageDisplay(Static):
    def __init__(
            self,
            image_path: str | Path,
            resize: tuple[int, int] | None = None,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.image_path = image_path
        self.resize = resize

    def on_mount(self) -> None:
        with Image.open(self.image_path) as image:
            pixels: Pixels = Pixels.from_image(image, resize=self.resize)

        self.update(pixels)