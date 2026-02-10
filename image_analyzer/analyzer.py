"""Image analysis using Anthropic Claude API."""
import base64
import io
import os
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance

from image_analyzer.models import PlayerRegion, BASE_WIDTH, NATURAL8_BASE_WIDTH, NATURAL8_5MAX_REGIONS


FEWSHOT_ZERO_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAANIAAAAmCAIAAAA++FIaAAACPElEQVR4nO2c63KEIAyFSafv/8rp"
    "dHfGUiUQkMuRPd+vjhsxJkeiQSshBFUNESISsHk7LCInzz8KgU/TiThZctr0uJNJsoccZYtcxPzJ"
    "bLUnoDJ9p9yqA0l7VY2FUqwhutelXlepwu4cFbmjpUc0/2qKPab+F+sn8HvK44Yuhvv4O2lmzUAZ"
    "gzz57DpVUjuTOc2kSbtWBPyWmR2rLsJavkYMepxk2z2WvsgMO5qbB7J2zwyr9UfsO5o1wqCYD5Hd"
    "454Gqg6aN57jv5aOAv5QBSc7f2GNf0rWgqLBBG7eGDiRF7X2V8IsoGX3DkQmHHG8TmbHxraAdtFH"
    "0f82rDtLp8QRnmCwZOeZzJDLx3z/JXWx4YMlu1X4s4Us+gcp73u1A6Sa4qogvvJAZzuEwN2Z2Kb5"
    "r/Cz7xrZre3A9QXTbTXanBn74pYdiixmtjzArlzJpc5WrfAmlccGCinjWU/76Hu7hz7k46dTjJZk"
    "0dXrXpOTMrzIWr1cwCw6Sb4TheaP2kVzUBN7hyfZtVy7uzgi8898yD5TduXJoO/rIUN5yg0MqOyQ"
    "r1SQjomODJG1ztsLrlI05mN7ZOSZYs12ntI2LfENB7rjvz6nlO8mO/D4NiveKUE1OsB+sXoC5Qzm"
    "0DoOXWSLn1OA0+C/OjJ9aj81lIXiLvFL7SNiDjfbQQnrZp3tZS/13V2oMF5Z9uVY0abtfxU0f++U"
    "WdO0xuzrv/o+NmveyzmPnuzB5UsIIYQQQgghhBBCCCGEEEJIQOcH6Bd6X4KAVyYAAAAASUVORK5C"
    "YII="
)
FEWSHOT_ZERO_NAME = "H0T M0USE!"

FEWSHOT_I_VS_L_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAANIAAAAmCAIAAAA++FIaAAABaUlEQVR4nO2a0a6DIBAFoen//zI3"
    "rWljERdsBbl7Zt4kLWicHFghBAAAAADwQgyuSSk9HjLGxvZzx81oGS69/tjv3mbgFgTIJHhfFuU4"
    "fbhq+0J6EjS4X30D3qi6FT9jTEc1ubTbY8BEFp+sW5KkZ1raLa88e/HFxn6jG2MlVQWda3chLVrH"
    "mpdecf60xcJw22jUj3s/Xi6N/o25NTaEn28RSbvWWW9bDq9bMmN8S/M70tpVl1ZnxY/sGk5Ru700"
    "2lKcgg9hzJtZh5Eg1Plu1+llG92ScKJp9yM6C/zxoN0x2jMMUw3QrqMlS0nLLsUWtBthJMknWlIc"
    "gmqgN6TdyZkkdX7pa9Cui4uYZ6Oi3XgPMM9ARbtL6H2M+f+Cdn1LTjbHiqDdMQvXLUVH+VbSgrR2"
    "nbzZ64EDUW88bzVy9GNaPKdddUKEq/CsHfXjtPjcHEO4yfGcdjAtEtqxsINBsCUPAAAAABAG8AcY"
    "UatG7SL5fwAAAABJRU5ErkJggg=="
)
FEWSHOT_I_VS_L_NAME = "jivr31"


