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


def annotate_proposed_move(
    screen: np.ndarray,
    move,
    actual_coord: tuple[int, int],
    orig_coord: tuple[int, int] | None = None,
    output_path: str = "tests/screenshots/proposed_move.jpg",
) -> str:
    """
    Draw a clear visual target overlay on the screenshot highlighting the proposed tap.
    The crosshairs and target ring directly mirror the exact jittered coordinate (actual_coord)
    where the tap will be sent to the device.
    """
    vis = screen.copy()
    tx, ty = actual_coord

    # If original center is provided and differs from actual jittered target, draw center dot and offset line
    if orig_coord and orig_coord != actual_coord:
        ox, oy = orig_coord
        cv2.line(vis, (ox, oy), (tx, ty), (120, 120, 120), 1, cv2.LINE_AA)
        cv2.circle(vis, (ox, oy), 4, (160, 160, 160), 1)

    # Draw target crosshair and pulsing concentric rings at actual tap location
    cv2.circle(vis, (tx, ty), 45, (0, 0, 0), 6)       # Black border
    cv2.circle(vis, (tx, ty), 45, (0, 255, 255), 3)   # Yellow ring
    cv2.circle(vis, (tx, ty), 20, (0, 255, 0), -1)    # Green center dot
    cv2.circle(vis, (tx, ty), 8, (255, 255, 255), -1) # White core

    # Draw crosshairs
    cv2.line(vis, (tx - 60, ty), (tx + 60, ty), (0, 255, 255), 2)
    cv2.line(vis, (tx, ty - 60), (tx, ty + 60), (0, 255, 255), 2)

    # Top info banner
    if move.move_type == MoveType.PLAY_CARD and move.target_card:
        action_label = f"PLAY [{move.target_card.rank}]"
    elif move.move_type == MoveType.DRAW_STOCK:
        action_label = "DRAW STOCK"
    elif move.move_type == MoveType.PLAY_WILD:
        action_label = "PLAY WILD"
    elif move.move_type == MoveType.END_LEVEL:
        action_label = "END LEVEL"
    else:
        action_label = move.move_type.name

    cv2.rectangle(vis, (0, 0), (vis.shape[1], 80), (20, 20, 20), -1)
    offset_str = f" [jitter: {tx - orig_coord[0]:+d}, {ty - orig_coord[1]:+d}]" if orig_coord else ""
    banner_text = f"PROPOSED: {action_label} at ({tx}, {ty}){offset_str} | {move.reason}"
    cv2.putText(vis, banner_text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2, cv2.LINE_AA)

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
            screen = adb_controller.screencap(dev)
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
        print(f"  • End Level Button: {'AVAILABLE' if state.has_end_level else 'NONE'}")

        # Check win condition
        if len(state.tableau) == 0:
            logger.success("🎉 CONGRATULATIONS! Tableau is completely cleared! GAME WON! 🎉")
            break

        move = solver.choose_move(state)
        if move.move_type == MoveType.NO_MOVES:
            logger.warning(f"⛔ NO LEGAL MOVES AVAILABLE: {move.reason}")
            action = input("\n[r] to retry capture, [q] to quit: ").strip().lower()
            if action == "r":
                continue
            else:
                break

        # Pre-compute exact jittered coordinate so the visual preview directly mirrors the actual tap
        orig_tx, orig_ty = int(move.tap_coord[0]), int(move.tap_coord[1])
        actual_tx, actual_ty = adb_controller.compute_jittered_coord(orig_tx, orig_ty)

        # Annotate preview with the exact tap target
        preview_path = annotate_proposed_move(screen, move, (actual_tx, actual_ty), (orig_tx, orig_ty))

        # Format descriptive move label
        if move.move_type == MoveType.PLAY_CARD and move.target_card:
            action_desc = f"PLAY CARD [{move.target_card.rank}] (Card #{move.target_card.card_id})"
            tap_prompt = f"👉 Play [{move.target_card.rank}] at ({actual_tx}, {actual_ty})? [Enter=YES, s=skip, q=quit]: "
        elif move.move_type == MoveType.DRAW_STOCK:
            action_desc = "DRAW FROM STOCK"
            tap_prompt = f"👉 Draw from stock at ({actual_tx}, {actual_ty})? [Enter=YES, s=skip, q=quit]: "
        elif move.move_type == MoveType.PLAY_WILD:
            action_desc = "PLAY WILD CARD"
            tap_prompt = f"👉 Play WILD card at ({actual_tx}, {actual_ty})? [Enter=YES, s=skip, q=quit]: "
        elif move.move_type == MoveType.END_LEVEL:
            action_desc = "END LEVEL"
            tap_prompt = f"👉 Tap END LEVEL at ({actual_tx}, {actual_ty})? [Enter=YES, s=skip, q=quit]: "
        else:
            action_desc = move.move_type.name
            tap_prompt = f"👉 Execute tap at ({actual_tx}, {actual_ty}) on device? [Enter=YES, s=skip, q=quit]: "

        print("\n" + "=" * 60)
        print(f"🎯 PROPOSED MOVE: {action_desc}")
        print(f"  • Target:  ({actual_tx}, {actual_ty}) [jitter: {actual_tx - orig_tx:+d}, {actual_ty - orig_ty:+d} from center ({orig_tx}, {orig_ty})]")
        print(f"  • Score:   {move.score:.1f}")
        print(f"  • Reason:  {move.reason}")
        print(f"  • Preview: {preview_path}")
        print("=" * 60)

        # User confirmation prompt
        try:
            choice = input(f"\n{tap_prompt}").strip().lower()
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
            # Execute tap at the exact pre-computed target (apply_jitter=False)
            logger.info(f"Tapping ({actual_tx}, {actual_ty})...")
            try:
                ax, ay = adb_controller.tap(dev, actual_tx, actual_ty, apply_jitter=False)
                logger.info(f"Tapped ({ax}, {ay}) on device")
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
