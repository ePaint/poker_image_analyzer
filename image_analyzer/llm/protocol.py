from typing import Protocol

from PIL import Image


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    def call(
        self,
        image: Image.Image,
        num_crops: int,
        few_shot_examples: list[tuple[str, str, str]],
        prompt: str,
    ) -> list[str]:
        """Send image to LLM and return extracted text for each crop.

        Args:
            image: Combined image with all crops stacked vertically
            num_crops: Number of text crops in the image
            few_shot_examples: List of (base64, name, description) tuples for few-shot learning
            prompt: The extraction prompt

        Returns:
            List of extracted text strings, one per crop
        """
        ...
