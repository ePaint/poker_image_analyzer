"""Hand history de-anonymizer package.

Converts GGPoker hand histories with encrypted player IDs to use real player names
extracted from screenshots.
"""
import tomllib
from typing import Literal

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
from settings import get_user_data_path, get_bundled_path

TableType = Literal["6_player", "5_player"]

DEFAULT_SEAT_MAPPINGS: dict[str, dict[str, int]] = {
    "6_player": {
        "bottom": 1,
        "bottom_left": 2,
        "top_left": 3,
        "top": 4,
        "top_right": 5,
        "bottom_right": 6,
    },
    "5_player": {
        "bottom": 1,
        "left": 2,
        "top_left": 3,
        "top_right": 4,
        "right": 5,
    },
}

_TABLE_TYPE_ALIASES = {
    "ggpoker": "6_player",
    "natural8": "5_player",
}


def _normalize_table_type(table_type: str) -> str:
    """Normalize legacy table type names to new format."""
    return _TABLE_TYPE_ALIASES.get(table_type, table_type)


def load_seat_mapping(table_type: str = "6_player") -> dict[str, int]:
    """Load seat mapping for a specific table type. User file takes priority over bundled.

    Args:
        table_type: Table type ("6_player" or "5_player", legacy "ggpoker"/"natural8" also supported)

    Returns:
        Dict mapping position name to seat number
    """
    normalized_type = _normalize_table_type(table_type)
    default = DEFAULT_SEAT_MAPPINGS.get(normalized_type, DEFAULT_SEAT_MAPPINGS["6_player"])

    user_path = get_user_data_path("seat_mapping.toml")
    if user_path.exists():
        with open(user_path, "rb") as f:
            data = tomllib.load(f)
        return data.get(normalized_type, default.copy())

    bundled_path = get_bundled_path("hand_history", "seat_mapping.toml")
    if bundled_path:
        with open(bundled_path, "rb") as f:
            data = tomllib.load(f)
        return data.get(normalized_type, default.copy())

    return default.copy()


def position_to_seat(
    position_names: dict[str, str],
    table_type: str = "6_player",
    seat_mapping: dict[str, int] | None = None,
) -> dict[int, str]:
    """Convert position-based names to seat-based names.

    Args:
        position_names: Dict from position name to player name (from OCR)
        table_type: Table type ("6_player" or "5_player", legacy "ggpoker"/"natural8" also supported)
        seat_mapping: Position to seat number mapping (loads default if None)

    Returns:
        Dict from seat number to player name
    """
    normalized_type = _normalize_table_type(table_type)
    mapping = seat_mapping or load_seat_mapping(normalized_type)
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
