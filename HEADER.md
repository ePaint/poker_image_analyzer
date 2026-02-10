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

## image_analyzer/constants.py

### Constants

```python
# Few-shot learning references for character disambiguation
FEWSHOT_ZERO_B64: str  # Base64-encoded crop of "H0T M0USE!" (0 vs O)
FEWSHOT_ZERO_NAME: str = "H0T M0USE!"
FEWSHOT_I_VS_L_B64: str  # Base64-encoded crop of "jivr31" (i vs l)
FEWSHOT_I_VS_L_NAME: str = "jivr31"
FEWSHOT_ZERO_ALT_B64: str  # Alternative crop of "H0T M0USE!" (different lighting)
FEWSHOT_ZERO_ALT_NAME: str = "H0T M0USE!"

# Default player regions for GGPoker 6-max
DEFAULT_REGIONS: tuple[PlayerRegion, ...]

# Hand info region for extracting hand number
HAND_INFO_REGION: PlayerRegion  # Top-left region (0, 0, 350, 25)

# Detection pixels (at respective base widths)
GGPOKER_DETECTION_PIXEL: tuple[int, int] = (702, 64)  # 800px base
GGPOKER_COLOR_BGR: tuple[int, int, int] = (6, 15, 219)
NATURAL8_DETECTION_PIXEL: tuple[int, int] = (880, 72)  # 960px base
NATURAL8_COLOR_BGR: tuple[int, int, int] = (145, 39, 140)
```

### Functions

```python
def load_corrections() -> dict[str, str]
```

## image_analyzer/corrections.toml

TOML file containing known OCR misreadings and their corrections.

```toml
[corrections]
"GY0KER_AA" = "GYOKER_AA"
```

## image_analyzer/llm/protocol.py

### Protocols

```python
class LLMProvider(Protocol):
    def call(
        self,
        image: Image.Image,
        num_crops: int,
        few_shot_examples: list[tuple[str, str, str]],
        prompt: str,
    ) -> list[str]
```

## image_analyzer/llm/anthropic.py

### Classes

```python
class AnthropicProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-haiku-4-5-20251001",
    )

    def call(
        self,
        image: Image.Image,
        num_crops: int,
        few_shot_examples: list[tuple[str, str, str]],
        prompt: str,
    ) -> list[str]
```

## image_analyzer/llm/__init__.py

### Types

```python
ProviderName = Literal["anthropic"]
```

### Functions

```python
def get_provider(
    name: ProviderName = "anthropic",
    api_key: str | None = None,
    model: str | None = None,
) -> LLMProvider
```

## image_analyzer/analyzer.py

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
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> dict[str, str]

def analyze_screenshot(
    image_path: str | Path,
    regions: tuple[PlayerRegion, ...] | None = None,  # None = auto-detect
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> dict[str, str]

def analyze_screenshots_batch(
    image_paths: list[str | Path],
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> list[dict[str, str]]

def extract_hand_number(
    image: np.ndarray,
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> str | None

def extract_hand_number_from_file(
    image_path: str | Path,
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> str | None
```

### Private Functions

```python
def _enhance_crop(image: Image.Image) -> Image.Image

def _extract_crops(
    image: np.ndarray,
    regions: tuple[PlayerRegion, ...],
    target_width: int = 400,
    start_index: int = 0,
) -> tuple[Image.Image, list[tuple[str, int]]]

def _build_prompt(num_crops: int) -> str

def _get_few_shot_examples() -> list[tuple[str, str, str]]

def _call_llm(
    image: Image.Image,
    num_crops: int,
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
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
    extract_hand_number,
    extract_hand_number_from_file,
    DEFAULT_REGIONS,
)
from image_analyzer.constants import HAND_INFO_REGION
from image_analyzer.llm import LLMProvider, ProviderName, get_provider
```

## hand_history/parser.py

### Constants

```python
HAND_HEADER_PATTERN: re.Pattern  # Matches "Poker Hand #OMxxx: ..."
TABLE_PATTERN: re.Pattern  # Matches "Table 'name' 6-max ..."
SEAT_PATTERN: re.Pattern  # Matches "Seat N: player ($xxx in chips)"
```

### Data Classes

```python
@dataclass(frozen=True)
class HandHistory:
    hand_number: str           # "OM262668465"
    table_name: str            # "PLO-5Platinum1"
    timestamp: datetime
    seats: dict[int, str]      # {1: "Hero", 2: "b3f8e036", ...}
    raw_text: str              # Original text for replacement

    def get_player_at_seat(self, seat: int) -> str | None
    def get_seat_for_player(self, player: str) -> int | None
```

### Functions

```python
def parse_hand(text: str) -> HandHistory | None

def parse_file(path: Path) -> list[HandHistory]

def find_hand_by_number(hands: list[HandHistory], hand_number: str) -> HandHistory | None
```

## hand_history/converter.py

### Data Classes

```python
@dataclass
class ConversionResult:
    hand_number: str
    success: bool
    original_text: str
    converted_text: str | None = None
    error: str | None = None
    replacements: dict[str, str] = field(default_factory=dict)
```

### Functions

```python
def convert_hand(
    hand: HandHistory,
    seat_to_name: dict[int, str],
) -> ConversionResult

def convert_hands(
    hands: list[HandHistory],
    hand_number_to_seats: dict[str, dict[int, str]],
) -> list[ConversionResult]

def write_converted_file(
    results: list[ConversionResult],
    output_path: Path,
) -> None

def write_skipped_file(
    results: list[ConversionResult],
    output_path: Path,
) -> None
```

## hand_history/seat_mapping.toml

```toml
[seats]
bottom = 1        # Hero position
bottom_left = 2
top_left = 3
top = 4
top_right = 5
bottom_right = 6
```

## hand_history/__init__.py (Public API)

### Constants

```python
DEFAULT_SEAT_MAPPING: dict[str, int] = {
    "bottom": 1,
    "bottom_left": 2,
    "top_left": 3,
    "top": 4,
    "top_right": 5,
    "bottom_right": 6,
}
```

### Functions

```python
def load_seat_mapping(path: Path | None = None) -> dict[str, int]

def position_to_seat(
    position_names: dict[str, str],
    seat_mapping: dict[str, int] | None = None,
) -> dict[int, str]
```

### Exports

```python
from hand_history.parser import (
    HandHistory,
    parse_hand,
    parse_file,
    find_hand_by_number,
)
from hand_history.converter import (
    ConversionResult,
    convert_hand,
    convert_hands,
    write_converted_file,
    write_skipped_file,
)
```

## convert.py (CLI Entry Point)

### Functions

```python
def process_screenshots(
    screenshots_dir: Path,
    api_key: str | None = None,
) -> dict[str, dict[int, str]]

def process_hands(
    hands_dir: Path,
    hand_data: dict[str, dict[int, str]],
    output_dir: Path,
) -> tuple[int, int]

def main(
    hands_dir: Path,
    screenshots_dir: Path,
    output_dir: Path,
    api_key: str | None = None,
) -> int
```

### CLI Arguments

```
--hands       Directory containing hand history files (default: input/hands)
--screenshots Directory containing screenshot files (default: input/screenshots)
--output      Output directory (default: output)
--api-key     API key for LLM provider (uses ANTHROPIC_API_KEY env var if not set)
```
