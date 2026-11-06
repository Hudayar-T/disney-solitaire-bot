"""
adb_controller.py
Handles all ADB communication: device connection, screen capture, and taps.
"""

import io
import random
import time
from pathlib import Path

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


def screencap(device) -> Image.Image:
    """
    Capture a screenshot from the device.
    Returns a PIL Image (RGB).
    """
    try:
        png_bytes = device.shell("screencap -p", encoding=None)
        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        logger.debug(f"Screenshot captured: {image.size}")
        return image
    except AdbError as e:
        raise RuntimeError(f"screencap failed: {e}") from e


def save_screenshot(image: Image.Image, folder: str = "tests/screenshots") -> Path:
    """
    Save a PIL Image to disk with a timestamp filename.
    Returns the saved file path.
    """
    out_dir = Path(folder)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"screen_{timestamp}.png"
    image.save(path)
    logger.info(f"Screenshot saved: {path}")
    return path


def tap(device, x: int, y: int) -> None:
    """
    Send a tap event to the device at (x, y).
    Applies a small random jitter to humanise timing.
    """
    jitter = random.uniform(config.TAP_DELAY_MIN, config.TAP_DELAY_MAX)
    time.sleep(jitter)
    device.shell(f"input tap {x} {y}")
    logger.debug(f"Tapped ({x}, {y}) after {jitter:.2f}s delay")


# ── Quick sanity-check (run this file directly) ───────────────────────────────
if __name__ == "__main__":
    logger.info("=== ADB Controller — connection test ===")
    dev = connect()

    logger.info("Taking screenshot...")
    img = screencap(dev)

    path = save_screenshot(img)
    logger.success(f"All good! Screenshot saved to: {path}")
    logger.info(f"Resolution reported by PIL: {img.size[0]}×{img.size[1]} px")
