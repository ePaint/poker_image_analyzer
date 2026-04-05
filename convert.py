#!/usr/bin/env python
"""CLI tool to de-anonymize GGPoker hand histories using screenshots."""
import argparse
import sys
from pathlib import Path

from image_analyzer import (
    analyze_screenshot,
    detect_button_position,
    ScreenshotFilename,
    SIX_PLAYER_REGIONS,
    FIVE_PLAYER_REGIONS,
)
from hand_history import (
    TableType,
    InvalidTableTypeError,
    parse_table_type_from_filename,
    OcrData,
    parse_file,
    convert_hands_with_propagation,
    write_converted_file,
    write_skipped_file,
)
import cv2


def process_screenshots(
    screenshots_dir: Path,
    hands_dir: Path,
    api_key: str | None = None,
) -> dict[str, OcrData]:
    """Process all screenshots and extract hand numbers + player names.

    Args:
        screenshots_dir: Directory containing screenshot files
        hands_dir: Directory containing hand history files (used to determine table type)
        api_key: API key for LLM provider

    Returns:
        Dict mapping hand number to OcrData (position_names, table_type, button_position)
    """
    result: dict[str, OcrData] = {}

    # Determine table type from hand history filenames
    txt_files = list(hands_dir.glob("*.txt"))
    if not txt_files:
        print("Error: No hand history files found")
        return result

    try:
        table_type = parse_table_type_from_filename(txt_files[0].name)
        regions = SIX_PLAYER_REGIONS if table_type == TableType.SIX_PLAYER else FIVE_PLAYER_REGIONS
        print(f"Table type from filename: {table_type.value}")
    except InvalidTableTypeError as e:
        print(f"Error: {e}")
        return result

    png_files = list(screenshots_dir.glob("*.png"))
    valid_files = [f for f in png_files if ScreenshotFilename.is_valid(f.name)]

    print(f"Found {len(valid_files)} valid screenshots")

    for i, screenshot_path in enumerate(valid_files, 1):
        print(f"Processing screenshot {i}/{len(valid_files)}: {screenshot_path.name}")

        try:
            parsed = ScreenshotFilename.parse(screenshot_path)
            if not parsed:
                print("  Error: Invalid filename format")
                continue

            hand_number = f"OM{parsed.table_id}"

            image = cv2.imread(str(screenshot_path))
            if image is None:
                print("  Error: Could not load image")
                continue

            position_names = analyze_screenshot(screenshot_path, regions=regions, api_key=api_key)
            button_position = detect_button_position(image, regions)

            result[hand_number] = OcrData(
                position_names=position_names,
                table_type=table_type,
                button_position=button_position,
            )
            print(f"  Hand #{hand_number}: {len(position_names)} players ({table_type.value})")

        except Exception as e:
            print(f"  Error: {e}")

    return result


def process_hands(
    hands_dir: Path,
    ocr_data: dict[str, OcrData],
    output_dir: Path,
) -> tuple[int, int]:
    """Process all hand history files and convert them.

    Uses mapping propagation to convert hands without direct screenshots
    by learning encrypted_id -> real_name from other hands at the same table.

    All files are processed together so mappings are shared across files for
    the same table (e.g., mappings from file1 apply to hands in file2 if they
    share a table).

    Args:
        hands_dir: Directory containing hand history files
        ocr_data: Mapping from hand number to OCR data
        output_dir: Output directory for converted files

    Returns:
        Tuple of (successful_count, failed_count)
    """
    from collections import defaultdict

    converted_dir = output_dir / "converted"
    skipped_dir = output_dir / "skipped"

    txt_files = list(hands_dir.glob("*.txt"))
    print(f"\nFound {len(txt_files)} hand history files")

    # Step 1: Parse all hands from all files, tracking origin file
    all_hands = []
    hand_to_file: dict[str, Path] = {}

    for hand_file in txt_files:
        print(f"Parsing: {hand_file.name}")
        try:
            hands = parse_file(hand_file)
            print(f"  Found {len(hands)} hands")
            for hand in hands:
                hand_to_file[hand.hand_number] = hand_file
            all_hands.extend(hands)
        except Exception as e:
            print(f"  Error: {e}")

    print(f"\nTotal hands parsed: {len(all_hands)}")

    if not all_hands:
        return 0, 0

    # Step 2: Convert ALL hands together (shared mappings across files)
    results = convert_hands_with_propagation(all_hands, ocr_data)

    # Step 3: Group results by original file
    file_results: dict[Path, list] = defaultdict(list)
    for result in results:
        original_file = hand_to_file.get(result.hand_number)
        if original_file:
            file_results[original_file].append(result)

    # Step 4: Write output per file
    total_success = 0
    total_failed = 0

    for hand_file in txt_files:
        results_for_file = file_results.get(hand_file, [])
        if not results_for_file:
            continue

        successful = [r for r in results_for_file if r.success]
        failed = [r for r in results_for_file if not r.success]

        if successful:
            output_path = converted_dir / hand_file.name
            write_converted_file(results_for_file, output_path)
            print(f"Converted {len(successful)} hands from {hand_file.name}")

        if failed:
            output_path = skipped_dir / hand_file.name
            write_skipped_file(results_for_file, output_path)
            print(f"Skipped {len(failed)} hands from {hand_file.name}")

        total_success += len(successful)
        total_failed += len(failed)

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
    ocr_data = process_screenshots(screenshots_dir, hands_dir, api_key)
    print(f"\nExtracted data for {len(ocr_data)} hands\n")

    if not ocr_data:
        print("No screenshot data extracted. Nothing to convert.")
        return 1

    print("Step 2: Converting hand histories (with mapping propagation)...")
    success, failed = process_hands(hands_dir, ocr_data, output_dir)

    print("\n=== Summary ===")
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
