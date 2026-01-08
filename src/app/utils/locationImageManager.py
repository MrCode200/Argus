import logging
import os
import time
from collections import deque
from pathlib import Path
from typing import Optional


class LocationImageManager:
    valid_suffixes = (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG")

    def __init__(
            self,
            max_images: int,
            dir_path: Path | str,
            load_existing_images: bool = False,
            blacklist: Optional[list[str]] = None,
            logger: Optional[logging.Logger] = None
    ):
        """

        Args:
            max_images: The max number of images that can exist at a time
            dir_path: Where to save the images
            load_existing_images: Whether to load existing images from the directory and track them
            blacklist: A list of image names to exclude from the history (needs to contain the correct suffix)
            logger: A logger to log to
        """
        self.image_dir: Path = dir_path if isinstance(dir_path, Path) else Path(dir_path)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.image_history: deque[str] = deque(maxlen=max_images)
        self.blacklist = blacklist if blacklist else []
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())

        if load_existing_images:
            for image in self.image_dir.iterdir():
                time.sleep(1)
                if image.suffix not in self.valid_suffixes or image.name in blacklist:
                    continue

                if len(self.image_history) >= self.image_history.maxlen:
                    num_valid_images: int = len(
                        [image for image in self.image_dir.iterdir() if
                         image.suffix in self.valid_suffixes and image.name not in blacklist]
                    )
                    raise ValueError(
                        f"Image history is full. Disable load_existing_images or increase max_images. "
                        f"{num_valid_images} images detected."
                    )

                self.logger.info(f"Loading existing image {image.name}. Limit: {self.format_limit_display()}")
                self.image_history.append(image.name)

    def format_limit_display(self):
        return f"{self.image_history.maxlen}/{len(self.image_history)}"

    def save_image(self, image_name: str, data: bytes):
        """
        Saves an image to the directory and adds it to the history

        Args:
            image_name: For blacklist to be accurate the image name needs to contain the correct suffix, else it will be given .png suffix
            data: The image data to save
        """
        if not image_name.endswith(self.valid_suffixes):
            image_name += self.valid_suffixes[0]

        if image_name in self.blacklist:
            self.logger.info(f"Image {image_name} is in blacklist")
            return

        if len(self.image_history) == self.image_history.maxlen:
            oldest = self.image_history[0]
            try:
                self.logger.info(f"Limit reached ({self.format_limit_display()}). Removing oldest image {oldest}")
                os.remove(self.image_dir / oldest)
            except FileNotFoundError:
                pass

        self.image_history.append(image_name)

        with open(self.image_dir / image_name, "wb") as f:
            f.write(data)
        self.logger.info(
            f"Imaged saved {image_name} at {self.image_dir / image_name}. Limit: {self.format_limit_display()}")

    def delete_image(self, image_name: str):
        """
        Deletes an image from the directory and removes it from the history if it exists

        Args:
            image_name: The name of the image
        """
        try:
            os.remove(self.image_dir.joinpath(image_name))

            if image_name in self.image_history:
                self.image_history.remove(image_name)
            self.logger.info(f"Deleted image {image_name}. Limit: {self.format_limit_display()}")
        except FileNotFoundError:
            pass

    def delete_all_images(self):
        """
        Deletes all Images which are tracked.
        """
        for image in self.image_history:
            if image in self.blacklist:
                self.logger.info(f"Image {image} is blacklisted. Skipping.")
                continue

            try:
                self.logger.info(f"Deleting image {image}")
                os.remove(self.image_dir / image)
            except FileNotFoundError:
                pass
        self.image_history.clear()
