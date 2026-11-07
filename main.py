"""
main.py
Disney Solitaire Bot — Autonomous Game Loop.

Runs continuously without user confirmation:
  1. Capture live screen via ADB
  2. Parse board state (card detection + DAG)
  3. Decide best move (solver)
  4. Execute tap on device
  5. Wait for animations to settle → repeat

Stops automatically on:
  - Win (tableau cleared)
  - No legal moves with empty stock (stuck)
  - ADB connection failure
  - KeyboardInterrupt (Ctrl+C)

Usage:
    python main.py                  # run until game over
    python main.py --max-steps 50   # stop after 50 steps (safety cap)
    python main.py --save-screens   # save every screenshot to tests/screenshots/
"""

from __future__ import annotations

import argparse
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


# ── Logging setup ──────────────────────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
    colorize=True,
)
logger.add(
    "logs/main_{time:YYYYMMDD_HHmmss}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention=5,
)

# ── Constants ──────────────────────────────────────────────────────────────────
# How many consecutive "no moves" frames to tolerate before declaring stuck.
# (Detection glitches can produce a false no-move frame; a few retries avoid quitting too early.)
NO_MOVE_PATIENCE = 3

# How long to wait after a failed capture before retrying (seconds)
CAPTURE_RETRY_DELAY = 2.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Disney Solitaire autonomous bot")
    p.add_argument(
        "--max-steps",
        type=int,
        default=0,
        metavar="N",
        help="Stop after N steps (0 = unlimited)",
    )
    p.add_argument(
        "--save-screens",
        action="store_true",
        help="Save every captured screenshot to tests/screenshots/",
    )
    return p.parse_args()


def capture_screen(dev) -> np.ndarray | None:
    """Grab a screenshot and return it as a BGR numpy array, or None on failure."""
    try:
        pil_img = adb_controller.screencap(dev)
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.error(f"Screencap failed: {e}")
        return None


def run(args: argparse.Namespace) -> None:
    logger.info("=" * 60)
    logger.info("DISNEY SOLITAIRE BOT — AUTONOMOUS MODE")
    logger.info("=" * 60)
    logger.info(f"Max steps : {args.max_steps if args.max_steps else 'unlimited'}")
    logger.info(f"Save screens: {args.save_screens}")

    # ── ADB connect ────────────────────────────────────────────────────────────
    try:
        dev = adb_controller.connect()
    except Exception as e:
        logger.error(f"ADB connection failed: {e}")
        return

    parser = BoardParser()
    solver = Solver()

    step = 0
    no_move_streak = 0

    while True:
        step += 1
        if args.max_steps and step > args.max_steps:
            logger.info(f"Reached max-steps limit ({args.max_steps}). Stopping.")
            break

        logger.info(f"── Step {step} ──────────────────────────────────")

        # ── 1. Capture ─────────────────────────────────────────────────────────
        screen = capture_screen(dev)
        if screen is None:
            logger.warning(f"Capture failed — retrying in {CAPTURE_RETRY_DELAY}s...")
            time.sleep(CAPTURE_RETRY_DELAY)
            step -= 1  # don't count failed captures
            continue

        # Warn on unexpected resolution
        h, w = screen.shape[:2]
        if (w, h) != (config.SCREEN_WIDTH, config.SCREEN_HEIGHT):
            logger.warning(f"Unexpected resolution {w}×{h} (expected {config.SCREEN_WIDTH}×{config.SCREEN_HEIGHT})")

        if args.save_screens:
            adb_controller.save_screenshot(
                Image.fromarray(cv2.cvtColor(screen, cv2.COLOR_BGR2RGB)),
                folder="tests/screenshots",
            )

        # ── 2. Parse board state ───────────────────────────────────────────────
        state = parser.parse(screen)

        waste_rank = state.waste.rank if state.waste else "NONE"
        playable_str = ", ".join(f"{c.rank}#{c.card_id}" for c in state.playable_cards) or "None"
        logger.info(
            f"Waste=[{waste_rank}]  "
            f"Playable={len(state.playable_cards)} ({playable_str})  "
            f"Tableau={len(state.tableau)}  "
            f"Stock={'YES' if state.has_normal_stock else 'EMPTY'}  "
            f"StockWILD={'YES' if state.stock_has_wild else 'NO'}  "
            f"WILD={'YES' if state.has_wild else 'NO'}"
        )

        # ── 3. Win check ───────────────────────────────────────────────────────
        if len(state.tableau) == 0:
            logger.success("🎉 GAME WON! Tableau is fully cleared!")
            break

        # ── 4. Decide move ─────────────────────────────────────────────────────
        move = solver.choose_move(state)

        if move.move_type == MoveType.NO_MOVES:
            no_move_streak += 1
            logger.warning(
                f"No legal moves ({no_move_streak}/{NO_MOVE_PATIENCE}): {move.reason}"
            )
            if no_move_streak >= NO_MOVE_PATIENCE:
                logger.error(
                    f"⛔ Stuck for {NO_MOVE_PATIENCE} consecutive frames — giving up."
                )
                break
            # Short wait then retry (maybe a card is mid-flip)
            time.sleep(config.SCREENCAP_INTERVAL)
            continue

        no_move_streak = 0  # reset on a valid move

        logger.info(
            f"Move: {move.move_type.name}  "
            f"target={move.target_card.rank if move.target_card else '—'}  "
            f"coord={move.tap_coord}  score={move.score:.1f}  reason={move.reason}"
        )

        # ── 5. Execute tap ─────────────────────────────────────────────────────
        tx, ty = move.tap_coord
        try:
            ax, ay = adb_controller.tap(dev, tx, ty, apply_jitter=True)
            logger.debug(f"Tapped ({ax}, {ay})")
        except RuntimeError as e:
            logger.error(f"Tap failed: {e}")
            break

        # ── 6. Wait for animations ─────────────────────────────────────────────
        time.sleep(config.SCREENCAP_INTERVAL)

    logger.info("Bot session ended.")


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args)
    except KeyboardInterrupt:
        logger.info("Interrupted by user (Ctrl+C). Exiting.")
