"""
tests/test_menu_navigation.py
Tests menu detection and navigation actions across all reference screenshots.
"""

import sys
from pathlib import Path
import cv2

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from vision.menu_detector import MenuDetector, ScreenState
from navigation.menu_handler import MenuHandler


def test_main_menu_bonus_detection():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)
    img = cv2.imread("tests/screenshots/main_menu/main_menu.jpg")
    assert img is not None

    action = handler.handle(img, dev=None)
    assert action.state == ScreenState.MAIN_MENU_COLLECT
    assert action.tapped_coord == config.MENU_COLLECT_CENTER
    assert action.is_gameplay_ready is False


def test_pre_level_modal_detection():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)
    img = cv2.imread("tests/screenshots/final_play_button/enough_money.jpg")
    assert img is not None

    action = handler.handle(img, dev=None)
    assert action.state == ScreenState.PRE_LEVEL_MODAL
    assert action.tapped_coord == config.MODAL_PLAY_CENTER
    assert action.is_gameplay_ready is False


def test_post_win_screen_detection():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)
    img = cv2.imread("tests/screenshots/post_win_screen/post_win_screen.jpg")
    assert img is not None

    action = handler.handle(img, dev=None)
    assert action.state == ScreenState.POST_WIN
    assert action.tapped_coord == config.POPUP_DISMISS_COORD
    assert action.is_gameplay_ready is False


def test_random_reward_detection():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)
    img = cv2.imread("tests/screenshots/random_reward/random_reward.jpg")
    assert img is not None

    action = handler.handle(img, dev=None)
    assert action.state == ScreenState.RANDOM_REWARD
    assert action.tapped_coord == config.POPUP_DISMISS_COORD
    assert action.is_gameplay_ready is False


def test_end_level_confirmation_detection():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)
    img = cv2.imread("tests/screenshots/end_level/end_level_confirmation.png")
    assert img is not None

    action = handler.handle(img, dev=None)
    assert action.state == ScreenState.END_LEVEL_CONFIRM
    assert action.tapped_coord == config.END_LEVEL_CONFIRM_CENTER
    assert action.is_gameplay_ready is False


def test_cards_being_dealt_detection():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)
    img = cv2.imread("tests/screenshots/card_are_being_dealt/cards_are_being_dealt.jpg")
    assert img is not None

    action = handler.handle(img, dev=None)
    assert action.state == ScreenState.CARDS_DEALING
    assert action.wait_seconds == config.DEAL_ANIMATION_WAIT
    assert action.is_gameplay_ready is False


def test_in_game_screen_detection():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)
    for num in [1, 10]:
        img = cv2.imread(f"tests/screenshots/algorithm/{num}.jpg")
        assert img is not None

        action = handler.handle(img, dev=None)
        assert action.state == ScreenState.IN_GAME
        assert action.is_gameplay_ready is True


if __name__ == "__main__":
    test_main_menu_bonus_detection()
    test_pre_level_modal_detection()
    test_post_win_screen_detection()
    test_random_reward_detection()
    test_end_level_confirmation_detection()
    test_cards_being_dealt_detection()
    test_in_game_screen_detection()
    print("All navigation unit tests passed successfully!")
