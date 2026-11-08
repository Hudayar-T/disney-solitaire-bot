"""
Test the Decision Engine Solver across all 9 screenshot board states,
plus synthetic edge cases testing restricted WILD logic and chaining.
"""

import sys
sys.path.insert(0, ".")

import cv2
from pathlib import Path
from board.parser import BoardParser
from board.state import Card, BoardState
from engine.solver import Solver, MoveType

parser = BoardParser()
solver = Solver()

print("=" * 60)
print("TEST 1: SOLVER DECISIONS ON REAL SCREENSHOTS")
print("=" * 60)

for idx in range(1, 13):
    img = cv2.imread(f"tests/screenshots/algorithm/{idx}.jpg")
    if img is None:
        continue
    state = parser.parse(img)
    move = solver.choose_move(state)
    print(f"\nScreenshot {idx} (Waste: {state.waste.rank if state.waste else 'None'}):")
    print(f"  Decision: {move}")

print("\n" + "=" * 60)
print("TEST 2: SYNTHETIC WILD RESTRICTION EDGE CASES")
print("=" * 60)

# Case A: Normal stock is NOT empty -> MUST DRAW STOCK, NOT USE WILD!
state_a = BoardState(
    tableau=[Card(card_id=1, rank="K", cx=1000, cy=500, w=130, h=200)],
    waste=Card(card_id=0, rank="5", cx=1336, cy=937, w=130, h=200),
    has_normal_stock=True,
    has_wild=True
)
move_a = solver.choose_move(state_a)
print("\nCase A (Stock available, 1 card left not adjacent to waste):")
print(f"  Expected: DRAW_STOCK | Got: {move_a.move_type.name} ({move_a.reason})")
assert move_a.move_type == MoveType.DRAW_STOCK, "Should draw stock when stock is available!"

# Case B: Stock IS empty, but cards CANNOT be chain-cleared -> DO NOT USE WILD!
state_b = BoardState(
    tableau=[
        Card(card_id=1, rank="2", cx=1000, cy=500, w=130, h=200),
        Card(card_id=2, rank="8", cx=1200, cy=500, w=130, h=200),
    ],
    waste=Card(card_id=0, rank="5", cx=1336, cy=937, w=130, h=200),
    has_normal_stock=False,
    has_wild=True
)
move_b = solver.choose_move(state_b)
print("\nCase B (Stock empty, 2 disconnected cards '2' and '8' that cannot chain):")
print(f"  Expected: NO_MOVES | Got: {move_b.move_type.name} ({move_b.reason})")
assert move_b.move_type == MoveType.NO_MOVES, "Should not waste WILD on un-chainable cards!"

# Case C: Stock IS empty, and exactly 1 card left -> USE WILD TO FINISH GAME!
state_c = BoardState(
    tableau=[Card(card_id=1, rank="K", cx=1000, cy=500, w=130, h=200)],
    waste=Card(card_id=0, rank="5", cx=1336, cy=937, w=130, h=200),
    has_normal_stock=False,
    has_wild=True
)
move_c = solver.choose_move(state_c)
print("\nCase C (Stock empty, exactly 1 card left):")
print(f"  Expected: PLAY_WILD | Got: {move_c.move_type.name} ({move_c.reason})")
assert move_c.move_type == MoveType.PLAY_WILD, "Should use WILD to finish the last card!"

# Case D: Stock IS empty, 3 cards left that form a full chain (e.g. 7 -> 8 -> 9) -> USE WILD!
state_d = BoardState(
    tableau=[
        Card(card_id=1, rank="7", cx=1000, cy=500, w=130, h=200),
        Card(card_id=2, rank="8", cx=1200, cy=500, w=130, h=200),
        Card(card_id=3, rank="9", cx=1400, cy=500, w=130, h=200),
    ],
    waste=Card(card_id=0, rank="2", cx=1336, cy=937, w=130, h=200),
    has_normal_stock=False,
    has_wild=True
)
move_d = solver.choose_move(state_d)
print("\nCase D (Stock empty, 3 cards '7-8-9' can 100% chain-clear with WILD):")
print(f"  Expected: PLAY_WILD | Got: {move_d.move_type.name} ({move_d.reason})")
assert move_d.move_type == MoveType.PLAY_WILD, "Should use WILD to chain-clear the board!"

