# Disney Solitaire Bot — Agent Context

## Project Overview
Automate playing **Disney Solitaire** (TriPeaks-style variant) on an Android phone via ADB + Python.
Core loop: Screen capture → Card detection & DAG parse → Move solver → ADB tap with humanized jitter.

## Device & Environment
- **Device:** Redmi Note 14 (USB debugging enabled)
- **Screen Resolution:** 2400 × 1080 px (native screenshots from ADB arrive in **Landscape**)
- **Dev Environment:** Windows machine, Python virtualenv at `.venv/`
- **Coordinate Origin:** (0,0) is top-left. All ROIs stored as `(x, y, w, h)`; all tap targets as `(x, y)` center.
- **Rule:** Never hardcode coordinates in code — always derive from `config.py`.

## Game Rules & Strategic Logic
- **Board Layout:** Cards stacked in haphazard overlapping piles (like Mahjong Titans, NOT a rigid grid). Pile count and card count vary by level.
- **Playability:** Only top uncovered face-up cards are playable (`len(blocked_by) == 0` and `is_face_up`). Cards underneath are visible but locked.
- **Rank Matching:** A tableau card is playable if rank is ±1 from waste top (wraps Ace ↔ King: A matches 2 and K). **Suit does NOT matter**.
- **Streak Bonus:** Consecutive chain clears increase score multiplier.

### 🃏 WILD Card Usage Rules
- **Center stack / waste WILD:** Play unconditionally whenever visible!
- **Bottom-right corner WILD (expensive / purchased):**
  - Use ONLY when stock is empty AND either:
    1. Exactly 1 card remains on the tableau (guarantees win), OR
    2. Remaining tableau cards can be 100% chain-cleared.
  - Never waste bottom-right WILD if remaining cards cannot clear the board.

### ⚠️ Stock Pile — "Buy More Cards" Trap & WILD Guard
- When stock runs out of real cards, the game shows a paid "+N cards" prompt (e.g. "+5" with a coin cost like "7,500").
- It resembles blue cards but has a distinct **yellow/gold border**.
- **NEVER tap stock with a yellow border** — it spends real in-game currency. Treat as **STOCK EMPTY**.
- **WILD in Stock False-Positive Guard:**
  - Yellow WILD cards sitting inside the stock pile also exhibit yellow pixels.
  - Detection logic: Before treating yellow as a buy prompt, check for WILD via template matching (`detect_stock_has_wild()`).
  - If WILD detected → yellow comes from the card; continue to blue card check.
  - If no WILD and yellow pixels ≥ 5% (H:15–40, S:80+, V:150+) → buy prompt confirmed → treat as empty.

## System Architecture & Mechanics

### 1. Vision & Detection (`vision/`)
- **Card Segmentation:** HSV color segmentation (blue backs vs white faces), `cv2.findContours`, `cv2.minAreaRect`, area filtering (12,000–45,000 px²).
- **Rank Recognition:** Template matching on large centered rank glyph.
  - Pre-rotated templates covering steep tilts up to ±48° (`TEMPLATE_ANGLES`).
  - NMS deduplication with IoU 0.35 threshold; confidence threshold ≥ 0.72.

### 2. Board State & Dependency Graph (`board/`)
- **Card Polygons:** Rotated bounding boxes from `cv2.boxPoints`.
- **Overlap Detection:** `cv2.rotatedRectangleIntersection`. Minimum intersection area: `2,000 px²` (~7% card overlap).
- **Z-Order / Occlusion Rules:**
  1. Face-up cards are strictly rendered on top of face-down cards.
  2. If overlapping cards share the same state (both face-up or both face-down):
     - If vertical distance `|cy1 - cy2| > 40px`: lower card on screen (larger `cy`) is on top (downward stacking order).
     - If vertical distance `|cy1 - cy2| <= 40px`: edge continuity (`Canny` + unbroken contour across intersection) determines front card.
- **Playable Card Definition:** `is_face_up == True` and `len(blocked_by) == 0`.

### 3. Decision Solver (`engine/`)
- **Move Generation:** Finds all playable cards matching waste rank ±1 (wrapping A↔K).
- **Lookahead & Chain Evaluation:**
  - Evaluates streak score and unblocked cards along lookahead branches.
  - Prioritizes branches that unblock face-down ("mystery") cards.
- **Fallback Hierarchy:** Tableau move → Draw stock (`STOCK_CENTER`) → Corner WILD (if conditions met) → `NO_MOVES`.

### 4. Tap Automation & Anti-Bot (`adb_controller.py`)
- **Spatial Jitter:** Coordinates randomized with 2D Gaussian offset (`TAP_JITTER_X=30`, `TAP_JITTER_Y=40`).
- **Timing Jitter:** Random delays between taps (`TAP_DELAY_MIN=0.3s`, `TAP_DELAY_MAX=1.6s`).
- **Animation Settling:** Waits `SCREENCAP_INTERVAL=1.2s` after tap for card flight and flip animations.

## Project Structure
```
disney-solitaire-bot/
├── GEMINI.md                  ← Agent context & mechanics reference (this file)
├── PLAN.md                    ← Build plan & active milestone tracking
├── config.py                  ← Screen coordinates, ROIs, thresholds, delays
├── adb_controller.py          ← ADB connection, screencap, jittered tap
├── vision/
│   ├── capture.py             ← Screen capture wrappers
│   ├── detector.py            ← Card segmentation & multi-angle template matching
│   └── templates/             ← Card rank & UI templates (A-K, BACK, UNDO, WILD)
├── board/
│   ├── state.py               ← Card & BoardState dataclasses with DAG tracking
│   └── parser.py              ← Detection → DAG & occlusion resolution
├── engine/
│   └── solver.py              ← Move selection, lookahead search, WILD rules
├── main.py                    ← Autonomous game loop orchestration
├── live_step.py               ← Interactive step-by-step debug runner
├── tests/
│   ├── screenshots/           ← Test screenshots
│   ├── test_detector.py       ← Card detection & stock/UI unit tests
│   ├── test_board_parser.py   ← DAG & occlusion resolution tests
│   └── test_solver.py         ← Move solver & heuristic chain tests
└── requirements.txt
```

## Running the Bot
- **Autonomous Loop:** `.venv\Scripts\python main.py [--max-steps N] [--save-screens]`
- **Interactive Step Debug:** `.venv\Scripts\python live_step.py`
- **Run Tests:** `.venv\Scripts\python tests/test_detector.py` (or `test_solver.py`, `test_board_parser.py`)

## Agent Guidelines
- Always verify coordinates against `config.py` — never hardcode.
- Never tap yellow-bordered stock.
- Update `PLAN.md` upon completing milestone tasks.
- Confirm with user before creating new modules or starting major phases.
