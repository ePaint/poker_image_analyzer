import pytesseract
import numpy as np

from image_analyzer.models import OCRResult


class TesseractEngine:
    def read(self, image: np.ndarray) -> list[OCRResult]:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        results = []
        for i, text in enumerate(data["text"]):
            text = text.strip()
            if not text:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            conf = data["conf"][i]
            if conf < 0:
                continue
            cx = x + w / 2
            cy = y + h / 2
            results.append(OCRResult(text, cx, cy, conf / 100))
        return results
