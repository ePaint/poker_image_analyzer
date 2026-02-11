from dataclasses import dataclass


DEFAULT_BOX_WIDTH = 105
DEFAULT_BOX_HEIGHT = 19
BASE_WIDTH = 800

NATURAL8_BASE_WIDTH = 960


@dataclass(frozen=True)
class PlayerRegion:
    name: str
    x: int
    y: int
    width: int = DEFAULT_BOX_WIDTH
    height: int = DEFAULT_BOX_HEIGHT
    base_width: int = BASE_WIDTH

    def scale(self, image_width: int) -> "PlayerRegion":
        """Scale region coordinates for different image widths."""
        if image_width == self.base_width:
            return self
        factor = image_width / self.base_width
        return PlayerRegion(
            name=self.name,
            x=int(self.x * factor),
            y=int(self.y * factor),
            width=int(self.width * factor),
            height=int(self.height * factor),
            base_width=image_width,
        )


# Natural8 5-max table constants (base width 960px)
NATURAL8_BOX_WIDTH = 132
NATURAL8_BOX_HEIGHT = 24

NATURAL8_5MAX_REGIONS = (
    PlayerRegion("top_left", 171, 199, NATURAL8_BOX_WIDTH, NATURAL8_BOX_HEIGHT, NATURAL8_BASE_WIDTH),
    PlayerRegion("top_right", 665, 199, NATURAL8_BOX_WIDTH, NATURAL8_BOX_HEIGHT, NATURAL8_BASE_WIDTH),
    PlayerRegion("left", 24, 496, NATURAL8_BOX_WIDTH, NATURAL8_BOX_HEIGHT, NATURAL8_BASE_WIDTH),
    PlayerRegion("right", 804, 496, NATURAL8_BOX_WIDTH, NATURAL8_BOX_HEIGHT, NATURAL8_BASE_WIDTH),
    PlayerRegion("bottom", 414, 672, NATURAL8_BOX_WIDTH, NATURAL8_BOX_HEIGHT, NATURAL8_BASE_WIDTH),
)
