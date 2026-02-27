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
    OcrData,
    convert_hand,
    convert_hands,
    convert_hands_with_ocr,
    write_converted_file,
    write_skipped_file,
)
from settings import get_user_data_path, get_bundled_path

TableType = Literal["6_player", "5_player"]

# Clockwise position order for rotation calculations
POSITION_ORDER_6PLAYER = ("bottom", "bottom_left", "top_left", "top", "top_right", "bottom_right")
POSITION_ORDER_5PLAYER = ("bottom", "left", "top_left", "top_right", "right")

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


def calculate_seat_mapping(
    screenshot_button_position: str,
    hand_button_seat: int,
    table_type: str = "6_player",
) -> dict[str, int]:
    """Calculate position-to-seat mapping based on button positions.

    Uses the dealer button as an anchor to align screenshot positions with
    hand history seat numbers. The button position in the screenshot tells us
    which screen position corresponds to the button seat in the hand history.

    Args:
        screenshot_button_position: Position name where D button was detected (e.g., "top_left")
        hand_button_seat: Seat number that has the button in hand history (1-6)
        table_type: "6_player" or "5_player"

    Returns:
        Dict mapping position name to seat number
    """
    normalized_type = _normalize_table_type(table_type)
    position_order = POSITION_ORDER_5PLAYER if normalized_type == "5_player" else POSITION_ORDER_6PLAYER
    num_seats = len(position_order)

    if screenshot_button_position not in position_order:
        return DEFAULT_SEAT_MAPPINGS.get(normalized_type, DEFAULT_SEAT_MAPPINGS["6_player"]).copy()

    button_position_idx = position_order.index(screenshot_button_position)

    mapping: dict[str, int] = {}
    for i, position in enumerate(position_order):
        offset = i - button_position_idx
        seat = ((hand_button_seat - 1 + offset) % num_seats) + 1
        mapping[position] = seat

    return mapping


def position_to_seat(
    position_names: dict[str, str],
    table_type: str = "6_player",
    seat_mapping: dict[str, int] | None = None,
    screenshot_button_position: str | None = None,
    hand_button_seat: int | None = None,
) -> dict[int, str]:
    """Convert position-based names to seat-based names.

    When screenshot_button_position and hand_button_seat are both provided,
    calculates a dynamic mapping based on the button positions. Otherwise
    uses the static seat_mapping (or loads the default).

    Args:
        position_names: Dict from position name to player name (from OCR)
        table_type: Table type ("6_player" or "5_player", legacy "ggpoker"/"natural8" also supported)
        seat_mapping: Position to seat number mapping (loads default if None)
        screenshot_button_position: Position where D button was detected
        hand_button_seat: Seat number that has the button in hand history

    Returns:
        Dict from seat number to player name
    """
    normalized_type = _normalize_table_type(table_type)

    if screenshot_button_position is not None and hand_button_seat is not None:
        mapping = calculate_seat_mapping(screenshot_button_position, hand_button_seat, normalized_type)
    else:
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
    "OcrData",
    "parse_hand",
    "parse_file",
    "find_hand_by_number",
    "convert_hand",
    "convert_hands",
    "convert_hands_with_ocr",
    "write_converted_file",
    "write_skipped_file",
    "load_seat_mapping",
    "position_to_seat",
    "calculate_seat_mapping",
    "DEFAULT_SEAT_MAPPINGS",
    "POSITION_ORDER_6PLAYER",
    "POSITION_ORDER_5PLAYER",
]
