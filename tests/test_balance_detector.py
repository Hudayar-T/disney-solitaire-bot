"""
tests/test_balance_detector.py
Validates the balance detector on all available game and menu screenshots.
"""

import sys
import unittest
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.balance_detector import BalanceDetector

TEST_CASES = [
    # (relative_path, expected_raw, expected_int)
    ("tests/screenshots/main_menu/main_menu.jpg", "25,871", 25871),
    ("tests/screenshots/final_play_button/enough_money.jpg", "41,669", 41669),
    ("tests/screenshots/algorithm/1.jpg", "444", 444),
    ("tests/screenshots/algorithm/2.jpg", "144", 144),
    ("tests/screenshots/algorithm/6.jpg", "21,679", 21679),
    ("tests/screenshots/algorithm/10.jpg", "23,869", 23869),
    ("tests/screenshots/algorithm/13.jpg", "21,471", 21471),
    ("tests/screenshots/algorithm/14.jpg", "37,269", 37269),
    ("tests/screenshots/card_are_being_dealt/cards_are_being_dealt.jpg", "37,269", 37269),
    ("tests/screenshots/random_offer/invite_friends.jpg", "1,315", 1315),
    ("tests/screenshots/random_offer/random_offer2.jpg", "1,315", 1315),
    ("tests/screenshots/random_offer/random_offer3.jpg", "1,315", 1315),
    ("tests/screenshots/random_reward/random_reward.jpg", "19,739", 19739),
    ("tests/screenshots/random_reward/random_reward2.jpg", "13,427", 13427),
    ("tests/screenshots/should_use_right_bottom_wild_card/enough_money.jpg", "33,123", 33123),
    ("tests/screenshots/should_use_right_bottom_wild_card/not_enough_money.jpg", "1,315", 1315),
]


class TestBalanceDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = BalanceDetector()

    def test_loads_templates(self):
        self.assertGreaterEqual(len(self.detector.templates), 10)
        self.assertIn(",", self.detector.templates)

    def test_all_screenshots(self):
        passed = 0
        total = len(TEST_CASES)

        print("\n" + "=" * 70)
        print(f"Running Balance Detector on {total} test screenshots:")
        print("=" * 70)

        for rel_path, exp_raw, exp_int in TEST_CASES:
            img_path = ROOT / rel_path
            if not img_path.exists():
                print(f"[-] {rel_path:55s} [SKIPPED - NOT FOUND]")
                continue

            img = cv2.imread(str(img_path))
            self.assertIsNotNone(img, f"Failed to load image: {img_path}")

            result = self.detector.detect(img)
            self.assertTrue(result.is_valid, f"Failed to parse balance for {rel_path}")
            self.assertEqual(result.raw_str, exp_raw, f"Raw mismatch in {rel_path}")
            self.assertEqual(result.value, exp_int, f"Int mismatch in {rel_path}")
            self.assertGreaterEqual(result.confidence, 0.85, f"Low conf in {rel_path}")

            passed += 1
            print(f"[+] {rel_path:50s} -> {result.raw_str:8s} int={result.value:<6d} (conf={result.confidence:.2f}) [PASS]")

        print("=" * 70)
        print(f"Result: {passed}/{total} passed ({(passed/total)*100:.1f}%)")
        print("=" * 70)

    def test_convenience_method(self):
        img_path = ROOT / "tests/screenshots/main_menu/main_menu.jpg"
        img = cv2.imread(str(img_path))
        self.assertEqual(self.detector.get_balance(img), 25871)

    def test_empty_screen(self):
        self.assertIsNone(self.detector.detect(None).value)
        self.assertIsNone(self.detector.get_balance(None))


if __name__ == "__main__":
    unittest.main()
