"""
adb_controller.py
Handles all ADB communication: device connection, screen capture, and taps.
"""

import io
import os
import random
import time
from pathlib import Path

# Ensure local ADB socket connection ignores terminal proxy
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

import cv2
import numpy as np
from adbutils import adb, AdbError
from loguru import logger
from PIL import Image

import config


def connect() -> object:
    """
    Connect to the first available ADB device.
    Returns the adbutils device handle.
    Raises RuntimeError if no device is found.
    """
    devices = adb.device_list()
    if not devices:
        raise RuntimeError(
            "No ADB device found. Make sure:\n"
            "  1. USB debugging is enabled on your phone\n"
            "  2. The phone is connected via USB\n"
            "  3. You have authorised this PC on the phone\n"
            "  4. `adb devices` shows your device"
        )
    device = devices[0]
    logger.info(f"Connected to device: {device.serial}")
    return device


def screencap(device) -> np.ndarray:
    """
    Capture a screenshot from the device directly into an OpenCV BGR numpy array.
    Uses cv2.imdecode from memory buffer to eliminate PIL roundtrips.
    """
    try:
        png_bytes = device.shell("screencap -p", encoding=None)
        image = cv2.imdecode(np.frombuffer(png_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError("cv2.imdecode failed to decode screenshot bytes from device")
        logger.debug(f"Screenshot captured: {image.shape[1]}x{image.shape[0]}")
        return image
    except AdbError as e:
        raise RuntimeError(f"screencap failed: {e}") from e


def save_screenshot(image: np.ndarray | Image.Image, folder: str = "tests/screenshots") -> Path:
    """
    Save a BGR numpy array or PIL Image to disk with a timestamp filename.
    Returns the saved file path.
    """
    out_dir = Path(folder)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"screen_{timestamp}.png"
    if isinstance(image, np.ndarray):
        cv2.imwrite(str(path), image)
    else:
        image.save(path)
    logger.info(f"Screenshot saved: {path}")
    return path


def compute_jittered_coord(x: int, y: int) -> tuple[int, int]:
    """
    Compute a randomized (jittered) coordinate around (x, y) using Gaussian distribution,
    clamped to max jitter bounds (config.TAP_JITTER_X, config.TAP_JITTER_Y).
    """
    jx = int(random.gauss(0, config.TAP_JITTER_X / 2.5))
    jy = int(random.gauss(0, config.TAP_JITTER_Y / 2.5))
    jx = max(-config.TAP_JITTER_X, min(config.TAP_JITTER_X, jx))
    jy = max(-config.TAP_JITTER_Y, min(config.TAP_JITTER_Y, jy))
    return x + jx, y + jy


def tap(device, x: int, y: int, apply_jitter: bool = True) -> tuple[int, int]:
    """
    Send a tap event to the device at (x, y).
    Applies timing jitter and spatial offset (anti-bot protection)
    while staying safely within the inner core of the card/button.
    Returns the actual (tap_x, tap_y) tapped.
    """
    if apply_jitter:
        tap_x, tap_y = compute_jittered_coord(x, y)
    else:
        tap_x, tap_y = x, y

    delay = random.uniform(config.TAP_DELAY_MIN, config.TAP_DELAY_MAX)
    time.sleep(delay)
    out = device.shell(f"input tap {tap_x} {tap_y}")
    if out and ("SecurityException" in out or "Exception" in out):
        raise RuntimeError(
            f"Tap failed on device: {out.strip()}\n"
            "On Xiaomi/Redmi devices, you MUST enable:\n"
            "  Settings -> Additional settings -> Developer options -> 'USB debugging (Security settings)'"
        )
    logger.debug(f"Tapped ({tap_x}, {tap_y}) [offset=({tap_x - x:+d}, {tap_y - y:+d})] after {delay:.2f}s delay")
    return (tap_x, tap_y)


# ── Quick sanity-check (run this file directly) ───────────────────────────────
if __name__ == "__main__":
    logger.info("=== ADB Controller — connection test ===")
    dev = connect()

    logger.info("Taking screenshot...")
    img = screencap(dev)

    path = save_screenshot(img)
    logger.success(f"All good! Screenshot saved to: {path}")
    logger.info(f"Resolution: {img.shape[1]}×{img.shape[0]} px")
