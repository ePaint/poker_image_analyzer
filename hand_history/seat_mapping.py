"""Seat mapping logic for position-to-seat conversion.

Handles the mapping between screenshot positions (bottom, top_left, etc.)
and hand history seat numbers (1-6), accounting for GGPoker's view rotation.
"""
import tomllib
from enum import StrEnum
from pathlib import Path

from settings import get_user_data_path, get_bundled_path


class TableType(StrEnum):
    SIX_PLAYER = "6_player"
    FIVE_PLAYER = "5_player"


class InvalidTableTypeError(Exception):
    """Raised when table type cannot be determined from filename."""
    pass


def parse_table_type_from_filename(filename: str | Path) -> TableType:
    """Parse table type from hand history filename.

    Args:
        filename: Hand history filename (e.g., "GG20260309-1420 - PLO-5Gold2 - 2 - 5 - 6max.txt")

    Returns:
        TableType enum value

    Raises:
        InvalidTableTypeError: If filename doesn't contain 5max or 6max
    """
    name = str(filename).lower()
    if "6max" in name:
        return TableType.SIX_PLAYER
    if "5max" in name:
        return TableType.FIVE_PLAYER
    raise InvalidTableTypeError(f"Cannot determine table type from filename: {filename}")

# Clockwise position order for rotation calculations
POSITION_ORDER_6PLAYER = ("bottom", "bottom_left", "top_left", "top", "top_right", "bottom_right")
POSITION_ORDER_5PLAYER = ("bottom", "left", "top_left", "top_right", "right")

DEFAULT_SEAT_MAPPINGS: dict[TableType, dict[str, int]] = {
    TableType.SIX_PLAYER: {
        "bottom": 1,
        "bottom_left": 2,
        "top_left": 3,
        "top": 4,
        "top_right": 5,
        "bottom_right": 6,
    },
    TableType.FIVE_PLAYER: {
        "bottom": 1,
        "left": 2,
        "top_left": 3,
        "top_right": 4,
        "right": 5,
    },
}

def _get_position_order(table_type: str | TableType) -> tuple[str, ...]:
    """Get position order tuple for the given table type."""
    return POSITION_ORDER_5PLAYER if table_type == TableType.FIVE_PLAYER else POSITION_ORDER_6PLAYER


def _get_table_type(table_type: str | TableType) -> TableType:
    """Convert string to TableType enum."""
    if isinstance(table_type, TableType):
        return table_type
    return TableType(table_type)


def load_seat_mapping(table_type: str | TableType = TableType.SIX_PLAYER) -> dict[str, int]:
    """Load seat mapping for a specific table type. User file takes priority over bundled.

    Args:
        table_type: Table type (TableType.SIX_PLAYER or TableType.FIVE_PLAYER)

    Returns:
        Dict mapping position name to seat number
    """
    tt = _get_table_type(table_type)
    default = DEFAULT_SEAT_MAPPINGS.get(tt, DEFAULT_SEAT_MAPPINGS[TableType.SIX_PLAYER])

    user_path = get_user_data_path("seat_mapping.toml")
    if user_path.exists():
        with open(user_path, "rb") as f:
            data = tomllib.load(f)
        return data.get(tt.value, default.copy())

    bundled_path = get_bundled_path("hand_history", "seat_mapping.toml")
    if bundled_path:
        with open(bundled_path, "rb") as f:
            data = tomllib.load(f)
        return data.get(tt.value, default.copy())

    return default.copy()


def calculate_seat_mapping(
    screenshot_button_position: str,
    hand_button_seat: int,
    table_type: str | TableType = TableType.SIX_PLAYER,
) -> dict[str, int]:
    """Calculate position-to-seat mapping based on button positions.

    Uses the dealer button as an anchor to align screenshot positions with
    hand history seat numbers. The button position in the screenshot tells us
    which screen position corresponds to the button seat in the hand history.

    Args:
        screenshot_button_position: Position name where D button was detected (e.g., "top_left")
        hand_button_seat: Seat number that has the button in hand history (1-6)
        table_type: TableType.SIX_PLAYER or TableType.FIVE_PLAYER

    Returns:
        Dict mapping position name to seat number
    """
    tt = _get_table_type(table_type)
    position_order = _get_position_order(tt)
    num_seats = len(position_order)

    if screenshot_button_position not in position_order:
        return DEFAULT_SEAT_MAPPINGS.get(tt, DEFAULT_SEAT_MAPPINGS[TableType.SIX_PLAYER]).copy()

    button_position_idx = position_order.index(screenshot_button_position)

    mapping: dict[str, int] = {}
    for i, position in enumerate(position_order):
        offset = i - button_position_idx
        seat = ((hand_button_seat - 1 + offset) % num_seats) + 1
        mapping[position] = seat

    return mapping


def calculate_seat_mapping_from_hero(
    hero_seat: int,
    table_type: str | TableType = TableType.SIX_PLAYER,
) -> dict[str, int]:
    """Calculate position-to-seat mapping based on Hero's seat.

    In GGPoker screenshots, Hero is always shown at the "bottom" position,
    regardless of their actual seat number. This function calculates the
    mapping using Hero's seat as the anchor point.

    Use this as fallback when button detection fails.

    Args:
        hero_seat: Seat number where Hero is sitting (1-6)
        table_type: TableType.SIX_PLAYER or TableType.FIVE_PLAYER

    Returns:
        Dict mapping position name to seat number
    """
    tt = _get_table_type(table_type)
    position_order = _get_position_order(tt)
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
    table_type: str | TableType = TableType.SIX_PLAYER,
    seat_mapping: dict[str, int] | None = None,
    screenshot_button_position: str | None = None,
    hand_button_seat: int | None = None,
    hero_seat: int | None = None,
) -> dict[int, str]:
    """Convert position-based names to seat-based names.

    Priority for seat mapping:
    1. Button position (if both screenshot_button_position and hand_button_seat provided)
    2. Hero position (if hero_seat provided - Hero is always at bottom)
    3. Custom seat_mapping (if provided)
    4. Static default mapping (last resort, likely incorrect)

    Args:
        position_names: Dict from position name to player name (from OCR)
        table_type: TableType.SIX_PLAYER or TableType.FIVE_PLAYER
        seat_mapping: Position to seat number mapping (loads default if None)
        screenshot_button_position: Position where D button was detected
        hand_button_seat: Seat number that has the button in hand history
        hero_seat: Seat number where Hero is sitting (fallback when button detection fails)

    Returns:
        Dict from seat number to player name
    """
    tt = _get_table_type(table_type)

    if screenshot_button_position is not None and hand_button_seat is not None:
        # Primary: use button position
        mapping = calculate_seat_mapping(screenshot_button_position, hand_button_seat, tt)
    elif hero_seat is not None:
        # Fallback: use Hero position (Hero is always at bottom)
        mapping = calculate_seat_mapping_from_hero(hero_seat, tt)
    else:
        # Last resort: static mapping
        mapping = seat_mapping or load_seat_mapping(tt)

    result: dict[int, str] = {}

    for position, player_name in position_names.items():
        seat = mapping.get(position)
        if seat is not None:
            result[seat] = player_name

    return result
