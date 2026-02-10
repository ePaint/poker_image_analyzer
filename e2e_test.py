"""E2E test: Run 20 random screenshots through Anthropic API."""
import random
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from image_analyzer import analyze_screenshot

SCREENSHOTS_DIR = Path(__file__).parent / "Screenshots_GG"
NUM_SAMPLES = 20


def main():
    all_images = sorted(SCREENSHOTS_DIR.glob("*.png"))
    print(f"Found {len(all_images)} images in {SCREENSHOTS_DIR}")

    random.seed(42)
    selected = random.sample(all_images, min(NUM_SAMPLES, len(all_images)))

    print(f"\nTesting {len(selected)} random images:\n")
    print("=" * 80)

    for i, image_path in enumerate(selected, 1):
        print(f"\n[{i}/{len(selected)}] {image_path.name}")
        print("-" * 60)

        try:
            results = analyze_screenshot(image_path)
            for position in ["top", "top_left", "top_right", "bottom_left", "bottom", "bottom_right"]:
                name = results.get(position, "")
                display = name if name else "(empty)"
                print(f"  {position:12}: {display}")
        except Exception as e:
            print(f"  ERROR: {e}")

        print()

    print("=" * 80)
    print("E2E test complete.")


if __name__ == "__main__":
    main()
