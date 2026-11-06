"""
Exploration script: find HSV ranges for blue card backs and white card faces.
Outputs annotated images to tests/debug/ for visual inspection.
"""

import cv2
import numpy as np
from pathlib import Path

DEBUG_DIR = Path("tests/debug")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOTS = sorted(Path("tests/screenshots").glob("*.jpg"))
print(f"Found {len(SCREENSHOTS)} screenshots: {[s.name for s in SCREENSHOTS]}")

for ss_path in SCREENSHOTS:
    img = cv2.imread(str(ss_path))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, w = img.shape[:2]
    name = ss_path.stem

    # ── Blue card backs ──────────────────────────────────────────────
    # Blue cards have a bright blue color with Mickey watermark
    # HSV: H ~100-120, S moderate-high, V moderate-high
    lower_blue = np.array([95, 80, 120])
    upper_blue = np.array([125, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # Morphological cleanup: close small gaps, remove noise
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)

    # ── White card faces ─────────────────────────────────────────────
    # White/cream cards: low saturation, high value
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([180, 60, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)

    # Cleanup
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)

    # ── Find contours ────────────────────────────────────────────────
    blue_contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    white_contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter by area (card should be at least ~20000 px²)
    MIN_CARD_AREA = 15000
    MAX_CARD_AREA = 200000

    blue_cards = [c for c in blue_contours if MIN_CARD_AREA < cv2.contourArea(c) < MAX_CARD_AREA]
    white_cards = [c for c in white_contours if MIN_CARD_AREA < cv2.contourArea(c) < MAX_CARD_AREA]

    print(f"\n=== {name} ===")
    print(f"Blue contours (all): {len(blue_contours)}, after area filter: {len(blue_cards)}")
    print(f"White contours (all): {len(white_contours)}, after area filter: {len(white_cards)}")

    # ── Annotate ─────────────────────────────────────────────────────
    annotated = img.copy()

    for cnt in blue_cards:
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect).astype(int)
        cv2.drawContours(annotated, [box], 0, (255, 0, 0), 3)  # Blue outline
        area = cv2.contourArea(cnt)
        cx, cy = int(rect[0][0]), int(rect[0][1])
        cv2.putText(annotated, f"BACK {area:.0f}", (cx-40, cy),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    for cnt in white_cards:
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect).astype(int)
        cv2.drawContours(annotated, [box], 0, (0, 255, 0), 3)  # Green outline
        area = cv2.contourArea(cnt)
        cx, cy = int(rect[0][0]), int(rect[0][1])
        cv2.putText(annotated, f"FACE {area:.0f}", (cx-40, cy),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imwrite(str(DEBUG_DIR / f"{name}_annotated.jpg"), annotated)

    # Also save the masks for debugging
    cv2.imwrite(str(DEBUG_DIR / f"{name}_blue_mask.jpg"), blue_mask)
    cv2.imwrite(str(DEBUG_DIR / f"{name}_white_mask.jpg"), white_mask)

    # Print blue contour details
    for i, cnt in enumerate(blue_cards):
        rect = cv2.minAreaRect(cnt)
        center, (rw, rh), angle = rect
        area = cv2.contourArea(cnt)
        print(f"  Blue #{i}: center=({center[0]:.0f},{center[1]:.0f}) "
              f"size=({rw:.0f}×{rh:.0f}) angle={angle:.1f}° area={area:.0f}")

    for i, cnt in enumerate(white_cards):
        rect = cv2.minAreaRect(cnt)
        center, (rw, rh), angle = rect
        area = cv2.contourArea(cnt)
        print(f"  White #{i}: center=({center[0]:.0f},{center[1]:.0f}) "
              f"size=({rw:.0f}×{rh:.0f}) angle={angle:.1f}° area={area:.0f}")

print(f"\nDebug images saved to {DEBUG_DIR.resolve()}")
