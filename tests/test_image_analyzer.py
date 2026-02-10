import tomllib
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys

from image_analyzer import (
    PlayerRegion,
    ScreenshotFilename,
    analyze_screenshot,
    DEFAULT_REGIONS,
)

TESTS_DIR = Path(__file__).parent
IMAGES_DIR = TESTS_DIR / "images"
RESULTS_FILE = TESTS_DIR / "testscreenresults.toml"


def load_expected_results() -> dict:
    with open(RESULTS_FILE, "rb") as f:
        return tomllib.load(f)


class TestPlayerRegion:
    def test_is_immutable(self):
        region = PlayerRegion("test", 100, 200)
        with pytest.raises(AttributeError):
            region.name = "changed"

    def test_stores_values(self):
        region = PlayerRegion("top", 348, 152)
        assert region.name == "top"
        assert region.x == 348
        assert region.y == 152
        assert region.width == 105
        assert region.height == 19


class TestScreenshotFilename:
    def test_parse_valid_filename(self):
        info = ScreenshotFilename.parse("2024-02-08_ 09-39_AM_$2_$5_#154753304.png")
        assert info is not None
        assert info.date == "2024-02-08"
        assert info.time == "09-39"
        assert info.period == "AM"
        assert info.small_blind == 2
        assert info.big_blind == 5
        assert info.table_id == 154753304

    def test_parse_pm_filename(self):
        info = ScreenshotFilename.parse("2024-11-16_ 01-34_PM_$5_$10_#207509370.png")
        assert info is not None
        assert info.date == "2024-11-16"
        assert info.time == "01-34"
        assert info.period == "PM"
        assert info.small_blind == 5
        assert info.big_blind == 10
        assert info.table_id == 207509370

    def test_parse_from_path(self):
        path = Path("/some/dir/2025-04-19_ 03-43_AM_$1_$2_#27294242.png")
        info = ScreenshotFilename.parse(path)
        assert info is not None
        assert info.date == "2025-04-19"
        assert info.small_blind == 1
        assert info.big_blind == 2

    def test_parse_invalid_returns_none(self):
        assert ScreenshotFilename.parse("invalid.png") is None
        assert ScreenshotFilename.parse("testscreen1.png") is None
        assert ScreenshotFilename.parse("") is None

    def test_is_valid(self):
        assert ScreenshotFilename.is_valid("2024-02-08_ 09-39_AM_$2_$5_#154753304.png")
        assert not ScreenshotFilename.is_valid("invalid.png")

    def test_stakes_property(self):
        info = ScreenshotFilename.parse("2024-02-08_ 09-39_AM_$2_$5_#154753304.png")
        assert info.stakes == "$2/$5"

    def test_datetime_property_am(self):
        info = ScreenshotFilename.parse("2024-02-08_ 09-39_AM_$2_$5_#154753304.png")
        expected = datetime(2024, 2, 8, 9, 39)
        assert info.datetime == expected

    def test_datetime_property_pm(self):
        info = ScreenshotFilename.parse("2024-11-16_ 01-34_PM_$5_$10_#207509370.png")
        expected = datetime(2024, 11, 16, 13, 34)
        assert info.datetime == expected

    def test_is_immutable(self):
        info = ScreenshotFilename.parse("2024-02-08_ 09-39_AM_$2_$5_#154753304.png")
        with pytest.raises(AttributeError):
            info.date = "2025-01-01"

    def test_parse_decimal_stakes(self):
        info = ScreenshotFilename.parse("2025-03-22_ 05-00_AM_$0.50_$1_#23359976.png")
        assert info is not None
        assert info.small_blind == 0.50
        assert info.big_blind == 1
        assert info.stakes == "$0.50/$1"

    def test_parse_decimal_both_blinds(self):
        info = ScreenshotFilename.parse("2025-01-01_ 12-00_PM_$0.25_$0.50_#12345678.png")
        assert info is not None
        assert info.small_blind == 0.25
        assert info.big_blind == 0.50
        assert info.stakes == "$0.25/$0.50"


class TestDefaultRegions:
    def test_has_six_regions(self):
        assert len(DEFAULT_REGIONS) == 6

    def test_region_names(self):
        names = {r.name for r in DEFAULT_REGIONS}
        expected = {"top", "top_left", "top_right", "bottom_left", "bottom", "bottom_right"}
        assert names == expected


@pytest.fixture(scope="module")
def expected_results():
    return load_expected_results()


def get_test_images():
    if not IMAGES_DIR.exists():
        return []
    return sorted(IMAGES_DIR.glob("testscreen*.png"))


def create_mock_anthropic_response(results: dict[str, str]) -> MagicMock:
    """Create a mock Anthropic API response."""
    region_order = ["top", "top_left", "top_right", "bottom_left", "bottom", "bottom_right"]
    response_lines = []
    for idx, region in enumerate(region_order):
        text = results.get(region, "")
        if text:
            response_lines.append(f"[{idx}] {text}")
        else:
            response_lines.append(f"[{idx}] EMPTY")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="\n".join(response_lines))]
    return mock_response


@pytest.fixture
def mock_anthropic():
    """Fixture to mock the anthropic module."""
    mock_module = MagicMock()
    mock_client = MagicMock()
    mock_module.Anthropic.return_value = mock_client

    with patch.dict(sys.modules, {"anthropic": mock_module}):
        yield mock_module, mock_client


class TestIntegration:
    def test_analyze_screenshot_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            analyze_screenshot("nonexistent.png")

    def test_analyze_returns_all_positions(self, mock_anthropic):
        images = get_test_images()
        if not images:
            pytest.skip("No test images available")

        mock_module, mock_client = mock_anthropic
        mock_results = {
            "top": "Player1",
            "top_left": "Player2",
            "top_right": "",
            "bottom_left": "Player4",
            "bottom": "Player5",
            "bottom_right": "Player6",
        }
        mock_client.messages.create.return_value = create_mock_anthropic_response(mock_results)

        results = analyze_screenshot(images[0], regions=DEFAULT_REGIONS)
        expected_keys = {"top", "top_left", "top_right", "bottom_left", "bottom", "bottom_right"}
        assert set(results.keys()) == expected_keys

    @pytest.mark.parametrize("image_path", get_test_images(), ids=lambda p: p.name)
    def test_analyze_matches_expected(self, mock_anthropic, expected_results, image_path):
        image_key = image_path.stem
        if image_key not in expected_results:
            pytest.skip(f"No expected results for {image_key}")

        expected = expected_results[image_key]
        if all(v == "" for v in expected.values()):
            pytest.skip(f"Expected results not filled in for {image_key}")

        mock_module, mock_client = mock_anthropic
        mock_client.messages.create.return_value = create_mock_anthropic_response(expected)

        results = analyze_screenshot(image_path, regions=DEFAULT_REGIONS)

        for position, expected_name in expected.items():
            ocr_name = results.get(position, "")
            assert ocr_name == expected_name, (
                f"{image_key} {position}: expected '{expected_name}', got '{ocr_name}'"
            )
