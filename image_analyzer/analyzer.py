"""Image analysis using LLM providers (Anthropic Claude, DeepSeek)."""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance

import re

from image_analyzer.constants import (
    GGPOKER_DETECTION_PIXEL, GGPOKER_COLOR_BGR, DEFAULT_REGIONS,
    NATURAL8_DETECTION_PIXEL, NATURAL8_COLOR_BGR,
    FEWSHOT_ZERO_B64, FEWSHOT_ZERO_NAME,
    FEWSHOT_I_VS_L_B64, FEWSHOT_I_VS_L_NAME,
    FEWSHOT_ZERO_ALT_B64, FEWSHOT_ZERO_ALT_NAME,
    HAND_INFO_REGION,
    load_corrections,
)
from image_analyzer.models import PlayerRegion, BASE_WIDTH, NATURAL8_BASE_WIDTH, NATURAL8_5MAX_REGIONS
from image_analyzer.llm import get_provider, ProviderName


def detect_table_type(image: np.ndarray, tolerance: int = 30) -> tuple[PlayerRegion, ...]:
    """Detect table type by sampling pixel colors at known UI locations."""
    image_width = image.shape[1]

    def sample_pixel(coords: tuple[int, int], base_width: int) -> tuple[int, int, int]:
        scale = image_width / base_width
        x = int(coords[0] * scale)
        y = int(coords[1] * scale)
        return tuple(image[y, x])

    def color_distance(c1: tuple, c2: tuple) -> float:
        return sum((int(a) - int(b)) ** 2 for a, b in zip(c1, c2)) ** 0.5

    gg_pixel = sample_pixel(GGPOKER_DETECTION_PIXEL, BASE_WIDTH)
    if color_distance(gg_pixel, GGPOKER_COLOR_BGR) < tolerance:
        return DEFAULT_REGIONS

    n8_pixel = sample_pixel(NATURAL8_DETECTION_PIXEL, NATURAL8_BASE_WIDTH)
    if color_distance(n8_pixel, NATURAL8_COLOR_BGR) < tolerance:
        return NATURAL8_5MAX_REGIONS

    return NATURAL8_5MAX_REGIONS


def _enhance_crop(image: Image.Image) -> Image.Image:
    """Enhance contrast and brightness for better text readability."""
    contrast = ImageEnhance.Contrast(image)
    image = contrast.enhance(1.5)

    brightness = ImageEnhance.Brightness(image)
    image = brightness.enhance(1.1)

    return image


def _extract_crops(
    image: np.ndarray,
    regions: tuple[PlayerRegion, ...],
    target_width: int = 400,
    start_index: int = 0,
) -> tuple[Image.Image, list[tuple[str, int]]]:
    """Extract and stack crops vertically into a single image.

    Args:
        image: BGR numpy array
        regions: Player region definitions
        target_width: Width to resize crops to
        start_index: Starting index for crop labels (for batch processing)

    Returns (combined_image, index_mapping) where index_mapping is
    [(region_name, y_position), ...].
    """
    image_width = image.shape[1]
    label_height = 20

    resized_crops = []
    for region in regions:
        scaled_region = region.scale(image_width)
        crop = image[
            scaled_region.y:scaled_region.y + scaled_region.height,
            scaled_region.x:scaled_region.x + scaled_region.width
        ]
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        pil_crop = Image.fromarray(crop_rgb)
        ratio = target_width / pil_crop.width
        new_height = int(pil_crop.height * ratio)
        resized = pil_crop.resize((target_width, new_height), Image.Resampling.LANCZOS)
        enhanced = _enhance_crop(resized)
        resized_crops.append((region.name, enhanced))

    total_height = sum(crop.height + label_height for _, crop in resized_crops)
    combined = Image.new("RGB", (target_width, total_height), (255, 255, 255))

    index_mapping = []
    y_offset = 0

    for idx, (region_name, crop) in enumerate(resized_crops):
        from PIL import ImageDraw
        draw = ImageDraw.Draw(combined)
        draw.rectangle([(0, y_offset), (target_width, y_offset + label_height)], fill=(240, 240, 240))
        draw.text((5, y_offset + 2), f"[{start_index + idx}]", fill=(0, 0, 0))
        y_offset += label_height

        index_mapping.append((region_name, y_offset))
        combined.paste(crop, (0, y_offset))
        y_offset += crop.height

    return combined, index_mapping


