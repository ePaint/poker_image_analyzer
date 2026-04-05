"""Hand history conversion - replaces encrypted IDs with real player names."""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

from hand_history.parser import HandHistory
from hand_history.seat_mapping import TableType, position_to_seat


class OcrData(TypedDict, total=False):
    """OCR data from screenshot processing."""
    position_names: dict[str, str]
    table_type: str
    button_position: str | None


@dataclass
class ConversionResult:
    """Result of converting a single hand."""

    hand_number: str
    success: bool
    original_text: str
    converted_text: str | None = None
    error: str | None = None
    replacements: dict[str, str] = field(default_factory=dict)


def convert_hand(
    hand: HandHistory,
    seat_to_name: dict[int, str],
    hero_seat: int | None = None,
) -> ConversionResult:
    """Convert a single hand by replacing encrypted IDs with real names.

    Args:
        hand: Parsed hand history
        seat_to_name: Mapping from seat number to real player name
        hero_seat: Hero's seat number (skip this seat from conversion)

    Returns:
        ConversionResult with converted text or error
    """
    text = hand.raw_text
    replacements: dict[str, str] = {}

    for seat, encrypted_id in hand.seats.items():
        # Skip hero: by seat if provided, otherwise by name "Hero" for backwards compat
        if hero_seat is not None:
            if seat == hero_seat:
                continue
        elif encrypted_id == "Hero":
            continue

        real_name = seat_to_name.get(seat)
        if real_name and real_name != "EMPTY":
            replacements[encrypted_id] = real_name
            text = re.sub(
                rf"\b{re.escape(encrypted_id)}\b",
                real_name,
                text,
            )

    return ConversionResult(
        hand_number=hand.hand_number,
        success=True,
        original_text=hand.raw_text,
        converted_text=text,
        replacements=replacements,
    )


def convert_hands(
    hands: list[HandHistory],
    hand_number_to_seats: dict[str, dict[int, str]],
) -> list[ConversionResult]:
    """Convert multiple hands using screenshot data.

    Args:
        hands: List of parsed hand histories
        hand_number_to_seats: Mapping from hand number to seat->name mapping

    Returns:
        List of ConversionResult objects
    """
    results = []

    for hand in hands:
        seat_data = hand_number_to_seats.get(hand.hand_number)

        if seat_data is None:
            results.append(ConversionResult(
                hand_number=hand.hand_number,
                success=False,
                original_text=hand.raw_text,
                error="No matching screenshot found",
            ))
            continue

        result = convert_hand(hand, seat_data)
        results.append(result)

    return results


def convert_hands_with_propagation(
    hands: list[HandHistory],
    hand_number_to_ocr: dict[str, OcrData],
) -> list[ConversionResult]:
    """Convert hands, propagating mappings to same-table hands without screenshots.

    Learns encrypted_id -> real_name mappings from hands with screenshots and
    applies them to ALL hands from the same table.

    Also replaces "Hero" with the real player name when detected from OCR data.

    Args:
        hands: List of parsed hand histories
        hand_number_to_ocr: Mapping from hand number to OCR data

    Returns:
        List of ConversionResult objects
    """
    # Step 1: Build encrypted_id -> name mappings per table from hands with screenshots
    # Also track Hero's real name and seat per table
    table_mappings: dict[str, dict[str, str]] = {}  # table_name -> {encrypted_id: real_name}
    table_hero_names: dict[str, str] = {}  # table_name -> hero_real_name
    table_hero_seats: dict[str, int] = {}  # table_name -> hero's seat number
    table_hero_player_names: dict[str, str] = {}  # table_name -> hero's name in hand history

    for hand in hands:
        ocr_data = hand_number_to_ocr.get(hand.hand_number)
        if ocr_data is None:
            continue

        # Find Hero's seat: try OCR bottom match first, fall back to literal "Hero"
        hero_seat = None
        hero_player_name = None
        bottom_name = ocr_data.get("position_names", {}).get("bottom", "")
        if bottom_name:
            for seat, player in hand.seats.items():
                if player.lower() == bottom_name.lower():
                    hero_seat = seat
                    hero_player_name = player
                    break
        if hero_seat is None:
            hero_seat = hand.get_seat_for_player("Hero")
            if hero_seat is not None:
                hero_player_name = "Hero"

        seat_to_name = position_to_seat(
            ocr_data.get("position_names", {}),
            ocr_data.get("table_type", TableType.SIX_PLAYER),
            screenshot_button_position=ocr_data.get("button_position"),
            hand_button_seat=hand.button_seat if hand.button_seat else None,
            hero_seat=hero_seat,
        )

        if hand.table_name not in table_mappings:
            table_mappings[hand.table_name] = {}

        # Track hero's seat and name for this table
        if hero_seat is not None:
            table_hero_seats[hand.table_name] = hero_seat
            if hero_player_name:
                table_hero_player_names[hand.table_name] = hero_player_name
            # Store Hero's real name from OCR
            hero_real_name = seat_to_name.get(hero_seat)
            if hero_real_name and hero_real_name != "EMPTY":
                table_hero_names[hand.table_name] = hero_real_name

        for seat, encrypted_id in hand.seats.items():
            if seat == hero_seat:
                continue
            real_name = seat_to_name.get(seat)
            if real_name and real_name != "EMPTY":
                table_mappings[hand.table_name][encrypted_id] = real_name

    # Step 2: Convert ALL hands using table mappings
    results = []
    for hand in hands:
        encrypted_to_name = table_mappings.get(hand.table_name, {})
        hero_real_name = table_hero_names.get(hand.table_name)
        hero_seat = table_hero_seats.get(hand.table_name)
        hero_player_name = table_hero_player_names.get(hand.table_name)

        if not encrypted_to_name and not hero_real_name:
            results.append(ConversionResult(
                hand_number=hand.hand_number,
                success=False,
                original_text=hand.raw_text,
                error="No screenshot data for this table",
            ))
            continue

        # Apply replacements
        text = hand.raw_text
        replacements: dict[str, str] = {}

        # Replace encrypted IDs with real names (skip hero's seat)
        for seat, encrypted_id in hand.seats.items():
            if seat == hero_seat:
                continue
            real_name = encrypted_to_name.get(encrypted_id)
            if real_name:
                replacements[encrypted_id] = real_name
                text = re.sub(rf"\b{re.escape(encrypted_id)}\b", real_name, text)

        # Replace hero's name (whatever it is: "Hero" or custom) with real name
        if hero_real_name and hero_player_name:
            replacements[hero_player_name] = hero_real_name
            text = re.sub(rf"\b{re.escape(hero_player_name)}\b", hero_real_name, text)

        results.append(ConversionResult(
            hand_number=hand.hand_number,
            success=True,
            original_text=hand.raw_text,
            converted_text=text,
            replacements=replacements,
        ))

    return results


def write_converted_file(
    results: list[ConversionResult],
    output_path: Path,
) -> None:
    """Write successfully converted hands to output file.

    Args:
        results: List of conversion results
        output_path: Path to write converted hands
    """
    texts = [r.converted_text for r in results if r.success and r.converted_text]

    if not texts:
        return

    content = "\n\n\n".join(texts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def write_skipped_file(
    results: list[ConversionResult],
    output_path: Path,
) -> None:
    """Write skipped/failed hands with error log.

    Args:
        results: List of conversion results
        output_path: Path to write skipped hands
    """
    failed = [r for r in results if not r.success]

    if not failed:
        return

    lines = []
    for r in failed:
        lines.append(f"# Hand {r.hand_number}: {r.error}")
        lines.append(r.original_text)
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
