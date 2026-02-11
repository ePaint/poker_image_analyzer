"""Hand history conversion - replaces encrypted IDs with real player names."""
import re
from dataclasses import dataclass, field
from pathlib import Path

from hand_history.parser import HandHistory


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
) -> ConversionResult:
    """Convert a single hand by replacing encrypted IDs with real names.

    Args:
        hand: Parsed hand history
        seat_to_name: Mapping from seat number to real player name

    Returns:
        ConversionResult with converted text or error
    """
    text = hand.raw_text
    replacements: dict[str, str] = {}

    for seat, encrypted_id in hand.seats.items():
        if encrypted_id == "Hero":
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


def write_converted_file(
    results: list[ConversionResult],
    output_path: Path,
) -> None:
    """Write successfully converted hands to output file.

    Args:
        results: List of conversion results
        output_path: Path to write converted hands
    """
    successful = [r for r in results if r.success and r.converted_text]

    if not successful:
        return

    content = "\n\n\n".join(r.converted_text for r in successful)
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
