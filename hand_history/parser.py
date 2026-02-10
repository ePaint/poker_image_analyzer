"""Hand history parsing for GGPoker hand files."""
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


HAND_HEADER_PATTERN = re.compile(
    r"^Poker Hand #(OM\d+): .+ - (\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})$"
)
TABLE_PATTERN = re.compile(r"^Table '([^']+)' 6-max Seat #\d+ is the button$")
SEAT_PATTERN = re.compile(r"^Seat (\d+): (.+) \(\$[\d,.]+ in chips\)$")


@dataclass(frozen=True)
class HandHistory:
    """Parsed hand history data."""

    hand_number: str
    table_name: str
    timestamp: datetime
    seats: dict[int, str]
    raw_text: str

    def get_player_at_seat(self, seat: int) -> str | None:
        """Get player name at given seat number."""
        return self.seats.get(seat)

    def get_seat_for_player(self, player: str) -> int | None:
        """Get seat number for given player name."""
        for seat, name in self.seats.items():
            if name == player:
                return seat
        return None


def parse_hand(text: str) -> HandHistory | None:
    """Parse a single hand history text block.

    Args:
        text: Raw text of a single hand history

    Returns:
        HandHistory object or None if parsing fails
    """
    lines = text.strip().split("\n")
    if not lines:
        return None

    header_match = HAND_HEADER_PATTERN.match(lines[0])
    if not header_match:
        return None

    hand_number = header_match.group(1)
    timestamp = datetime.strptime(header_match.group(2), "%Y/%m/%d %H:%M:%S")

    table_name = ""
    seats: dict[int, str] = {}

    for line in lines[1:]:
        if line.startswith("*** "):
            break

        table_match = TABLE_PATTERN.match(line)
        if table_match:
            table_name = table_match.group(1)
            continue

        seat_match = SEAT_PATTERN.match(line)
        if seat_match:
            seat_num = int(seat_match.group(1))
            player_name = seat_match.group(2)
            seats[seat_num] = player_name

    if not hand_number or not table_name:
        return None

    return HandHistory(
        hand_number=hand_number,
        table_name=table_name,
        timestamp=timestamp,
        seats=seats,
        raw_text=text,
    )


def parse_file(path: Path) -> list[HandHistory]:
    """Parse a hand history file containing multiple hands.

    Args:
        path: Path to the hand history file

    Returns:
        List of parsed HandHistory objects
    """
    if not path.exists():
        raise FileNotFoundError(f"Hand history file not found: {path}")

    content = path.read_text(encoding="utf-8")
    hand_blocks = re.split(r"\n{2,}(?=Poker Hand #)", content)

    hands = []
    for block in hand_blocks:
        block = block.strip()
        if not block:
            continue
        hand = parse_hand(block)
        if hand:
            hands.append(hand)

    return hands


def find_hand_by_number(hands: list[HandHistory], hand_number: str) -> HandHistory | None:
    """Find a hand by its hand number.

    Args:
        hands: List of parsed hands
        hand_number: Hand number to find (e.g., "OM262668465")

    Returns:
        HandHistory if found, None otherwise
    """
    for hand in hands:
        if hand.hand_number == hand_number:
            return hand
    return None
