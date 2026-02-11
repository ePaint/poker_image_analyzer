import base64
import io
import os
import re

from PIL import Image


def _image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


class AnthropicProvider:
    """Anthropic Claude API provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-haiku-4-5-20251001",
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model

    def call(
        self,
        image: Image.Image,
        num_crops: int,
        few_shot_examples: list[tuple[str, str, str]],
        prompt: str,
    ) -> list[str]:
        """Send image to Anthropic and return extracted text for each crop."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        image_b64 = _image_to_base64(image)

        messages = []
        for example_b64, example_name, description in few_shot_examples:
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": example_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": f"EXAMPLE: This player name is '{example_name}' - {description}",
                    },
                ],
            })
            messages.append({
                "role": "assistant",
                "content": f"Understood. '{example_name}' - I will apply this pattern.",
            })

        messages.append({
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
        })

        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0,
            messages=messages,
        )

        return self._parse_response(response.content[0].text, num_crops)

    def _parse_response(self, response_text: str, num_crops: int) -> list[str]:
        """Parse the LLM response into a list of extracted names."""
        results = [""] * num_crops

        for line in response_text.strip().split("\n"):
            line = line.strip()
            match = re.match(r'\[(\d+)\]\s*(.*)', line)
            if match:
                idx = int(match.group(1))
                text = match.group(2).strip()
                if text.upper() == "EMPTY":
                    text = ""
                if 0 <= idx < num_crops:
                    results[idx] = text

        if num_crops == 1 and results[0] == "":
            results[0] = response_text.strip()

        return results
