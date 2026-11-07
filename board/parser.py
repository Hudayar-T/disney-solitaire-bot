"""
board/parser.py
Constructs a BoardState DAG from vision detections and resolves card occlusions.
"""

from __future__ import annotations
import cv2
import numpy as np
from loguru import logger
from typing import Optional

from vision.detector import CardDetector, Detection
from board.state import Card, BoardState
import config

# Minimum intersection area in px² to consider two cards physically overlapping
# Standard card area is ~28,000 px²; 2,000 px² is ~7% overlap
OVERLAP_AREA_THRESHOLD = 2000.0


def _compute_overlap_area(c1: Card, c2: Card) -> float:
    """Compute the intersection area in px² between two oriented cards."""
    r1 = c1.rotated_rect
    r2 = c2.rotated_rect
    ret, pts = cv2.rotatedRectangleIntersection(r1, r2)
    if ret == cv2.INTERSECT_NONE or pts is None or len(pts) < 3:
        return 0.0
    return float(cv2.contourArea(pts))


def build_dependency_graph(cards: list[Card]) -> None:
    """
    Computes pairwise card intersections and resolves occlusion (Z-order)
    to populate card.blocked_by and card.blocks.
    
    Z-order rules:
      1. Face-up cards are strictly rendered on top of face-down cards.
      2. When two cards of the same type (face-up vs face-up or face-down vs face-down)
         overlap vertically, the card lower on the screen (larger cy) is rendered in front of
         the card higher on the screen (smaller cy).
    """
    n = len(cards)
    for i in range(n):
        for j in range(i + 1, n):
            c1 = cards[i]
            c2 = cards[j]

            area = _compute_overlap_area(c1, c2)
            if area < OVERLAP_AREA_THRESHOLD:
                continue

            # Determine who is on top (blocker) and who is underneath (blocked)
            if c1.is_face_up and c2.is_face_down:
                top, bottom = c1, c2
            elif c2.is_face_up and c1.is_face_down:
                top, bottom = c2, c1
            else:
                # Same type: lower on screen (larger cy) is in front
                if c1.cy > c2.cy:
                    top, bottom = c1, c2
                else:
                    top, bottom = c2, c1

            top.blocks.append(bottom.card_id)
            bottom.blocked_by.append(top.card_id)
            logger.debug(f"Occlusion: Card {top.card_id} ({top.rank}) blocks Card {bottom.card_id} ({bottom.rank}) [overlap={area:.0f}px²]")


class BoardParser:
    """
    Parses full screenshots into structured BoardState objects.
    """

    def __init__(self, detector: Optional[CardDetector] = None):
        self.detector = detector or CardDetector()

    def parse(self, screen: np.ndarray) -> BoardState:
        """
        Full pipeline: vision detection -> card instantiation -> DAG construction -> BoardState.
        """
        detections = self.detector.detect(screen)

        # Convert detections to Card instances
        cards: list[Card] = []
        for idx, d in enumerate(detections):
            cards.append(Card(
                card_id=idx,
                rank=d.rank,
                cx=d.cx,
                cy=d.cy,
                w=d.tw,
                h=d.th,
                angle=d.angle,
                confidence=d.confidence,
            ))

        # Build DAG
        build_dependency_graph(cards)

        # Detect UI elements
        waste_det = self.detector.detect_waste(screen)
        waste_card = None
        if waste_det:
            waste_card = Card(
                card_id=999,
                rank=waste_det.rank,
                cx=waste_det.cx,
                cy=waste_det.cy,
                w=waste_det.tw,
                h=waste_det.th,
                confidence=waste_det.confidence,
            )

        has_stock = self.detector.detect_stock_present(screen)
        has_undo = self.detector.detect_undo_present(screen)
        has_wild = self.detector.detect_wild_present(screen)

        state = BoardState(
            tableau=cards,
            waste=waste_card,
            has_stock=has_stock,
            has_undo=has_undo,
            has_wild=has_wild,
        )

        logger.info(f"Parsed {state}")
        return state
