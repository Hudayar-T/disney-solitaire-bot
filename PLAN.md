# 🃏 Disney Solitaire Bot — Master Plan

> **Game:** Disney Solitaire (TriPeaks-style) · **Device:** Redmi Note 14 (2400×1080 landscape) · **Stack:** Python + ADB + OpenCV

## Status Legend
- ✅ Done
- 🔄 In Progress
- ⬜ Not Started

---

## Milestone Progress

| Phase | Description | Status | Key Deliverables |
|---|---|---|---|
| **Phase 1** | ADB Setup & Screencap | ✅ Done | `adb_controller.py` screencap & tap, 2400×1080 landscape confirmed |
| **Phase 2** | Card Detection & UI | ✅ Done | Multi-angle templates (±48°), HSV masks, yellow buy-trap & WILD guard |
| **Phase 3** | Board State & DAG | ✅ Done | Overlap detection (`rotatedRectangleIntersection`), Z-order occlusion rules |
| **Phase 4** | Decision Engine | ✅ Done | Lookahead chain search, mystery card unblocking bonus, strict WILD rules |
| **Phase 5** | Tap Automation | ✅ Done | Anti-bot Gaussian spatial jitter + randomized human delays |
| **Phase 6** | Game Loop & Live Play | 🔄 In Progress | Autonomous loop in `main.py`, win/stuck detection, live testing |
| **Phase 7** | Menu & Level Progression | ✅ Done | Continuous multi-level play, bonus collection, deal guard |

---

## Active & Upcoming Tasks (Phase 6 & Beyond)

### Phase 6 — Game Loop & Live Testing
- [x] **6.1 Autonomous Game Loop:** `main.py` pipeline (capture → parse → solve → tap → settle) with `--max-steps` and `--save-screens`.
- [x] **6.2 Basic Win & Stuck Handling:** Board cleared win check (`len(state.tableau) == 0`) and patience retry streak (`no_move_streak >= NO_MOVE_PATIENCE`).
- [ ] **6.3 End-to-End Live Play Test:** Let the bot play a full live level autonomously on device; verify animation settling delays and reliability.

### Phase 7 — Menu Navigation & Level Progression (`handle_menu_navigation/`)
> Goal: Automate transitions between levels, handle bonus rewards, and recover from deal animations.
- [x] **7.1 Button ROIs & Coordinates (`config.py`):**
  - Define ROIs, HSV ranges, and tap coordinates:
    - Purple hourly bonus button: `MENU_COLLECT_ROI`, center `(1240, 950)`
    - Green level play button: `MENU_PLAY_ROI`, center `(2250, 930)`
    - Pre-level modal green PLAY button: `MODAL_PLAY_ROI`, center `(1204, 814)`
    - Neutral dismiss tap: `POPUP_DISMISS_COORD` `(1200, 930)`
- [x] **7.2 Menu State Detector (`vision/menu_detector.py`):**
  - Implemented screen state classifier for:
    - `MAIN_MENU`: Detects lobby (flags purple collect vs green play).
    - `PRE_LEVEL_MODAL`: Detects level confirmation popup with green PLAY button.
    - `POST_WIN`: Detects "MEGA WIN!" / "TAP ANYWHERE TO COLLECT" overlay.
    - `RANDOM_REWARD`: Detects "YOUR REWARDS!" / "TAP TO COLLECT" popup.
    - `CARDS_DEALING`: Detects deal transition (cards flying, 0 playable, waste unsettled).
    - `IN_GAME`: Active tableau play.
- [x] **7.3 Menu Navigation Controller (`navigation/menu_handler.py`):**
  - State machine dispatch:
    - If `POST_WIN` or `RANDOM_REWARD` → tap neutral area to dismiss.
    - If `MAIN_MENU` with hourly bonus → tap purple collect, wait for claim animation.
    - If `MAIN_MENU` ready → tap green level button to open modal.
    - If `PRE_LEVEL_MODAL` → tap green PLAY button to launch level.
    - If `CARDS_DEALING` → sleep 2.0s without tapping, retry capture.
- [x] **7.4 Unit Tests for Navigation (`tests/test_menu_navigation.py`):**
  - Tested detector and navigation actions across all reference screenshots (100% pass).
- [x] **7.5 Main Loop Multi-Level Integration (`main.py`):**
  - Unified game loop and menu handler to seamlessly loop from level win → rewards → menu → next level (with `--single-level` option).

---

## Open Questions & Considerations
- [ ] Screen timeout: Ensure phone stays awake during prolonged runs (via ADB or phone developer settings).
- [ ] Animated event popups: Check if mid-game event/bonus popups occur on certain levels that need dismiss taps.

---
*Detailed mechanics and architecture reference: see [GEMINI.md](GEMINI.md)*
