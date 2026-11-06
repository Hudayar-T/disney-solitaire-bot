"""Measure waste pile and stock pile positions from screenshots."""
import cv2
import numpy as np
import sys
sys.path.insert(0, ".")

from pathlib import Path

DEBUG_DIR = Path("tests/debug")

for ss_path in sorted(Path("tests/screenshots").glob("*.jpg")):
    img = cv2.imread(str(ss_path))
    h, w = img.shape[:2]
    name = ss_path.stem
    
    # Scan the bottom portion for the face-up waste card
    # The waste card is white/cream against the background
    # Let's look at the bottom 40% of the image
    bottom = img[int(h*0.65):, :]
    hsv_bottom = cv2.cvtColor(bottom, cv2.COLOR_BGR2HSV)
    
    # White card mask
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([180, 60, 255])
    white_mask = cv2.inRange(hsv_bottom, lower_white, upper_white)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter for card-sized white regions
    y_offset = int(h*0.65)
    print(f"=== {name} ===")
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 10000:
            rect = cv2.minAreaRect(cnt)
            center = (int(rect[0][0]), int(rect[0][1]) + y_offset)
            rw, rh = rect[1]
            print(f"  White region at ({center[0]},{center[1]}) "
                  f"size={rw:.0f}×{rh:.0f} area={area:.0f}")
    
    # Also look for the blue stock pile  
    lower_blue = np.array([95, 80, 120])
    upper_blue = np.array([125, 255, 255])
    blue_mask = cv2.inRange(hsv_bottom, lower_blue, upper_blue)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 10000:
            rect = cv2.minAreaRect(cnt)
            center = (int(rect[0][0]), int(rect[0][1]) + y_offset)
            rw, rh = rect[1]
            print(f"  Blue region at ({center[0]},{center[1]}) "
                  f"size={rw:.0f}×{rh:.0f} area={area:.0f}")
