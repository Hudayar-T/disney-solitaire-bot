"""
Test the updated CardDetector on all static screenshots.
Checks:
  - Tableau cards (face-up ranks and face-down backs)
  - Waste card rank
  - Stock deck presence
  - Undo button presence
  - Wild button presence
"""

import sys
sys.path.insert(0, ".")

import cv2
from pathlib import Path
from vision.detector import CardDetector
import config

DEBUG_DIR = Path("tests/debug")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

detector = CardDetector()
screenshots = sorted(Path("tests/screenshots/algorithm").glob("*.jpg"))
print(f"Testing detector on {len(screenshots)} screenshots\n")

for ss_path in screenshots:
    img = cv2.imread(str(ss_path))
    if img is None or img.shape[:2] != (config.SCREEN_HEIGHT, config.SCREEN_WIDTH):
        continue
    name = ss_path.stem
    print(f"=== Screenshot {name} ===")

    cards = detector.detect(img)
    faceup = [c for c in cards if not c.is_face_down]
    facedown = [c for c in cards if c.is_face_down]

    print(f"  Face-up:   {len(faceup)} cards -> {[c.rank for c in faceup]}")
    print(f"  Face-down: {len(facedown)} cards")

    waste = detector.detect_waste(img)
    waste_str = f"{waste.rank} ({waste.confidence:.2f})" if waste else "NONE"
    print(f"  Waste:     {waste_str}")

    stock = detector.detect_stock_present(img)
    print(f"  Stock:     {'Present' if stock else 'Empty'}")

    undo = detector.detect_undo_present(img)
    print(f"  Undo:      {'Active' if undo else 'Inactive'}")

    wild = detector.detect_wild_present(img)
    print(f"  Wild:      {'Available' if wild else 'Unavailable'}")

    end_lvl = detector.detect_end_level_present(img)
    print(f"  End Level: {'Available' if end_lvl else 'Unavailable'}")
    print()
