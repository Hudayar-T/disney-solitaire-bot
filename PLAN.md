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
| 2A.1 | HSV color segmentation — separate blue backs from white faces | ⬜ | `cv2.inRange` on HSV; blue backs have distinctive Mickey watermark |
| 2A.2 | Contour detection — find card boundaries from both masks | ⬜ | `cv2.findContours` + `cv2.minAreaRect` for rotated cards |
| 2A.3 | Filter contours by area — reject noise, keep card-sized blobs | ⬜ | Min/max area thresholds based on known card size (~195×295 px) |
| 2A.4 | Classify each contour as FACE_UP or FACE_DOWN | ⬜ | Based on which color mask it came from |
| 2A.5 | Test segmentation on all 5 static screenshots | ⬜ | Draw detected card outlines, visually verify |

### 2B — Face-Up Rank Recognition
| # | Step | Status | Notes |
|---|------|--------|-------|
| 2B.1 | Templates already in `vision/templates/` | ✅ | A–K + BACK, ~136×210 px each |
| 2B.2 | Measure template vs in-game size, determine scale factor | ⬜ | From screenshots: in-game ~195×295 → scale ~1.42× |
| 2B.3 | For each FACE_UP contour: crop → template match per rank | ⬜ | Match within the card's bounding box only (not full screen) |
| 2B.4 | Multi-scale matching fallback if single scale has weak hits | ⬜ | Range 1.25–1.60 in steps of 0.05 |
| 2B.5 | NMS to deduplicate overlapping detections | ✅ | Already implemented in `detector.py` |
| 2B.6 | Test rank recognition on all 5 screenshots | ⬜ | Print detected rank + confidence per card, compare with visual |

### 2C — Waste/Stock/UI Detection
| # | Step | Status | Notes |
|---|------|--------|-------|
| 2C.1 | Detect waste pile card (bottom-center, fixed ROI) | ⬜ | Template match in small region around `config.WASTE_CENTER` |
| 2C.2 | Detect stock pile presence (is deck empty?) | ⬜ | Blue card presence check in `config.STOCK_CENTER` region |
| 2C.3 | Detect WILD card availability | ⬜ | Check yellow WILD icon in bottom-right region |
| 2C.4 | Test UI detection on screenshots | ⬜ | Verify waste rank, stock empty/not, WILD available |

---

## Phase 3 — Board State & Dependency Graph
> Goal: Build a structured board state with a DAG representing which cards block which.

| # | Step | Status | Notes |
|---|------|--------|-------|
| 3.1 | Write `board/state.py` — Card, BoardState dataclasses | ⬜ | Card: rank, position, bbox polygon, is_face_up, is_playable |
| 3.2 | Build polygon representations for each detected card | ⬜ | Shapely `Polygon` from `cv2.minAreaRect` corners |
| 3.3 | Compute pairwise polygon intersections → overlap graph | ⬜ | `poly_A.intersects(poly_B)` with area threshold |
| 3.4 | Resolve Z-order / occlusion to determine blocking | ⬜ | Face-up on top of face-down; contour completeness for same-type |
| 3.5 | Determine playable cards (top of stack = not covered by any other card) | ⬜ | Leaf nodes in the DAG = playable |
| 3.6 | Write `board/parser.py` — screenshot → BoardState pipeline | ⬜ | Combines Phase 2 detection + Phase 3 DAG construction |
| 3.7 | Test parser on all 5 static screenshots | ⬜ | Print BoardState, verify playable cards match visual |

---

## Phase 4 — Decision Engine
> Goal: Given a BoardState, pick the best legal move.

| # | Step | Status | Notes |
|---|------|--------|-------|
| 4.1 | Implement legal move generator | ⬜ | Top cards ±1 rank from waste top (A↔K wrap) |
| 4.2 | Implement WILD card handling | ⬜ | WILD can play on anything — use it strategically |
| 4.3 | Implement chain/streak scorer | ⬜ | Prefer moves that extend chains, unblock more cards |
| 4.4 | Implement stock draw fallback | ⬜ | Draw when no tableau move available |
| 4.5 | Write `engine/solver.py` | ⬜ | |
| 4.6 | Test solver on known board states | ⬜ | Unit tests with hand-crafted BoardState objects |

---

## Phase 5 — Tap Automation
> Goal: Send tap events to the phone via ADB.

| # | Step | Status | Notes |
|---|------|--------|-------|
| 5.1 | Add `tap(x, y)` to `adb_controller.py` | ⬜ | `adb shell input tap` |
| 5.2 | Add randomized delay (jitter) | ⬜ | Mimic human rhythm, avoid anti-bot detection |
| 5.3 | Test tap on known coordinates | ⬜ | Tap waste pile, stock pile — verify correct response |

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
