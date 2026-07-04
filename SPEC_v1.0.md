# NeurOS v1.0 SPEC

## What Changes from v0.4.1

| Remove | Reason | Replace With |
|--------|--------|-------------|
| Fixed spoon count (integer) | Misses daily variability | Energy battery 0-100% |
| Streaks | Shame cycle for PDA/ADHD | Free Days, grace periods |
| Reward badges | Demands in disguise | Gentle completion celebration (no streaks) |
| Default-on notifications | Interruptions = extra executive drain | Opt-in only, batchable |
| Imperative UI text ("Clean kitchen") | Reads as demand → avoidance | Declarative ("Kitchen could use attention") |
| Multi-step onboarding | Complex setup → abandonment | Brain dump field (open → type → done) |
| Timer countdown (anxiety-inducing) | Countdown increases pressure | Count-up timer (gentle, pause without penalty) |

## Architecture Constraints

- **Hexagonal (Ports & Adapters)**: domain/ layer has zero framework imports. adapters/ implements repository interfaces.
- **Local-first**: SQLite is source of truth. Server is optional sync target.
- **Encryption at rest**: SQLCipher AES-256 for all user data.
- **Mobile shared domain**: TypeScript types + use cases in shared/ between RN and web.
- **AI integration via ports**: AI adapter interface, swapable (LM Studio, MLC-LLM, cloud).
- **4-tab max navigation**: ND research shows >4 tabs = overwhelm.

## Stack

| Layer | Choice |
|-------|--------|
| Mobile | React Native + Expo SDK 54 |
| Desktop | Tauri (existing) as thin client |
| State | Zustand (app) + Legend-State (persistence/sync) |
| Database | SQLite via expo-sqlite + SQLCipher |
| AI (desktop) | LM Studio via HTTP API (existing) |
| AI (mobile) | MLC-LLM or llama.cpp (GGUF) |
| CI/CD | GitHub Actions → Expo EAS |
| Accessibility target | WCAG 3.0 Bronze (target Gold) |

---

# Phase 1: Foundation

**Goal**: Replace all harmful patterns. Ship brain dump + energy battery.
**Sessions**: 1-2 (~3-5 days agentic)

### Deliverables

#### 1.1 Brain Dump
- Single textarea on app open: "What's on your mind?"
- Send to LM Studio → returns structured: tasks, notes, events
- Original raw text preserved, never hidden
- **AC**: dump "clean kitchen, call mom, why does my back hurt" → returns 2 tasks + 1 note. Raw text visible via expand.

#### 1.2 Energy Battery
- `EnergyBattery { percentage: 0-100, drainRate: 0-100, chargeRate: 0-100 }`
- Morning check-in: user sets % + optional pain/fatigue level
- Background drain ticks down even when idle (body is working)
- Tasks auto-deduct from battery based on spoon_cost → % mapping
- Traffic light: green (60-100), amber (20-59), red (0-19)
- **AC**: set 80% on check-in, complete 30% task → battery shows 50%

#### 1.3 Remove Coercive Features
- Delete streaks table and all streak logic
- Delete reward badges
- Change habits: remove streak column, add grace_period (Free Days)
- Change timer: count-up default, "stop" option always available without penalty
- **AC**: old `habits` table migration preserves data, drops streak column

#### 1.4 Declarative Language Rewrite
- UI text audit: every button label, placeholder, notification
- `"Clean the kitchen"` → `"Kitchen could use some attention"`
- `"You need to reply to emails"` → `"Emails are waiting when you're ready"`
- **AC**: no imperative verbs in UI text. "Begin", "Start", "Must", "Need", "Should" eliminated.

#### 1.5 Hexagonal Refactor
```
domain/
  entities/       # EnergyBattery, Task, BrainDump, ... pure TS
  repositories/   # TaskRepository (interface, no import)
  usecases/       # OrganizeBrainDump, UpdateEnergy, ...
application/
  viewmodels/     # MVVM bridges
infrastructure/
  adapters/       # SQLiteTaskRepository, AIStudioAdapter, ...
presentation/     # React components (thin, no logic)
shared/           # Types used by both mobile and desktop
```
- **AC**: `import { EnergyBattery } from 'domain/entities'` in a test file, no framework dependency.

#### 1.6 WCAG 3.0 Bronze
- Clear Language: no jargon, short sentences, active voice (declarative)
- Predictable Interaction: consistent navigation, undo available
- Error Prevention: confirm before destructive actions, save drafts
- **AC**: Lighthouse a11y audit passes at 90+. Keyboard-navigable.

---

# Phase 2: Pacing & Prevention

**Goal**: Energy-aware task suggestions. Proactive burnout prevention.
**Sessions**: 2 parallel with Phase 1 (~2-3 days)

