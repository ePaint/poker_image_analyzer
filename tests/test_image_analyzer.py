import tomllib
import pytest
from pathlib import Path

from image_analyzer import (
    PlayerRegion,
    OCRResult,
    analyze_screenshot,
    DEFAULT_REGIONS,
)
from image_analyzer.engines.easyocr_engine import EasyOCREngine

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
        assert region.width == 125
        assert region.height == 25


class TestOCRResult:
    def test_is_immutable(self):
        result = OCRResult("text", 100.0, 200.0, 0.95)
        with pytest.raises(AttributeError):
            result.text = "changed"

    def test_stores_values(self):
        result = OCRResult("PlayerName", 150.5, 250.5, 0.87)
        assert result.text == "PlayerName"
        assert result.center_x == 150.5
        assert result.center_y == 250.5
        assert result.confidence == 0.87


class TestDefaultRegions:
    def test_has_six_regions(self):
        assert len(DEFAULT_REGIONS) == 6

    def test_region_names(self):
        names = {r.name for r in DEFAULT_REGIONS}
        expected = {"top", "top_left", "top_right", "bottom_left", "bottom", "bottom_right"}
        assert names == expected


@pytest.fixture(scope="module")
def ocr_engine():
    return EasyOCREngine(gpu=False)


@pytest.fixture(scope="module")
def expected_results():
    return load_expected_results()


def get_test_images():
    if not IMAGES_DIR.exists():
        return []
    return sorted(IMAGES_DIR.glob("testscreen*.png"))


class TestIntegration:
    def test_analyze_screenshot_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            analyze_screenshot("nonexistent.png")

    def test_analyze_returns_all_positions(self, ocr_engine):
        images = get_test_images()
        if not images:
            pytest.skip("No test images available")

        results = analyze_screenshot(images[0], ocr_engine)
        expected_keys = {"top", "top_left", "top_right", "bottom_left", "bottom", "bottom_right"}
        assert set(results.keys()) == expected_keys

    @pytest.mark.parametrize("image_path", get_test_images(), ids=lambda p: p.name)
    def test_analyze_matches_expected(self, ocr_engine, expected_results, image_path):
        image_key = image_path.stem
        if image_key not in expected_results:
            pytest.skip(f"No expected results for {image_key}")

        expected = expected_results[image_key]
        if all(v == "" for v in expected.values()):
            pytest.skip(f"Expected results not filled in for {image_key}")

        results = analyze_screenshot(image_path, ocr_engine)

        for position, expected_name in expected.items():
            ocr_name = results.get(position, "")
            assert ocr_name == expected_name, (
                f"{image_key} {position}: expected '{expected_name}', got '{ocr_name}'"
            )
