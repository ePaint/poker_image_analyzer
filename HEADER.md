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
```

## image_analyzer/ocr_dump/__init__.py

### Types

```python
OcrDumpVersion = Literal["v1", "v2"]
```

### Constants

```python
CURRENT_VERSION: OcrDumpVersion = "v2"
```

### Functions

```python
def write_ocr_dump(
    results: list[dict],
    errors: list[dict],
    output_path: Path,
    screenshots_folder: Path,
    version: OcrDumpVersion = CURRENT_VERSION,
) -> Path

def parse_ocr_dump(path: Path) -> dict[str, dict[int, str]]
```

## image_analyzer/ocr_dump/v1.py

Version 1 format: Keys by hand_number only (duplicates overwrite).

```python
VERSION: str = "v1"

def write(
    results: list[dict],
    errors: list[dict],
    output_path: Path,
    screenshots_folder: Path,
) -> Path

def parse(path: Path) -> dict[str, dict[int, str]]
```

## image_analyzer/ocr_dump/v2.py

Version 2 format: Keys by hand_datetime composite (preserves all screenshots).

```python
VERSION: str = "v2"

def write(
    results: list[dict],
    errors: list[dict],
    output_path: Path,
    screenshots_folder: Path,
) -> Path

def parse(path: Path) -> dict[str, dict[int, str]]
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
[ggpoker]
bottom = 1
bottom_left = 2
top_left = 3
top = 4
top_right = 5
bottom_right = 6

[natural8]
bottom = 1
left = 2
top_left = 3
top_right = 5
right = 6
```

## hand_history/__init__.py (Public API)

### Types

```python
TableType = Literal["ggpoker", "natural8"]
```

### Constants

```python
DEFAULT_SEAT_MAPPINGS: dict[str, dict[str, int]] = {
    "ggpoker": {
        "bottom": 1,
        "bottom_left": 2,
        "top_left": 3,
        "top": 4,
        "top_right": 5,
        "bottom_right": 6,
    },
    "natural8": {
        "bottom": 1,
        "left": 2,
        "top_left": 3,
        "top_right": 5,
        "right": 6,
    },
}
```

### Functions

```python
def load_seat_mapping(
    table_type: TableType = "ggpoker",
    path: Path | None = None,
) -> dict[str, int]

def position_to_seat(
    position_names: dict[str, str],
    table_type: TableType = "ggpoker",
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

## gui/__init__.py (Public API)

```python
from gui.app import launch_app
```

## gui/app.py

### Functions

```python
def apply_dark_theme(app: QApplication) -> None

def launch_app() -> int
```

## gui/main_window.py

### Classes

```python
class MainWindow(QMainWindow):
    def __init__(self)

    # Slots
    def _on_screenshots_folder_changed(self, path: Path) -> None
    def _on_ocr_dump_selected(self, path: Path) -> None
    def _on_hands_folder_changed(self, path: Path) -> None
    def _on_output_changed(self, text: str) -> None
    def _browse_output(self) -> None
    def _update_convert_button(self) -> None
    def _show_settings(self) -> None
    def _start_conversion(self) -> None
    def _start_conversion_from_dump(self) -> None
    def _start_conversion_from_screenshots(self) -> None
    def _start_conversion_step2(self) -> None
    def _cancel_conversion(self) -> None
    def _set_processing_state(self, processing: bool) -> None
    def _save_folder_setting(self, key: str, path: Path) -> None
    def _load_saved_folders(self) -> None
    def _refresh_screenshots(self) -> None
    def _refresh_hands(self) -> None
    def _write_ocr_debug_file(self, results: list[dict], errors: list[dict]) -> None

    # Worker callbacks
    def _on_screenshot_progress(self, current: int, total: int, filename: str) -> None
    def _on_screenshot_result(self, hand_number: str, filename: str, position_count: int, seat_count: int) -> None
    def _on_screenshot_error(self, filename: str, message: str) -> None
    def _on_screenshots_done(self, data: tuple) -> None
    def _on_conversion_progress(self, current: int, total: int, filename: str) -> None
    def _on_hand_converted(self, hand_number: str, player_count: int) -> None
    def _on_hand_skipped(self, hand_number: str, reason: str) -> None
    def _on_conversion_done(self, success: int, failed: int) -> None
```

## gui/settings_dialog.py

### Constants

```python
DEFAULT_SEATS: dict[str, dict[str, int]] = {
    "ggpoker": {...},
    "natural8": {...},
}
```

### Functions

```python
def load_api_key() -> str | None
def save_api_key(key: str) -> None
def load_seat_mapping() -> dict[str, dict[str, int]]
def save_seat_mapping(mappings: dict[str, dict[str, int]]) -> None
def load_corrections() -> dict[str, str]
def save_corrections(corrections: dict[str, str]) -> None
```

### Classes

```python
class SettingsDialog(QDialog):
    GGPOKER_POSITIONS: list[str]  # 6 position names
    NATURAL8_POSITIONS: list[str]  # 5 position names

    def __init__(self, parent=None)
    def get_api_key(self) -> str
```

## gui/drop_zone.py

### Classes

```python
class DropZone(QFrame):
    folder_dropped: Signal(Path)
    file_dropped: Signal(Path)

    def __init__(self, label: str, allow_file_mode: bool = False, parent=None)
    def dragEnterEvent(self, event: QDragEnterEvent) -> None
    def dragLeaveEvent(self, event) -> None
    def dropEvent(self, event: QDropEvent) -> None
    def mousePressEvent(self, event: QMouseEvent) -> None
    def clear(self) -> None
    def get_folder(self) -> Path | None
    def is_file_mode(self) -> bool
    def set_remembered_file(self, path: Path) -> None
```

## gui/file_list.py

### Classes

```python
class FileListWidget(QWidget):
    refresh_clicked: Signal()

    def __init__(
        self,
        title: str,
        validator: Callable[[str], bool] | None = None,
        parent=None,
    )

    def set_folder(self, path: Path, pattern: str) -> int
    def set_title(self, title: str) -> None
    def clear(self) -> None
    def get_files(self) -> list[Path]
    def get_valid_files(self) -> list[Path]
    def count(self) -> int
    def valid_count(self) -> int
    def refresh(self) -> int
```

## gui/workers.py

### Classes

```python
class ScreenshotWorker(QThread):
    progress: Signal(int, int, str)  # current, total, filename
    result: Signal(str, str, int, int)  # hand_number, filename, position_count, seat_count
    error: Signal(str, str)  # filename, message
    finished_processing: Signal(object)  # (hand_data, ocr_results, ocr_errors)

    MAX_RETRIES: int = 5
    BASE_BACKOFF: float = 1.0

    def __init__(
        self,
        screenshots_dir: Path,
        api_key: str | None = None,
        parallel_calls: int = 5,
        rate_limit_per_minute: int = 50,
        parent=None,
    )
    def cancel(self) -> None
    def run(self) -> None


class ConversionWorker(QThread):
    progress: Signal(int, int, str)  # current, total, filename
    hand_converted: Signal(str, int)  # hand_number, replacement_count
    hand_skipped: Signal(str, str)  # hand_number, reason
    finished_processing: Signal(int, int)  # success_count, failed_count

    def __init__(
        self,
        hands_dir: Path,
        hand_data: dict[str, dict[int, str]],
        output_dir: Path,
        parent=None,
    )
    def cancel(self) -> None
    def run(self) -> None
```
