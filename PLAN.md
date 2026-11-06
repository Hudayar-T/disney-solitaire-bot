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

## Phase 2 — Card Vision
> Goal: Given a screenshot, detect and classify every visible card by rank.

| # | Step | Status | Notes |
|---|------|--------|-------|
| 2.1 | Move card templates to `vision/templates/` | ⬜ | Rename/organise from `img/cards/` |
| 2.2 | Inspect template sizes vs screenshot card sizes | ⬜ | Check if scaling is needed |
| 2.3 | Write `vision/detector.py` — template matching per rank | ⬜ | OpenCV `matchTemplate`, multi-scale if needed |
| 2.4 | Detect face-down (blue back) cards separately | ⬜ | Need a card-back template |
| 2.5 | Test detector on static screenshots | ⬜ | Print all matches with positions + ranks |
| 2.6 | Tune confidence threshold | ⬜ | Minimize false positives/negatives |

---

## Phase 3 — Board State Parser
> Goal: Turn detected cards into a structured `BoardState` (piles, top cards, positions).

| # | Step | Status | Notes |
|---|------|--------|-------|
| 3.1 | Understand pile topology from screenshots | ⬜ | Cards overlap haphazardly — need occlusion logic |
| 3.2 | Write `board/state.py` — Card, Pile, BoardState dataclasses | ⬜ | Card has: rank, suit(optional), (x,y), is_playable |
| 3.3 | Write `board/parser.py` — detections → BoardState | ⬜ | Use y-position + overlap to determine top card per pile |
| 3.4 | Identify waste pile card position | ⬜ | Fixed position bottom-center (confirmed in screenshots) |
| 3.5 | Identify stock pile position | ⬜ | Fixed position bottom-left |
| 3.6 | Test parser on static screenshots | ⬜ | Print parsed state, verify which cards are playable |

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
- [ ] How exactly does pile occlusion work? Which card is "on top" when they overlap?
- [ ] Is the WILD card always in the bottom-right or does it move?
- [ ] Does the game have idle timeout or screen lock during play?
- [ ] Are card templates the right scale vs in-game cards? (need to measure)
- [ ] Are there any animated transitions that might confuse screencap timing?

---

*Last updated: Phase 1 ✅ COMPLETE — 1080×2400 resolution confirmed, ADB live screencap working*