def _build_prompt(num_crops: int) -> str:
    """Build the extraction prompt for the LLM."""
    return f"""This image contains {num_crops} text crops stacked vertically, labeled [0] through [{num_crops - 1}].

Read each crop IN ORDER from top to bottom. Output one line per crop.

IMPORTANT:
- Some crops are EMPTY (dark/blank) - you MUST still output a line for them as "EMPTY"
- Some names REPEAT multiple times - output each occurrence separately at its index
- Never skip indices - output exactly {num_crops} lines
- The font is Roboto - uppercase I is slightly shorter than lowercase l, compare heights to distinguish
- 0 vs O: Compare WIDTHS - digit zero is noticeably NARROWER than letter O
- Dimmed/grayed text = "sitting out" players

Output format:
[0] PlayerName
[1] EMPTY
[2] PlayerName
[3] PlayerName

Rules:
- DO NOT autocorrect to English words - output exactly what you see
- Preserve exact spelling, capitalization, spacing
- Include special characters (hyphens, underscores, dots)
- Names ending with ".." are truncated - keep the ".."

Start now:"""


def _get_few_shot_examples() -> list[tuple[str, str, str]]:
    """Return few-shot examples for character disambiguation."""
    return [
        (
            FEWSHOT_ZERO_B64,
            FEWSHOT_ZERO_NAME,
            "it contains digit ZEROS (0), not letter O. Zeros are NARROWER than letter O. "
            "Do NOT autocorrect to English words.",
        ),
        (
            FEWSHOT_I_VS_L_B64,
            FEWSHOT_I_VS_L_NAME,
            "it contains lowercase 'i' (with dot above), not 'l'. Look for the dot to distinguish.",
        ),
        (
            FEWSHOT_ZERO_ALT_B64,
            FEWSHOT_ZERO_ALT_NAME,
            "same name as first example, different lighting conditions. Still contains digit ZEROS (0), "
            "not letter O. The zeros are narrower. Do NOT read as 'HOT MOUSE'.",
        ),
    ]


