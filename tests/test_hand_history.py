"""Tests for hand_history module."""
import pytest
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from hand_history import (
    HandHistory,
    ConversionResult,
    parse_hand,
    parse_file,
    find_hand_by_number,
    convert_hand,
    convert_hands,
    write_converted_file,
    write_skipped_file,
    load_seat_mapping,
    position_to_seat,
    DEFAULT_SEAT_MAPPING,
)


SAMPLE_HAND = """Poker Hand #OM262668465: PLO-5 ($5/$10) - 2025/12/21 15:09:46
Table 'PLO-5Platinum1' 6-max Seat #2 is the button
Seat 1: Hero ($1,180.48 in chips)
Seat 2: b3f8e036 ($1,000 in chips)
Seat 3: 4a363869 ($990 in chips)
Seat 5: 242a39be ($1,082.1 in chips)
Seat 6: 5440cd31 ($1,000 in chips)
4a363869: posts small blind $5
242a39be: posts big blind $10
*** HOLE CARDS ***
Dealt to Hero [7d 5c Kh 6c 8c]
5440cd31: folds
Hero: folds
b3f8e036: folds
4a363869: folds
Uncalled bet ($5) returned to 242a39be
*** SHOWDOWN ***
242a39be collected $10 from pot
*** SUMMARY ***
Total pot $10 | Rake $0
Seat 1: Hero folded before Flop (didn't bet)
Seat 2: b3f8e036 (button) folded before Flop (didn't bet)
Seat 3: 4a363869 (small blind) folded before Flop
Seat 5: 242a39be (big blind) collected ($10)
Seat 6: 5440cd31 folded before Flop (didn't bet)"""


SAMPLE_HAND_2 = """Poker Hand #OM262668461: PLO-5 ($5/$10) - 2025/12/21 15:09:01
Table 'PLO-5Platinum1' 6-max Seat #1 is the button
Seat 1: Hero ($1,134.73 in chips)
Seat 2: b3f8e036 ($300.31 in chips)
Seat 3: 4a363869 ($1,000 in chips)
4a363869: posts small blind $5
*** HOLE CARDS ***
Dealt to Hero [7h Jc Ks 8c Qh]
*** SUMMARY ***
Seat 1: Hero (button) won ($80.75)"""


class TestParseHand:
    def test_parses_hand_number(self):
        hand = parse_hand(SAMPLE_HAND)
        assert hand.hand_number == "OM262668465"

    def test_parses_table_name(self):
        hand = parse_hand(SAMPLE_HAND)
        assert hand.table_name == "PLO-5Platinum1"

    def test_parses_timestamp(self):
        hand = parse_hand(SAMPLE_HAND)
        assert hand.timestamp == datetime(2025, 12, 21, 15, 9, 46)

    def test_parses_seats(self):
        hand = parse_hand(SAMPLE_HAND)
        assert hand.seats == {
            1: "Hero",
            2: "b3f8e036",
            3: "4a363869",
            5: "242a39be",
            6: "5440cd31",
        }

    def test_stores_raw_text(self):
        hand = parse_hand(SAMPLE_HAND)
        assert hand.raw_text == SAMPLE_HAND

    def test_returns_none_for_invalid_header(self):
        assert parse_hand("Invalid hand text") is None

    def test_returns_none_for_empty_string(self):
        assert parse_hand("") is None

    def test_returns_none_for_missing_table(self):
        invalid = "Poker Hand #OM123: PLO-5 ($5/$10) - 2025/12/21 15:09:46\nSeat 1: Hero ($100 in chips)"
        assert parse_hand(invalid) is None


class TestHandHistory:
    def test_is_immutable(self):
        hand = parse_hand(SAMPLE_HAND)
        with pytest.raises(FrozenInstanceError):
            hand.hand_number = "OM999"

    def test_get_player_at_seat(self):
        hand = parse_hand(SAMPLE_HAND)
        assert hand.get_player_at_seat(1) == "Hero"
        assert hand.get_player_at_seat(2) == "b3f8e036"
        assert hand.get_player_at_seat(4) is None

    def test_get_seat_for_player(self):
        hand = parse_hand(SAMPLE_HAND)
        assert hand.get_seat_for_player("Hero") == 1
        assert hand.get_seat_for_player("b3f8e036") == 2
        assert hand.get_seat_for_player("unknown") is None


