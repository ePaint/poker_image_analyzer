# Module Signatures

## settings/config.py

### Constants

```python
SETTINGS_PATH: Path = Path.cwd() / "settings.toml"
DEFAULT_SETTINGS: dict = {}
```

### Functions

```python
def load_settings() -> dict

def save_settings(settings: dict) -> None
```

## settings/__init__.py (Public API)

```python
from settings.config import load_settings, save_settings
```

## image_analyzer/models/PlayerRegion.py

### Constants

```python
# GGPoker 6-max (default, 800px base)
DEFAULT_BOX_WIDTH: int = 105
DEFAULT_BOX_HEIGHT: int = 19
BASE_WIDTH: int = 800

# Natural8 5-max (960px base)
NATURAL8_BASE_WIDTH: int = 960
NATURAL8_BOX_WIDTH: int = 132
NATURAL8_BOX_HEIGHT: int = 24
NATURAL8_5MAX_REGIONS: tuple[PlayerRegion, ...]
```

### Data Classes

```python
@dataclass(frozen=True)
class PlayerRegion:
    name: str
    x: int
    y: int
    width: int = DEFAULT_BOX_WIDTH
    height: int = DEFAULT_BOX_HEIGHT
    base_width: int = BASE_WIDTH

    def scale(self, image_width: int) -> "PlayerRegion"
```

## image_analyzer/models/ScreenshotFilename.py

### Constants

```python
FILENAME_PATTERN: re.Pattern  # GGPoker filename regex
```

### Data Classes

```python
@dataclass(frozen=True)
class ScreenshotFilename:
    date: str           # "2024-02-08"
    time: str           # "09-39"
    period: str         # "AM" or "PM"
    small_blind: float  # 0.50 or 2
    big_blind: float    # 1 or 5
    table_id: int       # 154753304

    @classmethod
    def parse(cls, filename: str | Path) -> "ScreenshotFilename | None"

    @classmethod
    def is_valid(cls, filename: str | Path) -> bool

    @property
    def stakes(self) -> str

    @property
    def datetime(self) -> datetime
```

## image_analyzer/analyzer.py

### Constants

```python
DEFAULT_REGIONS: tuple[PlayerRegion, ...]

# Detection pixels (at respective base widths)
GGPOKER_DETECTION_PIXEL: tuple[int, int] = (702, 64)  # 800px base
GGPOKER_COLOR_BGR: tuple[int, int, int] = (6, 15, 219)
NATURAL8_DETECTION_PIXEL: tuple[int, int] = (880, 72)  # 960px base
NATURAL8_COLOR_BGR: tuple[int, int, int] = (145, 39, 140)

# Few-shot learning references for character disambiguation
FEWSHOT_ZERO_B64: str  # Base64-encoded crop of "H0T M0USE!" (0 vs O)
FEWSHOT_ZERO_NAME: str = "H0T M0USE!"
FEWSHOT_I_VS_L_B64: str  # Base64-encoded crop of "jivr31" (i vs l)
FEWSHOT_I_VS_L_NAME: str = "jivr31"
FEWSHOT_ZERO_ALT_B64: str  # Alternative crop of "H0T M0USE!" (different lighting)
FEWSHOT_ZERO_ALT_NAME: str = "H0T M0USE!"

# Post-processing corrections for known OCR misreadings
KNOWN_CORRECTIONS: dict[str, str] = {"GY0KER_AA": "GYOKER_AA"}
```

### Functions

```python
def detect_table_type(
    image: np.ndarray,
    tolerance: int = 30
) -> tuple[PlayerRegion, ...]

def analyze_image(
    image: np.ndarray,
    regions: tuple[PlayerRegion, ...] = DEFAULT_REGIONS,
    api_key: str | None = None,
) -> dict[str, str]

def analyze_screenshot(
    image_path: str | Path,
    regions: tuple[PlayerRegion, ...] | None = None,  # None = auto-detect
    api_key: str | None = None,
) -> dict[str, str]

def analyze_screenshots_batch(
    image_paths: list[str | Path],
    api_key: str | None = None,
) -> list[dict[str, str]]
```

### Private Functions

```python
def _image_to_base64(image: Image.Image) -> str

def _enhance_crop(image: Image.Image) -> Image.Image

def _extract_crops(
    image: np.ndarray,
    regions: tuple[PlayerRegion, ...],
    target_width: int = 400,
    start_index: int = 0,
) -> tuple[Image.Image, list[tuple[str, int]]]

def _call_anthropic(
    image: Image.Image,
    num_crops: int,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> list[str]
```

## image_analyzer/__init__.py (Public API)

```python
from image_analyzer.models import (
    PlayerRegion,
    ScreenshotFilename,
    NATURAL8_5MAX_REGIONS,
    NATURAL8_BASE_WIDTH,
)
from image_analyzer.analyzer import (
    analyze_screenshot,
    analyze_screenshots_batch,
    analyze_image,
    detect_table_type,
    DEFAULT_REGIONS,
)
```