def _call_llm(
    image: Image.Image,
    num_crops: int,
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> list[str]:
    """Send image to LLM provider and get text for each crop."""
    llm = get_provider(provider, api_key, model)
    prompt = _build_prompt(num_crops)
    few_shot_examples = _get_few_shot_examples()

    results = llm.call(image, num_crops, few_shot_examples, prompt)
    corrections = load_corrections()
    return [corrections.get(r, r) for r in results]


def analyze_image(
    image: np.ndarray,
    regions: tuple[PlayerRegion, ...] = DEFAULT_REGIONS,
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> dict[str, str]:
    """Analyze an image array and extract player names from regions.

    Args:
        image: BGR numpy array (from cv2.imread)
        regions: Player region definitions
        api_key: API key (uses provider-specific env var if None)
        provider: LLM provider name ("anthropic" or "deepseek")
        model: Model name (uses provider default if None)

    Returns:
        Dict mapping region name to extracted player name
    """
    batch_image, index_mapping = _extract_crops(image, regions)
    results = _call_llm(batch_image, len(regions), api_key, provider, model)

    return {region_name: results[idx] for idx, (region_name, _) in enumerate(index_mapping)}


def analyze_screenshot(
    image_path: str | Path,
    regions: tuple[PlayerRegion, ...] | None = None,
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> dict[str, str]:
    """Analyze a screenshot file and extract player names.

    Args:
        image_path: Path to the image file
        regions: Player region definitions (auto-detected if None)
        api_key: API key (uses provider-specific env var if None)
        provider: LLM provider name ("anthropic" or "deepseek")
        model: Model name (uses provider default if None)

    Returns:
        Dict mapping region name to extracted player name
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not load image: {path}")

    if regions is None:
        regions = detect_table_type(image)

    return analyze_image(image, regions, api_key, provider, model)


def analyze_screenshots_batch(
    image_paths: list[str | Path],
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> list[dict[str, str]]:
    """Analyze multiple screenshots in a single API call.

    Args:
        image_paths: List of paths to screenshot files
        api_key: API key (uses provider-specific env var if None)
        provider: LLM provider name ("anthropic" or "deepseek")
        model: Model name (uses provider default if None)

    Returns:
        List of dicts, each mapping region name to extracted player name
    """
    if not image_paths:
        return []

    images_data: list[tuple[np.ndarray, tuple[PlayerRegion, ...]]] = []
    for image_path in image_paths:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Could not load image: {path}")

        regions = detect_table_type(image)
        images_data.append((image, regions))

    all_crops: list[Image.Image] = []
    crop_boundaries: list[int] = []
    region_mappings: list[list[str]] = []

    current_index = 0
    target_width = 400

    for image, regions in images_data:
        crop_image, index_mapping = _extract_crops(
            image, regions, target_width, start_index=current_index
        )
        all_crops.append(crop_image)
        region_mappings.append([name for name, _ in index_mapping])
        crop_boundaries.append(current_index)
        current_index += len(regions)

    total_height = sum(crop.height for crop in all_crops)
    combined = Image.new("RGB", (target_width, total_height), (255, 255, 255))

    y_offset = 0
    for crop in all_crops:
        combined.paste(crop, (0, y_offset))
        y_offset += crop.height

    total_crops = current_index
    api_results = _call_llm(combined, total_crops, api_key, provider, model)

    results: list[dict[str, str]] = []
    for i, (_, regions) in enumerate(images_data):
        start = crop_boundaries[i]
        region_names = region_mappings[i]
        image_result = {
            region_names[j]: api_results[start + j]
            for j in range(len(region_names))
        }
        results.append(image_result)

    return results


HAND_NUMBER_PATTERN = re.compile(r"#(OM\d+)")


def extract_hand_number(
    image: np.ndarray,
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> str | None:
    """Extract hand number from top-left region of screenshot.

    Args:
        image: BGR numpy array (from cv2.imread)
        api_key: API key (uses provider-specific env var if None)
        provider: LLM provider name
        model: Model name (uses provider default if None)

    Returns:
        Hand number (e.g., "OM262668465") or None if not found
    """
    image_width = image.shape[1]
    region = HAND_INFO_REGION.scale(image_width)

    crop = image[
        region.y:region.y + region.height,
        region.x:region.x + region.width
    ]
    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(crop_rgb)
    enhanced = _enhance_crop(pil_image)

    llm = get_provider(provider, api_key, model)
    prompt = """Read the text in this image. It shows hand information like:
"HH PL PLO-5 $2 / $5 - #OM262843903"

Output ONLY the hand number starting with #OM, nothing else.
Example: #OM262843903"""

    results = llm.call(enhanced, 1, [], prompt)
    if not results:
        return None

    text = results[0]
    match = HAND_NUMBER_PATTERN.search(text)
    if match:
        return match.group(1)

    return None


def extract_hand_number_from_file(
    image_path: str | Path,
    api_key: str | None = None,
    provider: ProviderName = "anthropic",
    model: str | None = None,
) -> str | None:
    """Extract hand number from screenshot file.

    Args:
        image_path: Path to the image file
        api_key: API key (uses provider-specific env var if None)
        provider: LLM provider name
        model: Model name (uses provider default if None)

    Returns:
        Hand number (e.g., "OM262668465") or None if not found
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not load image: {path}")

    return extract_hand_number(image, api_key, provider, model)
