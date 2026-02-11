#!/usr/bin/env python
"""CLI tool to de-anonymize GGPoker hand histories using screenshots."""
import argparse
import sys
from pathlib import Path

from image_analyzer import (
    analyze_screenshot,
    ScreenshotFilename,
)
from hand_history import (
    parse_file,
    convert_hands,
    write_converted_file,
    write_skipped_file,
    position_to_seat,
    load_seat_mapping,
)


def process_screenshots(
    screenshots_dir: Path,
    api_key: str | None = None,
) -> dict[str, dict[int, str]]:
    """Process all screenshots and extract hand numbers + player names.

    Args:
        screenshots_dir: Directory containing screenshot files
        api_key: API key for LLM provider

    Returns:
        Dict mapping hand number to seat->name mapping
    """
    result: dict[str, dict[int, str]] = {}
    seat_mapping = load_seat_mapping()

    png_files = list(screenshots_dir.glob("*.png"))
    valid_files = [f for f in png_files if ScreenshotFilename.is_valid(f.name)]

    print(f"Found {len(valid_files)} valid screenshots")

    for i, screenshot_path in enumerate(valid_files, 1):
        print(f"Processing screenshot {i}/{len(valid_files)}: {screenshot_path.name}")

        try:
            parsed = ScreenshotFilename.parse(screenshot_path)
            hand_number = f"OM{parsed.table_id}"

            position_names = analyze_screenshot(screenshot_path, api_key=api_key)
            seat_names = position_to_seat(position_names, seat_mapping)

            result[hand_number] = seat_names
            print(f"  Hand #{hand_number}: {len(seat_names)} players")

        except Exception as e:
            print(f"  Error: {e}")

    return result


def process_hands(
    hands_dir: Path,
    hand_data: dict[str, dict[int, str]],
    output_dir: Path,
) -> tuple[int, int]:
    """Process all hand history files and convert them.

    Args:
        hands_dir: Directory containing hand history files
        hand_data: Mapping from hand number to seat->name
        output_dir: Output directory for converted files

    Returns:
        Tuple of (successful_count, failed_count)
    """
    converted_dir = output_dir / "converted"
    skipped_dir = output_dir / "skipped"

    txt_files = list(hands_dir.glob("*.txt"))
    print(f"\nFound {len(txt_files)} hand history files")

    total_success = 0
    total_failed = 0

    for hand_file in txt_files:
        print(f"Processing: {hand_file.name}")

        try:
            hands = parse_file(hand_file)
            print(f"  Parsed {len(hands)} hands")

            results = convert_hands(hands, hand_data)

            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]

            if successful:
                output_path = converted_dir / hand_file.name
                write_converted_file(results, output_path)
                print(f"  Converted {len(successful)} hands -> {output_path}")

            if failed:
                output_path = skipped_dir / hand_file.name
                write_skipped_file(results, output_path)
                print(f"  Skipped {len(failed)} hands -> {output_path}")

            total_success += len(successful)
            total_failed += len(failed)

        except Exception as e:
            print(f"  Error: {e}")

    return total_success, total_failed


def main(
    hands_dir: Path,
    screenshots_dir: Path,
    output_dir: Path,
    api_key: str | None = None,
) -> int:
    """Main entry point for hand history de-anonymization.

    Args:
        hands_dir: Directory containing .txt hand history files
        screenshots_dir: Directory containing .png screenshot files
        output_dir: Output directory for converted files
        api_key: API key for LLM provider

    Returns:
        Exit code (0 for success)
    """
    if not hands_dir.exists():
        print(f"Error: Hands directory not found: {hands_dir}")
        return 1

    if not screenshots_dir.exists():
        print(f"Error: Screenshots directory not found: {screenshots_dir}")
        return 1

    print("=== Hand History De-anonymizer ===\n")
    print(f"Hands:       {hands_dir}")
    print(f"Screenshots: {screenshots_dir}")
    print(f"Output:      {output_dir}\n")

    print("Step 1: Processing screenshots...")
    hand_data = process_screenshots(screenshots_dir, api_key)
    print(f"\nExtracted data for {len(hand_data)} hands\n")

    if not hand_data:
        print("No screenshot data extracted. Nothing to convert.")
        return 1

    print("Step 2: Converting hand histories...")
    success, failed = process_hands(hands_dir, hand_data, output_dir)

    print(f"\n=== Summary ===")
    print(f"Converted: {success} hands")
    print(f"Skipped:   {failed} hands")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="De-anonymize GGPoker hand histories using screenshots"
    )
    parser.add_argument(
        "--hands",
        type=Path,
        default=Path("input/hands"),
        help="Directory containing hand history files (default: input/hands)",
    )
    parser.add_argument(
        "--screenshots",
        type=Path,
        default=Path("input/screenshots"),
        help="Directory containing screenshot files (default: input/screenshots)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for LLM provider (uses ANTHROPIC_API_KEY env var if not set)",
    )

    args = parser.parse_args()

    sys.exit(main(args.hands, args.screenshots, args.output, args.api_key))
