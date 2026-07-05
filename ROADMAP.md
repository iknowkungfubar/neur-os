# NeurOS Roadmap

## Vision
A local-first, neuro-affirming cognitive prosthetic that helps ND individuals
manage energy, execute tasks, and regulate their nervous system — without
gamification, streaks, or coercion.

## Current: v1.0 — Complete (2026-07-05)

All 5 phases built, tested (56 passing), and running on Android emulator.

**Phase 1 — Foundation:**
- [x] Spoon energy tracking + brain dump
- [x] Hexagonal architecture (pure domain layer)
- [x] WCAG 3.0 Bronze (aria-labels, keyboard nav, focus indicators)
- [x] No coercive patterns (no streaks, badges, countdown timers)
- [x] Declarative language rewrite

**Phase 2 — Pacing:**
- [x] Energy envelope calculator (recommended max/min)
- [x] Boom-bust detection with confidence scoring
- [x] Proactive pacing suggestions in UI
- [x] Dopamine menu (4 categories, 12 defaults)
- [x] Interoception check-in (7 body signals)

**Phase 3 — Mobile:**
- [x] React Native (Expo) app — 4 tabs
- [x] Shared TypeScript domain (`shared/domain.ts`)
- [x] SQLCipher AES-256 encrypted local cache
- [x] Android APK builds (136MB debug)
- [x] Configurable API base URL
- [x] Offline brain dump caching

**Phase 4 — Intelligence:**
- [x] Energy patterns dashboard (peak hour, low point, best day)
- [x] LLM parsing via LM Studio (configurable endpoint)
- [x] Declarative rewrite pipeline (flag + rewrite + fallback)

**Phase 5 — Community:**
- [x] E2EE sync relay (opaque blob storage)
- [x] Admin night mode (WebSocket rooms, presence, timer)
- [x] Community template export/import
- [x] Cross-device sync via relay

### Tests
```bash
cd backend && python3 -m pytest -q
# → 56 passed
```

## Next

- **OS home screen widgets** (Android/iOS native — needs store build)
- **CI/CD via Expo EAS** (needs Expo account)
- **Local LLM on-device** (MLC-LLM cross-compile for Android)
- **iOS build** (tested via macOS only)
