"""Hand history de-anonymizer package.

Converts GGPoker hand histories with encrypted player IDs to use real player names
extracted from screenshots.
"""
import tomllib
from pathlib import Path

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

DEFAULT_SEAT_MAPPING: dict[str, int] = {
    # GGPoker 6-max positions
    "bottom": 1,
    "bottom_left": 2,
    "top_left": 3,
    "top": 4,
    "top_right": 5,
    "bottom_right": 6,
    # Natural8 5-max positions
    "left": 2,
    "right": 6,
}


def load_seat_mapping(path: Path | None = None) -> dict[str, int]:
    """Load seat mapping from TOML configuration.

    Args:
        path: Path to seat_mapping.toml (uses default if None)

    Returns:
        Dict mapping position name to seat number
    """
    config_path = path or _SEAT_MAPPING_PATH
    if not config_path.exists():
        return DEFAULT_SEAT_MAPPING.copy()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    return data.get("seats", DEFAULT_SEAT_MAPPING.copy())


def position_to_seat(
    position_names: dict[str, str],
    seat_mapping: dict[str, int] | None = None,
) -> dict[int, str]:
    """Convert position-based names to seat-based names.

    Args:
        position_names: Dict from position name to player name (from OCR)
        seat_mapping: Position to seat number mapping (loads default if None)

    Returns:
        Dict from seat number to player name
    """
    mapping = seat_mapping or load_seat_mapping()
    result: dict[int, str] = {}

    for position, player_name in position_names.items():
        seat = mapping.get(position)
        if seat is not None:
            result[seat] = player_name

    return result


__all__ = [
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
    "DEFAULT_SEAT_MAPPING",
]
