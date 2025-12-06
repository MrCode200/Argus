from pathlib import Path

from typing import NamedTuple

CARDINAL_DIRECTIONS_CIRCLE_PATH: Path = Path(".").parent.parent.joinpath(
    "assets/ui/ColoredCardinalDirectionsCircle.png").resolve()
RED_DOT_PATH: Path = Path(".").parent.parent.joinpath("assets/ui/RedCross.png").resolve()

CARDINAL_DIRECTIONS_CIRCLE_SIZE = (96, 96)

class Point(NamedTuple):
    x: int
    y: int

class CardinalCoordinates(NamedTuple):
    CENTER=Point(46, -27)
    NORTH=Point(46, -47)
    EAST=Point(86, -27)
    SOUTH=Point(46, -7)
    WEST=Point(6, -27)

CARDINAL_DIRECTIONS_COORDINATES = CardinalCoordinates()
