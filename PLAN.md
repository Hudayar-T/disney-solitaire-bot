# 🃏 Disney Solitaire Bot — Master Plan

> **Game:** Disney Solitaire (TriPeaks-style) · **Device:** Redmi Note 14 (1080×2400) · **Stack:** Python + ADB + OpenCV

## Legend
- ✅ Done
- 🔄 In Progress
- ⬜ Not Started
- ❌ Blocked

---

## Game Mechanics (observed from screenshots)

- Cards are stacked in **haphazard overlapping piles** — NOT a fixed grid (like Mahjong Titans)
- Number of cards per pile varies; piles grow and shrink as cards are removed
- **Only the top card of each pile** is playable (face-up, fully visible rank)
- Cards under another card are face-up but blocked (rank visible, not tappable)
- Bottom row: **Stock pile** (blue face-down deck) + **Waste pile** (current face-up card) + **Undo button**
- **WILD card** exists (bottom-right) — can be played on anything
- **Streak Bonus** bar in top-right — consecutive chain rewards
- Two card **color families**: red suits (♥♦) and blue/dark suits (♠♣)
- Rank displayed both top-left (small) and center (large) — large rank is the template target

## Template Strategy (observed from card crops)
- Templates show **full card face** at consistent size
- Cards in screenshots appear **slightly larger** than templates — will need scale handling or resize
- Rank label is large and centered — good for template matching on the large rank glyph
- Suits vary per card but rank is what matters for game logic
- Likely need **rank-only ROI** (crop top-left corner) for matching, ignoring the suit and center art

---

## Phase 1 — ADB Setup & Screen Capture
> Goal: Connect to phone, grab a screenshot from Python, confirm resolution.

| # | Step | Status | Notes |
|---|------|--------|-------|
| 1.1 | Enable Developer Options on Redmi Note 14 | ✅ | |
| 1.2 | Enable USB Debugging | ✅ | |
| 1.3 | Install ADB platform-tools on Windows | ✅ | |
| 1.4 | Plug in phone via USB, authorize RSA fingerprint | ✅ | Device serial: `uknzs47tv8bugekf` |
| 1.5 | Install Python dependencies | ✅ | Venv at `.venv/`, all packages installed |
| 1.6 | Write `adb_controller.py` | ✅ | connect + screencap + tap + save |
| 1.7 | Run live screencap test, confirm resolution | ✅ | **1080×2400 px confirmed** ✓ |

---

## Phase 2 — Card Detection & Classification
> Goal: Detect ALL cards (face-up and face-down) and classify face-up cards by rank.

### 2A — Card Segmentation (find all card regions)
| # | Step | Status | Notes |
|---|------|--------|-------|
| 2A.1 | HSV color segmentation — separate blue backs from white faces | ✅ | Calibrated HSV ranges in `config.py` |
| 2A.2 | Contour detection — find card boundaries from both masks | ✅ | `cv2.findContours` + `cv2.minAreaRect` |
| 2A.3 | Filter contours by area — reject noise, keep card-sized blobs | ✅ | Area thresholds (12k to 45k px²) |
| 2A.4 | Classify each contour as FACE_UP or FACE_DOWN | ✅ | HSV segmentation for backs, template matching for faces |
| 2A.5 | Test segmentation on all 5 static screenshots | ✅ | Verified across all test images |

### 2B — Face-Up Rank Recognition
| # | Step | Status | Notes |
|---|------|--------|-------|
| 2B.1 | Templates already in `vision/templates/` | ✅ | A–K, BACK, UNDO, WILD |
| 2B.2 | Measure template vs in-game size, determine scale factor | ✅ | 1:1 scale confirmed in landscape |
| 2B.3 | Multi-angle template matching per rank | ✅ | Pre-rotated templates (0°, ±12°, ±25°) |
| 2B.4 | Multi-scale matching fallback | ✅ | Standard scale works with high confidence |
| 2B.5 | NMS to deduplicate overlapping detections | ✅ | IoU 0.35 threshold in `detector.py` |
| 2B.6 | Test rank recognition on all 5 screenshots | ✅ | 100% accuracy (29/29 face-up cards detected) |

