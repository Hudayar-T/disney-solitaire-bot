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


def test_pre_level_modal_enough_money():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)
    img = cv2.imread("tests/screenshots/modal_play_button/enough_money.jpg")
    assert img is not None

    action = handler.handle(img, dev=None)
    assert action.state == ScreenState.PRE_LEVEL_MODAL
    assert action.tapped_coord == config.MODAL_PLAY_CENTER
    assert action.wait_seconds == 2.5
    assert action.is_gameplay_ready is False


def test_pre_level_modal_not_enough_money():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)

    # Case 1: not_enough_money.png (Balance 2,065 < Cost 2,200)
    img1 = cv2.imread("tests/screenshots/modal_play_button/not_enough_money.png")
    assert img1 is not None
    action1 = handler.handle(img1, dev=None)
    assert action1.state == ScreenState.PRE_LEVEL_MODAL
    assert action1.tapped_coord == config.MODAL_CLOSE_CENTER
    assert action1.wait_seconds == config.INSUFFICIENT_FUNDS_WAIT
    assert action1.is_gameplay_ready is False

    # Case 2: not_enough_money2.png (Balance 1,315 < Cost 4,600)
    img2 = cv2.imread("tests/screenshots/modal_play_button/not_enough_money2.png")
    assert img2 is not None
    action2 = handler.handle(img2, dev=None)
    assert action2.state == ScreenState.PRE_LEVEL_MODAL
    assert action2.tapped_coord == config.MODAL_CLOSE_CENTER
    assert action2.wait_seconds == config.INSUFFICIENT_FUNDS_WAIT
    assert action2.is_gameplay_ready is False


def test_post_win_screen_detection():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)
    img = cv2.imread("tests/screenshots/post_win_screen/post_win_screen.jpg")
    assert img is not None

    action = handler.handle(img, dev=None)
    assert action.state == ScreenState.POST_WIN
    rx, ry, rw, rh = config.POPUP_DISMISS_ROI
    assert rx <= action.tapped_coord[0] <= rx + rw
    assert ry <= action.tapped_coord[1] <= ry + rh
    assert action.is_gameplay_ready is False


def test_random_reward_detection():
    detector = MenuDetector()
    handler = MenuHandler(detector=detector)
    img = cv2.imread("tests/screenshots/random_reward/random_reward.jpg")
    assert img is not None

    action = handler.handle(img, dev=None)
    assert action.state == ScreenState.RANDOM_REWARD
    rx, ry, rw, rh = config.POPUP_DISMISS_ROI
    assert rx <= action.tapped_coord[0] <= rx + rw
    assert ry <= action.tapped_coord[1] <= ry + rh
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
    test_pre_level_modal_enough_money()
    test_pre_level_modal_not_enough_money()
    test_post_win_screen_detection()
    test_random_reward_detection()
    test_end_level_confirmation_detection()
    test_cards_being_dealt_detection()
    test_in_game_screen_detection()
    print("All navigation unit tests passed successfully!")
