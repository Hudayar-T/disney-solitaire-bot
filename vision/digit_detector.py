"""
vision/digit_detector.py
Universal digit detector for numbers and costs across the game UI.
Uses single-channel grayscale template matching with support for:
  - dark-on-light text (e.g. balance pill)
  - white-on-dark text (e.g. wild card cost, level play button cost)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from loguru import logger

import config

DEFAULT_DIGITS_DIR = Path(__file__).parent / "templates" / "digits"


@dataclass
class DigitMatch:
    """Represents a matched character (digit or comma)."""
    char: str
    x: int             # X coordinate (relative to screen or provided ROI offset)
    y: int             # Y coordinate
    w: int
    h: int
    confidence: float

    def __repr__(self) -> str:
        return f"DigitMatch('{self.char}', x={self.x}, y={self.y}, conf={self.confidence:.2f})"


@dataclass
class DigitResult:
    """Result of digit sequence parsing."""
    value: Optional[int] = None
    raw_str: str = ""
    confidence: float = 0.0
    matches: List[DigitMatch] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.value is not None


class DigitDetector:
    """
    Universal detector for fixed-font digits ('0'–'9') and comma (',').
    """

    def __init__(
        self,
        templates_dir: Optional[Path | str] = None,
        threshold: float = config.DIGIT_MATCH_THRESHOLD,
    ):
        self.templates_dir = Path(templates_dir) if templates_dir else DEFAULT_DIGITS_DIR
        self.threshold = threshold
        self.templates: Dict[str, np.ndarray] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        if not self.templates_dir.exists():
            logger.warning(f"Digits template directory not found: {self.templates_dir}")
            return

        for file_path in sorted(self.templates_dir.glob("*.*")):
            if file_path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
                continue

            stem = file_path.stem.lower()
            char = "," if stem == "comma" else stem

            # Load strictly as grayscale
            template_gray = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            if template_gray is None:
                logger.warning(f"Failed to load digit template: {file_path}")
                continue

            self.templates[char] = template_gray

        loaded = sorted(self.templates.keys())
        logger.info(f"Loaded {len(self.templates)} grayscale digit templates: {loaded}")

    def detect(
        self,
        image: np.ndarray,
        roi: Optional[Tuple[int, int, int, int]] = None,
        mode: str = "dark_on_light",
        threshold: Optional[float] = None,
    ) -> DigitResult:
        """
        Detect digits in an image or specific ROI.

        Args:
            image: Input image (BGR or grayscale).
            roi: Optional (x, y, w, h) bounding box within image.
            mode: Color mode:
                  - "dark_on_light": Dark text on light background (e.g. coin balance).
                  - "white_on_dark": White text on dark background (e.g. buttons/costs).
                  - "auto": Automatically determines based on ROI background brightness.
            threshold: Match confidence threshold override.

        Returns:
            DigitResult with value, raw_str, confidence, and matches.
        """
        if image is None or not self.templates:
            return DigitResult()

        thresh = threshold if threshold is not None else self.threshold

        # Extract ROI if specified
        offset_x, offset_y = 0, 0
        if roi is not None:
            rx, ry, rw, rh = roi
            ih, iw = image.shape[:2]
            x1 = max(0, min(rx, iw))
            y1 = max(0, min(ry, ih))
            x2 = max(x1, min(rx + rw, iw))
            y2 = max(y1, min(ry + rh, ih))
            if x2 - x1 < 10 or y2 - y1 < 10:
                return DigitResult()
            proc_img = image[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
        else:
            proc_img = image

        # Convert to grayscale
        if len(proc_img.shape) == 3:
            gray = cv2.cvtColor(proc_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = proc_img.copy()

        # Handle color polarity
        if mode == "auto":
            # Dark background if average intensity is low
            effective_mode = "white_on_dark" if gray.mean() < 128 else "dark_on_light"
            result = self._match_digits(gray, offset_x, offset_y, effective_mode, thresh)
            if result.is_valid:
                return result
            # Fallback to alternate mode if no digits matched
            alternate_mode = "dark_on_light" if effective_mode == "white_on_dark" else "white_on_dark"
            return self._match_digits(gray, offset_x, offset_y, alternate_mode, thresh)

        return self._match_digits(gray, offset_x, offset_y, mode, thresh)

    def _match_digits(
        self,
        gray: np.ndarray,
        offset_x: int,
        offset_y: int,
        mode: str,
        threshold: float,
    ) -> DigitResult:
        # Templates are dark-on-light. If searching for white-on-dark, invert the image.
        target = (255 - gray) if mode == "white_on_dark" else gray

        raw_matches: List[DigitMatch] = []
        for char, tmpl in self.templates.items():
            th, tw = tmpl.shape[:2]
            if target.shape[0] < th or target.shape[1] < tw:
                continue

            res = cv2.matchTemplate(target, tmpl, cv2.TM_CCOEFF_NORMED)
            locs = np.where(res >= threshold)

            for pt in zip(*locs[::-1]):
                conf = float(res[pt[1], pt[0]])
                raw_matches.append(
                    DigitMatch(
                        char=char,
                        x=offset_x + int(pt[0]),
                        y=offset_y + int(pt[1]),
                        w=tw,
                        h=th,
                        confidence=conf,
                    )
                )

        if not raw_matches:
            return DigitResult()

        # Non-Maximum Suppression (NMS) sorted left-to-right
        raw_matches.sort(key=lambda m: m.x)
        filtered_matches: List[DigitMatch] = []

        for match in raw_matches:
            if not filtered_matches:
                filtered_matches.append(match)
                continue

            prev = filtered_matches[-1]
            # Horizontal overlap threshold (10px)
            if abs(match.x - prev.x) < 10:
                if match.confidence > prev.confidence:
                    filtered_matches[-1] = match
            else:
                filtered_matches.append(match)

        if not filtered_matches:
            return DigitResult()

        # Group matches into contiguous clusters (max gap between consecutive characters ~40px)
        clusters: List[List[DigitMatch]] = []
        current_cluster: List[DigitMatch] = []
        max_char_gap = 42

        for match in filtered_matches:
            if not current_cluster:
                current_cluster.append(match)
            else:
                dx = match.x - current_cluster[-1].x
                if dx <= max_char_gap:
                    current_cluster.append(match)
                else:
                    clusters.append(current_cluster)
                    current_cluster = [match]
        if current_cluster:
            clusters.append(current_cluster)

        # Pick the strongest cluster (most characters, tie-broken by confidence sum)
        best_cluster = max(clusters, key=lambda c: (len(c), sum(m.confidence for m in c)))

        raw_str = "".join(m.char for m in best_cluster)
        avg_conf = (
            sum(m.confidence for m in best_cluster) / len(best_cluster)
            if best_cluster
            else 0.0
        )

        numeric_str = "".join(ch for ch in raw_str if ch.isdigit())
        int_value = int(numeric_str) if numeric_str else None

        return DigitResult(
            value=int_value,
            raw_str=raw_str,
            confidence=avg_conf,
            matches=best_cluster,
        )

    def parse_number(
        self,
        image: np.ndarray,
        roi: Optional[Tuple[int, int, int, int]] = None,
        mode: str = "dark_on_light",
        threshold: Optional[float] = None,
    ) -> Optional[int]:
        """Convenience method returning parsed integer or None."""
        return self.detect(image, roi=roi, mode=mode, threshold=threshold).value
