# config.py
# Central configuration — all screen coordinates and thresholds live here.
# Never hardcode coords in other files — always import from here.

# ── Screen ────────────────────────────────────────────────────────────────────
# Redmi Note 14 FHD+ — screenshots come in LANDSCAPE from ADB
SCREEN_WIDTH  = 2400  # px (landscape width)
SCREEN_HEIGHT = 1080  # px (landscape height)

# ── Tableau region (where card piles live, excluding UI bars and side decorations) ──
# Starts at x=500 to cleanly exclude left-side selfie video/Tinkerbell, spans to x=1950
TABLEAU_ROI = (500, 100, 1450, 680)  # (x, y, w, h) in landscape coords

# ── Fixed UI element positions (landscape coords, confirmed across screenshots) ──
# Stock pile (blue face-down deck) — tap top card to draw
STOCK_CENTER = (1134, 937)

# Waste pile (current face-up card) — right of stock
WASTE_CENTER = (1336, 937)

# Undo button — green circular arrow, right of waste
UNDO_CENTER = (1548, 909)

# WILD card button — bottom-right gold card
WILD_CENTER = (2277, 875)

# ── Template matching ─────────────────────────────────────────────────────────
TEMPLATE_MATCH_THRESHOLD = 0.72   # minimum confidence score for center glyphs
TEMPLATE_ANGLES          = [0, -11, 11, -21, 21]  # angles to handle tilted cards

# ── Timing ────────────────────────────────────────────────────────────────────
TAP_DELAY_MIN = 0.3   # seconds — minimum pause between taps
TAP_DELAY_MAX = 0.7   # seconds — maximum pause (randomised for human feel)
SCREENCAP_INTERVAL = 0.5  # seconds — wait after tap before next capture
