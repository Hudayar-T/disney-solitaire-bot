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

---

## Active & Upcoming Tasks (Phase 6 & Beyond)

### Phase 6 — Game Loop & Live Testing
- [x] **6.1 Autonomous Game Loop:** `main.py` pipeline (capture → parse → solve → tap → settle) with `--max-steps` and `--save-screens`.
- [x] **6.2 Basic Win & Stuck Handling:** Board cleared win check (`len(state.tableau) == 0`) and patience retry streak (`no_move_streak >= NO_MOVE_PATIENCE`).
- [ ] **6.3 End-Screen & Result Dialog Detection:** Detect Victory / Defeat popups and result overlays to cleanly finalize a level.
- [ ] **6.4 End-to-End Live Play Test:** Let the bot play full live levels autonomously on device; verify animation settling delays and reliability.

### Phase 7 — Post-MVP Enhancements (Optional)
- [ ] **7.1 Auto-Progression:** Detect and tap "Next Level" / "Play Again" buttons between rounds.
- [ ] **7.2 Speed Tuning:** Optimize template matching execution time and refine `SCREENCAP_INTERVAL` for snappier play.

---

## Open Questions & Considerations
- [ ] Screen timeout: Ensure phone stays awake during prolonged runs (via ADB or phone developer settings).
- [ ] Animated event popups: Check if mid-game event/bonus popups occur on certain levels that need dismiss taps.

---
*Detailed mechanics and architecture reference: see [GEMINI.md](GEMINI.md)*
