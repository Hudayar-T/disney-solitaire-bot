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
| **Phase 6** | Game Loop & Live Play | ✅ Done | Autonomous loop in `main.py`, win/stuck detection, live testing |
| **Phase 7** | Menu & Level Progression | ✅ Done | Continuous multi-level play, bonus collection, deal guard |
| **Phase 8** | Performance Optimization | ✅ Done | Multi-threaded template matching, waste-angle filtering, fast decoding |

---

## Active & Upcoming Tasks (Phase 8 & Beyond)

### Phase 8 — Performance Optimization
- [x] **8.1 Multi-Threaded Face-Up Template Matching:** Parallelized `cv2.matchTemplate` in `CardDetector.detect_faceup()` using `ThreadPoolExecutor` (8 workers). Tableau recognition dropped from ~3,040ms to ~810ms at 100% full resolution.
- [x] **8.2 Waste Pile Matching Restriction:** Restricted `detect_waste()` to upright templates (`0°`), dropping waste detection from ~190ms to ~15ms.
- [x] **8.3 Fast Memory Frame Decoding:** Streamlined image decoding using direct `cv2.imdecode` from byte buffer in `adb_controller.py`, bypassing PIL intermediate conversions (~50ms saved per frame).
- [x] **8.4 Benchmarking & Regression Verification:** Verified detection accuracy across all screenshots in `tests/test_detector.py`, `tests/test_solver.py`, and `tests/test_menu_navigation.py` (all tests passing).

---

## Open Questions & Considerations
- [ ] Animated event popups: Check if mid-game event/bonus popups occur on certain levels that need dismiss taps.

---
*Detailed mechanics and architecture reference: see [GEMINI.md](GEMINI.md)*
