"""Hand history de-anonymizer package.

Converts GGPoker hand histories with encrypted player IDs to use real player names
extracted from screenshots.
"""
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
    convert_hands_with_propagation,
    write_converted_file,
    write_skipped_file,
)
from hand_history.seat_mapping import (
    TableType,
    InvalidTableTypeError,
    parse_table_type_from_filename,
    POSITION_ORDER_6PLAYER,
    POSITION_ORDER_5PLAYER,
    DEFAULT_SEAT_MAPPINGS,
    load_seat_mapping,
    calculate_seat_mapping,
    calculate_seat_mapping_from_hero,
    position_to_seat,
)

__all__ = [
    "TableType",
    "InvalidTableTypeError",
    "parse_table_type_from_filename",
    "HandHistory",
    "ConversionResult",
    "OcrData",
    "parse_hand",
    "parse_file",
    "find_hand_by_number",
    "convert_hand",
    "convert_hands",
    "convert_hands_with_propagation",
    "write_converted_file",
    "write_skipped_file",
    "load_seat_mapping",
    "position_to_seat",
    "calculate_seat_mapping",
    "calculate_seat_mapping_from_hero",
    "DEFAULT_SEAT_MAPPINGS",
    "POSITION_ORDER_6PLAYER",
    "POSITION_ORDER_5PLAYER",
]
