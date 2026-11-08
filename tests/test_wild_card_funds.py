"""
tests/test_wild_card_funds.py
Validates:
1. Do we have a WILD card checker (tested on tests/screenshots/algorithm/*)
2. Funds to buy a WILD card checker & decision logic (tested on enough_money.jpg and not_enough_money.jpg)
"""

import sys
import unittest
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from vision.detector import CardDetector
from board.parser import BoardParser
from engine.solver import Solver, MoveType


class TestWildCardFunds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = CardDetector()
        cls.parser = BoardParser(detector=cls.detector)
        cls.solver = Solver()

    def test_has_free_wild_on_algorithm_screenshots(self):
        """
        Validates the free WILD card checker across algorithm screenshots:
        Screenshots 6, 7, 8, 9, 10, 11, 12, 13 have a red badge (has_free_wild = True).
        Screenshots 1, 2, 3, 4, 5, 14 do not (has_free_wild = False).
        """
        algo_dir = ROOT / "tests/screenshots/algorithm"
        self.assertTrue(algo_dir.exists())

        expected_results = {
            "1.jpg": False,
            "2.jpg": False,
            "3.jpg": False,
            "4.jpg": False,
            "5.jpg": False,
            "6.jpg": True,
            "7.jpg": True,
            "8.jpg": True,
            "9.jpg": True,
            "10.jpg": True,
            "11.jpg": True,
            "12.jpg": True,
            "13.jpg": True,
            "14.jpg": False,
        }

        print("\n" + "=" * 65)
        print("Test 1: Free WILD Badge Detection on algorithm screenshots")
        print("=" * 65)

        for filename, exp_has_free in expected_results.items():
            img_path = algo_dir / filename
            self.assertTrue(img_path.exists(), f"{filename} not found")
            img = cv2.imread(str(img_path))
            self.assertIsNotNone(img)

            has_free = self.detector.detect_has_free_wild(img)
            self.assertEqual(
                has_free,
                exp_has_free,
                f"Expected has_free_wild={exp_has_free} for {filename}, got {has_free}",
            )
            print(f"[+] {filename:8s} -> has_free_wild={has_free!s:5s} (expected={exp_has_free}) [PASS]")

    def test_wild_purchase_decision_enough_money(self):
        """
        In enough_money.jpg:
          - Tableau has 1 card left ('6')
          - Stock has +5 buy trap (empty)
          - Waste is '9' (cannot match 6)
          - No free WILD card owned (has_free_wild = False)
          - WILD purchase cost = 9,400
          - Balance = 33,123 (>= 9,400)
          -> Expected solver move: PLAY_WILD (purchase wild card)
        """
        img_path = ROOT / "tests/screenshots/should_use_right_bottom_wild_card/enough_money.jpg"
        self.assertTrue(img_path.exists())
        img = cv2.imread(str(img_path))
        self.assertIsNotNone(img)

        # 1. Vision assertions
        self.assertFalse(self.detector.detect_has_free_wild(img))
        cost = self.detector.detect_wild_cost(img)
        self.assertEqual(cost, 9400)

        # 2. Board state assertions
        state = self.parser.parse(img)
        self.assertFalse(state.has_free_wild)
        self.assertEqual(state.wild_cost, 9400)
        self.assertEqual(state.balance, 33123)
        self.assertEqual(len(state.tableau), 1)
        self.assertEqual(state.tableau[0].rank, "6")
        self.assertFalse(state.has_normal_stock)

        # 3. Solver decision assertion
        move = self.solver.choose_move(state)
        print("\nTest 2 (Enough Money to buy WILD):")
        print(f"  Decision: {move.move_type.name} at {move.tap_coord} (score={move.score})")
        print(f"  Reason: {move.reason}")
        self.assertEqual(move.move_type, MoveType.PLAY_WILD)
        self.assertEqual(move.tap_coord, state.wild_coord)

    def test_wild_purchase_decision_not_enough_money(self):
        """
        In not_enough_money.jpg:
          - Tableau has 1 card left ('J')
          - Stock has +5 buy trap (empty)
          - Waste is '2' (cannot match J)
          - No free WILD card owned (has_free_wild = False)
          - WILD purchase cost = 11,000
          - Balance = 1,315 (< 11,000)
          - END LEVEL button is visible
          -> Expected solver move: END_LEVEL (do NOT buy wild, end level instead)
        """
        img_path = ROOT / "tests/screenshots/should_use_right_bottom_wild_card/not_enough_money.jpg"
        self.assertTrue(img_path.exists())
        img = cv2.imread(str(img_path))
        self.assertIsNotNone(img)

        # 1. Vision assertions
        self.assertFalse(self.detector.detect_has_free_wild(img))
        cost = self.detector.detect_wild_cost(img)
        self.assertEqual(cost, 11000)

        # 2. Board state assertions
        state = self.parser.parse(img)
        self.assertFalse(state.has_free_wild)
        self.assertEqual(state.wild_cost, 11000)
        self.assertEqual(state.balance, 1315)
        self.assertEqual(len(state.tableau), 1)
        self.assertEqual(state.tableau[0].rank, "J")
        self.assertFalse(state.has_normal_stock)
        self.assertTrue(state.has_end_level)

        # 3. Solver decision assertion
        move = self.solver.choose_move(state)
        print("\nTest 3 (Not Enough Money to buy WILD):")
        print(f"  Decision: {move.move_type.name} at {move.tap_coord} (score={move.score})")
        print(f"  Reason: {move.reason}")
        self.assertEqual(move.move_type, MoveType.END_LEVEL)
        self.assertEqual(move.tap_coord, state.end_level_coord)


if __name__ == "__main__":
    unittest.main()
