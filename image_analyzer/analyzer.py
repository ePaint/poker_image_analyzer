from pathlib import Path

import cv2
import numpy as np

from image_analyzer.models import PlayerRegion
from image_analyzer.engines import OCREngine
from image_analyzer.upscalers import preprocess_region


DEFAULT_REGIONS = (
    PlayerRegion("top", 348, 152),
    PlayerRegion("top_left", 29, 234),
    PlayerRegion("top_right", 666, 233),
    PlayerRegion("bottom_left", 29, 459),
    PlayerRegion("bottom", 348, 565),
    PlayerRegion("bottom_right", 666, 459),
)


def run_ocr_on_region(
    engine: OCREngine,
    image: np.ndarray,
    region: PlayerRegion
) -> str:
    preprocessed = preprocess_region(image, region)
    results = engine.read(preprocessed)
    if not results:
        return ""
    filtered = [r for r in results if len(r.text) >= 3]
    if not filtered:
        filtered = results
    best = max(filtered, key=lambda r: (len(r.text), r.confidence))
    return best.text


def analyze_image(
    image: np.ndarray,
    engine: OCREngine,
    regions: tuple[PlayerRegion, ...] = DEFAULT_REGIONS
) -> dict[str, str]:
    return {region.name: run_ocr_on_region(engine, image, region) for region in regions}


def analyze_screenshot(
    image_path: str | Path,
    engine: OCREngine | None = None,
    regions: tuple[PlayerRegion, ...] = DEFAULT_REGIONS
) -> dict[str, str]:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not load image: {path}")

    if engine is None:
        from settings import get_engine
        engine = get_engine()

    return analyze_image(image, engine, regions)
