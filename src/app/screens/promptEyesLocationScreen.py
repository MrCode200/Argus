import time
from typing import Optional

from geopy import Location
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
from geopy.geocoders import Nominatim
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, Center
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Footer, Label

from src.app.screens.confirmationScreen import ConfirmationScreen

geolocator = Nominatim(user_agent="Argus")

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
                Button("Submit", variant="success")
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

        self.app.push_screen(
            ConfirmationScreen(
                f"Is the EYE located at: \n\n{self.user_location}?",
                "Yes",
                "No",
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
