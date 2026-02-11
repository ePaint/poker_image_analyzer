"""Hand history de-anonymizer package.

Converts GGPoker hand histories with encrypted player IDs to use real player names
extracted from screenshots.
"""
import tomllib
from pathlib import Path
from typing import Literal

TableType = Literal["ggpoker", "natural8"]

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

_SEAT_MAPPING_PATH = Path(__file__).parent / "seat_mapping.toml"

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


def load_seat_mapping(table_type: TableType = "ggpoker", path: Path | None = None) -> dict[str, int]:
    """Load seat mapping for a specific table type.

    Args:
        table_type: Table type ("ggpoker" or "natural8")
        path: Path to seat_mapping.toml (uses default if None)

    Returns:
        Dict mapping position name to seat number
    """
    config_path = path or _SEAT_MAPPING_PATH
    default = DEFAULT_SEAT_MAPPINGS.get(table_type, DEFAULT_SEAT_MAPPINGS["ggpoker"])

    if not config_path.exists():
        return default.copy()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    return data.get(table_type, default.copy())


def position_to_seat(
    position_names: dict[str, str],
    table_type: TableType = "ggpoker",
    seat_mapping: dict[str, int] | None = None,
) -> dict[int, str]:
    """Convert position-based names to seat-based names.

    Args:
        position_names: Dict from position name to player name (from OCR)
        table_type: Table type ("ggpoker" or "natural8")
        seat_mapping: Position to seat number mapping (loads default if None)

    Returns:
        Dict from seat number to player name
    """
    mapping = seat_mapping or load_seat_mapping(table_type)
    result: dict[int, str] = {}

    for position, player_name in position_names.items():
        seat = mapping.get(position)
        if seat is not None:
            result[seat] = player_name

    return result


__all__ = [
    "TableType",
    "HandHistory",
    "ConversionResult",
    "parse_hand",
    "parse_file",
    "find_hand_by_number",
    "convert_hand",
    "convert_hands",
    "write_converted_file",
    "write_skipped_file",
    "load_seat_mapping",
    "position_to_seat",
    "DEFAULT_SEAT_MAPPINGS",
]
