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
from concurrent.futures import ThreadPoolExecutor
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
        self._upright_glyph_templates = [t for t in self._glyph_templates if t[2] == 0.0]
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._undo_tmpl = self._load_template("UNDO.jpg")
        self._wild_tmpl = self._load_template("WILD.jpg")
        self._end_level_tmpl = self._load_template("end_level.png")
        self.last_wild_coord: tuple[int, int] = config.WILD_CENTER
        self.last_end_level_coord: tuple[int, int] = config.END_LEVEL_CENTER

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

    def detect_faceup(
        self,
        screen: np.ndarray,
        region: tuple[int, int, int, int],
        upright_only: bool = False,
    ) -> list[Detection]:
        """Detect face-up card ranks in region using multi-angle glyph matching in parallel."""
        rx, ry, rw, rh = region
        roi = screen[ry:ry+rh, rx:rx+rw]
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        threshold = config.TEMPLATE_MATCH_THRESHOLD
        templates = self._upright_glyph_templates if upright_only else self._glyph_templates

        def _match_template(item: tuple[str, np.ndarray, float, int, int]) -> list[Detection]:
            rank, tmpl, ang, gw, gh = item
            if gh > gray_roi.shape[0] or gw > gray_roi.shape[1]:
                return []

            res = cv2.matchTemplate(gray_roi, tmpl, cv2.TM_CCOEFF_NORMED)
            locs = np.where(res >= threshold)
            tmpl_hits: list[Detection] = []
            for py, px in zip(*locs):
                cx = rx + px + gw // 2
                cy = ry + py + gh // 2
                tmpl_hits.append(Detection(
                    rank=rank,
                    cx=cx, cy=cy,
                    confidence=float(res[py, px]),
                    tw=gw + 40,
                    th=gh + 80,
                    angle=-ang,
                ))
            return tmpl_hits

        results = self._executor.map(_match_template, templates)
        hits: list[Detection] = [hit for sublist in results for hit in sublist]

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
        Waste pile card is always upright, so only upright templates are checked.
        """
        wx, wy = config.WASTE_CENTER
        hw, hh = 110, 160
        region = (max(0, wx - hw), max(0, wy - hh), hw * 2, hh * 2)

        faceup = self.detect_faceup(screen, region, upright_only=True)
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

        IMPORTANT: Detects the yellow/gold *border* that indicates a paid
        "buy +N cards" prompt, while NOT being fooled by yellow WILD cards
        that may be sitting in the stock pile.

        Strategy — WILD-first disambiguation:
          Before checking for the yellow buy-prompt border, we first run a
          template match for a WILD card in the stock area.  If a WILD card is
          detected there, any yellow in the ROI belongs to the WILD card, NOT
          to a buy-prompt border.  We skip the yellow check entirely in that
          case and fall straight through to the blue-card check.

          If no WILD is found in the stock, yellow in the ROI reliably signals
          the buy-prompt, and we return False (stock empty / do not tap).
        """
        sx, sy = config.STOCK_CENTER
        hw, hh = 100, 100
        roi = screen[sy-hh:sy+hh, sx-hw:sx+hw]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        yellow_mask = cv2.inRange(hsv, YELLOW_LOWER, YELLOW_UPPER)
        yellow_ratio = float(np.count_nonzero(yellow_mask)) / yellow_mask.size

        if yellow_ratio > YELLOW_BORDER_THRESHOLD:
            # Yellow detected — could be buy-prompt OR a WILD card in the stock.
            # 1. Disambiguate with template match if WILD card is on top of the stock.
            wild_in_stock = self.detect_stock_has_wild(screen)
            if wild_in_stock:
                # Yellow comes from the WILD card on top — NOT a buy prompt.
                logger.debug(
                    f"Yellow in stock ROI ({yellow_ratio*100:.1f}%) but WILD card "
                    f"detected in stock — not a buy-prompt, continuing blue check"
                )
            else:
                # 2. Check if yellow forms a full perimeter button border.
                # A real buy-prompt button has a gold border wrapping the entire perimeter,
                # including the right half (x > sx).
                # A buried card stacked underneath fans out exclusively to the LEFT,
                # leaving the right side with 0 yellow pixels.
                right_mask = yellow_mask[:, hw:]
                right_yellow_ratio = float(np.count_nonzero(right_mask)) / right_mask.size

                if right_yellow_ratio >= 0.03:
                    # Confirmed buy-prompt border framing the card
                    logger.info(
                        f"Stock buy-prompt detected ({yellow_ratio*100:.1f}% yellow, "
                        f"right border {right_yellow_ratio*100:.1f}%) — treating stock as EMPTY"
                    )
                    return False
                else:
                    # Yellow is only on left stacked edge (buried WILD in deck)
                    logger.debug(
                        f"Yellow in stock ROI ({yellow_ratio*100:.1f}%) confined to left edge "
                        f"(right={right_yellow_ratio*100:.1f}%) — deck with buried card, continuing blue check"
                    )

        # No buy prompt — check for actual blue cards in the central area
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
        """Check if WILD card is available in bottom-right corner (matches lower 70% to ignore badge count).
        Searches config.WILD_ROI to handle screen orientation safe-area shifts (e.g. camera notch padding).
        """
        if self._wild_tmpl is None:
            return False
        rx, ry, rw, rh = config.WILD_ROI
        roi = screen[ry:min(screen.shape[0], ry+rh), rx:min(screen.shape[1], rx+rw)]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Match lower 70% of wild card
        th, tw = self._wild_tmpl.shape
        wild_body = self._wild_tmpl[int(th * 0.3):, :]
        res = cv2.matchTemplate(gray, wild_body, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= 0.75:
            cx = rx + max_loc[0] + tw // 2
            cy = ry + max_loc[1] - int(th * 0.3) + th // 2
            self.last_wild_coord = (cx, cy)
            logger.debug(f"WILD button detected at ({cx}, {cy}) (conf={max_val:.2f})")
            return True

        return False

    def detect_has_free_wild(self, screen: np.ndarray) -> bool:
        """
        Check if the player currently owns an available WILD card.
        Indicated by a red circular badge (with number e.g. '1') at the top-right of the WILD card.
        """
        rx, ry, rw, rh = config.WILD_BADGE_ROI
        sh, sw = screen.shape[:2]
        crop = screen[max(0, ry):min(sh, ry + rh), max(0, rx):min(sw, rx + rw)]
        if crop.size == 0:
            return False

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        r1 = cv2.inRange(hsv, (0, 140, 140), (10, 255, 255))
        r2 = cv2.inRange(hsv, (170, 140, 140), (180, 255, 255))
        red_count = cv2.countNonZero(r1 | r2)

        has_free = red_count > 300
        logger.debug(f"Free WILD badge check: red_px={red_count} -> {has_free}")
        return has_free

    def detect_wild_cost(self, screen: np.ndarray) -> Optional[int]:
        """
        Detects the coin cost to purchase a WILD card if the player doesn't already own one.
        """
        if not hasattr(self, "_digit_detector") or self._digit_detector is None:
            from vision.digit_detector import DigitDetector
            self._digit_detector = DigitDetector()

        return self._digit_detector.parse_number(
            screen,
            roi=config.WILD_COST_ROI,
            mode="white_on_dark",
            threshold=config.DIGIT_MATCH_THRESHOLD,
        )

    def detect_end_level_present(self, screen: np.ndarray) -> bool:
        """Check if END LEVEL button is visible in bottom-left corner."""
        rx, ry, rw, rh = config.END_LEVEL_ROI
        roi = screen[ry:min(screen.shape[0], ry+rh), rx:min(screen.shape[1], rx+rw)]
        if roi.size == 0:
            return False

        if self._end_level_tmpl is not None:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            th, tw = self._end_level_tmpl.shape
            if gray.shape[0] >= th and gray.shape[1] >= tw:
                res = cv2.matchTemplate(gray, self._end_level_tmpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val >= 0.75:
                    cx = rx + max_loc[0] + tw // 2
                    cy = ry + max_loc[1] + th // 2
                    self.last_end_level_coord = (cx, cy)
                    logger.debug(f"END LEVEL button detected at ({cx}, {cy}) (conf={max_val:.2f})")
                    return True

        # Fallback: check prominent red pill color in the ROI
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, 150, 120), (10, 255, 255)) | cv2.inRange(hsv, (170, 150, 120), (180, 255, 255))
        red_ratio = float((mask > 0).mean())
        if red_ratio >= 0.35:
            self.last_end_level_coord = config.END_LEVEL_CENTER
            logger.debug(f"END LEVEL button detected by HSV red ratio ({red_ratio:.2f})")
            return True

        return False
