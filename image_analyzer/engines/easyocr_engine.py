import easyocr
import numpy as np

from image_analyzer.engines.protocol import OCREngine
from image_analyzer.models import OCRResult


class EasyOCREngine(OCREngine):
    def __init__(self, gpu: bool = False):
        self._reader = easyocr.Reader(["en"], gpu=gpu)

    def read(self, image: np.ndarray) -> list[OCRResult]:
        raw_results = self._reader.readtext(image)
        results = []
        for box, text, confidence in raw_results:
            cx = sum(p[0] for p in box) / 4
            cy = sum(p[1] for p in box) / 4
            results.append(OCRResult(text, cx, cy, confidence))
        return results
