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
| **Phase 9** | Economy & Cost Management | ✅ Done | Balance & cost reader, insufficient funds guard (closes modal & 5m wait) |

---

## Active & Upcoming Tasks (Phase 9 & Beyond)

### Phase 9

---

## Open Questions & Considerations
- [ ] Animated event popups: Check if mid-game event/bonus popups occur on certain levels that need dismiss taps.

---
*Detailed mechanics and architecture reference: see [GEMINI.md](GEMINI.md)*
