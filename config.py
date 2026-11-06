# config.py
# Central configuration — all screen coordinates and thresholds live here.
# Never hardcode coords in other files — always import from here.

# ── Screen ────────────────────────────────────────────────────────────────────
# Redmi Note 14 FHD+ — screenshots come in LANDSCAPE from ADB
SCREEN_WIDTH  = 2400  # px (landscape width)
SCREEN_HEIGHT = 1080  # px (landscape height)

# ── Tableau region (where card piles live, excluding UI bars) ─────────────────
# Measured from landscape screenshots:
#   Top boundary: ~100px (below status bar + score)
#   Bottom boundary: ~750px (above stock/waste row)
#   Left boundary: ~300px (right of Tinkerbell/chest)
#   Right boundary: ~2100px (left of right edge decorations)
TABLEAU_ROI = (300, 100, 1900, 750)  # (x, y, w, h) in landscape coords

# ── Fixed UI element positions (landscape coords, measured from screenshots) ──
# Stock pile (blue face-down deck)
STOCK_CENTER = (1134, 937)  # (x, y) — confirmed across all 5 screenshots

# Waste pile (current face-up card) — right of stock
WASTE_CENTER = (1336, 937)  # (x, y) — confirmed across all 5 screenshots

# Undo button — green circular arrow, right of waste
UNDO_CENTER = (1530, 930)

# WILD card button — far right edge
WILD_CENTER = (1480, 620)

# ── Template matching ─────────────────────────────────────────────────────────
TEMPLATE_MATCH_THRESHOLD = 0.75   # minimum confidence score (0–1)
TEMPLATE_SCALE_FACTORS   = [1.0, 0.95, 0.90, 0.85, 1.05, 1.10]  # multi-scale search

# ── Timing ────────────────────────────────────────────────────────────────────
TAP_DELAY_MIN = 0.3   # seconds — minimum pause between taps
TAP_DELAY_MAX = 0.7   # seconds — maximum pause (randomised for human feel)
SCREENCAP_INTERVAL = 0.5  # seconds — wait after tap before next capture
