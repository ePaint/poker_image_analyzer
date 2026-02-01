from dataclasses import dataclass


@dataclass(frozen=True)
class OCRResult:
    text: str
    center_x: float
    center_y: float
    confidence: float