### Deliverables

#### 2.1 Energy Envelope Calculator
- `EnergyEnvelopeCalculator.calculate(current_energy, tasks_today, historical_pattern)`
- Returns safe range: `{ recommended_max: 60%, recommended_min: 15%, current_usage: 30% }`
- Visual envelope bar: green zone, amber edge, red over-exertion
- **AC**: user at 40% energy with 80% of tasks remaining → envelope shows "over" with warning

#### 2.2 Boom-Bust Detection
- `BoomBustDetector.analyze(history: EnergyLog[]): { pattern: 'boom-bust' | 'stable' | 'declining', confidence: float }`
- Detects: 3+ days of high output followed by 2+ days of very low
- Triggers proactive suggestion: "You've been pushing hard. Tomorrow might feel rough. Want to schedule rest?"
- **AC**: inject pattern `[80, 90, 85, 20, 15, 10]` → detects boom-bust with confidence >0.7

#### 2.3 Proactive Pacing
- Dashboard widget: "Your energy envelope suggests stopping at 60% today. You're at 55%."
- "What's one thing that would feel good to do right now?" (not "what must you do?")
- Recharge reminders: "Your battery has been draining for 4 hours. A 10-minute reset might help."
- **AC**: at 75% drain without break for 3+ hours → shows recharge suggestion

#### 2.4 Gentle Timer (count-up)
- Default: count-up (0:00 → 25:00). Optional countdown in settings.
- Pause without penalty at any time.
- Body doubling mode: shows "X others are also focusing right now"
- **AC**: start timer, pause 5min, resume → elapsed shows correct time. Stop at any point, no "abandoned" status.

#### 2.5 Dopamine Menu
- Categories: Starters (2-min), Sides (with-task), Mains (30+ min recovery), Desserts (guilty pleasure)
- Pre-populated with ND-common items + user customization
- Accessible from task board: "Need a boost? Pick from your menu."
- **AC**: 4 categories visible, each with 2+ default items. User can add/customize.

#### 2.6 Interoception Check-In
- Periodic prompt (user-configurable, default-off): "What do you notice right now?"
- Signal options: hungry, thirsty, tired, achy, buzzing, numb, can't-tell
- Logs to energy log for pattern discovery
- **AC**: check-in records at least one signal. Can opt out permanently.

---

# Phase 3: Mobile

**Goal**: iOS + Android apps sharing domain with desktop.
**Sessions**: 3 (~3-5 days)

### Deliverables

#### 3.1 React Native + Expo Scaffolding
- `npx create-expo-app` with shared/ domain layer imported as local package
- Same hexagonal structure as backend, adapted for mobile
- Zustand stores for app state, Legend-State for persistence
- **AC**: app boots on iOS simulator + Android emulator. Shows energy battery from local SQLCipher DB.

#### 3.2 Shared Domain Layer
- TypeScript entities and use cases extracted to `shared/` package
- Used by both RN mobile and existing Tauri web app
- **AC**: same `EnergyBattery.calculate()` returns identical result on mobile and desktop.

#### 3.3 SQLCipher Encryption
- `@zetetic/sqlcipher-react-native` integrated
- Key derived from device biometric + app-specific seed
- All local data encrypted at rest
- **AC**: inspect SQLite DB file → all content is ciphertext. App opens it fine.

#### 3.4 Mobile UI (4 tabs)
- Today (battery + brain dump + pacing status)
- Tasks (declarative board + dopamine menu)
- Regulate (body doubling + sensory controls + interoception)
- Reflect (weekly patterns + insights)
- 4-tab bottom nav. Never more. Modal for focus/pacing session.
- **AC**: all 4 tabs render with real data. Thumb-friendly (targets in lower 1/3).

#### 3.5 Home Screen Widgets
- iOS WidgetKit + Android App Widgets
- Widget 1: current energy battery %
- Widget 2: next suggested task (from pacing engine)
- **AC**: widgets render on home screen, update when app changes state.

#### 3.6 Voice Brain Dump
- OS-level voice shortcut (Siri Shortcut / Google Assistant tap)
- Captures speech → sends to AI adapter → returns structured
- Same brain dump backend as Phase 1.1
- **AC**: say "note to self: I need to pick up meds and call the doctor" → 2 tasks appear in app.

#### 3.7 OS Accessibility
- VoiceOver (iOS) / TalkBack (Android): all interactive elements labeled
- Switch Control / Switch Access: all actions reachable via sequential navigation
- Dynamic Type / Font Scaling: UI at 200% font shows no overlap
- Reduce Motion: all animations disable via OS setting
- **AC**: VoiceOver reads every button correctly. Tab through entire app without missing focusable elements.

