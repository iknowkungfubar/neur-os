# NeurOS

Energy-aware task management for neurodivergent brains. Spoon theory meets
local-first software.

## What It Is

NeurOS replaces the traditional "push harder" productivity stack with something
that respects energy variability. Instead of due dates and streaks, it asks
"What can you do right now?" and adapts to the answer.

Works fully offline. Your data is yours — SQLCipher AES-256 at rest, no
telemetry, no accounts required.

## Architecture

```
neuros-mobile/     → React Native (Expo) app — Android APK, iOS soon
backend/           → Python FastAPI server — data + sync relay
frontend/          → Single-page web app — served by backend
shared/            → TypeScript domain types — shared by mobile + web
desktop/           → Tauri shell — wraps web app as desktop app
```

All 4 clients hit the same REST API. Nothing requires cloud infrastructure.

## What Works (end-to-end)

| Feature | Backend | Web | Mobile Android | Notes |
|---------|---------|-----|---------------|-------|
| Energy battery (% + traffic light) | ✅ | ✅ | ✅ | |
| Brain dump → tasks + notes | ✅ | ✅ | ✅ | LLM-parsed via LM Studio |
| Spoon envelope calculator | ✅ | ✅ | ✅ | Proactive pacing |
| Boom-bust detection | ✅ | ✅ | ✅ | Confidence-ranked |
| Dopamine menu (4 categories) | ✅ | ✅ | ✅ | configurable |
| Interoception check-in | ✅ | ✅ | ✅ | 7-body-signal log |
| Gentle focus timer | ✅ | ✅ | ✅ | count-up, pause/stop |
| Declarative language rewrite | ✅ | ✅ | ✅ | no coercive patterns |
| WCAG 3.0 Bronze | — | ✅ | native RN a11y | aria-labels + keyboard nav |
| Habits (grace period) | ✅ | ✅ | ✅ | |
| Weekly review | ✅ | ✅ | ✅ | |
| Voice brain dump | — | Web Speech API | Web Speech API | |
| Admin night mode | ✅ | — | — | WebSocket rooms |
| E2EE sync relay | ✅ | — | — | opaque blobs, no server access |
| Community templates | ✅ | ✅ | — | export/import |
| Offline cache | — | — | ✅ | SQLCipher encrypted |
| Energy patterns (weekly) | ✅ | ✅ | ✅ | |

## Quick Start

```bash
# Start the server (requires Python 3.11+)
cd backend
pip install -r requirements.txt
python main.py
# → http://localhost:7447

# Mobile (requires Expo CLI)
cd neur-os-mobile
npm install
npx expo start
# → Scan QR code with Expo Go, or build APK

# Desktop (requires Rust + Tauri CLI)
cd desktop
npm install
npx tauri dev
```

### Prerequisites

- **Server:** Python 3.11+, LM Studio (localhost:1234/v1) for LLM features
- **Mobile:** Node 20+, JDK 21+, Android SDK 36+ (for native build)
- **Desktop:** Rust toolchain, system webview

### Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `API_BASE` | `http://localhost:7447/api` | Server URL (mobile settings) |
| `LM_STUDIO_URL` | `http://localhost:1234/v1` | LLM endpoint |

## Configuration

Energy scales, drain rates, and dopamine menu defaults are in
`backend/main.py` tops. To customise your dopamine menu:

```python
# backend/main.py
DOPAMINE_MENU = {
    "high energy":  ["go outside for a walk", "work on a creative project"],
    "low energy":   ["watch a comfort show", "take a nap"],
    "sensory":      ["listen to brown noise", "pet the cat"],
    "connection":   ["text a friend", "body double with someone"],
}
```

## Testing

```bash
cd backend && python3 -m pytest -q
# → 56 passed
```

## Data Storage

| Layer | Technology | Encryption |
|-------|-----------|------------|
| Mobile local | SQLite via `@op-engineering/op-sqlite` | AES-256 (SQLCipher) |
| Server | SQLite (Python `sqlite3`) | No (optional sync only) |
| Sync relay | Opaque encrypted blobs | Server never reads plaintext |

No user accounts, no cloud sync required. The sync relay is optional — enable
it only if you want cross-device data.

## Spec

This repo is built against `SPEC_v1.0.md`. Each feature has explicit
acceptance criteria with a passing test.

## License

MIT — see LICENSE
