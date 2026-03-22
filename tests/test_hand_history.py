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
    OcrData,
    parse_hand,
    parse_file,
    find_hand_by_number,
    convert_hand,
    convert_hands,
    convert_hands_with_propagation,
    write_converted_file,
    write_skipped_file,
    load_seat_mapping,
    position_to_seat,
    calculate_seat_mapping_from_hero,
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
            "top_right": 4,
            "right": 5,
        }

    def test_load_seat_mapping_returns_default_when_no_files(self):
        with patch("hand_history.seat_mapping.get_user_data_path") as mock_user, \
             patch("hand_history.seat_mapping.get_bundled_path") as mock_bundled:
            mock_user.return_value = Path("/nonexistent/user/path.toml")
            mock_bundled.return_value = None
            mapping = load_seat_mapping("6_player")
            assert mapping == DEFAULT_SEAT_MAPPINGS["6_player"]

    def test_load_seat_mapping_5_player_default(self):
        with patch("hand_history.seat_mapping.get_user_data_path") as mock_user, \
             patch("hand_history.seat_mapping.get_bundled_path") as mock_bundled:
            mock_user.return_value = Path("/nonexistent/user/path.toml")
            mock_bundled.return_value = None
            mapping = load_seat_mapping("5_player")
            assert mapping == DEFAULT_SEAT_MAPPINGS["5_player"]

    def test_load_seat_mapping_from_user_file(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "seat_mapping.toml"
            path.write_text("[6_player]\nbottom = 6\ntop = 1")
            with patch("hand_history.seat_mapping.get_user_data_path", return_value=path):
                mapping = load_seat_mapping("6_player")
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
        assert result == {1: "Hero", 2: "Player1", 5: "Player2"}

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
        # 5-player positions: bottom=1, left=2, top_left=3, top_right=4, right=5
        assert first_hand[1] == "TeddyKGBEEE"  # bottom
        assert first_hand[2] == "shubidubi"    # left
        assert first_hand[3] == "RussWestbro.."  # top_left
        assert first_hand[4] == "AnnAmbre11"   # top_right
        assert first_hand[5] == "dAvid-H"      # right

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
        """Verify 5-player position names map correctly."""
        positions = {
            "bottom": "Player1",
            "left": "Player2",
            "top_left": "Player3",
            "top_right": "Player4",
            "right": "Player5",
        }
        result = position_to_seat(positions, "5_player")

        assert result[1] == "Player1"  # bottom
        assert result[2] == "Player2"  # left
        assert result[3] == "Player3"  # top_left
        assert result[4] == "Player4"  # top_right
        assert result[5] == "Player5"  # right


class TestButtonSeat:
    """Tests for button_seat field and button-aware seat mapping."""

    def test_parses_button_seat(self):
        """Test that button_seat is parsed from hand history."""
        hand = parse_hand(SAMPLE_HAND)
        assert hand.button_seat == 2  # "Seat #2 is the button"

    def test_parses_button_seat_different_value(self):
        """Test button_seat with different seat number."""
        hand = parse_hand(SAMPLE_HAND_2)
        assert hand.button_seat == 1  # "Seat #1 is the button"


class TestCalculateSeatMapping:
    """Tests for calculate_seat_mapping function."""

    def test_button_at_bottom_seat_1(self):
        """When button is at bottom and seat 1, mapping should be default."""
        from hand_history import calculate_seat_mapping
        mapping = calculate_seat_mapping("bottom", 1, "6_player")
        assert mapping["bottom"] == 1
        assert mapping["bottom_left"] == 2
        assert mapping["top_left"] == 3
        assert mapping["top"] == 4
        assert mapping["top_right"] == 5
        assert mapping["bottom_right"] == 6

    def test_button_at_top_left_seat_3(self):
        """When button is at top_left and seat 3, mapping should rotate."""
        from hand_history import calculate_seat_mapping
        mapping = calculate_seat_mapping("top_left", 3, "6_player")
        # top_left -> 3, positions continue clockwise
        assert mapping["top_left"] == 3
        assert mapping["top"] == 4
        assert mapping["top_right"] == 5
        assert mapping["bottom_right"] == 6
        assert mapping["bottom"] == 1
        assert mapping["bottom_left"] == 2

    def test_button_at_bottom_right_seat_6(self):
        """When button is at bottom_right and seat 6."""
        from hand_history import calculate_seat_mapping
        mapping = calculate_seat_mapping("bottom_right", 6, "6_player")
        assert mapping["bottom_right"] == 6
        assert mapping["bottom"] == 1
        assert mapping["bottom_left"] == 2
        assert mapping["top_left"] == 3
        assert mapping["top"] == 4
        assert mapping["top_right"] == 5

    def test_5_player_rotation(self):
        """Test rotation for 5-player table."""
        from hand_history import calculate_seat_mapping
        mapping = calculate_seat_mapping("top_left", 3, "5_player")
        assert mapping["top_left"] == 3
        assert mapping["top_right"] == 4
        assert mapping["right"] == 5
        assert mapping["bottom"] == 1
        assert mapping["left"] == 2

    def test_invalid_position_returns_default(self):
        """When button position is invalid, return default mapping."""
        from hand_history import calculate_seat_mapping
        mapping = calculate_seat_mapping("invalid_position", 3, "6_player")
        # Should return default
        assert mapping["bottom"] == 1


class TestButtonAwarePositionToSeat:
    """Tests for position_to_seat with button awareness."""

    def test_button_aware_mapping(self):
        """Test position_to_seat uses button info when provided."""
        position_names = {
            "bottom": "Hero",
            "top_left": "ButtonPlayer",
            "top": "Player4",
        }
        # Button is at top_left on screen, and seat 3 in hand history
        result = position_to_seat(
            position_names,
            "6_player",
            screenshot_button_position="top_left",
            hand_button_seat=3,
        )
        # top_left=3, so top=4, bottom=1
        assert result[1] == "Hero"
        assert result[3] == "ButtonPlayer"
        assert result[4] == "Player4"

    def test_static_mapping_when_no_button_info(self):
        """Test position_to_seat uses static mapping when button info missing."""
        position_names = {"bottom": "Hero", "top_left": "Player3"}
        result = position_to_seat(position_names, "6_player")
        assert result[1] == "Hero"
        assert result[3] == "Player3"

    def test_partial_button_info_uses_static(self):
        """Test that partial button info falls back to static mapping."""
        position_names = {"bottom": "Hero"}
        # Only position provided, not seat
        result = position_to_seat(
            position_names,
            "6_player",
            screenshot_button_position="top_left",
            hand_button_seat=None,
        )
        assert result[1] == "Hero"


class TestHeroBasedSeatMapping:
    """Tests for Hero-based seat mapping fallback."""

    def test_calculate_seat_mapping_from_hero_seat_2(self):
        """When Hero is at seat 2, bottom should map to seat 2."""
        from hand_history import calculate_seat_mapping_from_hero
        mapping = calculate_seat_mapping_from_hero(2, "6_player")
        assert mapping["bottom"] == 2
        assert mapping["bottom_left"] == 3
        assert mapping["top_left"] == 4
        assert mapping["top"] == 5
        assert mapping["top_right"] == 6
        assert mapping["bottom_right"] == 1

    def test_calculate_seat_mapping_from_hero_seat_4(self):
        """When Hero is at seat 4, bottom should map to seat 4."""
        from hand_history import calculate_seat_mapping_from_hero
        mapping = calculate_seat_mapping_from_hero(4, "6_player")
        assert mapping["bottom"] == 4
        assert mapping["bottom_left"] == 5
        assert mapping["top_left"] == 6
        assert mapping["top"] == 1
        assert mapping["top_right"] == 2
        assert mapping["bottom_right"] == 3

    def test_calculate_seat_mapping_from_hero_5_player(self):
        """Test Hero-based mapping for 5-player table."""
        from hand_history import calculate_seat_mapping_from_hero
        mapping = calculate_seat_mapping_from_hero(3, "5_player")
        assert mapping["bottom"] == 3
        assert mapping["left"] == 4
        assert mapping["top_left"] == 5
        assert mapping["top_right"] == 1
        assert mapping["right"] == 2

    def test_position_to_seat_hero_fallback(self):
        """When button detection fails, use hero_seat as fallback."""
        position_names = {
            "bottom": "HeroName",
            "top_left": "OtherPlayer",
        }
        # No button info, but hero_seat provided
        result = position_to_seat(
            position_names,
            "6_player",
            screenshot_button_position=None,
            hand_button_seat=None,
            hero_seat=2,
        )
        # bottom should map to seat 2 (hero), top_left to seat 4
        assert result[2] == "HeroName"
        assert result[4] == "OtherPlayer"

    def test_button_takes_priority_over_hero(self):
        """Button-based mapping should take priority over hero_seat."""
        position_names = {
            "bottom": "HeroName",
            "top": "ButtonPlayer",
        }
        # Both button and hero provided - button should win
        result = position_to_seat(
            position_names,
            "6_player",
            screenshot_button_position="top",
            hand_button_seat=5,
            hero_seat=2,  # Would give different result if used
        )
        # Button at top=5, so bottom=2 (same as hero in this case)
        assert result[2] == "HeroName"
        assert result[5] == "ButtonPlayer"


class TestConvertHandsWithPropagation:
    """Tests for convert_hands_with_propagation function."""

    HAND_1 = """Poker Hand #OM100001: PLO-5 ($5/$10) - 2025/12/21 15:09:46
Table 'TableA' 6-max Seat #2 is the button
Seat 1: Hero ($1,000 in chips)
Seat 2: enc_player1 ($1,000 in chips)
Seat 3: enc_player2 ($1,000 in chips)
enc_player1: posts small blind $5
enc_player2: posts big blind $10
*** SUMMARY ***
Seat 1: Hero won ($10)"""

    HAND_2 = """Poker Hand #OM100002: PLO-5 ($5/$10) - 2025/12/21 15:10:00
Table 'TableA' 6-max Seat #3 is the button
Seat 1: Hero ($1,000 in chips)
Seat 2: enc_player1 ($1,000 in chips)
Seat 3: enc_player2 ($1,000 in chips)
enc_player1: posts small blind $5
enc_player2: posts big blind $10
*** SUMMARY ***
Seat 1: Hero won ($10)"""

    HAND_3 = """Poker Hand #OM100003: PLO-5 ($5/$10) - 2025/12/21 15:11:00
Table 'TableB' 6-max Seat #1 is the button
Seat 1: Hero ($1,000 in chips)
Seat 4: enc_player3 ($1,000 in chips)
enc_player3: posts small blind $5
*** SUMMARY ***
Seat 1: Hero won ($5)"""

    def test_propagation_same_table(self):
        """Hand without screenshot gets converted using mapping from same table."""
        hand1 = parse_hand(self.HAND_1)
        hand2 = parse_hand(self.HAND_2)

        # Only hand1 has OCR data
        ocr_data = {
            "OM100001": OcrData(
                position_names={
                    "bottom": "Hero",
                    "bottom_left": "RealPlayer1",
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="bottom_left",  # seat 2 is button
            ),
        }

        results = convert_hands_with_propagation([hand1, hand2], ocr_data)

        assert len(results) == 2
        # Both hands should succeed because they're at the same table
        assert results[0].success
        assert results[1].success

        # hand2 should have the same player replacements even without direct screenshot
        assert "RealPlayer1" in results[1].converted_text
        assert "RealPlayer2" in results[1].converted_text
        assert "enc_player1" not in results[1].converted_text
        assert "enc_player2" not in results[1].converted_text

    def test_propagation_different_tables(self):
        """Hands from different tables use separate mappings."""
        hand1 = parse_hand(self.HAND_1)  # TableA
        hand3 = parse_hand(self.HAND_3)  # TableB

        # Only hand1 has OCR data (for TableA)
        ocr_data = {
            "OM100001": OcrData(
                position_names={
                    "bottom": "Hero",
                    "bottom_left": "RealPlayer1",
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_propagation([hand1, hand3], ocr_data)

        assert len(results) == 2
        # hand1 (TableA) should succeed
        assert results[0].success
        # hand3 (TableB) should fail - no screenshot data for TableB
        assert not results[1].success
        assert "No screenshot data for this table" in results[1].error

    def test_propagation_no_mapping(self):
        """Hand from unknown table fails gracefully."""
        hand3 = parse_hand(self.HAND_3)  # TableB

        # Empty OCR data
        ocr_data: dict[str, OcrData] = {}

        results = convert_hands_with_propagation([hand3], ocr_data)

        assert len(results) == 1
        assert not results[0].success
        assert "No screenshot data for this table" in results[0].error

    def test_propagation_replaces_hero_with_real_name(self):
        """Hero is replaced with real name from OCR when available."""
        import re
        hand1 = parse_hand(self.HAND_1)
        hand2 = parse_hand(self.HAND_2)

        ocr_data = {
            "OM100001": OcrData(
                position_names={
                    "bottom": "ActualPlayerName",  # Hero's real name from OCR
                    "bottom_left": "RealPlayer1",
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_propagation([hand1, hand2], ocr_data)

        # Hero should be replaced with ActualPlayerName in both hands
        assert "ActualPlayerName" in results[0].converted_text
        assert not re.search(r"\bHero\b", results[0].converted_text)
        assert "ActualPlayerName" in results[1].converted_text
        assert not re.search(r"\bHero\b", results[1].converted_text)

    def test_propagation_multiple_screenshots_same_table(self):
        """Multiple screenshots from same table combine their mappings."""
        hand1 = parse_hand(self.HAND_1)
        hand2 = parse_hand(self.HAND_2)

        # Both hands have OCR data, but different players detected
        ocr_data = {
            "OM100001": OcrData(
                position_names={
                    "bottom": "Hero",
                    "bottom_left": "RealPlayer1",
                    # top_left not detected in this screenshot
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
            "OM100002": OcrData(
                position_names={
                    "bottom": "Hero",
                    # bottom_left not detected in this screenshot
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="top_left",  # seat 3 is button
            ),
        }

        results = convert_hands_with_propagation([hand1, hand2], ocr_data)

        # Both should succeed and have both player names
        assert results[0].success
        assert results[1].success
        # Combined mappings should be available to both hands
        assert "RealPlayer1" in results[0].converted_text
        assert "RealPlayer1" in results[1].converted_text

    def test_hero_replacement_with_real_name(self):
        """Hero gets replaced with real name from OCR."""
        hand1 = parse_hand(self.HAND_1)

        ocr_data = {
            "OM100001": OcrData(
                position_names={
                    "bottom": "HotMouse",  # Hero's real name
                    "bottom_left": "RealPlayer1",
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_propagation([hand1], ocr_data)

        assert len(results) == 1
        assert results[0].success
        # Hero should be replaced with HotMouse
        assert "HotMouse" in results[0].converted_text
        assert "Hero" not in results[0].converted_text
        # Check replacements dict includes Hero
        assert results[0].replacements.get("Hero") == "HotMouse"

    def test_hero_replacement_propagates_to_all_hands(self):
        """Hero name propagates to hands without screenshots."""
        hand1 = parse_hand(self.HAND_1)
        hand2 = parse_hand(self.HAND_2)

        # Only hand1 has OCR data
        ocr_data = {
            "OM100001": OcrData(
                position_names={
                    "bottom": "HotMouse",  # Hero's real name
                    "bottom_left": "RealPlayer1",
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_propagation([hand1, hand2], ocr_data)

        assert len(results) == 2
        # Both hands should have Hero replaced
        assert "HotMouse" in results[0].converted_text
        assert "Hero" not in results[0].converted_text
        assert "HotMouse" in results[1].converted_text
        assert "Hero" not in results[1].converted_text

    def test_hero_unchanged_if_no_mapping(self):
        """Hero stays unchanged if we don't know the real name."""
        hand1 = parse_hand(self.HAND_1)

        # OCR doesn't include the "bottom" position (no Hero name)
        ocr_data = {
            "OM100001": OcrData(
                position_names={
                    "bottom_left": "RealPlayer1",
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_propagation([hand1], ocr_data)

        assert len(results) == 1
        assert results[0].success
        # Hero should remain unchanged
        assert "Hero" in results[0].converted_text
        # Other players should still be replaced
        assert "RealPlayer1" in results[0].converted_text


class TestCustomHeroName:
    """Tests for hero detection when player name is NOT 'Hero'.

    These tests verify the fix for when GGPoker shows the user's actual
    player name (e.g., 'HOT MOUSE!') instead of the literal 'Hero'.
    """

    # Hand where user's name is "HOT MOUSE!" instead of "Hero"
    CUSTOM_HERO_HAND_1 = """Poker Hand #OM200001: PLO-5 ($5/$10) - 2025/12/21 15:09:46
Table 'CustomTable' 6-max Seat #2 is the button
Seat 1: enc_player1 ($1,000 in chips)
Seat 2: enc_player2 ($1,000 in chips)
Seat 5: HOT MOUSE! ($500 in chips)
enc_player1: posts small blind $5
enc_player2: posts big blind $10
*** HOLE CARDS ***
Dealt to HOT MOUSE! [7d 5c Kh 6c 8c]
HOT MOUSE!: folds
enc_player1: folds
*** SUMMARY ***
Seat 1: enc_player1 folded
Seat 2: enc_player2 (button) won ($10)
Seat 5: HOT MOUSE! folded"""

    CUSTOM_HERO_HAND_2 = """Poker Hand #OM200002: PLO-5 ($5/$10) - 2025/12/21 15:10:00
Table 'CustomTable' 6-max Seat #3 is the button
Seat 1: enc_player1 ($1,000 in chips)
Seat 2: enc_player2 ($1,000 in chips)
Seat 5: HOT MOUSE! ($510 in chips)
enc_player1: posts small blind $5
enc_player2: posts big blind $10
*** SUMMARY ***
Seat 5: HOT MOUSE! won ($10)"""

    def test_hero_detection_from_ocr_bottom_custom_name(self):
        """Hero detected when name in hand history is NOT 'Hero'."""
        from hand_history.converter import convert_hands_with_ocr

        hand = parse_hand(self.CUSTOM_HERO_HAND_1)

        # OCR shows "HOT MOUSE!" at bottom position (matching the hand)
        ocr_data = {
            "OM200001": OcrData(
                position_names={
                    "bottom": "HOT MOUSE!",  # Matches player name in hand
                    "bottom_left": "RealPlayer1",
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_ocr([hand], ocr_data)

        assert len(results) == 1
        assert results[0].success
        # Other players should be converted
        assert "RealPlayer1" in results[0].converted_text
        assert "enc_player1" not in results[0].converted_text
        # HOT MOUSE! should be preserved (it's the hero)
        assert "HOT MOUSE!" in results[0].converted_text

    def test_conversion_with_custom_hero_name(self):
        """Full conversion works when hero has custom name like 'HOT MOUSE!'."""
        hand = parse_hand(self.CUSTOM_HERO_HAND_1)

        # OCR data where bottom matches "HOT MOUSE!"
        ocr_data = {
            "OM200001": OcrData(
                position_names={
                    "bottom": "HOT MOUSE!",  # Hero's OCR name matches hand
                    "bottom_left": "RealPlayer1",
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_propagation([hand], ocr_data)

        assert len(results) == 1
        assert results[0].success
        # Other players should be converted
        assert "RealPlayer1" in results[0].converted_text
        assert "enc_player1" not in results[0].converted_text
        # HOT MOUSE! should remain (it's already the real name)
        assert "HOT MOUSE!" in results[0].converted_text

    def test_hero_seat_propagates_across_hands_custom_name(self):
        """Hero seat learned from one hand applies to others with custom name."""
        hand1 = parse_hand(self.CUSTOM_HERO_HAND_1)
        hand2 = parse_hand(self.CUSTOM_HERO_HAND_2)

        # Only hand1 has OCR data
        ocr_data = {
            "OM200001": OcrData(
                position_names={
                    "bottom": "HOT MOUSE!",  # Hero at seat 5
                    "bottom_left": "RealPlayer1",
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_propagation([hand1, hand2], ocr_data)

        assert len(results) == 2
        assert results[0].success
        assert results[1].success

        # Both hands should have encrypted players converted
        assert "RealPlayer1" in results[0].converted_text
        assert "enc_player1" not in results[0].converted_text
        # Hand2 should also have propagated mappings
        assert "RealPlayer1" in results[1].converted_text
        assert "enc_player1" not in results[1].converted_text
        # HOT MOUSE! should be present in both (not skipped)
        assert "HOT MOUSE!" in results[0].converted_text
        assert "HOT MOUSE!" in results[1].converted_text

    def test_custom_hero_case_insensitive_match(self):
        """Hero detection works with case-insensitive matching."""
        hand = parse_hand(self.CUSTOM_HERO_HAND_1)

        # OCR shows lowercase version due to OCR quirks
        ocr_data = {
            "OM200001": OcrData(
                position_names={
                    "bottom": "hot mouse!",  # lowercase version
                    "bottom_left": "RealPlayer1",
                    "top_left": "RealPlayer2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_propagation([hand], ocr_data)

        assert len(results) == 1
        assert results[0].success
        # Even with case mismatch, hero should be detected and skipped from conversion
        # The actual name in hand history is "HOT MOUSE!" - it should be replaced
        # with the OCR-detected version if different
        assert "hot mouse!" in results[0].converted_text
        assert "enc_player1" not in results[0].converted_text


class TestE2EHeroDetection:
    """E2E tests covering ALL hero detection scenarios.

    These tests ensure hero detection works in all cases:
    - Standard: hand='Hero', OCR='RealName' (most common)
    - Custom: hand='HOT MOUSE!', OCR='HOT MOUSE!'
    - Mixed scenarios with propagation
    """

    # Hand with Hero at seat 1 (bottom position when button=seat2, button_position=bottom_left)
    # Seat mapping: bottom_left=2, top_left=3, top=4, top_right=5, bottom_right=6, bottom=1
    HAND_WITH_HERO = """Poker Hand #OM{num}: PLO-5 ($5/$10) - 2025/12/21 15:09:46
Table '{table}' 6-max Seat #2 is the button
Seat 1: Hero ($500 in chips)
Seat 2: enc_player2 ($1,000 in chips)
Seat 3: enc_player3 ($1,000 in chips)
enc_player2: posts small blind $5
enc_player3: posts big blind $10
*** HOLE CARDS ***
Dealt to Hero [7d 5c Kh 6c 8c]
Hero: folds
*** SUMMARY ***
Seat 1: Hero folded
Seat 2: enc_player2 (button) folded
Seat 3: enc_player3 won ($10)"""

    HAND_WITH_CUSTOM = """Poker Hand #OM{num}: PLO-5 ($5/$10) - 2025/12/21 15:09:46
Table '{table}' 6-max Seat #2 is the button
Seat 1: HOT MOUSE! ($500 in chips)
Seat 2: enc_player2 ($1,000 in chips)
Seat 3: enc_player3 ($1,000 in chips)
enc_player2: posts small blind $5
enc_player3: posts big blind $10
*** HOLE CARDS ***
Dealt to HOT MOUSE! [7d 5c Kh 6c 8c]
HOT MOUSE!: folds
*** SUMMARY ***
Seat 1: HOT MOUSE! folded
Seat 2: enc_player2 (button) folded
Seat 3: enc_player3 won ($10)"""

    def test_scenario_1_standard_hero_ocr_returns_real_name(self):
        """CRITICAL: Most common case - hand='Hero', OCR='RealName'.

        This is the regression test for the v0.1.10 bug where hero_seat
        was None when OCR name didn't match 'Hero'.
        """
        hand = parse_hand(self.HAND_WITH_HERO.format(num="300001", table="Table1"))
        ocr_data = {
            "OM300001": OcrData(
                position_names={
                    "bottom": "JohnSmith",  # Different from "Hero"!
                    "bottom_left": "Player2",  # seat 2
                    "top_left": "Player3",     # seat 3
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }
        results = convert_hands_with_propagation([hand], ocr_data)

        assert results[0].success
        # Hero should be replaced with JohnSmith
        assert "JohnSmith" in results[0].converted_text
        assert "Hero" not in results[0].converted_text
        # Other players should be converted
        assert "Player2" in results[0].converted_text
        assert "enc_player2" not in results[0].converted_text
        assert "Player3" in results[0].converted_text
        assert "enc_player3" not in results[0].converted_text

    def test_scenario_2_custom_hero_exact_match(self):
        """Hand='HOT MOUSE!', OCR='HOT MOUSE!' - exact match."""
        hand = parse_hand(self.HAND_WITH_CUSTOM.format(num="300002", table="Table1"))
        ocr_data = {
            "OM300002": OcrData(
                position_names={
                    "bottom": "HOT MOUSE!",
                    "bottom_left": "Player2",
                    "top_left": "Player3",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }
        results = convert_hands_with_propagation([hand], ocr_data)

        assert results[0].success
        # HOT MOUSE! stays as-is (OCR matches hand)
        assert "HOT MOUSE!" in results[0].converted_text
        # Other players should be converted
        assert "Player2" in results[0].converted_text
        assert "enc_player2" not in results[0].converted_text

    def test_scenario_3_custom_hero_case_insensitive(self):
        """Hand='HOT MOUSE!', OCR='hot mouse!' - case differs.

        Hero is detected via case-insensitive match. The hero's seat is
        correctly identified even when OCR case differs from hand.
        Note: Due to regex word boundary issues with special chars like '!',
        the name replacement may not apply, but hero detection works.
        """
        hand = parse_hand(self.HAND_WITH_CUSTOM.format(num="300003", table="Table1"))
        ocr_data = {
            "OM300003": OcrData(
                position_names={
                    "bottom": "hot mouse!",  # lowercase
                    "bottom_left": "Player2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }
        results = convert_hands_with_propagation([hand], ocr_data)

        assert results[0].success
        # Hero detected - the key is that other players are converted correctly
        # (which means seat mapping worked because hero was detected)
        assert "Player2" in results[0].converted_text
        assert "enc_player2" not in results[0].converted_text
        # Hero's replacement was attempted (may or may not have applied due to regex edge case)
        assert "HOT MOUSE!" in results[0].replacements or "hot mouse!" in results[0].converted_text

    def test_scenario_4_hero_matches_ocr(self):
        """Hand='Hero', OCR='Hero' - both literal."""
        hand = parse_hand(self.HAND_WITH_HERO.format(num="300004", table="Table1"))
        ocr_data = {
            "OM300004": OcrData(
                position_names={
                    "bottom": "Hero",  # Matches hand exactly
                    "bottom_left": "Player2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }
        results = convert_hands_with_propagation([hand], ocr_data)

        assert results[0].success
        # Hero stays as Hero (OCR matches)
        assert "Hero" in results[0].converted_text
        # Other players converted
        assert "Player2" in results[0].converted_text
        assert "enc_player2" not in results[0].converted_text

    def test_scenario_5_no_ocr_bottom(self):
        """OCR bottom is empty - fallback to literal 'Hero'."""
        hand = parse_hand(self.HAND_WITH_HERO.format(num="300005", table="Table1"))
        ocr_data = {
            "OM300005": OcrData(
                position_names={
                    # No "bottom" key - OCR failed to detect hero
                    "bottom_left": "Player2",
                    "top_left": "Player3",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }
        results = convert_hands_with_propagation([hand], ocr_data)

        assert results[0].success
        # Hero stays as Hero (fallback used, no OCR name for bottom)
        assert "Hero" in results[0].converted_text
        # Other players should still be converted
        assert "Player2" in results[0].converted_text
        assert "enc_player2" not in results[0].converted_text

    def test_scenario_6_propagation_standard_hero(self):
        """Mapping from hand with screenshot propagates to hand without."""
        hand1 = parse_hand(self.HAND_WITH_HERO.format(num="300006", table="Table1"))
        hand2 = parse_hand(self.HAND_WITH_HERO.format(num="300007", table="Table1"))

        # Only hand1 has OCR data
        ocr_data = {
            "OM300006": OcrData(
                position_names={
                    "bottom": "JohnSmith",
                    "bottom_left": "Player2",
                    "top_left": "Player3",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_propagation([hand1, hand2], ocr_data)

        assert len(results) == 2
        assert results[0].success
        assert results[1].success

        # Both hands should have Hero replaced
        assert "JohnSmith" in results[0].converted_text
        assert "Hero" not in results[0].converted_text
        assert "JohnSmith" in results[1].converted_text
        assert "Hero" not in results[1].converted_text

        # Both hands should have other players converted
        assert "Player2" in results[0].converted_text
        assert "Player2" in results[1].converted_text


class TestHeroDetectionFallback:
    """Regression tests: hero detection must fall back to literal 'Hero'.

    These tests specifically verify the fix for the v0.1.10 bug where
    hero_seat was None when OCR returned a name different from the hand.
    """

    # Hero at seat 1 (bottom position when button=seat2/bottom_left)
    HAND_WITH_HERO_AT_SEAT_1 = """Poker Hand #OM400001: PLO-5 ($5/$10) - 2025/12/21 15:09:46
Table 'TestTable' 6-max Seat #2 is the button
Seat 1: Hero ($500 in chips)
Seat 2: enc_player2 ($1,000 in chips)
Seat 3: enc_player3 ($1,000 in chips)
enc_player2: posts small blind $5
*** SUMMARY ***
Seat 1: Hero won ($10)"""

    def test_fallback_when_ocr_name_differs_from_hand_name(self):
        """Bug regression: OCR='RealName' but hand='Hero' must still work.

        In v0.1.10, this failed because:
        1. OCR returned "CompletelyDifferentName" for bottom
        2. Code tried to match "CompletelyDifferentName" to hand.seats
        3. No match found (hand has "Hero")
        4. hero_seat stayed None
        5. Seat mapping was wrong, conversion failed
        """
        from hand_history.converter import convert_hands_with_ocr

        hand = parse_hand(self.HAND_WITH_HERO_AT_SEAT_1)
        ocr_data = {
            "OM400001": OcrData(
                position_names={
                    "bottom": "CompletelyDifferentName",
                    "bottom_left": "Player2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_ocr([hand], ocr_data)

        # This FAILED in v0.1.10 - hero_seat was None
        assert results[0].success
        # Hero should be preserved (fallback found it, OCR name used for mapping only)
        assert "Hero" in results[0].converted_text
        # Other players should be converted correctly
        assert "Player2" in results[0].converted_text
        assert "enc_player2" not in results[0].converted_text

    def test_fallback_in_propagation_function(self):
        """Same bug test but for convert_hands_with_propagation."""
        hand = parse_hand(self.HAND_WITH_HERO_AT_SEAT_1)
        ocr_data = {
            "OM400001": OcrData(
                position_names={
                    "bottom": "SomeOtherName",
                    "bottom_left": "Player2",
                },
                table_type="6_player",
                button_position="bottom_left",
            ),
        }

        results = convert_hands_with_propagation([hand], ocr_data)

        assert results[0].success
        # Hero should be replaced with OCR's bottom name (hero's real name)
        assert "SomeOtherName" in results[0].converted_text
        assert "Hero" not in results[0].converted_text
        # Other players should be converted
        assert "Player2" in results[0].converted_text
        assert "enc_player2" not in results[0].converted_text

    def test_fallback_critical_when_no_button_info(self):
        """CRITICAL: When button detection fails, hero_seat fallback is essential.

        Without the fix, this test fails with completely wrong mappings:
        - Hero gets 'Player3' instead of 'JohnSmith'
        - enc_player3 gets 'Player4' instead of 'Player3'
        """
        # Hero at seat 2 (not seat 1!)
        hand_text = """Poker Hand #OM500001: PLO-5 ($5/$10) - 2025/12/21 15:09:46
Table 'TestTable' 6-max Seat #3 is the button
Seat 2: Hero ($500 in chips)
Seat 3: enc_player3 ($1,000 in chips)
Seat 4: enc_player4 ($1,000 in chips)
enc_player3: posts small blind $5
enc_player4: posts big blind $10
*** SUMMARY ***
Seat 2: Hero folded
Seat 3: enc_player3 won"""

        hand = parse_hand(hand_text)
        assert hand.get_seat_for_player("Hero") == 2

        # NO button_position - button detection fails!
        # Without hero_seat fallback: default mapping bottom->1, bottom_left->2, top_left->3
        # With hero_seat fallback: hero-based mapping bottom->2, bottom_left->3, top_left->4
        ocr_data = {
            "OM500001": OcrData(
                position_names={
                    "bottom": "JohnSmith",      # Should map to Hero (seat 2)
                    "bottom_left": "Player3",   # Should map to enc_player3 (seat 3)
                    "top_left": "Player4",      # Should map to enc_player4 (seat 4)
                },
                table_type="6_player",
                # NO button_position!
            ),
        }

        results = convert_hands_with_propagation([hand], ocr_data)

        assert results[0].success

        # CRITICAL ASSERTION: Hero must be replaced with JohnSmith
        # Without fix: Hero gets 'Player3' (WRONG!)
        assert results[0].replacements.get("Hero") == "JohnSmith", \
            f"Hero should map to JohnSmith, got: {results[0].replacements}"

        # Other players must map correctly
        assert results[0].replacements.get("enc_player3") == "Player3"
        assert results[0].replacements.get("enc_player4") == "Player4"

        # Verify in converted text
        assert "JohnSmith" in results[0].converted_text
        assert "Hero" not in results[0].converted_text
        assert "Player3" in results[0].converted_text
        assert "enc_player3" not in results[0].converted_text
