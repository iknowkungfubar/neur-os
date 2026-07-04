# NeurOS v0.4.1 — "Resilience & Onboarding"

**Status:** Draft — spec only, not built  
**Date:** 2026-07-03  
**Previous:** v0.4 (ship ready)  
**Next:** v0.5 (encryption, LanceDB)

---

## Objective

Close three critical gaps identified from verified research: passive energy logging, automatic crisis detection, and narrative-driven onboarding. These are the highest-impact features that require no new infrastructure.

---

## Functional Requirements

### FR-A: Passive Hourly Logger

| ID | Description | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| A-01 | Backend cron task triggers a "What are you doing?" desktop notification every 60–90 minutes during waking hours | P0 | Notification appears with text input field. Backend schedules 6–10 notifications per day |
| A-02 | User response is saved to SQLite with: timestamp, spoon count at time of response, current task title, raw text | P0 | `SELECT * FROM passive_log` returns rows with all fields populated |
| A-03 | Wind-down view shows today's passive log entries for reflection | P1 | `/api/passive-log/today` returns today's entries ordered by timestamp |
| A-04 | Weekly review aggregates passive log into "time spent by task category" rough breakdown | P2 | Review page shows bar of logged activities grouped by energy tag |
| A-05 | User can mute passive log notifications for the day | P1 | Button "Enough for today" suppresses notifications until next day |

### FR-B: Auto Crisis Detection

| ID | Description | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| B-01 | Frontend tracks behavioral signals on a 60-second sliding window: rapid navigation changes (>3 tab switches/min), task creation aborts (task dialog opened and closed without saving >2/min), timer aborts (timer started and stopped within 30s >2/min), help/declarative button spam (>5 clicks/min) | P0 | Signals are collected in memory, never sent to backend |
| B-02 | Backend endpoint `POST /api/crisis/check` accepts aggregated scores, returns crisis recommendation | P0 | `{"cognitive_load": 0.72, "frustration_markers": 0.4, "trigger": true}` |
| B-03 | When threshold is crossed (configurable, default 0.7), frontend auto-activates crisis mode without user action | P0 | Crisis mode engages (sensory blackout, demand eradication, grounding cue) when score > 0.7 |
| B-04 | User can dismiss auto-crisis ("I'm fine") which suppresses auto-detection for 2 hours | P1 | Dismiss button appears in crisis overlay. Backend logs `auto_crisis_dismissed` event |
| B-05 | Crisis activation auto-requests: re-check every 5 minutes until score drops below 0.5 or user manually resolves | P2 | If still in crisis after 5 min, check again. Auto-resolve when score < 0.5 for two consecutive checks |

### FR-E: Narrative Onboarding

| ID | Description | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| E-01 | On first launch, app asks "What's one thing you'd like help with?" instead of showing a form | P0 | Onboarding screen shows single text prompt, no form fields |
| E-02 | LLM analyzes the response and asks one follow-up question per interaction | P0 | Each user response generates exactly one LLM-based follow-up question |
| E-03 | After 3-5 conversational turns, system extracts: spoon baseline (from "how much energy do you usually have"), pain patterns (from "what drains you most"), task preferences (from "what kind of things do you need to do") | P1 | Onboarding state saved to SQLite `onboarding_state` table with extracted profile |
| E-04 | Onboarding resumes where it left off if user closes and reopens | P1 | Reopening the app during onboarding phase continues the conversation, not restart |
| E-05 | Onboarding completes after 5-7 total turns OR user says "I'm good" | P1 | After completion, app shows normal check-in screen. User profile populated with extracted data |
| E-06 | User can skip onboarding entirely ("Just show me the app") | P0 | Skip button on first screen. App starts in default state with 10 spoons |

---

## Non-Functional Requirements

