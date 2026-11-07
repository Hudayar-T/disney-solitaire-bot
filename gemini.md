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
- It resembles blue cards but has a distinct **yellow/gold border** wrapping around the entire button perimeter.
- **NEVER tap stock with a yellow border** — it spends real in-game currency. Treat as **STOCK EMPTY**.
- **WILD in Stock & Buried Deck Disambiguation:**
  1. *WILD on top:* Template match `detect_stock_has_wild()` verifies if a yellow WILD is the active top card.
  2. *WILD buried in deck:* When cards in the deck fan out to the left, yellow edges of buried cards appear only on the left stacked edge (`x < STOCK_CENTER_X`).
  3. *True Buy Prompt:* The gold border frames the whole button, so the right half (`x > STOCK_CENTER_X`) has strong yellow pixels (`right_yellow >= 3%`, typically ~7.5%).
  - If yellow is confined to the left stacked edge (`right_yellow < 3%`), it is a normal deck with a buried card — continue to draw normally!

## System Architecture & Mechanics

The bot runs a continuous loop: **Screencap → Menu Check → Board Parse → Solve → Tap → Wait → Repeat**. Below is each subsystem with exact file and line references so agents can jump straight to the right code.

### 1. Configuration — `config.py` (63 lines)

Single source of truth for every coordinate, ROI, threshold, and timing constant. **All other modules import from here — never hardcode coordinates.**

- **L7-12:** Screen dimensions (2400×1080 landscape) and `TABLEAU_ROI` (where card piles live).
- **L16-26:** Fixed UI positions — `STOCK_CENTER`, `WASTE_CENTER`, `UNDO_CENTER`, `WILD_CENTER/ROI`.
- **L29-37:** Template matching settings (threshold 0.72, angles ±48°) and anti-bot timing/jitter constants.
- **L41-53:** Menu/modal button ROIs and tap centers (`MENU_COLLECT`, `MENU_PLAY`, `MODAL_PLAY`, `POPUP_DISMISS_COORD`).
- **L56-63:** HSV color ranges for menu detection and `DEAL_ANIMATION_WAIT = 2.0s`.

### 2. ADB Communication — `adb_controller.py` (118 lines)

Handles all device I/O: connection, screenshots, and humanized tapping.

- **L23-54:** `connect()` finds the first ADB device via `adbutils`; `screencap()` runs `screencap -p` and returns a PIL Image (RGB).
- **L57-68:** `save_screenshot()` writes a timestamped PNG to `tests/screenshots/`.
- **L71-105:** `compute_jittered_coord()` applies Gaussian 2D offset; `tap()` sends `input tap` with random delay and jitter, checks for Xiaomi `SecurityException`.

### 3. Vision & Detection — `vision/detector.py` (405 lines)

Core card detection engine. Segments face-down cards via HSV color, identifies face-up ranks via multi-angle template matching, and detects UI elements (waste, stock, undo, wild).

- **L22-62:** Constants — HSV color ranges (blue backs, green mystery, yellow buy-prompt), area filters (8K-45K px²), template dir.
- **L28-44:** `Detection` dataclass — `rank, cx, cy, confidence, tw, th, angle`.
- **L65-100:** `_nms()` — Non-Maximum Suppression (IoU 0.30).
- **L103-148:** `CardDetector.__init__` + `_load_glyph_templates()` — loads A-K rank images, extracts center glyphs, pre-rotates at all `TEMPLATE_ANGLES`.
- **L150-259:** Card detection — `detect_facedown()` uses HSV segmentation + contour analysis; `detect_faceup()` uses multi-angle template matching (threshold ≥ 0.72); `detect()` combines both, sorted by position.
- **L261-286:** `detect_waste()` — glyph match in 220×320 ROI around waste center, with WILD template fallback.
- **L288-368:** Stock detection — `detect_normal_stock_present()` implements the WILD-first disambiguation algorithm (yellow ratio → WILD template → right-half yellow check → blue ratio fallback); `detect_stock_has_wild()` and `detect_stock_present()` wrap the logic.
- **L370-405:** `detect_undo_present()` and `detect_wild_present()` — template matches for undo button and bottom-right corner WILD card.

