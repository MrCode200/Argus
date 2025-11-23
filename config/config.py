import json
from typing import Literal, Optional
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource
)

# Constants
CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_FILE = CONFIG_DIR / "state.json"
JSON_FILE_ENCODING: str = "utf-8"

# --- Dev Config ---
class ConfigDev(BaseModel):
    debug_mode: bool = False
    skip_banner_animation: bool = True
    skip_launch_code_prompt: bool = True
    display_image_container: bool = True
    force_push_screens: bool = False
    auto_continue: bool = True
    exit_on_worker_error: bool = False

    def get_value(self, field_name: str, ignore_debug_mode: bool = False):
        """
        Get a field value, but return False if debug_mode is False.
        If debug_mode is True, return the actual field value.
        """
        if not ignore_debug_mode and not self.debug_mode:
            return False
        return getattr(self, field_name)

# --- Tracking Config ---
class TrackingConfig(BaseModel):
    display_data: bool = True
    refresh_rate: float = 0.1

# --- Units Config ---
class AngleUnitConfig(BaseModel):
    unit: Literal["radians", "degrees", "hours", "arcminutes", "arcseconds", "milliarcseconds"] = "degrees"
    decimals: int = 4

class DistanceUnitConfig(BaseModel):
    unit: Literal["au", "km", "m"] = "au"
    decimals: int = 4

class UnitsConfig(BaseModel):
    azimuth: AngleUnitConfig = Field(default_factory=AngleUnitConfig)
    altitude: AngleUnitConfig = Field(default_factory=AngleUnitConfig)
    distance: DistanceUnitConfig = Field(default_factory=DistanceUnitConfig)

class _Settings(BaseSettings):
    dev: ConfigDev = Field(default_factory=ConfigDev, alias="config-dev")
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    units: UnitsConfig = Field(default_factory=UnitsConfig)

    model_config = SettingsConfigDict(
        json_file=CONFIG_FILE,
        json_file_encoding=JSON_FILE_ENCODING,

        extra="forbid",
        validate_assignment=True,
        validate_default=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (JsonConfigSettingsSource(settings_cls),)

    def save(self):
        with open(CONFIG_FILE, "w", encoding=JSON_FILE_ENCODING) as f:
            f.write(self.model_dump_json(by_alias=True, indent=2))

    def reset(self):
        self.dev = ConfigDev()
        self.tracking = TrackingConfig()
        self.units = UnitsConfig()
        self.save()


class AppState(BaseModel):
    last_address: Optional[str] = None
    last_ephemeris_file: Optional[str] = None
    last_celestial_body: Optional[str] = None

    @classmethod
    def load(cls):
        with open(STATE_FILE, "r", encoding=JSON_FILE_ENCODING) as f:
            data = json.load(f)
        return cls(**data)

    def save(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(by_alias=True, indent=2))

    def reset(self):
        self.last_address = None
        self.last_ephemeris_file = None
        self.last_celestial_body = None
        self.save()

settings = _Settings()
app_state = AppState.load()