| ID | Description | Target | Verification |
|----|-------------|--------|-------------|
| NFR-01 | Passive logger notifications must be non-coercive, declarative language | "Checking in — what's on your mind?" not "You need to log your task" | Manual review |
| NFR-02 | Crisis detection must run client-side only — no network calls | `POST /api/crisis/check` is the only network request, scores computed in browser | DevTools network tab |
| NFR-03 | Onboarding must not feel like a questionnaire — average response time < 3 words | User can respond with 1-3 words and still get a sensible follow-up | Manual test |
| NFR-04 | All new features must work with LM Studio offline (degrade gracefully) | Without LLM: onboarding shows progressive disclosure checklist, passive log still collects | Shut down LM Studio, verify |
| NFR-05 | Zero new dependencies beyond FastAPI/httpx/uvicorn | No pip install new-package | `pip list` |

---

## Data Model Additions

```sql
-- A: Passive Log
CREATE TABLE IF NOT EXISTS passive_log (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    response TEXT NOT NULL,
    spoons_at_time REAL,
    current_task_id TEXT,
    source TEXT DEFAULT 'notification'  -- 'notification', 'manual', 'wind_down'
);

-- E: Onboarding State
CREATE TABLE IF NOT EXISTS onboarding_state (
    id TEXT PRIMARY KEY DEFAULT 'current',
    phase INTEGER DEFAULT 0,
    turns INTEGER DEFAULT 0,
    extracted_profile TEXT,  -- JSON blob
    created_at TEXT,
    updated_at TEXT
);
```

No DB changes for B — crisis detection is client-side scoring, backend simply tracks active crisis state (already exists).

---

## API Contracts

### `GET /api/passive-log/check`
Returns whether a notification should fire now (based on last response time).

```json
Request: {}
Response: {"should_prompt": true, "last_response_minutes_ago": 75}
```

### `POST /api/passive-log/submit`
Saves a passive log entry.

```json
Request:  {"response": "cleaning the kitchen", "spoons_at_time": 5, "current_task_id": "abc-123"}
Response: {"saved": true, "id": "log-uuid"}
```

### `GET /api/passive-log/today`
Returns today's log entries.

```json
Response: {"entries": [{"id": "...", "timestamp": "...", "response": "...", "spoons_at_time": 5}]}
```

### `POST /api/crisis/check`
Accepts client-side scores, returns crisis recommendation.

```json
Request:  {"cognitive_load": 0.72, "frustration_markers": 0.4, "error_rate": 0.1}
Response: {"trigger": true, "confidence": 0.85, "threshold": 0.7}
```

---

## Task Breakdown

| Task | ID | Files | Depends On |
|------|----|-------|-----------|
| Passive log DB schema + backend endpoints | T-A-01 | `backend/main.py` | None |
| Passive log notification scheduler | T-A-02 | `backend/main.py` | T-A-01 |
| Passive log UI (notification popover) | T-A-03 | `frontend/index.html` | T-A-01 |
| Crisis detection signal collection (client) | T-B-01 | `frontend/index.html` | None |
| Crisis check endpoint (backend) | T-B-02 | `backend/main.py` | None |
| Auto-crisis trigger + dismiss (client) | T-B-03 | `frontend/index.html` | T-B-01, T-B-02 |
| Onboarding DB schema | T-E-01 | `backend/main.py` | None |
| Onboarding conversation flow (LLM-driven) | T-E-02 | `backend/main.py`, `frontend/index.html` | T-E-01 |
| Onboarding skip + resume logic | T-E-03 | `backend/main.py`, `frontend/index.html` | T-E-02 |
| Integration tests | T-ALL-01 | `backend/test_main.py` | All above |

---

## Boundaries

- No new Python dependencies. Everything uses stdlib + httpx + FastAPI.
- Crisis detection is heuristic only — no ML model. Hardcoded weights based on the verified heuristic monitoring pattern.
- Passive log notifications fire at most once per 60 minutes. No spam.
- Onboarding resets if user skips. `onboarding_state` table cleared on skip.