### 2C — Waste/Stock/UI Detection
| # | Step | Status | Notes |
|---|------|--------|-------|
| 2C.1 | Detect waste pile card (bottom-center, fixed ROI) | ✅ | Verified (5/5 accurate with 0.96-1.00 conf) |
| 2C.2 | Detect stock pile presence (is deck empty?) | ✅ | Blue presence ratio check at `STOCK_CENTER` |
| 2C.3 | Detect WILD card availability | ✅ | Template match with user's cropped WILD template |
| 2C.4 | Test UI detection on screenshots | ✅ | Waste, stock, undo, wild verified on all 5 images |

---

## Phase 3 — Board State & Dependency Graph
> Goal: Build a structured board state with a DAG representing which cards block which.

| # | Step | Status | Notes |
|---|------|--------|-------|
| 3.1 | Write `board/state.py` — Card, BoardState dataclasses | ✅ | Card, BoardState dataclasses with DAG tracking |
| 3.2 | Build polygon representations for each detected card | ✅ | `cv2.boxPoints` from rotated rectangles |
| 3.3 | Compute pairwise polygon intersections → overlap graph | ✅ | `cv2.rotatedRectangleIntersection` (exact & fast) |
| 3.4 | Resolve Z-order / occlusion to determine blocking | ✅ | Face-up on top of face-down; lower-y on top of higher-y |
| 3.5 | Determine playable cards (top of stack = not covered by any other card) | ✅ | `is_face_up` and `len(blocked_by) == 0` |
| 3.6 | Write `board/parser.py` — screenshot → BoardState pipeline | ✅ | Vision detections → Card objects → DAG → BoardState |
| 3.7 | Test parser on all 5 static screenshots | ✅ | Verified across all test images and visually annotated |

---

## Phase 4 — Decision Engine
> Goal: Given a BoardState, pick the best legal move.

| # | Step | Status | Notes |
|---|------|--------|-------|
| 4.1 | Implement legal move generator | ✅ | Playable cards ±1 rank from waste top (A↔K wrap) |
| 4.2 | Implement restricted WILD card handling | ✅ | If WILD is in the center (stack/waste) -> play undoubtedly! If WILD is in the right bottom corner -> apply strict rules (only when stock is empty AND 1 card left or 100% chain clear). |
| 4.3 | Implement chain/streak scorer & lookahead | ✅ | Lookahead simulation + unblocking heuristics (bonus for mystery cards) |
| 4.4 | Implement stock draw fallback | ✅ | Falls back to `STOCK_CENTER` when no tableau moves exist |
| 4.5 | Write `engine/solver.py` | ✅ | Clean Solver and Move data structures |
| 4.6 | Test solver on known board states | ✅ | Verified on all 12 screenshots + synthetic edge cases |

---

## Phase 5 — Tap Automation
> Goal: Send tap events to the phone via ADB.

| # | Step | Status | Notes |
|---|------|--------|-------|
| 5.1 | Add `tap(x, y)` to `adb_controller.py` | ✅ | `adb shell input tap` with coordinate passing |
| 5.2 | Add randomized delay (jitter) | ✅ | Configurable min/max delay to mimic human touch |
| 5.3 | Test tap on known coordinates | ✅ | Interactive confirmation mode in `live_step.py` |

---

## Phase 6 — Game Loop
> Goal: Tie everything together into a working bot.

| # | Step | Status | Notes |
|---|------|--------|-------|
| 6.1 | Write `main.py` — capture → parse → decide → tap loop | ⬜ | |
| 6.2 | Add game-over / win detection | ⬜ | Detect end screen (empty board or result overlay) |
| 6.3 | Add stuck detection | ⬜ | No moves + empty stock → game over |
| 6.4 | End-to-end test: let bot play one full game | ⬜ | Record outcome |

---

## Open Questions / Blockers
- [x] How exactly does pile occlusion work? → Face-up cards sit ON TOP of face-down; contour completeness resolves same-type overlap
- [x] Is the WILD card always in the bottom-right or does it move? → Yes, always bottom-right (confirmed across all 5 screenshots)
- [ ] Does the game have idle timeout or screen lock during play?
- [x] Are card templates the right scale vs in-game cards? → Templates ~136×210, in-game ~195×295, scale factor ~1.42×
- [ ] Are there any animated transitions that might confuse screencap timing?
- [ ] Screenshots are in **landscape** (2400×1080) — need to confirm ADB screencap orientation vs PIL orientation
- [ ] Some face-down cards are **rotated/angled** — `minAreaRect` handles this, but need to verify detection
- [ ] Need to add `shapely` to requirements.txt for polygon intersection

---

*Last updated: Phase 2 starting — plan revised with HSV segmentation + DAG approach from suggestions*
