"""Test OCR on random sample of screenshots for manual verification."""

import random
import shutil
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from image_analyzer import analyze_screenshot


def main():
    project_root = Path(__file__).parent
    source_dir = project_root / "Screenshots_GG"
    target_dir = project_root / "tests" / "images" / "random_sample"

    target_dir.mkdir(parents=True, exist_ok=True)

    all_images = list(source_dir.glob("*.png"))
    print(f"Found {len(all_images)} images in Screenshots_GG/")

    existing = list(target_dir.glob("*.png"))
    if existing:
        print(f"Using {len(existing)} existing images in random_sample/")
        sample_images = existing
    else:
        sample_images = random.sample(all_images, min(20, len(all_images)))
        print(f"Copying {len(sample_images)} random images...")
        for img in sample_images:
            shutil.copy(img, target_dir / img.name)
        sample_images = list(target_dir.glob("*.png"))

    print("\n" + "=" * 80)
    print("OCR RESULTS")
    print("=" * 80)

    for i, img_path in enumerate(sorted(sample_images), 1):
        print(f"\n[{i}/{len(sample_images)}] {img_path.name}")
        print("-" * 60)

        try:
            results = analyze_screenshot(str(img_path))
            for position, name in sorted(results.items()):
                print(f"  {position:5s}: {name}")
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n" + "=" * 80)
    print("Manual verification complete. Review results above for OCR accuracy.")
    print("=" * 80)


if __name__ == "__main__":
    main()
