from pathlib import Path
import tomllib
import tomli_w

from image_analyzer.engines import OCREngine
from settings.models import EngineName

SETTINGS_PATH = Path.cwd() / "settings.toml"
DEFAULT_SETTINGS = {"ocr": {"engine": EngineName.EASYOCR.value, "gpu": False}}
TESSERACT_BIN_DIR = Path(__file__).parent.parent / "image_analyzer" / "bin" / "tesseract"


def load_settings() -> dict:
    """Load settings.toml from project root, return defaults if not found."""
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, "rb") as f:
            return tomllib.load(f)
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    """Save settings to settings.toml."""
    with open(SETTINGS_PATH, "wb") as f:
        tomli_w.dump(settings, f)


def get_engine() -> OCREngine:
    """Factory function to create the configured OCR engine."""
    settings = load_settings()
    ocr_settings = settings.get("ocr", {})
    engine_name = ocr_settings.get("engine", EngineName.EASYOCR.value)
    gpu = ocr_settings.get("gpu", False)

    if engine_name == EngineName.EASYOCR.value:
        try:
            from image_analyzer.engines.easyocr_engine import EasyOCREngine
        except ImportError:
            raise ImportError(
                "EasyOCR engine requires easyocr. "
                "Install with: uv pip install oitnow2[easyocr]"
            )
        return EasyOCREngine(gpu=gpu)
    elif engine_name == EngineName.TESSERACT.value:
        try:
            from image_analyzer.engines.tesseract_engine import TesseractEngine
            import pytesseract
        except ImportError:
            raise ImportError(
                "Tesseract engine requires pytesseract. "
                "Install with: uv pip install oitnow2[tesseract]"
            )
        tesseract_exe = TESSERACT_BIN_DIR / "tesseract.exe"
        if tesseract_exe.exists():
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_exe)
        return TesseractEngine()
    else:
        raise ValueError(f"Unknown OCR engine: {engine_name}")
