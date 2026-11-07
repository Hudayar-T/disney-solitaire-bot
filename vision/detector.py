"""
vision/detector.py
Hybrid card & UI detection:
  - Face-up card rank detection via multi-angle center-glyph matching
  - Face-down card detection (both blue backs and green '?' mystery cards) via HSV segmentation
  - Waste pile rank detection
  - Stock deck presence detection
  - Undo & Wild button status detection
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

ALL_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_VALUES = {r: i for i, r in enumerate(ALL_RANKS)}  # A=0 … K=12


@dataclass
class Detection:
    """A single detected card on screen."""
    rank: str          # e.g. "K", "10", "A", or "BACK"
    cx: int            # center x in screen coords
    cy: int            # center y in screen coords
    confidence: float  # match score 0–1
    tw: int            # bounding box width
    th: int            # bounding box height
    angle: float = 0.0 # rotation angle in degrees

    @property
    def is_face_down(self) -> bool:
        return self.rank in ("BACK", "MYSTERY")

    def __repr__(self):
        return f"Detection({self.rank}, pos=({self.cx},{self.cy}), conf={self.confidence:.2f}, ang={self.angle:.0f}°)"


# ── HSV ranges for facedown cards ───────────────────────────────────────────
# Blue card backs
BLUE_LOWER = np.array([95, 80, 120])
BLUE_UPPER = np.array([125, 255, 255])

# Green mystery cards ('?')
GREEN_LOWER = np.array([40, 60, 50])
GREEN_UPPER = np.array([85, 255, 220])

# Yellow/gold border on "buy +N cards" prompt (stock empty trap)
YELLOW_LOWER = np.array([15, 80, 150])
YELLOW_UPPER = np.array([40, 255, 255])
YELLOW_BORDER_THRESHOLD = 0.05  # 5% yellow pixels in stock ROI → buy prompt detected

MIN_FACEDOWN_AREA = 8000
MAX_FACEDOWN_AREA = 45000


def _nms(detections: list[Detection], iou_threshold: float = 0.30) -> list[Detection]:
    """
    Non-Maximum Suppression: remove overlapping detections, keep highest confidence.
    """
    if not detections:
        return []

    dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept = []

    while dets:
        best = dets.pop(0)
        kept.append(best)
        remaining = []
        for d in dets:
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
    Card and board state vision detector for Disney Solitaire.
    Pre-loads center-glyph templates at varied angles for fast, rotation-resilient matching.
    """

    def __init__(self):
        self._glyph_templates: list[tuple[str, np.ndarray, float, int, int]] = []
        self._load_glyph_templates()
        self._undo_tmpl = self._load_template("UNDO.jpg")
        self._wild_tmpl = self._load_template("WILD.jpg")

    def _load_template(self, filename: str) -> Optional[np.ndarray]:
        path = TEMPLATES_DIR / filename
        if not path.exists():
            logger.warning(f"Template not found: {path}")
            return None
        return cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)

    def _load_glyph_templates(self):
        """Extract center rank glyph and pre-rotate across angles."""
        angles = config.TEMPLATE_ANGLES
        for rank in ALL_RANKS:
            path = TEMPLATES_DIR / f"{rank}.jpg"
            if not path.exists():
                logger.warning(f"Rank template missing: {path}")
                continue
            full_card = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if full_card is None:
                continue

            # Extract center glyph (large rank number/letter)
            h, w = full_card.shape
            glyph = full_card[int(h * 0.35):int(h * 0.85), int(w * 0.15):int(w * 0.85)]
            gh, gw = glyph.shape

            for ang in angles:
                if ang == 0:
                    self._glyph_templates.append((rank, glyph, 0.0, gw, gh))
                else:
                    M = cv2.getRotationMatrix2D((gw / 2, gh / 2), ang, 1.0)
                    rot = cv2.warpAffine(glyph, M, (gw, gh), borderMode=cv2.BORDER_CONSTANT, borderValue=240)
                    self._glyph_templates.append((rank, rot, float(ang), gw, gh))

        logger.info(f"Loaded {len(ALL_RANKS)} rank glyphs ({len(self._glyph_templates)} rotated variants)")

    def detect_facedown(self, screen: np.ndarray, region: tuple[int, int, int, int]) -> list[Detection]:
        """
        Detect face-down cards in region via HSV segmentation.
        Differentiates between standard blue backs ("BACK") and green mystery cards ("MYSTERY").
        """
        rx, ry, rw, rh = region
        roi = screen[ry:ry+rh, rx:rx+rw]
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        blue_mask = cv2.inRange(hsv_roi, BLUE_LOWER, BLUE_UPPER)
        green_mask = cv2.inRange(hsv_roi, GREEN_LOWER, GREEN_UPPER)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)
        blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)

        facedown_cards = []

        # 1. Standard blue card backs
        contours_blue, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours_blue:
            area = cv2.contourArea(cnt)
            if area < MIN_FACEDOWN_AREA or area > MAX_FACEDOWN_AREA:
                continue
            rect = cv2.minAreaRect(cnt)
            center, (w, h), angle = rect
            cx = int(center[0]) + rx
            cy = int(center[1]) + ry
            # Standard card dimensions for occlusion DAG (even if only sliver is exposed)
            card_w = max(int(min(w, h)), 136)
            card_h = max(int(max(w, h)), 185)
            facedown_cards.append(Detection(
                rank="BACK",
                cx=cx, cy=cy,
                confidence=1.0,
                tw=card_w,
                th=card_h,
                angle=angle,
            ))

        # 2. Green mystery question-mark cards
        contours_green, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours_green:
            area = cv2.contourArea(cnt)
            if area < MIN_FACEDOWN_AREA or area > MAX_FACEDOWN_AREA:
                continue
            rect = cv2.minAreaRect(cnt)
            center, (w, h), angle = rect
            cx = int(center[0]) + rx
            cy = int(center[1]) + ry
            card_w = max(int(min(w, h)), 136)
            card_h = max(int(max(w, h)), 185)
            facedown_cards.append(Detection(
                rank="MYSTERY",
                cx=cx, cy=cy,
                confidence=1.0,
                tw=card_w,
                th=card_h,
                angle=angle,
            ))

        return facedown_cards

    def detect_faceup(self, screen: np.ndarray, region: tuple[int, int, int, int]) -> list[Detection]:
        """Detect face-up card ranks in region using multi-angle glyph matching."""
        rx, ry, rw, rh = region
        roi = screen[ry:ry+rh, rx:rx+rw]
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        hits: list[Detection] = []
        threshold = config.TEMPLATE_MATCH_THRESHOLD

        for rank, tmpl, ang, gw, gh in self._glyph_templates:
            if gh > gray_roi.shape[0] or gw > gray_roi.shape[1]:
                continue

            res = cv2.matchTemplate(gray_roi, tmpl, cv2.TM_CCOEFF_NORMED)
            locs = np.where(res >= threshold)

            for py, px in zip(*locs):
                cx = rx + px + gw // 2
                cy = ry + py + gh // 2
                hits.append(Detection(
                    rank=rank,
                    cx=cx, cy=cy,
                    confidence=float(res[py, px]),
                    tw=gw + 40,
                    th=gh + 80,
                    angle=-ang,
                ))

        return _nms(hits, iou_threshold=0.30)

    def detect(self, screen: np.ndarray, region: tuple[int, int, int, int] | None = None) -> list[Detection]:
        """
        Detect all tableau cards (both face-down and face-up).
        Returns combined list of Detections sorted top-to-bottom, left-to-right.
        """
        if region is None:
            region = config.TABLEAU_ROI

        facedown = self.detect_facedown(screen, region)
        faceup = self.detect_faceup(screen, region)

        all_cards = facedown + faceup
        all_cards.sort(key=lambda d: (d.cy, d.cx))
        logger.debug(f"Detected {len(all_cards)} tableau cards ({len(faceup)} face-up, {len(facedown)} face-down)")
        return all_cards

    def detect_waste(self, screen: np.ndarray) -> Optional[Detection]:
        """
        Detect the rank of the current waste pile card (bottom-center).
        """
        wx, wy = config.WASTE_CENTER
        hw, hh = 110, 160
        region = (max(0, wx - hw), max(0, wy - hh), hw * 2, hh * 2)

        faceup = self.detect_faceup(screen, region)
        if not faceup:
            # Check if a WILD card is sitting on the waste pile
            if self._wild_tmpl is not None:
                roi = screen[max(0, wy-hh):min(screen.shape[0], wy+hh), max(0, wx-hw):min(screen.shape[1], wx+hw)]
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                th, tw = self._wild_tmpl.shape
                wild_body = self._wild_tmpl[int(th * 0.3):, :]
                res = cv2.matchTemplate(gray, wild_body, cv2.TM_CCOEFF_NORMED)
                if float(res.max()) >= 0.70:
                    logger.debug(f"Waste pile: WILD (conf={float(res.max()):.2f})")
                    return Detection(rank="WILD", cx=wx, cy=wy, confidence=float(res.max()), tw=tw, th=th)

            logger.warning("Waste pile card not detected")
            return None
        best = max(faceup, key=lambda d: d.confidence)
        logger.debug(f"Waste pile: {best.rank} (conf={best.confidence:.2f})")
        return best

    def detect_normal_stock_present(self, screen: np.ndarray) -> bool:
        """Check if regular blue-backed cards remain in the stock pile.
        
        IMPORTANT: First checks for the yellow/gold border that indicates
        a paid "buy +N cards" prompt. If the yellow border is detected,
        the stock is treated as EMPTY regardless of blue pixel presence
        (the buy prompt still shows blue card imagery inside the border).
        """
        sx, sy = config.STOCK_CENTER
        hw, hh = 100, 100
        roi = screen[sy-hh:sy+hh, sx-hw:sx+hw]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Check for yellow/gold border (buy prompt trap)
        yellow_mask = cv2.inRange(hsv, YELLOW_LOWER, YELLOW_UPPER)
        yellow_ratio = float(np.count_nonzero(yellow_mask)) / yellow_mask.size
        if yellow_ratio > YELLOW_BORDER_THRESHOLD:
            logger.info(f"Stock pile has yellow border ({yellow_ratio*100:.1f}% yellow) — 'buy cards' prompt detected, treating as EMPTY")
            return False

        # No yellow border — check for actual blue cards
        small_roi = screen[sy-40:sy+40, sx-40:sx+40]
        hsv_small = cv2.cvtColor(small_roi, cv2.COLOR_BGR2HSV)
        blue_mask = cv2.inRange(hsv_small, BLUE_LOWER, BLUE_UPPER)
        ratio = float(np.count_nonzero(blue_mask)) / blue_mask.size
        return ratio > 0.40

    def detect_stock_has_wild(self, screen: np.ndarray) -> bool:
        """Check if the stock pile currently holds a bought/expensive WILD card."""
        if self._wild_tmpl is None:
            return False
        sx, sy = config.STOCK_CENTER
        hw, hh = 100, 120
        roi = screen[max(0, sy-hh):min(screen.shape[0], sy+hh), max(0, sx-hw):min(screen.shape[1], sx+hw)]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        th, tw = self._wild_tmpl.shape
        wild_body = self._wild_tmpl[int(th * 0.3):, :]
        res = cv2.matchTemplate(gray, wild_body, cv2.TM_CCOEFF_NORMED)
        return float(res.max()) >= 0.70

    def detect_stock_present(self, screen: np.ndarray) -> bool:
        """Check if any cards (normal or WILD) remain in the stock pile."""
        return self.detect_normal_stock_present(screen) or self.detect_stock_has_wild(screen)

    def detect_undo_present(self, screen: np.ndarray) -> bool:
        """Check if UNDO button is visible and active."""
        if self._undo_tmpl is None:
            return False
        ux, uy = config.UNDO_CENTER
        hw, hh = 90, 80
        roi = screen[uy-hh:uy+hh, ux-hw:ux+hw]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(gray, self._undo_tmpl, cv2.TM_CCOEFF_NORMED)
        max_val = float(res.max())
        return max_val >= 0.80

    def detect_wild_present(self, screen: np.ndarray) -> bool:
        """Check if WILD card is available (matches lower 70% to ignore badge count)."""
        if self._wild_tmpl is None:
            return False
        wx, wy = config.WILD_CENTER
        hw, hh = 80, 120
        roi = screen[wy-hh:wy+hh, wx-hw:wx+hw]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Match lower 70% of wild card
        th, tw = self._wild_tmpl.shape
        wild_body = self._wild_tmpl[int(th * 0.3):, :]
        res = cv2.matchTemplate(gray, wild_body, cv2.TM_CCOEFF_NORMED)
        max_val = float(res.max())
        return max_val >= 0.75
