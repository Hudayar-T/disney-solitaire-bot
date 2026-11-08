"""
engine/solver.py
Decision engine for Disney Solitaire:
  - Generates legal tableau moves (+-1 rank with A <-> K wrapping)
  - Scores moves by lookahead streak potential and unblocking value
  - Implements strict WILD card usage:
      * Only when stock is empty
      * Only when 1 card left OR remaining cards can completely chain-clear the board
  - Decides between playing a tableau card, drawing from stock, or using a WILD card
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional
from loguru import logger

from board.state import Card, BoardState
import config

# Card rank values: A=0 ... K=12
ALL_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_TO_VAL = {r: i for i, r in enumerate(ALL_RANKS)}


class MoveType(Enum):
    PLAY_CARD = auto()   # Tap a playable card on the tableau
    DRAW_STOCK = auto()  # Tap stock deck to flip next card
    PLAY_WILD = auto()   # Tap wild card (last resort)
    END_LEVEL = auto()   # Tap END LEVEL button when out of moves/stock
    NO_MOVES = auto()    # Game stuck / out of moves


@dataclass
class Move:
    """Action recommended by the solver."""
    move_type: MoveType
    target_card: Optional[Card] = None  # Tableau card to tap if PLAY_CARD
    tap_coord: tuple[int, int] = (0, 0)
    score: float = 0.0
    reason: str = ""

    def __repr__(self) -> str:
        if self.move_type == MoveType.PLAY_CARD and self.target_card:
            return f"Move(PLAY {self.target_card.rank} at {self.tap_coord}, score={self.score:.1f}, reason='{self.reason}')"
        return f"Move({self.move_type.name} at {self.tap_coord}, score={self.score:.1f}, reason='{self.reason}')"


def are_ranks_adjacent(r1: str, r2: str) -> bool:
    """
    Check if two ranks are adjacent (+-1) with wrapping:
    A (0) <-> 2 (1) ... Q (11) <-> K (12) <-> A (0)
    WILD matches any rank.
    """
    if r1 == "WILD" or r2 == "WILD":
        return True
    if r1 not in RANK_TO_VAL or r2 not in RANK_TO_VAL:
        return False
    v1 = RANK_TO_VAL[r1]
    v2 = RANK_TO_VAL[r2]
    diff = abs(v1 - v2)
    return diff == 1 or diff == 12


def get_legal_tableau_moves(state: BoardState) -> list[Card]:
    """
    Return all cards on the tableau that can legally be played onto the current waste card.
    Must be playable (uncovered) and rank must be adjacent (+-1) to waste card.
    """
    if not state.waste:
        return []

    waste_rank = state.waste.rank
    legal = []
    for card in state.playable_cards:
        if are_ranks_adjacent(card.rank, waste_rank):
            legal.append(card)
    return legal


def simulate_play_card(cards: list[Card], played_card_id: int) -> list[Card]:
    """
    Simulate removing a card from the board:
    Returns a new list of Card objects with DAG dependencies updated.
    """
    new_cards = []
    for c in cards:
        if c.card_id == played_card_id:
            continue
        new_c = Card(
            card_id=c.card_id,
            rank=c.rank,
            cx=c.cx,
            cy=c.cy,
            w=c.w,
            h=c.h,
            angle=c.angle,
            confidence=c.confidence,
            blocked_by=[bid for bid in c.blocked_by if bid != played_card_id],
            blocks=[bid for bid in c.blocks if bid != played_card_id],
        )
        new_cards.append(new_c)
    return new_cards


def _get_card_from_list(cards: list[Card], card_id: int) -> Optional[Card]:
    for c in cards:
        if c.card_id == card_id:
            return c
    return None


def find_best_chain(waste_rank: str, cards: list[Card], max_depth: int = 10) -> tuple[int, float, list[str]]:
    """
    Search for the optimal sequence of playable cards starting from waste_rank.
    Optimizes for:
      1. Longest chain (streak bonus)
      2. Maximum unblocking value of covered cards along the path
    Returns (chain_length, total_chain_value, list_of_ranks_in_chain).
    """
    if max_depth <= 0:
        return (0, 0.0, [])

    playable = [c for c in cards if c.is_playable]
    legal_candidates = [c for c in playable if are_ranks_adjacent(c.rank, waste_rank)]

    if not legal_candidates:
        return (0, 0.0, [])

    best_len = 0
    best_score = -1.0
    best_path = []

    for candidate in legal_candidates:
        sim_cards = simulate_play_card(cards, candidate.card_id)
        # Check all newly uncovered cards (both face-up and face-down!)
        newly_uncovered = [
            c for c in sim_cards 
            if len(c.blocked_by) == 0 and len(_get_card_from_list(cards, c.card_id).blocked_by) > 0
        ]

        step_score = 20.0  # streak length bonus
        for unblocked in newly_uncovered:
            if unblocked.is_mystery:
                step_score += 35.0
            elif unblocked.is_face_down:
                step_score += 25.0
            else:
                step_score += 15.0

        for blocked_id in candidate.blocks:
            c_obj = _get_card_from_list(cards, blocked_id)
            if c_obj and len(c_obj.blocked_by) > 1:
                step_score += 5.0

        sub_len, sub_score, sub_path = find_best_chain(candidate.rank, sim_cards, max_depth - 1)
        total_len = 1 + sub_len
        total_score = step_score + sub_score

        if total_score > best_score:
            best_score = total_score
            best_len = total_len
            best_path = [candidate.rank] + sub_path

    return (best_len, best_score, best_path)


def can_chain_clear_tableau(cards: list[Card]) -> bool:
    """
    Check if the remaining tableau cards can be completely cleared in a single continuous chain,
    starting from ANY rank (as would happen if a WILD card is played first).
    """
    total_cards = len(cards)
    if total_cards == 0:
        return True
    if total_cards == 1:
        return True

    # Check if starting on any playable card allows clearing all cards
    playable = [c for c in cards if c.is_playable]
    for first_card in playable:
        sim_cards = simulate_play_card(cards, first_card.card_id)
        chain_len, _, _ = find_best_chain(first_card.rank, sim_cards, max_depth=total_cards)
        if 1 + chain_len == total_cards:
            return True
    return False


def score_tableau_move(candidate: Card, state: BoardState) -> tuple[float, str]:
    """
    Score a legal tableau move based on:
      1. Immediate unblocking of covered cards (+15 per normal card, +25 per facedown, +35 per mystery card)
      2. Partial unblocking (reducing blocker count of cards underneath)
      3. Lookahead streak potential & multi-step unblocking along the best chain
    """
    score = 10.0  # Base score for any legal play
    reasons = []

    # 1. Unblocking analysis of candidate itself
    new_cards = simulate_play_card(state.tableau, candidate.card_id)
    newly_uncovered = [
        c for c in new_cards 
        if len(c.blocked_by) == 0 and len(state.get_card(c.card_id).blocked_by) > 0
    ]

    for unblocked in newly_uncovered:
        if unblocked.is_mystery:
            score += 35.0
            reasons.append(f"unblocks MYSTERY (?) #{unblocked.card_id}")
        elif unblocked.is_face_down:
            score += 25.0
            reasons.append(f"uncovers facedown #{unblocked.card_id}")
        else:
            score += 15.0
            reasons.append(f"uncovers faceup {unblocked.rank}")

    # Cards that still have blockers, but candidate was one of them
    for blocked_id in candidate.blocks:
        card_obj = state.get_card(blocked_id)
        if card_obj and len(card_obj.blocked_by) > 1:
            score += 5.0

    # 2. Lookahead streak & chain evaluation
    chain_len, chain_score, chain_ranks = find_best_chain(candidate.rank, new_cards, max_depth=10)
    if chain_len > 0:
        score += chain_score
        reasons.append(f"enables chain of {chain_len + 1} ({' -> '.join([candidate.rank] + chain_ranks)})")

    reason_str = ", ".join(reasons) if reasons else f"plays {candidate.rank}"
    return (score, reason_str)


class Solver:
    """
    Disney Solitaire Move Solver:
    Evaluates current BoardState and picks the optimal action.
    """

    def choose_move(self, state: BoardState) -> Move:
        """
        Evaluate board and return best Move:
          1. If legal tableau moves exist -> score them and pick highest.
          2. If no legal moves but stock is available -> DRAW_STOCK.
          3. If no legal moves and stock is EMPTY:
             Check restricted WILD conditions:
               - Only if 1 card remains, OR
               - Remaining cards can be 100% chain-cleared.
             If yes -> PLAY_WILD.
          4. Otherwise -> NO_MOVES.
        """
        # 1. Check legal tableau moves
        legal_moves = get_legal_tableau_moves(state)

        if legal_moves:
            best_card = None
            best_score = -1.0
            best_reason = ""

            for card in legal_moves:
                s, reason = score_tableau_move(card, state)
                logger.debug(f"Candidate Move: {card.rank} at ({card.cx}, {card.cy}) -> score={s:.1f} ({reason})")
                if s > best_score:
                    best_score = s
                    best_card = card
                    best_reason = reason

            if best_card:
                return Move(
                    move_type=MoveType.PLAY_CARD,
                    target_card=best_card,
                    tap_coord=(best_card.cx, best_card.cy),
                    score=best_score,
                    reason=best_reason,
                )

        # 2. No legal tableau moves:
        # Rule A: If WILD is in the center stack -> play undoubtedly!
        if state.stock_has_wild:
            return Move(
                move_type=MoveType.DRAW_STOCK,
                tap_coord=config.STOCK_CENTER,
                score=90.0,
                reason="WILD is in the center stack — play undoubtedly!",
            )

        # Rule B: If regular stock cards exist -> draw next card
        if state.has_normal_stock:
            return Move(
                move_type=MoveType.DRAW_STOCK,
                tap_coord=config.STOCK_CENTER,
                score=5.0,
                reason="No legal tableau moves, draw next card from stock",
            )

        # Rule C: If WILD is in the right bottom corner -> apply strict rules!
        # (Bought/expensive: only use if guarantees finishing the board)
        if state.has_wild:
            remaining_tableau = len(state.tableau)
            qualifies_for_wild = (remaining_tableau == 1) or (
                remaining_tableau > 1 and can_chain_clear_tableau(state.tableau)
            )

            if qualifies_for_wild:
                # Case 1: If we already have a free WILD card (red badge '1'), use it unconditionally
                if state.has_free_wild:
                    return Move(
                        move_type=MoveType.PLAY_WILD,
                        tap_coord=state.wild_coord,
                        score=100.0 if remaining_tableau == 1 else 90.0,
                        reason=(
                            "Stock empty and only 1 card left — use right bottom WILD to finish!"
                            if remaining_tableau == 1
                            else f"Stock empty: remaining {remaining_tableau} cards can be 100% chain-cleared with right bottom WILD!"
                        ),
                    )

                # Case 2: We do not have a free WILD card -> check funds to buy one
                balance = state.balance
                cost = state.wild_cost

                # If balance and cost are known, compare them; if not provided (e.g. synthetic test), allow
                has_insufficient_funds = (
                    balance is not None and cost is not None and balance < cost
                )

                if has_insufficient_funds:
                    logger.warning(
                        f"Insufficient funds to buy WILD card: Balance ({balance}) < Cost ({cost})"
                    )
                    if state.has_end_level:
                        return Move(
                            move_type=MoveType.END_LEVEL,
                            tap_coord=state.end_level_coord,
                            score=1.0,
                            reason=f"Stock empty: Insufficient funds to buy WILD (Balance {balance:,} < Cost {cost:,}) — tap END LEVEL",
                        )
                else:
                    reason = (
                        f"Stock empty: Purchasing WILD card (Balance {balance:,} >= Cost {cost:,}) to finish!"
                        if (balance is not None and cost is not None)
                        else "Stock empty and only 1 card left — use right bottom WILD to finish!"
                    )
                    return Move(
                        move_type=MoveType.PLAY_WILD,
                        tap_coord=state.wild_coord,
                        score=100.0 if remaining_tableau == 1 else 90.0,
                        reason=reason,
                    )
            else:
                logger.info("Right bottom WILD available, but remaining cards cannot finish the game without more cards.")

        # 4. Out of moves / stock empty:
        # If END LEVEL button is visible (or stock empty and remaining cards cannot finish),
        # tap END LEVEL to end the level gracefully.
        if state.has_end_level:
            return Move(
                move_type=MoveType.END_LEVEL,
                tap_coord=state.end_level_coord,
                score=1.0,
                reason="Stock empty and remaining cards cannot finish board — tap END LEVEL",
            )

        # 5. Out of moves (stuck mid-level or no END LEVEL button visible)
        return Move(
            move_type=MoveType.NO_MOVES,
            score=0.0,
            reason="No legal moves, stock empty, right bottom WILD cannot finish board",
        )