#### 3.8 CI/CD Pipeline
- GitHub Actions: lint → test (domain + adapters) → build (Android APK + iOS IPA)
- Expo EAS for app store submission
- Fastlane for code signing and metadata
- **AC**: `git push` triggers full pipeline. Green build produces installable artifact.

---

# Phase 4: Intelligence

**Goal**: Local AI that learns user patterns. On-device RAG.
**Sessions**: 2-3 (~3-5 days)

### Deliverables

#### 4.1 Local LLM Integration (Mobile)
- MLC-LLM or llama.cpp packaged for iOS/Android
- Model: Phi-3-mini-Q4 or smaller (3B class, runs on device)
- Falls back to LM Studio (desktop) when available
- **AC**: brain dump on mobile → local model processes it in <5s without network call

#### 4.2 Personal RAG
- Brain dump entries → embedded locally → stored in SQLite-adjacent vector store
- Query: "what was I working on last week?" → returns semantically relevant chunks
- No cloud dependency. All embeddings local.
- **AC**: "find tasks about the kitchen" returns kitchen-related entries even when exact words differ.

#### 4.3 Energy Pattern Recognition
- Analyzes 7+ days of energy logs
- Identifies: best time of day, worst days, boom-bust cycles, energy killers
- Presents as: "You tend to have most energy between 10am-12pm. Your lowest point is usually 3pm."
- **AC**: inject 7 days of synthetic data → pattern output matches injected cycles.

#### 4.4 Declarative Translation Engine
- User types/shouts "I need to FUCKING clean this goddamn kitchen"
- AI rewrites to: "Kitchen needs some attention when you have energy"
- Both versions stored. Original never deleted.
- **AC**: aggressive imperative text → output is declarative. Original preserved.

---

# Phase 5: Community & Sync

**Goal**: Optional encrypted sync. Shared experiences.
**Sessions**: 2-3 (~3-4 days)

### Deliverables

#### 5.1 Optional E2EE Sync
- Legend-State sync adapter with E2E encryption
- User-provided key (optional, no sync without key)
- Syncs: tasks, energy logs, habits
- Server: Supabase or minimal Go service. No plaintext access.
- **AC**: enable sync on device A → data appears on device B. Server cannot read content.

#### 5.2 Admin Night Mode
- Virtual co-working room: "admin night — bring your unfinished tasks"
- Shared timer + optional video/voice (WebRTC)
- No chat requirement — presence is enough
- **AC**: join room, see "X others focusing", timer runs, leave.

#### 5.3 Community Templates
- Shareable dopamine menus, routine templates, pacing configs
- JSON export/import with validation
- Optional public template gallery (opt-in)
- **AC**: export my dopamine menu → import on another device → identical structure

#### 5.4 Cross-Device Sync
- Mobile ↔ Desktop sync via Legend-State
- Conflict resolution: last-write-wins with tombstone markers
- **AC**: add task on mobile → appears on desktop within 5s. Edit on both offline → merge on reconnect.

---

## Session Burn-Down

| Phase | Sessions | Wall Clock | Parallel With |
|-------|----------|------------|---------------|
| Phase 1 Foundation | 1-2 | 3-5 days | — |
| Phase 2 Pacing | 2 | 2-3 days | Phase 1 (can share session 2) |
| Phase 3 Mobile | 3 | 3-5 days | Phase 1-2 (domain layer is prerequisite) |
| Phase 4 Intelligence | 2-3 | 3-5 days | Phase 3 (can overlap late Phase 3) |
| Phase 5 Community | 2-3 | 3-4 days | Phase 4 |

**Total**: 10-13 sessions, ~14-21 calendar days.

## Acceptance Testing for Each Phase

Before claiming any phase complete:
- [ ] All acceptance criteria in that phase pass
- [ ] Existing Phase 1 AC still pass (regression)
- [ ] `npm test` (domain) and `pytest` (backend) green
- [ ] The app opens and the primary flow works (brain dump → see tasks → do → reflect)
- [ ] No new streaks, badges, or coercive patterns introduced

## Risk Mitigation

| Risk | Hedge |
|------|-------|
| Local LLM too slow on mobile | Ship without local LLM first (Phase 4 is optional). Cloud fallback. |
| Mobile sync conflicts complex | Ship Phase 5 last — local-only app is fully functional. Sync is bonus. |
| User doesn't like declarative language | Settings toggle: declarative / neutral. Never revert to imperative. |
| WCAG 3.0 spec still in draft | Target Bronze tier (stable recommendations). Ignore Gold until spec final. |

---

*Sources: 80-turn research (Jul 2026) at research/research_synthesis.md, research/architecture_spec.md, research/verification_report.md*
