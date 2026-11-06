"""
vision/detector.py
Card detection via multi-scale template matching.

Pipeline per frame:
  1. Convert screenshot to grayscale
  2. For each rank template (A–K) + BACK:
       a. Scale template to match in-game card size (scale ~1.42×)
       b. Run cv2.matchTemplate across the tableau ROI
       c. Collect all hits above threshold
  3. Non-Maximum Suppression to remove duplicate hits
  4. Return list of Detection(rank, cx, cy, confidence)

Key constants (derived from measurement):
  - In-game card: ~195w × 295h px  (portrait orientation)
  - Template size: ~136w × 210h px
  - Scale factor:  ~1.42×
  - Multi-scale range: 1.25–1.60 in steps of 0.05
"""

from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from loguru import logger
from typing import NamedTuple

import config

TEMPLATES_DIR = Path(__file__).parent / "templates"

# All valid ranks + special tokens
ALL_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_VALUES = {r: i for i, r in enumerate(ALL_RANKS)}  # A=0 … K=12


@dataclass
class Detection:
    """A single detected card on screen."""
    rank: str          # e.g. "K", "10", "A", or "BACK"
    cx: int            # center x in portrait screen coords
    cy: int            # center y in portrait screen coords
    confidence: float  # match score 0–1
    tw: int            # matched template width (for bounding box)
    th: int            # matched template height

    @property
    def is_face_down(self) -> bool:
        return self.rank == "BACK"

    def __repr__(self):
        return f"Detection(rank={self.rank}, pos=({self.cx},{self.cy}), conf={self.confidence:.2f})"


def _load_templates() -> dict[str, np.ndarray]:
    """
    Load all rank templates + BACK as grayscale OpenCV images.
    Returns dict: rank_str → grayscale ndarray
    """
    templates = {}
    for rank in ALL_RANKS + ["BACK"]:
        path = TEMPLATES_DIR / f"{rank}.jpg"
        if not path.exists():
            logger.warning(f"Template missing: {path}")
            continue
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            logger.warning(f"Failed to load template: {path}")
            continue
        templates[rank] = img
        logger.debug(f"Loaded template {rank}: {img.shape[1]}w×{img.shape[0]}h")
    logger.info(f"Loaded {len(templates)} templates: {list(templates.keys())}")
    return templates


def _nms(detections: list[Detection], iou_threshold: float = 0.4) -> list[Detection]:
    """
    Non-Maximum Suppression: remove overlapping detections, keep highest confidence.
    Two detections overlap if their bounding boxes have IoU > threshold.
    """
    if not detections:
        return []

    # Sort by confidence descending
    dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept = []

    while dets:
        best = dets.pop(0)
        kept.append(best)
        remaining = []
        for d in dets:
            # Compute IoU between best and d
            bx1, by1 = best.cx - best.tw // 2, best.cy - best.th // 2
            bx2, by2 = best.cx + best.tw // 2, best.cy + best.th // 2
            dx1, dy1 = d.cx - d.tw // 2,   d.cy - d.th // 2
            dx2, dy2 = d.cx + d.tw // 2,   d.cy + d.th // 2

            inter_x1, inter_y1 = max(bx1, dx1), max(by1, dy1)
            inter_x2, inter_y2 = min(bx2, dx2), min(by2, dy2)
            inter_w = max(0, inter_x2 - inter_x1)
            inter_h = max(0, inter_y2 - inter_y1)
            inter_area = inter_w * inter_h

            area_best = best.tw * best.th
            area_d    = d.tw * d.th
            union_area = area_best + area_d - inter_area
            iou = inter_area / union_area if union_area > 0 else 0

            if iou < iou_threshold:
                remaining.append(d)
        dets = remaining

    return kept


class CardDetector:
    """
    Detects card ranks in a screenshot using multi-scale template matching.
    Instantiate once; call detect() for each frame.
    """

    def __init__(self):
        self._templates = _load_templates()
        # Scale factors to try: covers in-game cards that are ~1.4× template size
        self._scales = config.TEMPLATE_SCALE_FACTORS
        self._threshold = config.TEMPLATE_MATCH_THRESHOLD

    def detect(
        self,
        screen: np.ndarray,
        region: tuple[int, int, int, int] | None = None,
    ) -> list[Detection]:
        """
        Detect all cards in `screen` (BGR portrait numpy array).

        Args:
            screen: full portrait screenshot (BGR)
            region: optional (x, y, w, h) ROI to search within.
                    Defaults to config.TABLEAU_ROI.

        Returns:
            List of Detection objects after NMS, sorted top-to-bottom left-to-right.
        """
        if region is None:
            x, y, w, h = config.TABLEAU_ROI
        else:
            x, y, w, h = region

        roi = screen[y:y+h, x:x+w]
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        all_detections: list[Detection] = []

        for rank, tmpl_gray in self._templates.items():
            tmpl_h, tmpl_w = tmpl_gray.shape[:2]

            for scale in self._scales:
                # Resize template to this scale
                new_w = int(tmpl_w * scale)
                new_h = int(tmpl_h * scale)
                if new_w < 10 or new_h < 10:
                    continue
                scaled = cv2.resize(tmpl_gray, (new_w, new_h), interpolation=cv2.INTER_AREA)

                # Skip if template is larger than ROI
                if new_h > gray_roi.shape[0] or new_w > gray_roi.shape[1]:
                    continue

                result = cv2.matchTemplate(gray_roi, scaled, cv2.TM_CCOEFF_NORMED)
                locs = np.where(result >= self._threshold)

                for pt_y, pt_x in zip(*locs):
                    score = float(result[pt_y, pt_x])
                    # Convert ROI-relative top-left → screen-space center
                    cx = x + pt_x + new_w // 2
                    cy = y + pt_y + new_h // 2
                    all_detections.append(Detection(
                        rank=rank, cx=cx, cy=cy,
                        confidence=score, tw=new_w, th=new_h
                    ))

        # Deduplicate with NMS
        final = _nms(all_detections, iou_threshold=0.4)

        # Sort: top-to-bottom, left-to-right
        final.sort(key=lambda d: (d.cy, d.cx))

        logger.debug(f"Detected {len(final)} cards: {[d.rank for d in final]}")
        return final

    def detect_waste(self, screen: np.ndarray) -> Detection | None:
        """
        Detect the rank of the current waste pile card.
        Uses a fixed ROI around the waste pile position from config.
        """
        wx, wy = config.WASTE_CENTER
        half_w, half_h = 110, 165  # half-card dimensions
        region = (wx - half_w, wy - half_h, half_w * 2, half_h * 2)

        # Clamp to screen bounds
        sh, sw = screen.shape[:2]
        rx = max(0, region[0])
        ry = max(0, region[1])
        rw = min(region[2], sw - rx)
        rh = min(region[3], sh - ry)

        hits = self.detect(screen, region=(rx, ry, rw, rh))
        if not hits:
            logger.warning("Could not detect waste pile rank")
            return None
        # Return highest-confidence non-BACK detection
        face_up = [d for d in hits if not d.is_face_down]
        if not face_up:
            return None
        best = max(face_up, key=lambda d: d.confidence)
        logger.debug(f"Waste pile: {best.rank} (conf={best.confidence:.2f})")
        return best
