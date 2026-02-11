"""Versioned OCR dump writer and parser.

Format versions:
- v1: Keys by hand_number only (duplicates overwrite)
- v2: Keys by hand_datetime composite (preserves all screenshots)
"""
import tomllib
from pathlib import Path
from typing import Literal

from image_analyzer.ocr_dump import v1, v2

OcrDumpVersion = Literal["v1", "v2"]
CURRENT_VERSION: OcrDumpVersion = "v2"

_WRITERS = {
    "v1": v1.write,
    "v2": v2.write,
}

_PARSERS = {
    "v1": v1.parse,
    "v2": v2.parse,
}


def write_ocr_dump(
    results: list[dict],
    errors: list[dict],
    output_path: Path,
    screenshots_folder: Path,
    version: OcrDumpVersion = CURRENT_VERSION,
) -> Path:
    """Write OCR results to TOML file.

    Args:
        results: List of dicts with hand_number, filename, table_type, position_names
        errors: List of dicts with filename and error
        output_path: Directory to write the file
        screenshots_folder: Source folder for screenshots
        version: Format version to use (default: current version)

    Returns:
        Path to the written file
    """
    writer = _WRITERS.get(version)
    if not writer:
        raise ValueError(f"Unknown OCR dump version: {version}")
    return writer(results, errors, output_path, screenshots_folder)


def parse_ocr_dump(path: Path) -> dict[str, dict[int, str]]:
    """Parse OCR dump TOML file into hand_data format.

    Automatically detects version from metadata and uses appropriate parser.

    Args:
        path: Path to OCR results TOML file

    Returns:
        Dict mapping hand number to seat->name dict
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)

    version = data.get("metadata", {}).get("version", "v1")
    parser = _PARSERS.get(version)
    if not parser:
        raise ValueError(f"Unknown OCR dump version: {version}")
    return parser(path)


__all__ = ["write_ocr_dump", "parse_ocr_dump", "OcrDumpVersion", "CURRENT_VERSION"]