**Also in `vision/`:**
- `menu_detector.py` (147 lines) — See §5 below.

### 4. Board State & Dependency Graph — `board/`

**`board/state.py` (105 lines):** `Card` dataclass (L11-51) with DAG fields (`blocked_by`, `blocks`) and properties (`is_playable`, `is_face_up`, `is_mystery`, `rotated_rect`). `BoardState` dataclass (L54-105) aggregates tableau, waste, stock/wild/undo flags, and provides filtered views (`playable_cards`, `faceup_cards`, `facedown_cards`).

**`board/parser.py` (163 lines):** Converts raw detections into a `BoardState` with DAG.
- **L18-58:** Overlap helpers — `_compute_overlap_area()` uses `cv2.rotatedRectangleIntersection()` (min 2000 px²); `_determine_front_by_edge()` uses Canny edge continuity for cards at similar heights.
- **L61-98:** `build_dependency_graph()` — O(n²) pairwise overlap. Z-order: face-up > face-down; same type uses cy distance or edge analysis.
- **L106-163:** `BoardParser.parse()` — full pipeline: detect cards → assign IDs → build DAG → detect waste/stock/undo/wild → return `BoardState`.

### 5. Menu Detection & Navigation — `vision/menu_detector.py` + `navigation/menu_handler.py`

The `handle_menu_navigation/` folder is **reference screenshots only** (no code). Actual logic lives in these two files:

**`vision/menu_detector.py` (147 lines):** Screen state classifier. `ScreenState` enum (L18-27) covers `MAIN_MENU_COLLECT/PLAY`, `PRE_LEVEL_MODAL`, `POST_WIN`, `RANDOM_REWARD`, `CARDS_DEALING`, `IN_GAME`, `UNKNOWN`. `detect_state()` (L52-85) is a priority-ordered classifier using template matching (post-win, random reward popups) and HSV color ratios (menu buttons, pre-level modal green). Falls back to `IN_GAME`.

**`navigation/menu_handler.py` (111 lines):** Tap dispatch controller. `MenuHandler.handle()` (L35-111) calls `detect_state()` and dispatches: IN_GAME → gameplay ready; CARDS_DEALING → sleep 2s; POST_WIN/RANDOM_REWARD → tap dismiss; MAIN_MENU → tap collect or play; PRE_LEVEL_MODAL → tap play button. Executes jittered tap if device is provided.

### 6. Decision Solver — `engine/solver.py` (320 lines)

Move selection, chain search, and WILD usage rules.

- **L22-45:** Constants, `MoveType` enum (`PLAY_CARD`, `DRAW_STOCK`, `PLAY_WILD`, `NO_MOVES`), and `Move` dataclass.
- **L48-102:** Move helpers — `are_ranks_adjacent()` (±1 with A↔K wrap), `get_legal_tableau_moves()`, `simulate_play_card()` (removes card from DAG).
- **L112-229:** Scoring engine — `find_best_chain()` does recursive DFS lookahead (max depth 10) with unblock bonuses (+35 mystery, +25 facedown, +15 faceup); `can_chain_clear_tableau()` tests full clearability for WILD decisions; `score_tableau_move()` combines immediate unblocks + chain lookahead.
- **L238-320:** `Solver.choose_move()` — **Decision hierarchy**: ① highest-scored tableau move; ② stock WILD on top (score=90); ③ normal stock draw (score=5); ④ corner WILD only if 1 card left or can chain-clear; ⑤ NO_MOVES.

### 7. Game Loop — `main.py` (229 lines) & `live_step.py` (197 lines)

