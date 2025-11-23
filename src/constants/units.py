from enum import Enum
from typing import NamedTuple
from skyfield.units import Angle, Distance

class UnitInfo(NamedTuple):
    unit: str
    symbol: str
    description: str

class AngleUnit(Enum):
    RADIANS = UnitInfo("radians", "rad", "Radians (2π in a circle)")
    DEGREES = UnitInfo("degrees", "°", "Degrees (360° in a circle)")
    HOURS = UnitInfo("hours", "h", "Hours (24h in a circle)")
    ARCMINUTES = UnitInfo("arcminutes", "'", "Arcminutes (1/60 of a degree)")
    ARCSECONDS = UnitInfo("arcseconds", "\"", "Arcseconds (1/3600 of a degree)")
    MILLIARCSECONDS = UnitInfo("milliarcseconds", "mas", "Milliarcseconds (1/3600000 of a degree)")

    @property
    def key(self):
        return self.value.unit

    @property
    def symbol(self):
        return self.value.symbol

    @property
    def description(self):
        return self.value.description

    def get_value(self, angle: Angle) -> float:
        """Extract the angle value in this unit."""
        attr = getattr(angle, self.key)
        return attr() if callable(attr) else attr

    @classmethod
    def from_key(cls, key: str):
        for unit in cls:
            if unit.value.unit == key:
                return unit


class DistanceUnit(Enum):
    AU = UnitInfo("au", "au", "Astronomical Unit")
    KM = UnitInfo("km", "km", "Kilometer")
    M = UnitInfo("m", "m", "Meter")

    @property
    def key(self):
        return self.value.unit

    @property
    def symbol(self):
        return self.value.symbol

    @property
    def description(self):
        return self.value.description

    def get_value(self, distance: Distance) -> float:
        """Extract the distance value in this unit."""
        attr = getattr(distance, self.key)
        return attr() if callable(attr) else attr

    @classmethod
    def from_key(cls, key: str):
        for unit in cls:
            if unit.value.unit == key:
                return unit