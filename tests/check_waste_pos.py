"""Quick check: where exactly is the waste pile in each screenshot?"""
import cv2
import sys
sys.path.insert(0, ".")

from pathlib import Path

for ss_path in sorted(Path("tests/screenshots").glob("*.jpg")):
    img = cv2.imread(str(ss_path))
    h, w = img.shape[:2]
    name = ss_path.stem
    
    # The waste pile card is at roughly the same position in all screenshots
    # Looking at screenshots: it's roughly at x=850, y=600 in landscape
    # Let's sample pixel colors at candidate positions
    candidates = [
        (830, 580), (850, 600), (870, 620), (850, 640),
        (860, 580), (860, 600), (860, 620), (860, 640),
    ]
    
    print(f"=== {name} ({w}×{h}) ===")
    for cx, cy in candidates:
        if 0 <= cy < h and 0 <= cx < w:
            b, g, r = img[cy, cx]
            print(f"  ({cx},{cy}): RGB=({r},{g},{b})")
