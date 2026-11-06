# config.py
# Central configuration — all screen coordinates and thresholds live here.
# Never hardcode coords in other files — always import from here.

# ── Screen ────────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 1080  # px — Redmi Note 14 FHD+ (verify with live screencap)
SCREEN_HEIGHT = 2400  # px

# ── Tableau region (upper area where card piles live) ────────────────────────
# Rough bounding box; exact card positions are detected dynamically
TABLEAU_ROI = (0, 80, 1080, 1550)  # (x, y, w, h)

# ── Fixed UI element positions (from screenshots) ────────────────────────────
# Stock pile (blue face-down deck) — bottom-left
STOCK_CENTER = (620, 1900)  # (x, y) — tap here to draw

# Waste pile (current face-up card) — bottom-center
WASTE_CENTER = (810, 1900)  # (x, y) — read rank from here

# Undo button — green circular arrow, bottom-center-right
UNDO_CENTER = (1000, 1900)

# WILD card button — bottom-right corner
WILD_CENTER = (1480, 1900)

# ── Template matching ─────────────────────────────────────────────────────────
TEMPLATE_MATCH_THRESHOLD = 0.75   # minimum confidence score (0–1)
TEMPLATE_SCALE_FACTORS   = [1.0, 0.95, 0.90, 0.85]  # multi-scale search range

# ── Timing ────────────────────────────────────────────────────────────────────
TAP_DELAY_MIN = 0.3   # seconds — minimum pause between taps
TAP_DELAY_MAX = 0.7   # seconds — maximum pause (randomised for human feel)
SCREENCAP_INTERVAL = 0.5  # seconds — wait after tap before next capture
