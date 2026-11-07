"""
tests/test_stock_yellow_bug.py

Regression test for the "WILD card yellow mistaken for buy-prompt yellow border" bug.

Scenarios tested:
  1. Bug screenshot — stock has blue cards WITH WILD cards alongside:
     detect_normal_stock_present() must return True (stock has blue cards, the yellow
     comes from WILD cards, not a buy-prompt).
  2. Synthetic buy-prompt — yellow in stock ROI but no WILD template match:
     detect_normal_stock_present() must return False.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from vision.detector import CardDetector, YELLOW_LOWER, YELLOW_UPPER


BUG_SCREENSHOT = (
    Path(__file__).parent.parent
    / "bugs_to_be_fixed"
    / "yellow_of_wild_cards_mistaken_for_yellow_border_of_stock.jpg"
)


def load_screenshot(path: Path) -> np.ndarray:
    img = cv2.imread(str(path))
    assert img is not None, f"Could not load {path}"
    return img


# ---------------------------------------------------------------------------
# Test 1 — Bug screenshot: WILD cards alongside blue cards in stock
# ---------------------------------------------------------------------------
def test_wild_in_stock_not_treated_as_buy_prompt():
    """
    The bug screenshot has WILD cards (yellow) alongside blue cards in the stock.
    detect_normal_stock_present() must return True (blue cards still present).
    Previously this would have returned False if yellow bled into the ROI.
    """
    screen = load_screenshot(BUG_SCREENSHOT)
    detector = CardDetector()
    result = detector.detect_normal_stock_present(screen)
    assert result is True, (
        "Expected detect_normal_stock_present() == True when stock contains both "
        f"blue cards and WILD cards (yellow), but got {result}"
    )
    print("✅ PASS: bug screenshot — WILD-in-stock not mistaken for buy-prompt; "
          "blue cards correctly detected.")


# ---------------------------------------------------------------------------
# Test 2 — Synthetic buy-prompt: yellow in ROI, NO WILD template match
# ---------------------------------------------------------------------------
def test_buy_prompt_detected_when_no_wild():
    """
    Craft a scenario with yellow in the stock ROI and no WILD in stock.
    detect_normal_stock_present() must return False.

    We stub detect_stock_has_wild() to return False (no WILD template found)
    and paint yellow into the stock ROI to trigger the buy-prompt path.
    """
    # Build a fake screen filled with blue (simulates normal stock)
    screen = np.full((config.SCREEN_HEIGHT, config.SCREEN_WIDTH, 3), 128, dtype=np.uint8)
    sx, sy = config.STOCK_CENTER

    # Paint a yellow/gold colour throughout the ±100 stock ROI (buy-prompt look)
    gold_bgr = np.array(
        cv2.cvtColor(np.array([[[25, 200, 220]]], dtype=np.uint8), cv2.COLOR_HSV2BGR)[0, 0],
        dtype=np.uint8,
    )
    screen[sy - 100 : sy + 100, sx - 100 : sx + 100] = gold_bgr

    # Also ensure the central ±40 area is NOT dominated by blue (so the fall-through
    # blue check also returns False, confirming the method returns False overall).
    # (central area is gold, not blue)

    detector = CardDetector()

    # Stub detect_stock_has_wild to return False → yellow must be buy-prompt
    with patch.object(detector, "detect_stock_has_wild", return_value=False):
        result = detector.detect_normal_stock_present(screen)

    assert result is False, (
        "Expected detect_normal_stock_present() == False for a fully yellow ROI "
        f"with no WILD in stock (buy-prompt), but got {result}"
    )
    print("✅ PASS: synthetic buy-prompt (yellow ROI, no WILD) correctly returns False.")


# ---------------------------------------------------------------------------
# Test 3 — Synthetic WILD-in-stock: yellow in ROI + WILD template found
# ---------------------------------------------------------------------------
def test_yellow_roi_with_wild_in_stock_not_buy_prompt():
    """
    Yellow in stock ROI but detect_stock_has_wild() says True →
    yellow comes from WILD card, not buy-prompt.
    If blue cards also exist in the ±40 center, must return True.
    """
    screen = np.full((config.SCREEN_HEIGHT, config.SCREEN_WIDTH, 3), 128, dtype=np.uint8)
    sx, sy = config.STOCK_CENTER

    # Paint yellow in the ±100 stock ROI (simulates WILD card yellow)
    gold_bgr = np.array(
        cv2.cvtColor(np.array([[[25, 200, 220]]], dtype=np.uint8), cv2.COLOR_HSV2BGR)[0, 0],
        dtype=np.uint8,
    )
    screen[sy - 100 : sy + 100, sx - 100 : sx + 100] = gold_bgr

    # Paint blue in the ±40 inner area (blue cards behind the WILD)
    blue_bgr = np.array(
        cv2.cvtColor(np.array([[[110, 200, 200]]], dtype=np.uint8), cv2.COLOR_HSV2BGR)[0, 0],
        dtype=np.uint8,
    )
    screen[sy - 40 : sy + 40, sx - 40 : sx + 40] = blue_bgr

    detector = CardDetector()

    # Stub detect_stock_has_wild to return True → yellow is WILD, not buy-prompt
    with patch.object(detector, "detect_stock_has_wild", return_value=True):
        result = detector.detect_normal_stock_present(screen)

    assert result is True, (
        "Expected detect_normal_stock_present() == True when WILD is in stock "
        f"(yellow from WILD) and blue cards are in center, but got {result}"
    )
    print("✅ PASS: synthetic WILD-in-stock with blue cards — yellow not treated as buy-prompt.")


# ---------------------------------------------------------------------------
# Test 4 — proposed_move.jpg: real buy-prompt (+5 cards for 7,500 coins)
# ---------------------------------------------------------------------------
def test_buy_prompt_on_proposed_move_screenshot():
    """
    proposed_move.jpg shows the stock has transformed into a '+5 cards for 7,500 coins'
    buy-prompt (yellow/gold border, blue card face with '+5' text).
    No WILD card is in the stock area.
    detect_normal_stock_present() must return False.
    """
    screenshot = (
        Path(__file__).parent
        / "screenshots"
        / "proposed_move.jpg"
    )
    screen = load_screenshot(screenshot)
    detector = CardDetector()
    result = detector.detect_normal_stock_present(screen)
    assert result is False, (
        "Expected detect_normal_stock_present() == False for proposed_move.jpg "
        f"(buy-prompt with yellow border, no WILD), but got {result}"
    )
    print("✅ PASS: proposed_move.jpg — buy-prompt correctly detected as EMPTY stock.")


if __name__ == "__main__":
    test_wild_in_stock_not_treated_as_buy_prompt()
    test_buy_prompt_detected_when_no_wild()
    test_yellow_roi_with_wild_in_stock_not_buy_prompt()
    test_buy_prompt_on_proposed_move_screenshot()
    print("\nAll tests passed.")
