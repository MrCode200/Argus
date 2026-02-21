import json
from typing import Literal, Optional, Any, get_origin, get_args
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, JsonConfigSettingsSource, PydanticBaseSettingsSource

from src.validation import validate_locationiq_key

# --- Constants ---
CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_FILE = CONFIG_DIR / "state.json"


# --- Config Metadata ---
class ConfigFieldMeta:
    """Simple metadata for a config field to generate UI."""

    def __init__(self, model: BaseModel, field_name: str, prefix: str = "", connector: str = "."):
        self.name = field_name
        self.pathed_name = f"{prefix}{connector}{field_name}" if prefix else field_name
        self.model = model
        field_info = model.model_fields[field_name]

        # Extract type info
        self.field_type = field_info.annotation
        self.description = field_info.description or ""
        self.default = field_info.default

        # Extract choices for Literal types
        self.choices = None
        if get_origin(self.field_type) is Literal:
            self.choices = list(get_args(self.field_type))

    @property
    def value(self) -> Any:
        """Get current value from model."""
        return getattr(self.model, self.name)

    @value.setter
    def value(self, new_value: Any):
        """Set value on model."""
        setattr(self.model, self.name, new_value)

    @property
    def display_name(self) -> str:
        """Convert field_name to Display Name."""
        return self.pathed_name.replace("_", " ").replace("-", " ").replace(".", " ").title()

    @property
    def is_bool(self) -> bool:
        return self.field_type is bool

    @property
    def is_int(self) -> bool:
        return self.field_type is int

    @property
    def is_float(self) -> bool:
        return self.field_type is float

    @property
    def is_choice(self) -> bool:
        return self.choices is not None

    @property
    def is_str(self) -> bool:
        return self.field_type is str

    @property
    def is_nested_model(self) -> bool:
        """Check if this field is a nested BaseModel."""
        try:
            return isinstance(self.field_type, type) and issubclass(self.field_type, BaseModel)
        except TypeError:
            return False


def get_config_fields(model: BaseModel, max_depth: int = 2, prefix: str = "", connector: str = ".") -> list[
    ConfigFieldMeta]:
    """
    Extract all fields from a Pydantic model, including nested models.

    Args:
        model: The Pydantic model to extract from
        max_depth: How deep to recurse into nested models (0 = no recursion)
        prefix: Internal - tracks the field path for nested models
        connector: Internal - tracks the connector for nested models

    Returns:
        List of ConfigFieldMeta for all extractable fields
    """
    fields: list[ConfigFieldMeta] = []

    for field_name in model.model_fields.keys():
        field_meta = ConfigFieldMeta(model, field_name, prefix, connector)

        if field_meta.is_nested_model and (max_depth == -1 or max_depth > 0):
            nested_instance = getattr(model, field_name)
            nested_fields = get_config_fields(
                nested_instance,
                (max_depth - 1) if max_depth > 0 else max_depth,
                field_meta.pathed_name,
                connector
            )
            fields.extend(nested_fields)
        else:
            fields.append(field_meta)

    return fields


# --- Dev Config ---
class DevConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True, validate_default=True)

    debug_mode: bool = Field(default=False, description="Enable debug features and logging")
    skip_banner_animation: bool = Field(default=True, description="Skip startup banner animation")
    skip_launch_code_prompt: bool = Field(default=True, description="Skip launch code prompt")
    display_image_container: bool = Field(default=True, description="Show image container on startup")
    auto_continue: bool = Field(default=True, description="Automatically continue from last session")
    raise_on_error: bool = Field(default=False, description="Raises when errors occur")

    def get_value(self, field_name: str, ignore_debug_mode: bool = False) -> bool:
        """Get field value, returns False if debug_mode is False (unless ignored)."""
        if not ignore_debug_mode and not self.debug_mode:
            return False
        return getattr(self, field_name)


# --- Tracking Config ---
class TrackingConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True, validate_default=True)

    display_data: bool = Field(default=True, description="Show tracking data labels")
    refresh_rate: float = Field(default=0.1, description="Update interval in seconds")


# --- Unit Configs ---
class AngleUnitConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True, validate_default=True)

    unit: Literal["radians", "degrees", "hours", "arcminutes", "arcseconds", "milliarcseconds"] = Field(
        default="degrees",
        description="Unit for angle measurements"
    )
    decimals: int = Field(default=4, description="Number of decimal places")


class DistanceUnitConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True, validate_default=True)

    unit: Literal["au", "km", "m"] = Field(default="au", description="Unit for distance measurements")
    decimals: int = Field(default=4, description="Number of decimal places")


class UnitsConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True, validate_default=True)

    azimuth: AngleUnitConfig = Field(default_factory=AngleUnitConfig)
    altitude: AngleUnitConfig = Field(default_factory=AngleUnitConfig)
    distance: DistanceUnitConfig = Field(default_factory=DistanceUnitConfig)

# --- Env Settings ---
class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path("../.env").resolve(),
        env_file_encoding="utf-8",
        extra="forbid",
        validate_assignment=True,
        validate_default=True,
    )

    LOCATIONIQ_API_KEY: str = Field(
        description="LocationIQ API key",
        min_length=32,
    )

    @classmethod
    @field_validator('LOCATIONIQ_API_KEY', mode='after') # TODO: doesn't validate env var
    def validate_locationiq_api_key(cls, v):
        if not validate_locationiq_key(v):
            raise ValueError("Invalid LocationIQ API key")
        return v

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,  # values passed programmatically
            dotenv_settings,  # .env file (APPLIES TO NESTED MODELS)
            env_settings,  # OS env vars override .env
        )

# --- Main Settings ---
class Settings(BaseSettings):
    dev: DevConfig = Field(default_factory=DevConfig, alias="config-dev")
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    units: UnitsConfig = Field(default_factory=UnitsConfig)
    env: EnvSettings = Field(default_factory=EnvSettings)

    model_config = SettingsConfigDict(
        env_file=Path("../.env").resolve(),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        json_file=str(CONFIG_FILE),
        json_file_encoding="utf-8",
        extra='forbid',
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
        return (
            JsonConfigSettingsSource(settings_cls),  # lowest priority
        )

    def save(self) -> None:
        """Save settings to config.json."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(by_alias=True, indent=2, exclude={"env": ...}))

    def reset(self) -> None:
        """Reset all settings to defaults."""
        self.dev = DevConfig()
        self.tracking = TrackingConfig()
        self.units = UnitsConfig()
        self.save()


# --- App State ---
class AppState(BaseModel):
    model_config = ConfigDict(validate_assignment=True, validate_default=True)

    last_address: Optional[str] = None
    last_ephemeris_file: Optional[Path] = None
    last_celestial_body: Optional[str] = None
    network_identifier: Optional[str] = None

    @classmethod
    def load(cls) -> "AppState":
        """Load state from file, return defaults if file doesn't exist."""
        if not STATE_FILE.exists():
            return cls()

        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def save(self) -> None:
        """Save state to state.json."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    def reset(self) -> None:
        """Clear all state."""
        self.last_address = None
        self.last_ephemeris_file = None
        self.last_celestial_body = None
        self.save()


# --- Global Instances ---
settings = Settings()
app_state = AppState.load()

if __name__ == '__main__':
    print(settings.env.LOCATIONIQ_API_KEY)
