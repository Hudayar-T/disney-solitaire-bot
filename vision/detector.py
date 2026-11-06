"""
vision/detector.py
Hybrid card detection: template matching for face-up ranks + HSV segmentation for face-down cards.

Pipeline per frame:
  1. HSV segmentation to find face-down (blue) card regions
  2. Template matching across tableau for face-up card rank identification
  3. NMS to remove duplicate hits
  4. Return list of Detection objects (face-up with rank, face-down with position)

Key constants (derived from measurements):
  - In-game face-up card:  ~135w × 208h px (in landscape screenshots)
  - In-game face-down card: ~121w × 193h px
  - Template size: ~136w × 210h px (nearly 1:1 with face-up cards)
"""

from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from loguru import logger
from typing import Optional

import config

TEMPLATES_DIR = Path(__file__).parent / "templates"

# All valid ranks + special tokens
ALL_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_VALUES = {r: i for i, r in enumerate(ALL_RANKS)}  # A=0 … K=12


@dataclass
class Detection:
    """A single detected card on screen."""
    rank: str          # e.g. "K", "10", "A", or "BACK"
    cx: int            # center x in screen coords
    cy: int            # center y in screen coords
    confidence: float  # match score 0–1 (1.0 for face-down cards)
    tw: int            # bounding box width
    th: int            # bounding box height
    angle: float = 0.0 # rotation angle (for face-down cards)

    @property
    def is_face_down(self) -> bool:
        return self.rank == "BACK"

    def __repr__(self):
        return f"Detection(rank={self.rank}, pos=({self.cx},{self.cy}), conf={self.confidence:.2f})"


# ── HSV ranges (calibrated from screenshots) ────────────────────────────────
BLUE_LOWER = np.array([95, 80, 120])
BLUE_UPPER = np.array([125, 255, 255])

# ── Face-down card area thresholds ───────────────────────────────────────────
MIN_FACEDOWN_AREA = 12000
MAX_FACEDOWN_AREA = 45000  # Larger = merged blob (skip or split)


def _load_templates() -> dict[str, np.ndarray]:
    """
    Load all rank templates as grayscale OpenCV images.
    Returns dict: rank_str → grayscale ndarray
    """
    templates = {}
    for rank in ALL_RANKS:
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


def _detect_facedown_cards(
    screen: np.ndarray,
    region: tuple[int, int, int, int],
) -> list[Detection]:
    """
    Use HSV color segmentation to find face-down (blue) cards.
    Returns Detection objects with rank="BACK".
    """
    x, y, w, h = region
    roi = screen[y:y+h, x:x+w]
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Blue mask
    blue_mask = cv2.inRange(hsv_roi, BLUE_LOWER, BLUE_UPPER)

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)

    # Find contours
    contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_FACEDOWN_AREA:
            continue
        if area > MAX_FACEDOWN_AREA:
            # Merged blob — skip for now (could split later)
            logger.debug(f"Skipping merged blue blob: area={area:.0f}")
            continue

        rect = cv2.minAreaRect(cnt)
        center, (rw, rh), angle = rect

        # Convert ROI-relative → screen-space
        cx = int(center[0]) + x
        cy = int(center[1]) + y

        detections.append(Detection(
            rank="BACK",
            cx=cx, cy=cy,
            confidence=1.0,
            tw=int(max(rw, rh)),  # Normalize: longer side as width
            th=int(min(rw, rh)),
            angle=angle,
        ))

    logger.debug(f"Detected {len(detections)} face-down cards via HSV segmentation")
    return detections


def _detect_faceup_cards(
    screen: np.ndarray,
    templates: dict[str, np.ndarray],
    region: tuple[int, int, int, int],
    scales: list[float],
    threshold: float,
) -> list[Detection]:
    """
    Use multi-scale template matching to find face-up cards and identify their rank.
    """
    x, y, w, h = region
    roi = screen[y:y+h, x:x+w]
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    all_detections: list[Detection] = []

    for rank, tmpl_gray in templates.items():
        tmpl_h, tmpl_w = tmpl_gray.shape[:2]

        for scale in scales:
            new_w = int(tmpl_w * scale)
            new_h = int(tmpl_h * scale)
            if new_w < 10 or new_h < 10:
                continue
            scaled = cv2.resize(tmpl_gray, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # Skip if template is larger than ROI
            if new_h > gray_roi.shape[0] or new_w > gray_roi.shape[1]:
                continue

            result = cv2.matchTemplate(gray_roi, scaled, cv2.TM_CCOEFF_NORMED)
            locs = np.where(result >= threshold)

            for pt_y, pt_x in zip(*locs):
                score = float(result[pt_y, pt_x])
                # Convert ROI-relative top-left → screen-space center
                cx = x + pt_x + new_w // 2
                cy = y + pt_y + new_h // 2
                all_detections.append(Detection(
                    rank=rank, cx=cx, cy=cy,
                    confidence=score, tw=new_w, th=new_h
                ))

    return all_detections


class CardDetector:
    """
    Hybrid card detector: HSV segmentation for face-down + template matching for face-up.
    Instantiate once; call detect() for each frame.
    """

    def __init__(self):
        self._templates = _load_templates()
        self._scales = config.TEMPLATE_SCALE_FACTORS
        self._threshold = config.TEMPLATE_MATCH_THRESHOLD

    def detect(
        self,
        screen: np.ndarray,
        region: tuple[int, int, int, int] | None = None,
    ) -> list[Detection]:
        """
        Detect all cards in `screen` (BGR numpy array, landscape or portrait).

        Args:
            screen: full screenshot (BGR)
            region: optional (x, y, w, h) ROI to search within.
                    Defaults to config.TABLEAU_ROI.

        Returns:
            List of Detection objects after NMS, sorted top-to-bottom left-to-right.
        """
        if region is None:
            region = config.TABLEAU_ROI

        # 1. Face-down cards via HSV segmentation
        facedown = _detect_facedown_cards(screen, region)

        # 2. Face-up cards via template matching
        faceup = _detect_faceup_cards(
            screen, self._templates, region,
            self._scales, self._threshold
        )

        # 3. NMS on face-up (template hits often overlap)
        faceup = _nms(faceup, iou_threshold=0.4)

        # 4. Combine and sort: top-to-bottom, left-to-right
        all_cards = facedown + faceup
        all_cards.sort(key=lambda d: (d.cy, d.cx))

        logger.debug(
            f"Total: {len(all_cards)} cards "
            f"({len(facedown)} face-down, {len(faceup)} face-up)"
        )
        return all_cards

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

        # Only template matching for waste (it's always face-up)
        hits = _detect_faceup_cards(
            screen, self._templates, (rx, ry, rw, rh),
            self._scales, self._threshold
        )
        hits = _nms(hits, iou_threshold=0.4)

        if not hits:
            logger.warning("Could not detect waste pile rank")
            return None
        best = max(hits, key=lambda d: d.confidence)
        logger.debug(f"Waste pile: {best.rank} (conf={best.confidence:.2f})")
        return best
