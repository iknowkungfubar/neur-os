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

## Future

Not yet built. Organized by dependency readiness.

### Ready Now (no infra required)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| A | **Passive hourly logger** — periodic "what are you doing?" prompts, auto-logs with spoon context | ~30 min | |
| B | **Auto crisis detection** — track form errors, timer aborts, erratic nav, auto-trigger crisis | ~2 hr | |
| C | **Narrative onboarding** — conversational setup over days, strengths-based profiling | ~3 hr | LLM already wired |
| D | **OS home screen widgets** (Android/iOS) | varies | needs native build pipeline |
| E | **CI/CD via Expo EAS** | ~1 hr | needs Expo account |
| F | **iOS build** | varies | needs macOS |

### Could Use the Encrypted Local Storage We Now Have

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| G | **XChaCha20-Poly1305 encryption** as an alternative cipher layer | ~2 hr | SQLCipher is in already; this would be an option |
| H | **LanceDB vector store for semantic search** | ~4 hr | LIKE-search covers current scale |

### Hardware-Gated / Downstream

| # | Feature | Depends On | Effort | Notes |
|---|---------|-----------|--------|-------|
| I | **Bio-sensor / HRV pipeline** (NeuroKit2 → stress-aware pacing) | Wearable hardware | ~2 wk | |
| J | **OS-level transparent overlay** (Tauri float window) | Tauri v2 API | ~1 wk | |
| K | **Dynamic quantization scaling** (auto-downshift model at low battery) | Battery monitoring | ~1 wk | |
| L | **LoRA fine-tuning on user data** | Curated dataset, GPU hours | ~2 wk | |
| M | **P2P encrypted sync** (multi-device without relay) | CRDT library | ~2 wk | E2EE relay exists; P2P is the trustless variant |
| N | **Micro-moment RLHF** from dismiss/closing patterns | Passive logger (A) data | ~1 wk | |
| O | **Strengths-based profiling** (UDL asset identification) | Narrative onboarding (C) | ~4 hr | |
