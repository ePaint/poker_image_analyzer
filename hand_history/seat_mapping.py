"""Seat mapping logic for position-to-seat conversion.

Handles the mapping between screenshot positions (bottom, top_left, etc.)
and hand history seat numbers (1-6), accounting for GGPoker's view rotation.
"""
import tomllib
from typing import Literal

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


def _get_position_order(table_type: str) -> tuple[str, ...]:
    """Get position order tuple for the given table type."""
    normalized = _normalize_table_type(table_type)
    return POSITION_ORDER_5PLAYER if normalized == "5_player" else POSITION_ORDER_6PLAYER


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
    position_order = _get_position_order(normalized_type)
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


def calculate_seat_mapping_from_hero(
    hero_seat: int,
    table_type: str = "6_player",
) -> dict[str, int]:
    """Calculate position-to-seat mapping based on Hero's seat.

    In GGPoker screenshots, Hero is always shown at the "bottom" position,
    regardless of their actual seat number. This function calculates the
    mapping using Hero's seat as the anchor point.

    Use this as fallback when button detection fails.

    Args:
        hero_seat: Seat number where Hero is sitting (1-6)
        table_type: "6_player" or "5_player"

    Returns:
        Dict mapping position name to seat number
    """
    normalized_type = _normalize_table_type(table_type)
    position_order = _get_position_order(normalized_type)
    num_seats = len(position_order)

    # Hero is always at "bottom" (index 0 in position_order)
    hero_position_idx = 0

    mapping: dict[str, int] = {}
    for i, position in enumerate(position_order):
        offset = i - hero_position_idx
        seat = ((hero_seat - 1 + offset) % num_seats) + 1
        mapping[position] = seat

    return mapping


def position_to_seat(
    position_names: dict[str, str],
    table_type: str = "6_player",
    seat_mapping: dict[str, int] | None = None,
    screenshot_button_position: str | None = None,
    hand_button_seat: int | None = None,
    hero_seat: int | None = None,
) -> dict[int, str]:
    """Convert position-based names to seat-based names.

    Priority for seat mapping:
    1. Button position (if both screenshot_button_position and hand_button_seat provided)
    2. Hero position (if hero_seat provided - Hero is always at bottom in GGPoker)
    3. Custom seat_mapping (if provided)
    4. Static default mapping (last resort, likely incorrect for GGPoker)

    Args:
        position_names: Dict from position name to player name (from OCR)
        table_type: Table type ("6_player" or "5_player", legacy "ggpoker"/"natural8" also supported)
        seat_mapping: Position to seat number mapping (loads default if None)
        screenshot_button_position: Position where D button was detected
        hand_button_seat: Seat number that has the button in hand history
        hero_seat: Seat number where Hero is sitting (fallback when button detection fails)

    Returns:
        Dict from seat number to player name
    """
    normalized_type = _normalize_table_type(table_type)

    if screenshot_button_position is not None and hand_button_seat is not None:
        # Primary: use button position
        mapping = calculate_seat_mapping(screenshot_button_position, hand_button_seat, normalized_type)
    elif hero_seat is not None:
        # Fallback: use Hero position (Hero is always at bottom in GGPoker)
        mapping = calculate_seat_mapping_from_hero(hero_seat, normalized_type)
    else:
        # Last resort: static mapping
        mapping = seat_mapping or load_seat_mapping(normalized_type)

    result: dict[int, str] = {}

    for position, player_name in position_names.items():
        seat = mapping.get(position)
        if seat is not None:
            result[seat] = player_name

    return result
