"""
Test the hybrid CardDetector on all static screenshots.
Outputs annotated images showing face-up (green) and face-down (blue) detections.
"""

import sys
sys.path.insert(0, ".")

import cv2
import numpy as np
from pathlib import Path
from vision.detector import CardDetector

DEBUG_DIR = Path("tests/debug")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOTS = sorted(Path("tests/screenshots").glob("*.jpg"))
print(f"Testing on {len(SCREENSHOTS)} screenshots\n")

detector = CardDetector()

for ss_path in SCREENSHOTS:
    img = cv2.imread(str(ss_path))
    name = ss_path.stem

    print(f"=== {name} ({img.shape[1]}×{img.shape[0]}) ===")

    # Detect all cards in tableau
    detections = detector.detect(img)

    facedown = [d for d in detections if d.is_face_down]
    faceup = [d for d in detections if not d.is_face_down]

    print(f"  Face-down: {len(facedown)}")
    print(f"  Face-up:   {len(faceup)}")
    print(f"  Ranks:     {[d.rank for d in faceup]}")

    # Detect waste pile
    waste = detector.detect_waste(img)
    if waste:
        print(f"  Waste:     {waste.rank} (conf={waste.confidence:.2f})")
    else:
        print(f"  Waste:     NOT DETECTED")

    # ── Annotate ─────────────────────────────────────────────────────
    annotated = img.copy()

    for d in facedown:
        # Draw rotated bounding box for face-down
        half_w, half_h = d.tw // 2, d.th // 2
        box = np.array([
            [d.cx - half_w, d.cy - half_h],
            [d.cx + half_w, d.cy - half_h],
            [d.cx + half_w, d.cy + half_h],
            [d.cx - half_w, d.cy + half_h],
        ])
        cv2.drawContours(annotated, [box], 0, (255, 100, 0), 2)
        cv2.putText(annotated, "BACK", (d.cx - 20, d.cy + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 100, 0), 2)

    for d in faceup:
        half_w, half_h = d.tw // 2, d.th // 2
        cv2.rectangle(annotated,
                      (d.cx - half_w, d.cy - half_h),
                      (d.cx + half_w, d.cy + half_h),
                      (0, 255, 0), 2)
        label = f"{d.rank} ({d.confidence:.2f})"
        cv2.putText(annotated, label, (d.cx - 30, d.cy - half_h - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Mark waste pile
    if waste:
        cv2.circle(annotated, (waste.cx, waste.cy), 10, (0, 0, 255), -1)
        cv2.putText(annotated, f"WASTE: {waste.rank}",
                    (waste.cx - 40, waste.cy - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    cv2.imwrite(str(DEBUG_DIR / f"{name}_detector.jpg"), annotated)
    print()

print(f"Annotated images saved to {DEBUG_DIR.resolve()}")
