# NeurOS Roadmap

## Vision
A local-first, neuro-affirming cognitive prosthetic that helps ND individuals manage energy, execute tasks, and regulate their nervous system — without gamification, streaks, or coercion.

## Current: v0.4 — Shipped

Packaged, installable, wired to LM Studio.

**Features:**
- [x] Spoon theory energy tracking + daily check-in
- [x] Task board with energy tags (low/medium/high)
- [x] Task micro-chunking (automatic subtask distribution)
- [x] Crisis mode (sensory blackout, demand eradication)
- [x] Declarative language translation (LM Studio — qwythos-9b)
- [x] 5-tab UI (Ready / Focus / All / Habits / Review)
- [x] Focus timer (5/15/25/45/60 min, pause/resume/stop)
- [x] "Just Start" 2-minute timer
- [x] Recurring tasks (daily/weekday/weekly/monthly)
- [x] Habit tracking with streaks
- [x] Traffic-light pacing mode (green/amber/red)
- [x] Body doubling mode
- [x] Wind-down evening reflection
- [x] Weekly review dashboard (energy trends, bar charts, insights)
- [x] Soundscapes (Web Audio API — brown noise, rain, breathing tone)
- [x] Desktop notifications (non-coercive, declarative)
- [x] Data export (JSON + Markdown)
- [x] Data import/restore endpoint
- [x] Auto-backup
- [x] Tauri v2 desktop shell (native app, 9.1MB binary)
- [x] Systemd user service (auto-start on boot)
- [x] .desktop entry (launches Tauri binary)
- [x] Onboarding first-run wizard
- [x] Install script (one-command, deploys web + desktop)

## Planned

**Short-term:**
- Local encryption at rest (XChaCha20-Poly1305)
- Backup/restore CLI scripts
- P2P sync between devices (SyftBox)

**Stretch:**
- Packaged releases (AppImage, .deb)
- Calendar integration (ICS import)
- Full documentation and landing page

---

## Gaps (Verified Research, Not Yet Built)

Features from verified research not yet implemented. Organized by dependency readiness.

### Ready Now (no infra required)

| # | Feature | Depends On | Effort | Source |
|---|---------|-----------|--------|--------|
| A | **Passive hourly logger** — periodic "what are you doing?" prompts, auto-logs to SQLite with spoon context. SheepCat-style. | Nothing new | ~30 min | SheepCat project, verified |
| B | **Auto crisis detection** — track form errors, timer aborts, erratic navigation. Compute Cognitive Load score on sliding window. Auto-trigger crisis mode when threshold crossed. | Frontend event tracking middleware | ~2 hr | Heuristic monitoring pattern, verified |
| E | **Narrative onboarding** — conversational setup over days, strengths-based profiling (UDL), collaborative discovery stance. | LLM already wired | ~3 hr | UDL framework, verified |

### Blocked by Dependencies

| # | Feature | Depends On | Effort | Source |
|---|---------|-----------|--------|--------|
| C | **XChaCha20-Poly1305 encryption at rest** | SQLite encryption library (sqlcipher or libsodium binding) | ~4 hr | RFC 8439, verified |
| D | **LanceDB vector store for RAG** | LanceDB server or embedded | ~4 hr | lancedb.github.io, verified |

### Hardware-Gated

| # | Feature | Depends On | Effort | Source |
|---|---------|-----------|--------|--------|
| F | **Strengths-based profiling** (UDL asset identification) | Narrative onboarding (E) first | ~4 hr | UDL framework |
| G | **Micro-moment RLHF** — implicit feedback from dismiss/closing patterns | Passive logger (A) data accumulated | ~1 week | Cybernetic feedback loops, verified |
| H | **Bio-sensor / HRV pipeline** — NeuroKit2, PPG wearable → stress-aware pacing | Wearable hardware, NeuroKit2 | ~2 week | NeuroKit2, verified |
| I | **OS-level transparent overlay** — Tauri float window, keyboard-triggered | Tauri v2 API capabilities | ~1 week | Tauri docs |
| J | **Dynamic quantization scaling** — auto-downshift model at low battery | System thermal/battery monitoring | ~1 week | Edge computing research |
| K | **LoRA fine-tuning on user data** — personalized model tone | Curated dataset, GPU hours | ~2 week | LoRA paper, verified (note: "T-LoRA" name is fabricated, real tech is Dynamic LoRA/CoLoR) |
| L | **P2P encrypted sync** — multi-device without cloud | SyftBox or CRDT library | ~2 week | SyftBox, verified |

### Intentionally Deferred (YAGNI until evidence shows need)

- Bio-sensor HRV (no wearable hardware owned)
- OS transparent overlay (replaces desktop, different UX paradigm)
- LoRA fine-tuning (requires labeled data + GPU)
- P2P sync (single-user app)
- Micro-moment RLHF (requires weeks of usage data)
