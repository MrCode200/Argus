import time
from pathlib import Path
from typing import Optional
import logging

from geopy import Location
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
from geopy.geocoders import Nominatim
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, Center
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Footer, Label

from config.config import settings
from src.app.screens.confirmationScreen import ConfirmationScreen
from src.app.utils.locationImageManager import LocationImageManager
from src.locator.mapping import generate_map

geolocator = Nominatim(user_agent="Argus")

MAP_IMG_DIR: Path = Path(".").parent.parent.joinpath("assets/locationImages/")
location_image_manager = LocationImageManager(
    5,
    MAP_IMG_DIR,
    load_existing_images=True,
    blacklist=["placeholder_map.png"],
    logger=logging.getLogger("argus.app")
)

INFO_TEXT: str = """
Trust me you don't need to read this...
We are not not allowed to maybe use your data for personal financial gains.
There exist the possibility that your data may be sold to a third party. 
Just maybe.
You may become the target of thieves or scammers.
"""


class PromptEyesLocationScreen(ModalScreen):
    BINDINGS = [
        Binding("ctrl+c", "cancel", "Cancel", show=True, priority=True),
        Binding("enter", "validate_location", "Submit", show=True, priority=True),
    ]
    CSS_PATH = "../css/screens/promptEyesLocationScreenTcss.tcss"

    def __init__(self):
        super().__init__()
        self.user_location: Optional[Location] = None

    def compose(self) -> ComposeResult:
        dialog: Center = Center(
            Label("Enter the EYEs address: ( •̀ ω •́ )✧", id="prompt_lbl"),
            HorizontalGroup(
                Input(
                    placeholder="ex. Whip-Ma-Whop-Ma-Gate Str. 67 New York",
                    tooltip="A detailed address increases the accuracy of the locator to locate your position. (╭ರ_•́)︎"
                ),
                Button("Submit", variant="success"),
            ),
            Label(INFO_TEXT, id="info_lbl"),
            id="dialog"
        )
        dialog.border_title = "ARGUS-LocatorV1.0"
        yield dialog
        yield Footer()

    @on(Button.Pressed)
    def action_validate_location(self):
        prompt_lbl = self.query_one("#prompt_lbl", Label)

        while True:
            try:
                self.user_location: Location | None = geolocator.geocode(self.query_one(Input).value)
                break
            except (GeocoderUnavailable, GeocoderTimedOut) as e:
                prompt_lbl.update("Pls wait ... (_　_)。゜zｚＺ")
                self.app.notify(
                    str(e),
                    title="Geocoder Error",
                    severity="error",
                    timeout=6
                )
                self.user_location = None
                time.sleep(1)

        if self.user_location is None:
            prompt_lbl.update("The address could not be found. Please be more specific! (►__◄) ")
            prompt_lbl.add_class("invalid_address")
            return
        else:
            prompt_lbl = self.query_one("#prompt_lbl", Label)
            prompt_lbl.remove_class("invalid_address")
            prompt_lbl.update("Enter the EYEs address: ( •̀ ω •́ )✧")

        # Location Image Logic
        data = generate_map(
            api_key=settings.env.LOCATIONIQ_API_KEY,
            lat=self.user_location.latitude,
            lon=self.user_location.longitude,
            markers=[(self.user_location.latitude, self.user_location.longitude)],
        )
        image_name = f"lat_{self.user_location.latitude}_lon_{self.user_location.longitude}.png"
        location_image_manager.save_image(
            image_name=f"lat_{self.user_location.latitude}_lon_{self.user_location.longitude}.png",
            data=data
        )

        self.app.push_screen(
            ConfirmationScreen(
                title=f"Is the EYE located at:",
                prompt=f"{self.user_location}",
                green_btn_lbl="Yes",
                red_btn_lbl="No",
                image_path=MAP_IMG_DIR/image_name
            ),
            callback=self.set_location
        )

    def set_location(self, event: Button.Pressed):
        if event.button.id == "red_btn":
            return

        self.dismiss(self.user_location)

    def action_cancel(self):
        if self.app.user_location is not None:
            self.dismiss()

        else:
            self.app.notify(
                "You haven't yet selected a location. "
                "Please select a location before closing the screen."
                "(￢︿̫̿￢☆)",
                title="⚠️  No Selection Made",
                severity="warning",
                timeout=6
            )
