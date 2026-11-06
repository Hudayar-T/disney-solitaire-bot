"""
Refined segmentation: focus on the tableau region, separate face-up from face-down,
handle merged blue blobs, and exclude UI elements.
"""

import cv2
import numpy as np
from pathlib import Path

DEBUG_DIR = Path("tests/debug")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOTS = sorted(Path("tests/screenshots").glob("*.jpg"))

# ── Tableau ROI (excludes top bar + bottom UI row) ─────────────────────────
# Screenshots are landscape: 2400w × 1080h
# Top bar: ~80px, Bottom UI (stock/waste/undo/wild): below ~750px
TABLEAU_Y_MIN = 80
TABLEAU_Y_MAX = 750
TABLEAU_X_MIN = 300   # Tinkerbell/chest on the left
TABLEAU_X_MAX = 1500  # Right edge cutoff (skip WILD button area)

# ── Card area thresholds ────────────────────────────────────────────────────
# A single card is roughly 135w × 208h = ~28,000 px² at face-up size
# Face-down cards are slightly smaller ~120w × 190h = ~22,800 px²
# But overlapping blue contours can merge → need to handle large blobs
MIN_CARD_AREA = 12000
MAX_SINGLE_CARD_AREA = 45000   # Anything bigger = merged blob


for ss_path in SCREENSHOTS:
    img = cv2.imread(str(ss_path))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, w = img.shape[:2]
    name = ss_path.stem

    # ── Crop to tableau ROI ──────────────────────────────────────────
    tableau = img[TABLEAU_Y_MIN:TABLEAU_Y_MAX, TABLEAU_X_MIN:TABLEAU_X_MAX]
    tableau_hsv = hsv[TABLEAU_Y_MIN:TABLEAU_Y_MAX, TABLEAU_X_MIN:TABLEAU_X_MAX]

    # ── Blue card backs ──────────────────────────────────────────────
    lower_blue = np.array([95, 80, 120])
    upper_blue = np.array([125, 255, 255])
    blue_mask = cv2.inRange(tableau_hsv, lower_blue, upper_blue)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)

    # ── White card faces ─────────────────────────────────────────────
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([180, 60, 255])
    white_mask = cv2.inRange(tableau_hsv, lower_white, upper_white)

    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)

    # ── Find contours ────────────────────────────────────────────────
    blue_contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    white_contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter by area
    blue_cards = [c for c in blue_contours if cv2.contourArea(c) > MIN_CARD_AREA]
    white_cards = [c for c in white_contours if cv2.contourArea(c) > MIN_CARD_AREA]

    print(f"\n=== {name} ===")
    print(f"Blue (tableau): {len(blue_cards)} contours")
    print(f"White (tableau): {len(white_cards)} contours")

    # ── Annotate on full image ───────────────────────────────────────
    annotated = img.copy()

    # Draw tableau ROI
    cv2.rectangle(annotated,
                  (TABLEAU_X_MIN, TABLEAU_Y_MIN),
                  (TABLEAU_X_MAX, TABLEAU_Y_MAX),
                  (0, 255, 255), 2)

    for cnt in blue_cards:
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect).astype(int)
        # Offset back to full image coords
        box[:, 0] += TABLEAU_X_MIN
        box[:, 1] += TABLEAU_Y_MIN
        area = cv2.contourArea(cnt)
        center = (int(rect[0][0]) + TABLEAU_X_MIN, int(rect[0][1]) + TABLEAU_Y_MIN)
        rw, rh = rect[1]

        is_merged = area > MAX_SINGLE_CARD_AREA
        color = (0, 0, 255) if is_merged else (255, 0, 0)  # Red if merged, blue if single
        cv2.drawContours(annotated, [box], 0, color, 3)
        label = f"MERGED {area:.0f}" if is_merged else f"BACK {rw:.0f}x{rh:.0f}"
        cv2.putText(annotated, label, (center[0]-40, center[1]),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 2)

        status = "MERGED" if is_merged else "single"
        print(f"  Blue: ({center[0]},{center[1]}) {rw:.0f}×{rh:.0f} "
              f"area={area:.0f} [{status}]")

    for cnt in white_cards:
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect).astype(int)
        box[:, 0] += TABLEAU_X_MIN
        box[:, 1] += TABLEAU_Y_MIN
        area = cv2.contourArea(cnt)
        center = (int(rect[0][0]) + TABLEAU_X_MIN, int(rect[0][1]) + TABLEAU_Y_MIN)
        rw, rh = rect[1]

        cv2.drawContours(annotated, [box], 0, (0, 255, 0), 3)
        label = f"FACE {rw:.0f}x{rh:.0f}"
        cv2.putText(annotated, label, (center[0]-40, center[1]),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 2)

        print(f"  White: ({center[0]},{center[1]}) {rw:.0f}×{rh:.0f} area={area:.0f}")

    cv2.imwrite(str(DEBUG_DIR / f"{name}_refined.jpg"), annotated)

print(f"\nRefined debug images saved to {DEBUG_DIR.resolve()}")
