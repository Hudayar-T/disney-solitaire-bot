"""
Test BoardParser and DAG dependency resolution on all static screenshots.
Draws green boxes around PLAYABLE cards and orange boxes around BLOCKED cards.
"""

import sys
sys.path.insert(0, ".")

import cv2
import numpy as np
from pathlib import Path
from board.parser import BoardParser

DEBUG_DIR = Path("tests/debug")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

parser = BoardParser()
screenshots = sorted(Path("tests/screenshots").glob("*.jpg"))

for ss_path in screenshots:
    img = cv2.imread(str(ss_path))
    name = ss_path.stem
    print(f"\n==================== SCREENSHOT {name} ====================")

    state = parser.parse(img)

    print(f"Waste card: {state.waste.rank if state.waste else 'None'}")
    print(f"Total cards on board: {len(state.tableau)}")
    print(f"Face-up: {len(state.faceup_cards)}, Face-down: {len(state.facedown_cards)}")

    playable = state.playable_cards
    print(f"\nPLAYABLE CARDS ({len(playable)}):")
    for c in playable:
        print(f"  - Card #{c.card_id}: {c.rank} at ({c.cx}, {c.cy})")

    blocked_faceup = [c for c in state.faceup_cards if not c.is_playable]
    print(f"\nBLOCKED FACE-UP CARDS ({len(blocked_faceup)}):")
    for c in blocked_faceup:
        blockers = [f"#{bid} ({state.get_card(bid).rank})" for bid in c.blocked_by]
        print(f"  - Card #{c.card_id}: {c.rank} at ({c.cx}, {c.cy}) blocked by {blockers}")

    # ── Visual Annotation ────────────────────────────────────────────
    vis = img.copy()

    for c in state.tableau:
        rect = c.rotated_rect
        box = cv2.boxPoints(rect).astype(int)

        if c.is_playable:
            color = (0, 255, 0)  # Bright Green for playable!
            cv2.drawContours(vis, [box], 0, color, 3)
            label = f"{c.rank} [PLAY]"
            cv2.putText(vis, label, (c.cx - 35, c.cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        elif c.is_face_up:
            color = (0, 140, 255)  # Orange for blocked face-up
            cv2.drawContours(vis, [box], 0, color, 2)
            label = f"{c.rank} (blkd)"
            cv2.putText(vis, label, (c.cx - 35, c.cy), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
        else:
            color = (255, 100, 0)  # Light blue/grey for face-down
            cv2.drawContours(vis, [box], 0, color, 1)

    # Waste card
    if state.waste:
        cv2.circle(vis, (state.waste.cx, state.waste.cy), 8, (0, 0, 255), -1)
        cv2.putText(vis, f"WASTE: {state.waste.rank}", (state.waste.cx - 40, state.waste.cy - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.imwrite(str(DEBUG_DIR / f"{name}_dag_board.jpg"), vis)

print(f"\nAnnotated DAG boards saved to {DEBUG_DIR.resolve()}")
