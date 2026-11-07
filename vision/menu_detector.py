"""
vision/menu_detector.py
Detects menu screens, popup dialogs, and level transitions for Disney Solitaire.
"""

from __future__ import annotations
from enum import Enum, auto
from pathlib import Path
from typing import Optional
import cv2
import numpy as np
from loguru import logger

import config
from vision.detector import CardDetector


class ScreenState(Enum):
    MAIN_MENU_COLLECT = auto()  # Main menu with hourly purple "COLLECT" bonus ready
    MAIN_MENU_PLAY = auto()     # Main menu idle (green level play button)
    PRE_LEVEL_MODAL = auto()    # Level pre-start popup with green "PLAY" button
    POST_WIN = auto()           # "MEGA WIN!" overlay ("TAP ANYWHERE TO COLLECT")
    RANDOM_REWARD = auto()      # "YOUR REWARDS!" popup ("TAP TO COLLECT")
    CARDS_DEALING = auto()      # Level entry dealing animation (wait)
    IN_GAME = auto()            # Active gameplay with waste and cards
    UNKNOWN = auto()            # Unrecognized state


class MenuDetector:
    """
    Classifies screen captures into menu, popup, transition, or gameplay states.
    Fast HSV and template checks run first (<10ms) before invoking card detection.
    """

    def __init__(self, template_dir: str = "vision/templates", card_detector: Optional[CardDetector] = None):
        self.tmpl_path = Path(template_dir)
        self.card_detector = card_detector

        # Load navigation popup templates
        self.tmpl_tap_win = self._load_template("tap_anywhere_to_collect.png")
        self.tmpl_tap_reward = self._load_template("tap_to_collect.png")

    def _load_template(self, filename: str) -> Optional[np.ndarray]:
        p = self.tmpl_path / filename
        if p.exists():
            img = cv2.imread(str(p))
            logger.debug(f"Loaded menu template: {filename} ({img.shape if img is not None else 'None'})")
            return img
        logger.warning(f"Menu template not found: {p}")
        return None

    def detect_state(self, screen: np.ndarray) -> ScreenState:
        """
        Classifies the given screenshot into a ScreenState enum.
        """
        hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

        # ── 1. Check Post-Win Screen ("MEGA WIN!" / red curtains) ──────────────
        if self._is_post_win(screen, hsv):
            logger.info("Detected screen state: POST_WIN (Victory Celebration)")
            return ScreenState.POST_WIN

        # ── 2. Check Random Reward Popup ("YOUR REWARDS!" / "TAP TO COLLECT") ──
        if self._is_random_reward(screen):
            logger.info("Detected screen state: RANDOM_REWARD (Bonus/Mission Popup)")
            return ScreenState.RANDOM_REWARD

        # ── 3. Check Pre-Level Modal (Green "PLAY" button at center bottom) ────
        if self._is_pre_level_modal(hsv):
            logger.info("Detected screen state: PRE_LEVEL_MODAL (Level Start Confirmation)")
            return ScreenState.PRE_LEVEL_MODAL

        # ── 4. Check Main Menu (Hourly bonus or Level play button) ─────────────
        menu_state = self._check_main_menu(hsv)
        if menu_state is not None:
            logger.info(f"Detected screen state: {menu_state.name} (Main Menu)")
            return menu_state

        # ── 5. Check In-Game vs Cards Dealing ─────────────────────────────────
        if self._is_cards_dealing(screen):
            logger.info("Detected screen state: CARDS_DEALING (Animations in progress)")
            return ScreenState.CARDS_DEALING

        logger.debug("Detected screen state: IN_GAME")
        return ScreenState.IN_GAME

    def _is_post_win(self, screen: np.ndarray, hsv: np.ndarray) -> bool:
        # Check template match for 'TAP ANYWHERE TO COLLECT'
        if self.tmpl_tap_win is not None:
            bot_search = screen[950:1050, 900:1500]
            res = cv2.matchTemplate(bot_search, self.tmpl_tap_win, cv2.TM_CCOEFF_NORMED)
            if cv2.minMaxLoc(res)[1] > 0.70:
                return True

        # Fallback: check red curtains on both left and right sides
        lc = hsv[100:700, 50:250]
        rc = hsv[100:700, 2150:2350]
        def red_ratio(crop: np.ndarray) -> float:
            r1 = cv2.inRange(crop, (0, 100, 60), (10, 255, 255))
            r2 = cv2.inRange(crop, (170, 100, 60), (180, 255, 255))
            return (cv2.countNonZero(r1) + cv2.countNonZero(r2)) / (crop.shape[0] * crop.shape[1])

        return (red_ratio(lc) > 0.40) and (red_ratio(rc) > 0.40)

    def _is_random_reward(self, screen: np.ndarray) -> bool:
        if self.tmpl_tap_reward is None:
            return False
        bot_search = screen[950:1050, 1000:1400]
        res = cv2.matchTemplate(bot_search, self.tmpl_tap_reward, cv2.TM_CCOEFF_NORMED)
        return cv2.minMaxLoc(res)[1] > 0.70

    def _is_pre_level_modal(self, hsv: np.ndarray) -> bool:
        mx, my, mw, mh = config.MODAL_PLAY_ROI
        modal_crop = hsv[my:my+mh, mx:mx+mw]
        m_green = cv2.inRange(modal_crop, config.GREEN_HSV_LOWER, config.GREEN_HSV_UPPER)
        green_pct = (cv2.countNonZero(m_green) / (mw * mh)) * 100
        return green_pct > 35.0

    def _check_main_menu(self, hsv: np.ndarray) -> Optional[ScreenState]:
        # Priority 1: Hourly bonus (purple button at center-bottom)
        cx, cy, cw, ch = config.MENU_COLLECT_ROI
        c_crop = hsv[cy:cy+ch, cx:cx+cw]
        c_purple = cv2.inRange(c_crop, config.PURPLE_HSV_LOWER, config.PURPLE_HSV_UPPER)
        purple_pct = (cv2.countNonZero(c_purple) / (cw * ch)) * 100
        if purple_pct > 20.0:
            return ScreenState.MAIN_MENU_COLLECT

        # Priority 2: Green level play button at bottom-right
        px, py, pw, ph = config.MENU_PLAY_ROI
        p_crop = hsv[py:py+ph, px:px+pw]
        p_green = cv2.inRange(p_crop, config.GREEN_HSV_LOWER, config.GREEN_HSV_UPPER)
        green_pct = (cv2.countNonZero(p_green) / (pw * ph)) * 100
        if green_pct > 25.0:
            return ScreenState.MAIN_MENU_PLAY

        return None

    def _is_cards_dealing(self, screen: np.ndarray) -> bool:
        """
        Returns True if cards are actively being dealt (waste card not yet flipped/settled).
        """
        if self.card_detector is None:
            self.card_detector = CardDetector()

        waste = self.card_detector.detect_waste(screen)
        # If waste is missing while not in any menu, cards are in flight or being dealt
        return waste is None
