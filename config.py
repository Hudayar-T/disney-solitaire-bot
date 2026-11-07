# config.py
# Central configuration — all screen coordinates and thresholds live here.
# Never hardcode coords in other files — always import from here.

# ── Screen ────────────────────────────────────────────────────────────────────
# Redmi Note 14 FHD+ — screenshots come in LANDSCAPE from ADB
SCREEN_WIDTH  = 2400  # px (landscape width)
SCREEN_HEIGHT = 1080  # px (landscape height)

# ── Tableau region (where card piles live, excluding UI bars and side decorations) ──
# Starts at x=400 to include wide edge cards while excluding side buttons/avatar, spans to x=2050
TABLEAU_ROI = (400, 80, 1650, 720)  # (x, y, w, h) in landscape coords

# ── Fixed UI element positions (landscape coords, confirmed across screenshots) ──
# Stock pile (blue face-down deck) — tap top card to draw
STOCK_CENTER = (1134, 937)

# Waste pile (current face-up card) — right of stock
WASTE_CENTER = (1336, 937)

# Undo button — green circular arrow, right of waste
UNDO_CENTER = (1548, 909)

# WILD card button — bottom-right gold card (WILD_ROI handles orientation shifts like notch padding)
WILD_CENTER = (2277, 875)
WILD_ROI = (2050, 720, 350, 330)  # (x, y, w, h) search region in landscape coords

# ── Template matching ─────────────────────────────────────────────────────────
TEMPLATE_MATCH_THRESHOLD = 0.72   # minimum confidence score for center glyphs
TEMPLATE_ANGLES          = [0, -10, 10, -20, 20, -30, 30, -40, 40, -48, 48]  # angles to handle steep card tilts up to ±48°

# ── Timing & Anti-Bot Jitter ──────────────────────────────────────────────────
TAP_DELAY_MIN = 0.3   # seconds — minimum pause between taps
TAP_DELAY_MAX = 1.6   # seconds — maximum pause (randomised for human feel)
TAP_JITTER_X  = 30    # px — maximum random horizontal offset from center (68)
TAP_JITTER_Y  = 40    # px — maximum random vertical offset from center (92)
SCREENCAP_INTERVAL = 1.2  # seconds — wait after tap for flight & flip animations to settle

# ── Menu & Navigation Positions (landscape coords) ───────────────────────────
# Main menu: Purple "COLLECT" button (hourly coin bonus)
MENU_COLLECT_ROI    = (1080, 860, 320, 180)  # (x, y, w, h)
MENU_COLLECT_CENTER = (1240, 950)

# Main menu: Green play button (bottom-right level button)
MENU_PLAY_ROI       = (2140, 815, 220, 230)  # (x, y, w, h)
MENU_PLAY_CENTER    = (2250, 930)

# Pre-level modal: Green "PLAY" button at modal center-bottom
MODAL_PLAY_ROI      = (1034, 736, 340, 156)  # (x, y, w, h)
MODAL_PLAY_CENTER   = (1204, 814)

# Neutral dismiss tap coordinate for popups ("TAP TO COLLECT", "TAP ANYWHERE TO COLLECT")
POPUP_DISMISS_COORD = (1200, 930)

# ── Menu Detection Thresholds & Color Ranges ──────────────────────────────────
GREEN_HSV_LOWER     = (35, 100, 100)
GREEN_HSV_UPPER     = (85, 255, 255)

PURPLE_HSV_LOWER    = (125, 60, 60)
PURPLE_HSV_UPPER    = (160, 255, 255)

# Wait time when cards are being dealt (seconds)
DEAL_ANIMATION_WAIT = 2.0
