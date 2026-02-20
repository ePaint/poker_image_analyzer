"""Tests for hand_history module."""
import pytest
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock
import sys

from hand_history import (
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
    DEFAULT_SEAT_MAPPINGS,
)
from image_analyzer.ocr_dump import parse_ocr_dump, CURRENT_VERSION

TESTS_DIR = Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / "fixtures"


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
    def test_default_seat_mappings_6_player(self):
        assert DEFAULT_SEAT_MAPPINGS["6_player"] == {
            "bottom": 1,
            "bottom_left": 2,
            "top_left": 3,
            "top": 4,
            "top_right": 5,
            "bottom_right": 6,
        }

    def test_default_seat_mappings_5_player(self):
        assert DEFAULT_SEAT_MAPPINGS["5_player"] == {
            "bottom": 1,
            "left": 2,
            "top_left": 3,
            "top_right": 5,
            "right": 6,
        }

    def test_load_seat_mapping_returns_default_for_missing_file(self):
        mapping = load_seat_mapping("6_player", Path("/nonexistent/path.toml"))
        assert mapping == DEFAULT_SEAT_MAPPINGS["6_player"]

    def test_load_seat_mapping_5_player_for_missing_file(self):
        mapping = load_seat_mapping("5_player", Path("/nonexistent/path.toml"))
        assert mapping == DEFAULT_SEAT_MAPPINGS["5_player"]

    def test_load_seat_mapping_from_file(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.toml"
            path.write_text("[6_player]\nbottom = 6\ntop = 1")
            mapping = load_seat_mapping("6_player", path)
            assert mapping["bottom"] == 6
            assert mapping["top"] == 1

    def test_position_to_seat_6_player(self):
        position_names = {
            "bottom": "Hero",
            "top_left": "Player1",
            "bottom_right": "Player2",
        }
        result = position_to_seat(position_names, "6_player")
        assert result == {1: "Hero", 3: "Player1", 6: "Player2"}

    def test_position_to_seat_5_player(self):
        position_names = {
            "bottom": "Hero",
            "left": "Player1",
            "right": "Player2",
        }
        result = position_to_seat(position_names, "5_player")
        assert result == {1: "Hero", 2: "Player1", 6: "Player2"}

    def test_position_to_seat_with_custom_mapping(self):
        position_names = {"bottom": "Hero"}
        custom_mapping = {"bottom": 5}
        result = position_to_seat(position_names, "6_player", custom_mapping)
        assert result == {5: "Hero"}

    def test_position_to_seat_ignores_unknown_positions(self):
        position_names = {"unknown_position": "Player"}
        result = position_to_seat(position_names, "6_player")
        assert result == {}


class TestParseOcrDump:
    def test_parse_v1_format(self):
        """Test parsing v1 format (keyed by hand_number only)."""
        toml_content = """
[metadata]
version = "v1"
total_successful = 2

[results.OM123456]
filename = "test1.png"
table_type = "6_player"

[results.OM123456.positions]
bottom = "Hero"
top_left = "Player2"
top_right = "Player3"

[results.OM789012]
filename = "test2.png"
table_type = "5_player"

[results.OM789012.positions]
bottom = "Hero"
left = "Player4"
"""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ocr_dump.toml"
            path.write_text(toml_content)

            result = parse_ocr_dump(path)

            assert len(result) == 2
            assert "OM123456" in result
            assert "OM789012" in result
            assert result["OM123456"][1] == "Hero"
            assert result["OM123456"][3] == "Player2"
            assert result["OM123456"][5] == "Player3"
            assert result["OM789012"][1] == "Hero"
            assert result["OM789012"][2] == "Player4"

    def test_parse_v2_format(self):
        """Test parsing v2 format (keyed by hand_datetime composite)."""
        toml_content = """
[metadata]
version = "v2"
total_successful = 2

[results.OM123456_2024-01-15_10-30_AM]
hand_number = "OM123456"
filename = "2024-01-15_ 10-30_AM_$5_$10_#123456.png"
table_type = "6_player"

[results.OM123456_2024-01-15_10-30_AM.positions]
bottom = "Hero"
top_left = "Player2"
top_right = "Player3"

[results.OM789012_2024-01-15_11-00_AM]
hand_number = "OM789012"
filename = "2024-01-15_ 11-00_AM_$5_$10_#789012.png"
table_type = "5_player"

[results.OM789012_2024-01-15_11-00_AM.positions]
bottom = "Hero"
left = "Player4"
"""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ocr_dump.toml"
            path.write_text(toml_content)

            result = parse_ocr_dump(path)

            assert len(result) == 2
            assert "OM123456" in result
            assert "OM789012" in result
            assert result["OM123456"][1] == "Hero"
            assert result["OM123456"][3] == "Player2"
            assert result["OM123456"][5] == "Player3"
            assert result["OM789012"][1] == "Hero"
            assert result["OM789012"][2] == "Player4"

    def test_parse_defaults_to_v1_without_version(self):
        """Test that files without version field parse as v1."""
        toml_content = """
[metadata]
total_successful = 1

[results.OM123456]
filename = "test1.png"
table_type = "6_player"

[results.OM123456.positions]
bottom = "Hero"
"""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ocr_dump.toml"
            path.write_text(toml_content)

            result = parse_ocr_dump(path)

            assert "OM123456" in result
            assert result["OM123456"][1] == "Hero"

    def test_parse_empty_results(self):
        """Test parsing TOML with no results."""
        toml_content = """
[metadata]
version = "v1"
total_successful = 0
"""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.toml"
            path.write_text(toml_content)

            result = parse_ocr_dump(path)
            assert result == {}

    def test_v2_duplicate_hand_numbers_last_wins(self):
        """Test v2: when same hand_number appears multiple times, last entry wins."""
        toml_content = """
[metadata]
version = "v2"
total_successful = 2

[results.OM123456_2024-01-15_10-30_AM]
hand_number = "OM123456"
filename = "earlier.png"
table_type = "6_player"

[results.OM123456_2024-01-15_10-30_AM.positions]
bottom = "EarlierPlayer"

[results.OM123456_2024-01-15_11-00_AM]
hand_number = "OM123456"
filename = "later.png"
table_type = "6_player"

[results.OM123456_2024-01-15_11-00_AM.positions]
bottom = "LaterPlayer"
"""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ocr_dump.toml"
            path.write_text(toml_content)

            result = parse_ocr_dump(path)

            assert len(result) == 1
            assert result["OM123456"][1] == "LaterPlayer"

    def test_current_version_is_v2(self):
        """Verify current version constant is v2."""
        assert CURRENT_VERSION == "v2"


@pytest.fixture
def mock_anthropic():
    """Fixture to mock the anthropic module."""
    mock_module = MagicMock()
    mock_client = MagicMock()
    mock_module.Anthropic.return_value = mock_client

    with patch.dict(sys.modules, {"anthropic": mock_module}):
        yield mock_module, mock_client


class TestIntegration:
    """Integration tests for the full conversion workflow."""

    def test_full_conversion_workflow(self, mock_anthropic):
        """Test parsing hands, mapping seats, and converting."""
        fixture_hands = FIXTURES_DIR / "sample_hands.txt"
        if not fixture_hands.exists():
            pytest.skip("Fixture hands not available")

        hands = parse_file(fixture_hands)
        assert len(hands) == 2
        assert hands[0].hand_number == "OM262735460"

        position_names = {
            "bottom": "Hero",
            "bottom_left": "RealPlayer2",
            "top_left": "RealPlayer3",
            "top": "RealPlayer4",
            "top_right": "RealPlayer5",
            "bottom_right": "RealPlayer6",
        }
        seat_names = position_to_seat(position_names, "6_player")

        assert seat_names == {
            1: "Hero",
            2: "RealPlayer2",
            3: "RealPlayer3",
            4: "RealPlayer4",
            5: "RealPlayer5",
            6: "RealPlayer6",
        }

        hand_data = {"OM262735460": seat_names}
        results = convert_hands(hands, hand_data)

        assert len(results) == 2

        matched = results[0]
        assert matched.success
        assert matched.hand_number == "OM262735460"
        assert "RealPlayer2" in matched.converted_text
        assert "ebc711d3" not in matched.converted_text

        unmatched = results[1]
        assert not unmatched.success
        assert "No matching screenshot" in unmatched.error

    def test_write_converted_and_skipped(self):
        """Test writing conversion results to files."""
        fixture_hands = FIXTURES_DIR / "sample_hands.txt"
        if not fixture_hands.exists():
            pytest.skip("Fixture hands not available")

        hands = parse_file(fixture_hands)

        seat_names = {2: "Player2", 3: "Player3", 4: "Player4", 5: "Player5", 6: "Player6"}
        hand_data = {"OM262735460": seat_names}
        results = convert_hands(hands, hand_data)

        with TemporaryDirectory() as tmpdir:
            converted_path = Path(tmpdir) / "converted.txt"
            skipped_path = Path(tmpdir) / "skipped.txt"

            write_converted_file(results, converted_path)
            write_skipped_file(results, skipped_path)

            assert converted_path.exists()
            converted_content = converted_path.read_text()
            assert "Player2" in converted_content
            assert "OM262735460" in converted_content

            assert skipped_path.exists()
            skipped_content = skipped_path.read_text()
            assert "OM262735456" in skipped_content
            assert "No matching screenshot" in skipped_content


class TestIntegrationWithFixtures:
    """Integration tests using real OCR dump and matching hand histories."""

    INTEGRATION_DIR = FIXTURES_DIR / "integration"

    @pytest.mark.parametrize("dump_filename,version", [
        ("ocr_dump_v1.toml", "v1"),
        ("ocr_dump_v2.toml", "v2"),
        ("ocr_dump.toml", "v2"),  # Original fixture is v2
    ])
    def test_parse_ocr_dump_both_versions(self, dump_filename, version):
        """Verify parsing OCR dump files in both v1 and v2 formats."""
        dump_path = self.INTEGRATION_DIR / dump_filename
        if not dump_path.exists():
            pytest.skip(f"Integration fixture {dump_filename} not available")

        hand_data = parse_ocr_dump(dump_path)

        assert len(hand_data) == 570

        # Verify first hand structure (same data regardless of format)
        first_hand = hand_data.get("OM154753304")
        assert first_hand is not None
        # Natural8 positions: left=2, right=6, bottom=1, top_left=3, top_right=5
        assert first_hand[1] == "TeddyKGBEEE"  # bottom
        assert first_hand[2] == "shubidubi"    # left
        assert first_hand[3] == "RussWestbro.."  # top_left
        assert first_hand[5] == "AnnAmbre11"   # top_right
        assert first_hand[6] == "dAvid-H"      # right

    def test_v1_and_v2_produce_identical_hand_data(self):
        """Verify v1 and v2 parsers produce identical output for same data."""
        v1_path = self.INTEGRATION_DIR / "ocr_dump_v1.toml"
        v2_path = self.INTEGRATION_DIR / "ocr_dump_v2.toml"
        if not v1_path.exists() or not v2_path.exists():
            pytest.skip("Integration fixtures not available")

        v1_data = parse_ocr_dump(v1_path)
        v2_data = parse_ocr_dump(v2_path)

        assert len(v1_data) == len(v2_data)
        assert set(v1_data.keys()) == set(v2_data.keys())

        for hand_number in v1_data:
            assert v1_data[hand_number] == v2_data[hand_number], f"Mismatch for {hand_number}"

    def test_full_conversion_with_real_data(self):
        """End-to-end conversion test with real fixtures."""
        dump_path = self.INTEGRATION_DIR / "ocr_dump.toml"
        hands_path = self.INTEGRATION_DIR / "sample_hands.txt"
        if not dump_path.exists() or not hands_path.exists():
            pytest.skip("Integration fixtures not available")

        hand_data = parse_ocr_dump(dump_path)
        hands = parse_file(hands_path)

        assert len(hands) == 10

        results = convert_hands(hands, hand_data)

        # All 10 hands should match
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        assert len(successful) == 10, f"Expected 10 successes, got {len(successful)}. Failed: {[r.hand_number for r in failed]}"
        assert len(failed) == 0

        # Verify specific replacement in first hand (OM154753304)
        # Hand has seats 1, 3, 4 (Hero). OCR: seat1=TeddyKGBEEE, seat3=RussWestbro..
        first_result = next(r for r in results if r.hand_number == "OM154753304")
        assert "TeddyKGBEEE" in first_result.converted_text  # seat 1
        assert "RussWestbro.." in first_result.converted_text  # seat 3
        assert "Hero" in first_result.converted_text  # preserved
        # Encrypted IDs should be gone
        assert "1e1c80c2" not in first_result.converted_text
        assert "8096fcb8" not in first_result.converted_text

    def test_write_files_with_real_data(self):
        """Test writing conversion output files."""
        dump_path = self.INTEGRATION_DIR / "ocr_dump.toml"
        hands_path = self.INTEGRATION_DIR / "sample_hands.txt"
        if not dump_path.exists() or not hands_path.exists():
            pytest.skip("Integration fixtures not available")

        hand_data = parse_ocr_dump(dump_path)
        hands = parse_file(hands_path)
        results = convert_hands(hands, hand_data)

        with TemporaryDirectory() as tmpdir:
            converted_path = Path(tmpdir) / "converted.txt"
            skipped_path = Path(tmpdir) / "skipped.txt"

            write_converted_file(results, converted_path)
            write_skipped_file(results, skipped_path)

            # Converted file should exist with content
            assert converted_path.exists()
            content = converted_path.read_text()
            assert "OM154753304" in content
            assert "shubidubi" in content

            # Skipped file should be empty (all hands matched)
            assert not skipped_path.exists() or skipped_path.read_text() == ""

    def test_position_mapping_natural8(self):
        """Verify Natural8 position names map correctly."""
        positions = {
            "bottom": "Player1",
            "left": "Player2",     # Natural8 specific
            "top_left": "Player3",
            "top_right": "Player4",
            "right": "Player5",    # Natural8 specific
        }
        result = position_to_seat(positions, "5_player")

        assert result[1] == "Player1"  # bottom
        assert result[2] == "Player2"  # left
        assert result[3] == "Player3"  # top_left
        assert result[5] == "Player4"  # top_right
        assert result[6] == "Player5"  # right