**`main.py`:** Autonomous game loop. Logging setup (L47-60), CLI args `--max-steps/--save-screens/--single-level` (L71-90). `run()` (L103-221): connects ADB → inits BoardParser/Solver/MenuHandler → loops: capture → menu handling → board parse → solver → tap → wait.

**`live_step.py`:** Interactive debug runner. `annotate_proposed_move()` (L24-73) draws crosshair overlay on screenshot. `run_interactive_loop()` (L76-194) runs same pipeline but pauses for user confirmation (`Enter/s/q`) before each tap.

### Pipeline Flow Diagram
```
main.py loop:
  ADB screencap (adb_controller.py:43)
    → PIL Image → cv2 BGR numpy
    ↓
  MenuHandler.handle(screen)  (navigation/menu_handler.py:35)
    → MenuDetector.detect_state()  (vision/menu_detector.py:52)
    ↓ if IN_GAME
  BoardParser.parse(screen)  (board/parser.py:109)
    → CardDetector.detect()  (vision/detector.py:245)
       ├─ detect_facedown()  HSV segmentation  (vision/detector.py:150)
       └─ detect_faceup()    template matching  (vision/detector.py:215)
    → build_dependency_graph()  O(n²) overlap + Z-order  (board/parser.py:61)
    → detect waste/stock/undo/wild  (vision/detector.py:261-405)
    → BoardState  (board/state.py:54)
    ↓
  Solver.choose_move(state)  (engine/solver.py:238)
    → get_legal_tableau_moves()   rank ±1 adjacency  (engine/solver.py:64)
    → score_tableau_move()        unblock value + DFS chain  (engine/solver.py:188)
    → Move decision hierarchy     play > draw > wild > no_moves
    ↓
  adb_controller.tap(dev, x, y)  Gaussian jitter + random delay  (adb_controller.py:83)
    ↓
  time.sleep(SCREENCAP_INTERVAL)  → next iteration
```

## Project Structure
```
disney-solitaire-bot/
├── GEMINI.md                        ← Agent context & mechanics reference (this file)
├── PLAN.md                          ← Build plan & active milestone tracking
├── config.py                  [63L] ← All screen coordinates, ROIs, thresholds, delays
├── adb_controller.py         [118L] ← ADB connection, screencap, jittered tap
├── main.py                   [229L] ← Autonomous game loop orchestration
├── live_step.py              [197L] ← Interactive step-by-step debug runner
├── vision/
│   ├── detector.py           [405L] ← Card segmentation, template matching, UI detection
│   ├── menu_detector.py      [147L] ← Screen state classifier (menus, popups, dealing)
│   └── templates/                   ← A-K rank images, BACK, UNDO, WILD, popup templates
├── board/
│   ├── state.py              [105L] ← Card & BoardState dataclasses with DAG fields
│   └── parser.py             [163L] ← Detection → DAG, occlusion resolution
├── engine/
│   └── solver.py             [320L] ← Move scoring, DFS chain search, WILD rules
├── navigation/
│   └── menu_handler.py       [111L] ← Menu/popup tap dispatch controller
├── handle_menu_navigation/          ← Reference screenshots only (no code)
│   ├── main_menu.jpg, post_win_screen.jpg, random_reward.jpg
│   ├── one_more_play_button.jpg, cards_are_being_dealt.jpg
│   └── handle_menu_navigation.txt
├── tests/
│   ├── screenshots/                 ← Test screenshots (numbered + debug images)
│   │   └── end_level/              ← End-of-level screenshots
│   ├── test_detector.py       [52L] ← Card detection & UI element tests
│   ├── test_board_parser.py   [71L] ← DAG & occlusion tests with visual annotation
│   ├── test_solver.py        [136L] ← Solver decisions + synthetic WILD edge cases
│   └── test_menu_navigation.py [97L] ← Menu detection & navigation tests
├── logs/                            ← Rotating log files from main.py runs
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
