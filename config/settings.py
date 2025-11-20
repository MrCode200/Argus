from typing import Optional, Literal

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource
)


class ConfigDev(BaseModel):
    debug_mode: bool = False
    skip_banner_animation: bool = True
    skip_launch_code_prompt: bool = True
    display_image_container: bool = True
    force_push_screens: bool = False
    auto_continue: bool = False
    exit_on_worker_error: bool = False

    def get_value(self, field_name: str, ignore_debug_mode: bool = False):
        """
        Get a field value, but return False if debug_mode is False.
        If debug_mode is True, return the actual field value.
        """
        if not ignore_debug_mode and not self.debug_mode:
            return False
        return getattr(self, field_name)

class HiddenConfig(BaseModel):
    last_address: Optional[str] = None
    last_ephemeris_file: Optional[str] = None
    last_celestial_body: Optional[str] = None

class _Settings(BaseSettings):
    config_dev: ConfigDev = Field(default_factory=ConfigDev, alias="config-dev")
    hidden_config: HiddenConfig = Field(default_factory=HiddenConfig, alias="hidden-config")

    display_tracking_data: bool = True
    tracking_body_refresh_rate: float = 0.1
    altaz_units: Literal["default"] = "default"
    distance_units: Literal["au", "km"] = "au"

    model_config = SettingsConfigDict(
        json_file="config/config.json",
        json_file_encoding="utf-8",

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


settings = _Settings()
