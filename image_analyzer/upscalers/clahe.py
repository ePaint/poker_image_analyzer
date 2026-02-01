import cv2
import numpy as np

from image_analyzer.models import PlayerRegion


def preprocess_region(image: np.ndarray, region: PlayerRegion) -> np.ndarray:
    crop = image[region.y:region.y + region.height, region.x:region.x + region.width]
    scaled = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return enhanced