# Case E: WILD is in the center stack -> PLAY UNDOUBTEDLY!
state_e = BoardState(
    tableau=[
        Card(card_id=1, rank="2", cx=1000, cy=500, w=130, h=200),
        Card(card_id=2, rank="6", cx=1200, cy=500, w=130, h=200),
    ],
    waste=Card(card_id=0, rank="J", cx=1336, cy=937, w=130, h=200),
    has_normal_stock=False,
    stock_has_wild=True,
    has_wild=True  # Right bottom also has wild, but center takes precedence
)
move_e = solver.choose_move(state_e)
print("\nCase E (WILD in center stack -> play undoubtedly):")
print(f"  Expected: DRAW_STOCK | Got: {move_e.move_type.name} ({move_e.reason})")
assert move_e.move_type == MoveType.DRAW_STOCK, "Center WILD must be played undoubtedly!"

# Case F: Waste STACK holds a WILD card -> Can immediately play ANY tableau card!
state_f = BoardState(
    tableau=[
        Card(card_id=1, rank="8", cx=1000, cy=500, w=130, h=200),
    ],
    waste=Card(card_id=0, rank="WILD", cx=1336, cy=937, w=130, h=200),
    has_normal_stock=False,
    has_wild=False
)
move_f = solver.choose_move(state_f)
print("\nCase F (Waste STACK has WILD card -> freely play tableau card):")
print(f"  Expected: PLAY_CARD | Got: {move_f.move_type.name} ({move_f.reason})")
assert move_f.move_type == MoveType.PLAY_CARD, "WILD on waste stack should freely play onto tableau!"

# Case G: WILD is ONLY in right bottom corner, disconnected cards -> STRICT RULE BLOCKS IT!
state_g = BoardState(
    tableau=[
        Card(card_id=1, rank="2", cx=1000, cy=500, w=130, h=200),
        Card(card_id=2, rank="6", cx=1200, cy=500, w=130, h=200),
    ],
    waste=Card(card_id=0, rank="J", cx=1336, cy=937, w=130, h=200),
    has_normal_stock=False,
    stock_has_wild=False,
    has_wild=True,
    has_end_level=False
)
move_g = solver.choose_move(state_g)
print("\nCase G (Right bottom WILD only, un-chainable cards, no end level -> STRICT RULE: NO_MOVES):")
print(f"  Expected: NO_MOVES | Got: {move_g.move_type.name} ({move_g.reason})")
assert move_g.move_type == MoveType.NO_MOVES, "Right bottom WILD must obey strict rules!"

# Case H: Stock empty, un-chainable cards, END LEVEL button visible -> TAP END LEVEL!
state_h = BoardState(
    tableau=[
        Card(card_id=1, rank="2", cx=1000, cy=500, w=130, h=200),
        Card(card_id=2, rank="6", cx=1200, cy=500, w=130, h=200),
    ],
    waste=Card(card_id=0, rank="J", cx=1336, cy=937, w=130, h=200),
    has_normal_stock=False,
    stock_has_wild=False,
    has_wild=True,
    has_end_level=True,
    end_level_coord=(571, 978)
)
move_h = solver.choose_move(state_h)
print("\nCase H (Stock empty, cannot clear, END LEVEL button visible -> TAP END LEVEL):")
print(f"  Expected: END_LEVEL | Got: {move_h.move_type.name} ({move_h.reason})")
assert move_h.move_type == MoveType.END_LEVEL, "Should tap END LEVEL when stock empty and board un-clearable!"
assert move_h.tap_coord == (571, 978), f"Tap coord should match end_level_coord, got {move_h.tap_coord}"

# Case I: Real end_level screenshot -> MUST CHOOSE END_LEVEL
img_end = cv2.imread("tests/screenshots/end_level/end_level_20261107_223046.png")
if img_end is not None:
    state_end = parser.parse(img_end)
    move_end = solver.choose_move(state_end)
    print("\nCase I (Real Screenshot end_level_20261107_223046.png):")
    print(f"  has_end_level: {state_end.has_end_level}")
    print(f"  Decision: {move_end}")
    assert state_end.has_end_level is True, "end_level button must be detected in real screenshot!"
    assert move_end.move_type == MoveType.END_LEVEL, "Solver must choose END_LEVEL on real end_level screenshot!"

print("\n" + "=" * 60)
print("ALL DECISION ENGINE TESTS PASSED!")
print("=" * 60)
