"""
navigation/menu_handler.py
State machine controller for menu navigation, bonus collection, and level starts.
"""

from __future__ import annotations
import random
import time
from dataclasses import dataclass
from typing import Optional
import numpy as np
from loguru import logger

import config
import adb_controller
from vision.menu_detector import MenuDetector, ScreenState
from vision.balance_detector import BalanceDetector


@dataclass
class NavigationAction:
    state: ScreenState
    action_taken: str
    tapped_coord: Optional[tuple[int, int]] = None
    wait_seconds: float = 1.0
    is_gameplay_ready: bool = False


class MenuHandler:
    """
    Coordinates actions when the device is on a menu, popup, or deal transition screen.
    """

    def __init__(
        self,
        detector: Optional[MenuDetector] = None,
        balance_detector: Optional[BalanceDetector] = None,
    ):
        self.detector = detector or MenuDetector()
        self.balance_detector = balance_detector or BalanceDetector()

    @staticmethod
    def get_random_dismiss_coord() -> tuple[int, int]:
        """Compute a randomized (x, y) tap within the safe popup dismiss region."""
        rx, ry, rw, rh = config.POPUP_DISMISS_ROI
        return (
            random.randint(rx, rx + rw),
            random.randint(ry, ry + rh),
        )

    def handle(self, screen: np.ndarray, dev=None) -> NavigationAction:
        """
        Detects screen state and executes the appropriate tap or wait action.
        If dev is provided, performs the jittered tap on the device.
        """
        state = self.detector.detect_state(screen)

        if state == ScreenState.IN_GAME:
            return NavigationAction(
                state=state,
                action_taken="Gameplay active — proceed to card solver",
                is_gameplay_ready=True,
            )

        if state == ScreenState.CARDS_DEALING:
            logger.info(f"Cards are being dealt. Waiting {config.DEAL_ANIMATION_WAIT}s for board to settle...")
            if dev is not None:
                time.sleep(config.DEAL_ANIMATION_WAIT)
            return NavigationAction(
                state=state,
                action_taken=f"Waited {config.DEAL_ANIMATION_WAIT}s for cards dealing",
                wait_seconds=config.DEAL_ANIMATION_WAIT,
                is_gameplay_ready=False,
            )

        # ── Menu / Popup actions ──────────────────────────────────────────────
        target_coord = None
        action_desc = ""
        wait_time = config.SCREENCAP_INTERVAL

        if state == ScreenState.POST_WIN:
            target_coord = self.get_random_dismiss_coord()
            action_desc = f"Dismissed victory screen (randomized tap at {target_coord})"
            wait_time = 2.0  # allow victory summary animations to clear

        elif state == ScreenState.RANDOM_REWARD:
            target_coord = self.get_random_dismiss_coord()
            action_desc = f"Dismissed random reward popup (randomized tap at {target_coord})"
            wait_time = 1.5

        elif state == ScreenState.END_LEVEL_CONFIRM:
            target_coord = self.detector.last_confirm_coord or config.END_LEVEL_CONFIRM_CENTER
            action_desc = "Confirmed end level modal (tapped red confirmation button)"
            wait_time = 2.0  # allow level forfeit/defeat transition to settle

        elif state == ScreenState.MAIN_MENU_COLLECT:
            target_coord = config.MENU_COLLECT_CENTER
            action_desc = "Claimed hourly bonus (tapped purple COLLECT button)"
            wait_time = 2.0  # coin fly animation

        elif state == ScreenState.MAIN_MENU_PLAY:
            target_coord = config.MENU_PLAY_CENTER
            action_desc = "Opened level modal (tapped green LEVEL button)"
            wait_time = 1.5

        elif state == ScreenState.PRE_LEVEL_MODAL:
            balance = self.balance_detector.get_balance(screen)
            cost = self.detector.detect_modal_cost(screen)

            if balance is not None and cost is not None and balance < cost:
                target_coord = config.MODAL_CLOSE_CENTER
                action_desc = (
                    f"Insufficient funds: Balance ({balance:,}) < Cost ({cost:,}). "
                    f"Closed modal (tapped X button), sleeping {config.INSUFFICIENT_FUNDS_WAIT}s"
                )
                wait_time = config.INSUFFICIENT_FUNDS_WAIT
                logger.warning(f"MenuHandler: {action_desc}")
            else:
                target_coord = config.MODAL_PLAY_CENTER
                if balance is not None and cost is not None:
                    action_desc = (
                        f"Balance ({balance:,}) >= Cost ({cost:,}). "
                        f"Started level (tapped green PLAY button in modal)"
                    )
                else:
                    action_desc = (
                        f"Started level (tapped green PLAY button in modal, "
                        f"balance={balance}, cost={cost})"
                    )
                wait_time = 2.5  # wait for level loading and dealing initiation

        else:
            return NavigationAction(
                state=state,
                action_taken="Unknown screen state — no action taken",
                is_gameplay_ready=False,
            )

        logger.info(f"Navigation: {state.name} -> {action_desc} at {target_coord}")

        if dev is not None and target_coord is not None:
            tx, ty = target_coord
            ax, ay = adb_controller.tap(dev, tx, ty, apply_jitter=True)
            logger.debug(f"Executed navigation tap at ({ax}, {ay})")
            time.sleep(wait_time)

        return NavigationAction(
            state=state,
            action_taken=action_desc,
            tapped_coord=target_coord,
            wait_seconds=wait_time,
            is_gameplay_ready=False,
        )
