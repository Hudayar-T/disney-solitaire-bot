"""
live_step.py
Interactive Step-by-Step Live Runner for Disney Solitaire Bot.

Captures the live phone screen, parses the board state, calculates the best move,
annotates a visual preview of the tap target, and prompts for user confirmation
before sending any tap via ADB.
"""

import sys
import time
import cv2
import numpy as np
from pathlib import Path
from loguru import logger
from PIL import Image

import config
import adb_controller
from board.parser import BoardParser
from engine.solver import Solver, MoveType


def annotate_proposed_move(screen: np.ndarray, move, output_path: str = "tests/screenshots/proposed_move.jpg") -> str:
    """
    Draw a clear visual target overlay on the screenshot highlighting the proposed tap.
    """
    vis = screen.copy()
    tx, ty = int(move.tap_coord[0]), int(move.tap_coord[1])

    # Draw target crosshair and pulsing concentric rings
    cv2.circle(vis, (tx, ty), 45, (0, 0, 0), 6)       # Black border
    cv2.circle(vis, (tx, ty), 45, (0, 255, 255), 3)   # Yellow ring
    cv2.circle(vis, (tx, ty), 20, (0, 255, 0), -1)    # Green center dot
    cv2.circle(vis, (tx, ty), 8, (255, 255, 255), -1) # White core

    # Draw crosshairs
    cv2.line(vis, (tx - 60, ty), (tx + 60, ty), (0, 255, 255), 2)
    cv2.line(vis, (tx, ty - 60), (tx, ty + 60), (0, 255, 255), 2)

    # Top info banner
    cv2.rectangle(vis, (0, 0), (vis.shape[1], 80), (20, 20, 20), -1)
    banner_text = f"PROPOSED MOVE: {move.move_type.name} at ({tx}, {ty}) | {move.reason}"
    cv2.putText(vis, banner_text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_file), vis)
    return str(out_file)


def run_interactive_loop():
    logger.info("=" * 60)
    logger.info("DISNEY SOLITAIRE BOT — INTERACTIVE STEP RUNNER")
    logger.info("=" * 60)

    try:
        dev = adb_controller.connect()
    except Exception as e:
        logger.error(f"Failed to connect to ADB device: {e}")
        return

    parser = BoardParser()
    solver = Solver()

    step_count = 0

    while True:
        step_count += 1
        print("\n" + "─" * 60)
        logger.info(f"▶ STEP {step_count}: Capturing live screen...")

        try:
            pil_img = adb_controller.screencap(dev)
            screen = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"Screencap failed: {e}")
            break

        # Check resolution
        h, w, _ = screen.shape
        if (w, h) != (config.SCREEN_WIDTH, config.SCREEN_HEIGHT):
            logger.warning(f"Unexpected screen resolution: {w}x{h} (expected {config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT})")

        # Parse board state
        state = parser.parse(screen)

        # Print state overview
        waste_rank = state.waste.rank if state.waste else "NONE"
        playable_str = ", ".join([f"{c.rank}#{c.card_id}" for c in state.playable_cards]) or "None"
        print(f"\n📋 BOARD STATUS:")
        print(f"  • Waste Card:       [{waste_rank}]")
        print(f"  • Playable Cards:   [{playable_str}] ({len(state.playable_cards)} total)")
        print(f"  • Remaining Cards:  {len(state.tableau)} tableau ({len(state.faceup_cards)} face-up, {len(state.facedown_cards)} face-down)")
        print(f"  • Normal Stock:     {'YES' if state.has_normal_stock else 'EMPTY'}")
        print(f"  • Center WILD:      {'YES' if state.stock_has_wild else 'NO'}")
        print(f"  • Bottom-Right WILD:{'AVAILABLE' if state.has_wild else 'NONE'}")

        # Check win condition
        if len(state.tableau) == 0:
            logger.success("🎉 CONGRATULATIONS! Tableau is completely cleared! GAME WON! 🎉")
            break

        # Compute next move
        move = solver.choose_move(state)

        if move.move_type == MoveType.NO_MOVES:
            logger.warning(f"⛔ NO LEGAL MOVES AVAILABLE: {move.reason}")
            action = input("\n[r] to retry capture, [q] to quit: ").strip().lower()
            if action == "r":
                continue
            else:
                break

        # Annotate preview
        preview_path = annotate_proposed_move(screen, move)

        print("\n" + "=" * 60)
        print(f"🎯 PROPOSED MOVE: {move.move_type.name}")
        print(f"  • Target:  ({move.tap_coord[0]}, {move.tap_coord[1]})")
        print(f"  • Score:   {move.score:.1f}")
        print(f"  • Reason:  {move.reason}")
        print(f"  • Preview: {preview_path}")
        print("=" * 60)

        # User confirmation prompt
        try:
            choice = input("\n👉 Execute this tap on device? [Enter=YES, s=skip, q=quit]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting interactive runner.")
            break

        if choice == "q":
            logger.info("Session stopped by user.")
            break
        elif choice == "s":
            logger.info("Move skipped by user. Re-evaluating next frame...")
            continue
        else:
            # Execute tap
            tx, ty = int(move.tap_coord[0]), int(move.tap_coord[1])
            logger.info(f"Tapping ({tx}, {ty})...")
            try:
                adb_controller.tap(dev, tx, ty)
            except RuntimeError as e:
                logger.error(f"\n{e}\n")
                input("Press [Enter] after enabling the setting on your phone to retry...")
                continue

            # Wait for animation to settle
            settle_time = config.SCREENCAP_INTERVAL
            logger.debug(f"Waiting {settle_time:.1f}s for animations...")
            time.sleep(settle_time)


if __name__ == "__main__":
    run_interactive_loop()
