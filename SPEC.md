# NeurOS — Neuro-Affirming Cognitive Prosthetic

## Verified Design Spec (Post-Research)

### Core Concept
A local-first, trauma-informed digital assistant for neurodivergent individuals that functions as a **cognitive prosthetic** — externalizing executive function, managing energy via Spoon Theory, and providing declarative/non-coercive support.

### VERIFIED Technologies (from 20-turn research)
| Component | Technology | Source |
|-----------|-----------|--------|
| **Desktop shell** | Tauri v2 + React/TypeScript | tauri.app, verified |
| **Local LLM** | LM Studio (qwythos-9b-claude-mythos-5-1m) | MS/HuggingFace, wired and tested |
| **Vector DB** | LanceDB (disk-based, columnar) | lancedb.github.io, verified |
| **Structured DB** | SQLite | Standard |
| **Encryption** | XChaCha20-Poly1305 | libsodium/RFC 8439 |
| **Biosignal** | NeuroKit2 (Python) for HRV | neuropsychology.github.io |
| **Crisis detection** | Heuristic monitoring (custom) | Circuit breaker pattern, verified |
| **LLM unlearning** | Recover-to-Forget (R2F) | NeurIPS 2025, arXiv 2512.07374 |
| **Memory portability** | Latent Context Compilation | arXiv 2602.21221 |
| **Sycophancy defense** | R-FT / RBED | ACL 2026 |
| **P2P sync** | SyftBox (OpenMined) or CRDTs | openmined.org, verified |
| **Pacing framework** | Spoon Theory + Energy Envelope | Christine Miserandino, Dr. Leonard Jason |

### VERIFIED Research Frameworks (Durable Reference)

These are the verified real frameworks, papers, and tools that inform the design. Do not re-verify unless >6 months have passed.

| Framework / Tool | Domain | Verified? | Source |
|---|---|---|---|
| **Spoon Theory** — energy as finite daily units | Energy pacing | ✅ Real | Christine Miserandino (2003) |
| **Energy Envelope** — stay within 80% of capacity | Chronic fatigue pacing | ✅ Real | Dr. Leonard Jason |
| **Polyvagal Theory** — ventral vagal safety cues | Nervous system regulation | ✅ Real | Dr. Stephen Porges (1994) |
| **Somatic Experiencing** — resourcing, pendulation | Trauma resolution | ✅ Real | Dr. Peter Levine |
| **Double Empathy Problem** — mutual communication breakdown | Neurotype relations | ✅ Real | Dr. Damian Milton |
| **Pervasive Drive for Autonomy** (reframes PDA) | Demand avoidance | ✅ Real | Neuro-affirming reframe |
| **Neuro-Affirming ACT** — acceptance & commitment therapy | ND therapy | ✅ Real | Russ Harris |
| **Cognitive Prosthetic** framing — app as external exec function | Design philosophy | ✅ Real | arXiv 2603.02072 |
| **SheepCat** — local LLM passive logger, SQLite, Docker | Reference implementation | ✅ Real | GitHub, verified |
| **OpenJarvis** — Stanford 5-primitive local-first agent framework | Reference architecture | ✅ Real | Stanford, verified |
| **Gentle Ally** — declarative language translation | Reference pattern | ✅ Real | Apple App Store, verified |
| **NeuroWise** — Double Empathy multi-agent system | Multi-agent ND support | ✅ Real | Verified |
| **R2F (Recover-to-Forget)** — LLM unlearning | Privacy tech | ✅ Real | NeurIPS 2025 |
| **Latent Context Compilation** — portable memory buffer tokens | Memory tool | ✅ Real | arXiv 2602.21221 |
| **SycEval** — medical sycophancy benchmark (not "Med-Stress") | Evaluation | ✅ Real | arXiv 2502.08177 |
| **R-FT / RBED** — adversarial robustness in LLMs | Security | ✅ Real | ACL 2026 |

### FABRICATED Claims Discarded
- "T-LoRA" — does not exist. Use Dynamic LoRA or CoLoR instead.
- "Med-Stress" — does not exist. Use SycEval instead.
- "Threshold" app — fabricated. Build custom crisis detection.
- Qwen 2.5-3B 128K context — wrong. It's 32K. Phi-3 Mini has 128K.

### Architecture Layers

```
┌─────────────────────────────────────────────┐
│           PRESENTATION LAYER                │
│  Tauri + React (TypeScript)                 │
│  - Minimalist UI (dark charcoal on warm bg) │
│  - No gamification, no streaks, no punitive │
│  - Declarative language everywhere          │
│  - Crisis mode: sensory blackout            │
├─────────────────────────────────────────────┤
│              AGENT LAYER                    │
│  - Local LLM (LM Studio endpoint)           │
│  - Declarative language translation         │
│  - Spoon cost estimation                    │
│  - Task micro-chunking                      │
│  - Circuit breaker (graceful degradation)   │
├─────────────────────────────────────────────┤
│            MEMORY LAYER                     │
│  - SQLite (tasks, energy logs, preferences) │
│  - LanceDB (vector embeddings for RAG)      │
│  - XChaCha20-Poly1305 encryption at rest    │
├─────────────────────────────────────────────┤
│         SOMATIC TRACKING LAYER              │
│  - Manual energy/symptom check-ins          │
│  - (Future: NeuroKit2 HRV via wearables)    │
│  - Traffic-light pacing (Green/Amber/Red)   │
└─────────────────────────────────────────────┘
```

### Phase 1 Build (This Session)
**Core:** Task + Energy management with local LLM integration
1. Tauri + React scaffold
2. Spoon Theory energy tracking (daily spoons, task cost assignment)
3. Task management with micro-chunking
4. Declarative language translation via LM Studio
5. Crisis mode (simplified: hides tasks, dims screen)
6. Local-only (SQLite, no cloud)

### MVP User Flow
1. **Morning check-in**: "How many spoons do you have today?" (1-10)
2. **Task list**: Shows tasks with energy cost estimates
3. **Add task**: Describe task → LLM estimates spoon cost + suggests micro-chunking
4. **Declarative mode**: LLM translates urgent tasks into non-coercive language
5. **Energy update**: Mid-day re-check adjusts task visibility
6. **Crisis button**: Hides everything, dims screen, plays grounding audio
