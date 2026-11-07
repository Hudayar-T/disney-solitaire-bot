"""
board/state.py
Data structures representing the Disney Solitaire game state.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Card:
    """A card in the game (either on tableau, stock, or waste)."""
    card_id: int
    rank: str               # "A", "2"..."10", "J", "Q", "K", or "BACK"
    cx: int                 # Center x
    cy: int                 # Center y
    w: int                  # Bounding box width
    h: int                  # Bounding box height
    angle: float = 0.0      # Rotation angle in degrees
    confidence: float = 1.0

    # Dependency tracking (DAG)
    blocked_by: list[int] = field(default_factory=list)  # card_ids of cards covering this card
    blocks: list[int] = field(default_factory=list)      # card_ids of cards underneath this card

    @property
    def is_face_up(self) -> bool:
        return self.rank not in ("BACK", "MYSTERY")

    @property
    def is_face_down(self) -> bool:
        return self.rank in ("BACK", "MYSTERY")

    @property
    def is_mystery(self) -> bool:
        return self.rank == "MYSTERY"

    @property
    def is_playable(self) -> bool:
        """Playable on tableau if it is face-up and not covered by any other card."""
        return self.is_face_up and len(self.blocked_by) == 0

    @property
    def rotated_rect(self) -> tuple[tuple[float, float], tuple[float, float], float]:
        """Returns OpenCV RotatedRect format: ((cx, cy), (w, h), angle)."""
        return ((float(self.cx), float(self.cy)), (float(self.w), float(self.h)), float(self.angle))

    def __repr__(self) -> str:
        status = "PLAYABLE" if self.is_playable else ("COVERED" if self.is_face_up else "FACEDOWN")
        return f"Card(id={self.card_id}, {self.rank}, pos=({self.cx},{self.cy}), {status})"


@dataclass
class BoardState:
    """Full snapshot of the board at a given moment."""
    tableau: list[Card] = field(default_factory=list)
    waste: Optional[Card] = None
    has_stock: bool = True
    has_undo: bool = False
    has_wild: bool = False

    @property
    def playable_cards(self) -> list[Card]:
        """All cards currently eligible to be tapped/played on the waste."""
        return [c for c in self.tableau if c.is_playable]

    @property
    def faceup_cards(self) -> list[Card]:
        """All face-up cards (both playable and covered)."""
        return [c for c in self.tableau if c.is_face_up]

    @property
    def facedown_cards(self) -> list[Card]:
        """All face-down cards remaining on the board."""
        return [c for c in self.tableau if c.is_face_down]

    def get_card(self, card_id: int) -> Optional[Card]:
        for c in self.tableau:
            if c.card_id == card_id:
                return c
        return None

    def __repr__(self) -> str:
        waste_str = self.waste.rank if self.waste else "None"
        playable = [c.rank for c in self.playable_cards]
        return (
            f"BoardState(waste={waste_str}, "
            f"playable={playable}, "
            f"faceup={len(self.faceup_cards)}, "
            f"facedown={len(self.facedown_cards)}, "
            f"stock={self.has_stock}, wild={self.has_wild})"
        )
