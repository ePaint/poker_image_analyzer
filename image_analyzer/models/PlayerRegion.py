from dataclasses import dataclass


DEFAULT_BOX_WIDTH = 125
DEFAULT_BOX_HEIGHT = 25


@dataclass(frozen=True)
class PlayerRegion:
    name: str
    x: int
    y: int
    width: int = DEFAULT_BOX_WIDTH
    height: int = DEFAULT_BOX_HEIGHT
