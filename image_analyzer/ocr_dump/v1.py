"""OCR dump format version 1.

Keys: hand_number only (e.g., "OM154753304")
Note: Duplicate hand numbers overwrite previous entries.
"""
import tomllib
from datetime import datetime
from pathlib import Path

import tomli_w

from hand_history import DEFAULT_SEAT_MAPPINGS, position_to_seat

VERSION = "v1"


def write(
    results: list[dict],
    errors: list[dict],
    output_path: Path,
    screenshots_folder: Path,
) -> Path:
    """Write OCR results to TOML file.

    Args:
        results: List of dicts with hand_number, filename, table_type, position_names
        errors: List of dicts with filename and error
        output_path: Directory to write the file
        screenshots_folder: Source folder for screenshots

    Returns:
        Path to the written file
    """
    timestamp = datetime.now()
    filename = f"ocr_results_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.toml"
    path = output_path / filename

    path.parent.mkdir(parents=True, exist_ok=True)

    results_dict = {
        r["hand_number"]: {
            "filename": r["filename"],
            "table_type": r["table_type"],
            "positions": r["position_names"],
        }
        for r in sorted(results, key=lambda x: x["filename"])
    }

    data = {
        "metadata": {
            "version": VERSION,
            "timestamp": timestamp.isoformat(),
            "screenshots_folder": str(screenshots_folder),
            "total_successful": len(results_dict),
            "total_errors": len(errors),
        },
        "seat_mappings": DEFAULT_SEAT_MAPPINGS,
        "results": results_dict,
    }

    if errors:
        data["errors"] = {
            e["filename"]: e["error"]
            for e in sorted(errors, key=lambda x: x["filename"])
        }

    with open(path, "wb") as f:
        tomli_w.dump(data, f)

    return path


def parse(path: Path) -> dict[str, dict[int, str]]:
    """Parse OCR dump TOML file into hand_data format.

    Args:
        path: Path to OCR results TOML file

    Returns:
        Dict mapping hand number (e.g., "OM154753304") to seat->name dict
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)

    result: dict[str, dict[int, str]] = {}

    for hand_number, info in data.get("results", {}).items():
        positions = info.get("positions", {})
        table_type = info.get("table_type", "6_player")
        seat_names = position_to_seat(positions, table_type)
        result[hand_number] = seat_names

    return result