DEFAULT_REGIONS = (
    PlayerRegion("top", 347, 152),
    PlayerRegion("top_left", 29, 234),
    PlayerRegion("top_right", 666, 234),
    PlayerRegion("bottom_left", 29, 459),
    PlayerRegion("bottom", 347, 565),
    PlayerRegion("bottom_right", 666, 459),
)

GGPOKER_DETECTION_PIXEL = (702, 64)
GGPOKER_COLOR_BGR = (6, 15, 219)
NATURAL8_DETECTION_PIXEL = (880, 72)
NATURAL8_COLOR_BGR = (145, 39, 140)


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


def _image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


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


def _call_anthropic(
    image: Image.Image,
    num_crops: int,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> list[str]:
    """Send image to Anthropic and get text for each crop."""
    import anthropic

    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")

    client = anthropic.Anthropic(api_key=api_key)
    image_b64 = _image_to_base64(image)

    prompt = f"""This image contains {num_crops} text crops stacked vertically, labeled [0] through [{num_crops - 1}].

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

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": FEWSHOT_ZERO_B64,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        f"EXAMPLE: This player name is '{FEWSHOT_ZERO_NAME}' - it contains "
                        "digit ZEROS (0), not letter O. Zeros are NARROWER than letter O. "
                        "Do NOT autocorrect to English words."
                    ),
                },
            ],
        },
        {
            "role": "assistant",
            "content": f"Understood. '{FEWSHOT_ZERO_NAME}' uses digit zeros (0) which are narrower than letter O. I will distinguish 0 vs O by width.",
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": FEWSHOT_I_VS_L_B64,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        f"EXAMPLE: This player name is '{FEWSHOT_I_VS_L_NAME}' - it contains "
                        "lowercase 'i' (with dot above), not 'l'. Look for the dot to distinguish."
                    ),
                },
            ],
        },
        {
            "role": "assistant",
            "content": f"Understood. '{FEWSHOT_I_VS_L_NAME}' uses lowercase 'i' with a dot above it, not 'l'. I will look for dots to distinguish i vs l.",
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        },
    ]

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        messages=messages,
    )

    response_text = response.content[0].text.strip()
    results = [""] * num_crops

    for line in response_text.split("\n"):
        line = line.strip()
        match = re.match(r'\[(\d+)\]\s*(.*)', line)
        if match:
            idx = int(match.group(1))
            text = match.group(2).strip()
            if text.upper() == "EMPTY":
                text = ""
            if 0 <= idx < num_crops:
                results[idx] = text

    return results


def analyze_image(
    image: np.ndarray,
    regions: tuple[PlayerRegion, ...] = DEFAULT_REGIONS,
    api_key: str | None = None,
) -> dict[str, str]:
    """Analyze an image array and extract player names from regions.

    Args:
        image: BGR numpy array (from cv2.imread)
        regions: Player region definitions
        api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)

    Returns:
        Dict mapping region name to extracted player name
    """
    batch_image, index_mapping = _extract_crops(image, regions)
    results = _call_anthropic(batch_image, len(regions), api_key)

    return {region_name: results[idx] for idx, (region_name, _) in enumerate(index_mapping)}


def analyze_screenshot(
    image_path: str | Path,
    regions: tuple[PlayerRegion, ...] | None = None,
    api_key: str | None = None,
) -> dict[str, str]:
    """Analyze a screenshot file and extract player names.

    Args:
        image_path: Path to the image file
        regions: Player region definitions (auto-detected if None)
        api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)

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

    return analyze_image(image, regions, api_key)


def analyze_screenshots_batch(
    image_paths: list[str | Path],
    api_key: str | None = None,
) -> list[dict[str, str]]:
    """Analyze multiple screenshots in a single API call.

    Args:
        image_paths: List of paths to screenshot files
        api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)

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
    api_results = _call_anthropic(combined, total_crops, api_key)

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
