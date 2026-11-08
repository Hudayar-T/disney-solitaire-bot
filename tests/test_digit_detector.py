"""
tests/test_digit_detector.py
Validates DigitDetector on both dark-on-light (balance) and white-on-dark (costs).
"""

import sys
import unittest
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.digit_detector import DigitDetector


class TestDigitDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = DigitDetector()

    def test_templates_loaded(self):
        # 0-9 and comma = 11 templates
        self.assertEqual(len(self.detector.templates), 11)
        for d in "0123456789":
            self.assertIn(d, self.detector.templates)
        self.assertIn(",", self.detector.templates)

    def test_white_on_dark_play_cost(self):
        """Tests parsing '4,600' from cost_example.png (white text on dark background)."""
        img_path = ROOT / "tests/screenshots/modal_play_button/cost_example.png"
        img = cv2.imread(str(img_path))
        self.assertIsNotNone(img)

        # In cost_example.png, the number is right after the coin
        # Digits start around x=190
        res = self.detector.detect(img, mode="white_on_dark", threshold=0.78)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.raw_str, "4,600")
        self.assertEqual(res.value, 4600)
        self.assertGreaterEqual(res.confidence, 0.85)

    def test_white_on_dark_wild_card_cost(self):
        """Tests parsing '11,000' from we_dont_have_a_wild_card.jpg."""
        img_path = ROOT / "tests/screenshots/should_use_right_bottom_wild_card/we_dont_have_a_wild_card.jpg"
        img = cv2.imread(str(img_path))
        self.assertIsNotNone(img)

        # Digits are at the bottom: y=210..275, x=40..180
        roi = (40, 210, 140, 65)
        res = self.detector.detect(img, roi=roi, mode="white_on_dark", threshold=0.78)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.raw_str, "11,000")
        self.assertEqual(res.value, 11000)
        self.assertGreaterEqual(res.confidence, 0.82)

    def test_auto_mode(self):
        """Tests that mode='auto' works seamlessly for both dark and white text."""
        # 1. Dark on light (balance)
        balance_img = cv2.imread(str(ROOT / "tests/screenshots/main_menu/main_menu.jpg"))
        res_dark = self.detector.detect(balance_img, roi=(240, 65, 380, 60), mode="auto")
        self.assertEqual(res_dark.raw_str, "25,871")
        self.assertEqual(res_dark.value, 25871)

        # 2. White on dark (play cost)
        cost_img = cv2.imread(str(ROOT / "tests/screenshots/modal_play_button/cost_example.png"))
        res_white = self.detector.detect(cost_img, mode="auto")
        self.assertEqual(res_white.raw_str, "4,600")
        self.assertEqual(res_white.value, 4600)

    def test_parse_number_convenience(self):
        cost_img = cv2.imread(str(ROOT / "tests/screenshots/modal_play_button/cost_example.png"))
        val = self.detector.parse_number(cost_img, mode="white_on_dark")
        self.assertEqual(val, 4600)


if __name__ == "__main__":
    unittest.main()
