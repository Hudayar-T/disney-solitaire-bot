"""
vision/balance_detector.py
Detects and parses the coin balance in the top-left corner using DigitDetector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np

import config
from vision.digit_detector import DigitDetector, DigitMatch, DigitResult

DEFAULT_DIGITS_DIR = Path(__file__).parent / "templates" / "digits"

# Type aliases for backwards compatibility
BalanceDigitMatch = DigitMatch
BalanceResult = DigitResult


class BalanceDetector:
    """
    Detects coin balance numbers from top-left screen region using DigitDetector.
    """

    def __init__(
        self,
        templates_dir: Optional[Path | str] = None,
        threshold: float = config.BALANCE_MATCH_THRESHOLD,
    ):
        self.threshold = threshold
        self.digit_detector = DigitDetector(
            templates_dir=templates_dir or DEFAULT_DIGITS_DIR,
            threshold=threshold,
        )

    @property
    def templates(self):
        """Expose loaded templates for backward compatibility."""
        return self.digit_detector.templates

    def detect(self, screen: np.ndarray) -> BalanceResult:
        """
        Parses the balance from the full screenshot.

        Args:
            screen: Full screen BGR numpy array (2400x1080).

        Returns:
            BalanceResult containing the integer value, raw string, and match details.
        """
        if screen is None:
            return BalanceResult()

        return self.digit_detector.detect(
            image=screen,
            roi=config.BALANCE_ROI,
            mode="dark_on_light",
            threshold=self.threshold,
        )

    def get_balance(self, screen: np.ndarray) -> Optional[int]:
        """Convenience method returning the balance as an int, or None if undetectable."""
        return self.detect(screen).value
