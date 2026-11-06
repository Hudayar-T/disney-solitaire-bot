"""
vision/capture.py
Raw screenshot acquisition and orientation normalisation.
All other modules receive images from here — always portrait, always RGB numpy arrays.
"""

import io
import numpy as np
from PIL import Image
from loguru import logger


def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """Convert PIL Image (RGB) to OpenCV BGR numpy array."""
    return np.array(pil_image)[:, :, ::-1].copy()


def cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
    """Convert OpenCV BGR numpy array to PIL Image (RGB)."""
    return Image.fromarray(cv2_image[:, :, ::-1])


def normalise_orientation(img: np.ndarray) -> np.ndarray:
    """
    ADB screencap returns a landscape buffer (2400×1080) even when the phone
    is in portrait mode. Rotate 90° CCW to get a proper portrait image.
    If the image is already taller than wide, return it unchanged.
    """
    import cv2
    h, w = img.shape[:2]
    if w > h:
        logger.debug(f"Rotating landscape {w}×{h} → portrait")
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img


def screenshot_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """
    Full pipeline: PIL Image from ADB → normalised portrait OpenCV BGR array.
    This is the single entry point used by all other vision modules.
    """
    cv2_img = pil_to_cv2(pil_image)
    return normalise_orientation(cv2_img)