class TestParseFile:
    def test_parses_multiple_hands(self):
        content = SAMPLE_HAND + "\n\n\n" + SAMPLE_HAND_2
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "hands.txt"
            path.write_text(content)
            hands = parse_file(path)
            assert len(hands) == 2
            assert hands[0].hand_number == "OM262668465"
            assert hands[1].hand_number == "OM262668461"

    def test_raises_for_missing_file(self):
        with pytest.raises(FileNotFoundError):
            parse_file(Path("/nonexistent/file.txt"))

    def test_handles_empty_file(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.txt"
            path.write_text("")
            hands = parse_file(path)
            assert hands == []


class TestFindHandByNumber:
    def test_finds_existing_hand(self):
        hand1 = parse_hand(SAMPLE_HAND)
        hand2 = parse_hand(SAMPLE_HAND_2)
        hands = [hand1, hand2]
        found = find_hand_by_number(hands, "OM262668461")
        assert found == hand2

    def test_returns_none_for_missing(self):
        hand = parse_hand(SAMPLE_HAND)
        assert find_hand_by_number([hand], "OM999") is None

    def test_handles_empty_list(self):
        assert find_hand_by_number([], "OM123") is None


class TestConvertHand:
    def test_replaces_encrypted_ids(self):
        hand = parse_hand(SAMPLE_HAND)
        seat_to_name = {2: "RealPlayer1", 3: "RealPlayer2"}
        result = convert_hand(hand, seat_to_name)
        assert result.success
        assert "RealPlayer1" in result.converted_text
        assert "RealPlayer2" in result.converted_text
        assert "b3f8e036" not in result.converted_text
        assert "4a363869" not in result.converted_text

    def test_preserves_hero(self):
        hand = parse_hand(SAMPLE_HAND)
        seat_to_name = {1: "SomeOtherName"}
        result = convert_hand(hand, seat_to_name)
        assert "Hero" in result.converted_text

    def test_skips_empty_names(self):
        hand = parse_hand(SAMPLE_HAND)
        seat_to_name = {2: "EMPTY", 3: "RealPlayer"}
        result = convert_hand(hand, seat_to_name)
        assert "b3f8e036" in result.converted_text
        assert "RealPlayer" in result.converted_text

    def test_tracks_replacements(self):
        hand = parse_hand(SAMPLE_HAND)
        seat_to_name = {2: "Player1", 3: "Player2"}
        result = convert_hand(hand, seat_to_name)
        assert result.replacements == {
            "b3f8e036": "Player1",
            "4a363869": "Player2",
        }

    def test_replaces_all_occurrences(self):
        hand = parse_hand(SAMPLE_HAND)
        seat_to_name = {3: "SmallBlindPlayer"}
        result = convert_hand(hand, seat_to_name)
        assert result.converted_text.count("SmallBlindPlayer") >= 3


class TestConvertHands:
    def test_converts_matching_hands(self):
        hand = parse_hand(SAMPLE_HAND)
        hand_data = {"OM262668465": {2: "Player1"}}
        results = convert_hands([hand], hand_data)
        assert len(results) == 1
        assert results[0].success

    def test_marks_unmatched_as_failed(self):
        hand = parse_hand(SAMPLE_HAND)
        hand_data = {}
        results = convert_hands([hand], hand_data)
        assert len(results) == 1
        assert not results[0].success
        assert "No matching screenshot" in results[0].error


class TestWriteFiles:
    def test_write_converted_file(self):
        result = ConversionResult(
            hand_number="OM123",
            success=True,
            original_text="original",
            converted_text="converted text",
        )
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "output.txt"
            write_converted_file([result], path)
            assert path.exists()
            assert path.read_text() == "converted text"

    def test_write_converted_skips_failed(self):
        result = ConversionResult(
            hand_number="OM123",
            success=False,
            original_text="original",
            error="Some error",
        )
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.txt"
            write_converted_file([result], path)
            assert not path.exists()

    def test_write_skipped_file(self):
        result = ConversionResult(
            hand_number="OM123",
            success=False,
            original_text="original hand",
            error="No screenshot",
        )
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skipped.txt"
            write_skipped_file([result], path)
            assert path.exists()
            content = path.read_text()
            assert "OM123" in content
            assert "No screenshot" in content
            assert "original hand" in content


class TestSeatMapping:
    def test_default_seat_mapping(self):
        assert DEFAULT_SEAT_MAPPING == {
            "bottom": 1,
            "bottom_left": 2,
            "top_left": 3,
            "top": 4,
            "top_right": 5,
            "bottom_right": 6,
        }

    def test_load_seat_mapping_returns_default_for_missing_file(self):
        mapping = load_seat_mapping(Path("/nonexistent/path.toml"))
        assert mapping == DEFAULT_SEAT_MAPPING

    def test_load_seat_mapping_from_file(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.toml"
            path.write_text("[seats]\nbottom = 6\ntop = 1")
            mapping = load_seat_mapping(path)
            assert mapping["bottom"] == 6
            assert mapping["top"] == 1

    def test_position_to_seat(self):
        position_names = {
            "bottom": "Hero",
            "top_left": "Player1",
            "bottom_right": "Player2",
        }
        result = position_to_seat(position_names)
        assert result == {1: "Hero", 3: "Player1", 6: "Player2"}

    def test_position_to_seat_with_custom_mapping(self):
        position_names = {"bottom": "Hero"}
        custom_mapping = {"bottom": 5}
        result = position_to_seat(position_names, custom_mapping)
        assert result == {5: "Hero"}

    def test_position_to_seat_ignores_unknown_positions(self):
        position_names = {"unknown_position": "Player"}
        result = position_to_seat(position_names)
        assert result == {}
