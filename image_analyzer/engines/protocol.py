from typing import Protocol

import numpy as np

from image_analyzer.models import OCRResult


class OCREngine(Protocol):
    def read(self, image: np.ndarray) -> list[OCRResult]:
        """Run OCR on an image and return detected text results."""
        ...
