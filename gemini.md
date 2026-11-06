# Disney Solitaire Bot — Agent Context

## Project Goal
Automate playing **Disney Solitaire** (TriPeaks-style variant) on an Android phone via ADB + Python.
The bot captures the screen, detects cards via template matching, parses board state,
decides the best move, and taps the screen — all in a loop.

## Device
- **Phone:** Redmi Note 14
- **Resolution:** 1080 × 2400 px (FHD+, 20:9) — verify on first screencap
- **Connection:** USB (ADB)
- **OS:** Windows (dev machine)

## Game Rules — Disney Solitaire (NOT standard TriPeaks)
- Cards are stacked in **haphazard overlapping piles** (like Mahjong Titans, NOT a fixed grid)
- Number of cards and pile count varies per level
- Only the **top card of each pile** is playable (fully uncovered)
- Cards under another card are visible but not tappable
- A tableau card is playable if its rank is ±1 from the waste top (wraps: A↔K)
- **Suit does NOT matter** for playability
- **WILD card** exists (bottom-right UI) — plays on anything, use strategically
- **Streak Bonus** mechanic — consecutive chains increase score multiplier
- Goal: clear all tableau cards

## UI Layout (confirmed from screenshots)
- Tableau: upper 70% of screen, haphazard overlapping card piles
- Stock pile: bottom-left (blue face-down deck)
- Waste pile: bottom-center (current face-up card)
- Undo button: bottom-center-right (green circular arrow)
- WILD card: bottom-right corner
- Streak bonus bar: top-right

## Tech Stack
| Concern         | Library/Tool         | Notes                              |
|----------------|----------------------|------------------------------------|
| ADB control    | `adbutils`           | Python ADB client                  |
| Screencap      | `adb exec-out screencap -p` via adbutils | PNG piped to Python |
| Image I/O      | `Pillow`             | PIL Image ↔ numpy conversion       |
| Vision         | `opencv-python`      | Template matching for card detect  |
| Logging        | `loguru`             | Structured debug logging           |
| Config         | `config.py`          | ROI coords, thresholds, constants  |
| Decision       | Custom greedy + BFS  | Chain search over ±1 rank sequences|

## Project Structure
```
disney-solitaire-bot/
├── gemini.md                  ← this file (agent context)
├── PLAN.md                    ← build plan with step tracking
├── config.py                  ← screen resolution, ROI coords, thresholds
├── adb_controller.py          ← ADB connect, screencap, tap
├── vision/
│   ├── capture.py             ← raw screenshot → PIL/numpy
│   ├── detector.py            ← template matching, card detection
│   └── templates/             ← card rank images (A, 2-10, J, Q, K + card back)
├── board/
│   ├── state.py               ← BoardState, Card, Pile dataclasses
│   └── parser.py              ← screenshot → BoardState
├── engine/
│   └── solver.py              ← move decision / chain search
├── main.py                    ← game loop orchestration
├── tests/
│   ├── screenshots/           ← static test screenshots
│   └── test_vision.py         ← unit tests with static screenshots
└── requirements.txt
```

## Coordinate System
- Origin (0,0) is top-left of screen
- All ROI rects stored as (x, y, w, h)
- All tap targets stored as (x, y) center of card
- Do NOT hardcode coords — always derive from config.py constants

## Template Notes
- Card templates are in `vision/templates/` (moved from `img/cards/`)
- Templates show full card face — rank glyph is large and centered
- Cards in-game may appear at different scale than templates — handle with resize or multi-scale matching
- Two color families: red suits (♥♦) and dark suits (♠♣) — only rank matters for logic

## Agent Notes
- Always confirm with user before creating new files or moving to next phase
- Update PLAN.md after completing each step (mark ✅)
- Store all test screenshots in tests/screenshots/
- Do NOT hardcode (x,y) coords — always derive from config.py constants
- Ask before making assumptions about layout, scale, or card detection approach
