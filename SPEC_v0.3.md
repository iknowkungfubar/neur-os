# NeurOS v0.3 Spec — "I Can Start" (IMPLEMENTED)

> **Status:** Fully implemented as of v0.4. Single-task focus, traffic-light pacing, 2-min timer, body doubling, wind-down, soundscapes, desktop notifications all shipped. This doc is kept for reference.

## Core Insight
The hardest part of being ND isn't organizing tasks — it's *starting* them. v0.2 has the scaffolding (timer, habits, energy tracking). v0.3 solves the **activation energy problem**: getting the user from "I'm overwhelmed" to "I'm doing one thing" in as few cognitive steps as possible.

---

## Problem Diagnosis

| Pain Point | Current State | v0.3 Target |
|------------|--------------|-------------|
| **Opening the app** | Shows tabs and a check-in card. Still multiple choices. | One question: "What's one thing?" |
| **Too many tasks visible** | Full list with spoon costs. Visual noise. | Single-task focus mode. One task, front and center. |
| **No momentum** | No "just start" mechanism. | Two-minute "just start" timer + body doubling presence. |
| **Bad days aren't different** | Same interface regardless of energy. | Traffic-light mode: Green/Amber/Red completely changes the UI. |
| **No end-of-day closure** | Nothing happens after tasks are done. | Wind-down mode: reflection, gratitude, close the day. |
| **No feedback loop** | Can't see "am I improving?" | Weekly trend visualization + meaningful insights. |

---

## Feature Spec

### F1: Single-Task Focus Mode (HIGHEST IMPACT)

When you open the app and have tasks, it shows **one task** — the best one for your current energy level. That's it.

```
┌──────────────────────────────┐
│                              │
│        "One thing"           │
│                              │
│   [Write project proposal]   │
│        🍴 2 spoons           │
│                              │
│  ┌──────────────────────┐   │
│  │   Start (25 min)     │   │
│  └──────────────────────┘   │
│                              │
│  Show all tasks →            │
│  Not this one →              │
└──────────────────────────────┘
```

**Rules:**
- Auto-picks the highest-spoon task you can afford (use it while you have energy)
- "Not this one" cycles to the next task
- "Show all tasks" opens the full list
- After completing, asks: "Same again?" or "Next?"
- On empty: "What's one thing you want to get done?" with quick capture

### F2: Traffic-Light Pacing Mode

Replace fixed spoon counting with three modes that change how the app behaves:

| Mode | Meaning | App Behavior |
|------|---------|-------------|
| 🟢 **Green** | Good energy | Show all tasks. Focus timer available. Habits shown. |
| 🟡 **Amber** | Low energy | Only show low-spoon tasks. Timer defaults to 15 min. Recommend breaks. |
| 🔴 **Red** | Survival mode | Hide all tasks. "What do you need right now?" — rest, eat, hydrate, breathe. Crisis mode adjacent. |

**How it triggers:**
- Manual override (tap the mode indicator)
- Auto-suggest based on check-in spoons (≤3 spoons → Amber, 0 → Red)
- Auto-suggest based on habit completion (if no habits done by 2pm → Amber)

### F3: "Just Start" — Two-Minute Timer

A button that says **"Just start for 2 minutes"** — not 25, not 15. Two.

```
┌──────────────────────────────┐
│   "Just start for 2 min"    │
│                              │
│       1:42 remaining         │
│                              │
│   [Working on: task name]    │
│                              │
│         ████████░░           │
│                              │
│        Stop / Continue       │
└──────────────────────────────┘
```

**Why:** The hardest part is starting. 2 minutes is non-threatening. Once started, most people continue. This is the on-ramp to the full focus timer.

### F4: Body Doubling Mode

A simulated presence — not a real person, but a ambient indicator that "someone is here with you."

```
┌──────────────────────────────┐
│   🧑 You + 🤖 Companion     │
│                              │
│   Focus session: 12:34       │
│                              │
│   Companion: "I'm working    │
│   alongside you. You've got  │
│   this."                     │
│                              │
│         Pause / Stop         │
└──────────────────────────────┘
```

**Implementation:**
- A minimal UI element showing a second "person" present
- Periodic gentle prompts: "Still going?" (non-coercive, declarative)
- Works with any timer session
- Background changes subtly to signal "shared space"

### F5: Wind-Down Mode (Evening)

End-of-day closure — not more tasks, but reflection.

```
┌──────────────────────────────┐
│   Day is winding down.       │
│                              │
│   What went well today?      │
│   [text area]                │
│                              │
│   What drained energy?       │
│   [text area]                │
│                              │
│   Tomorrow's one thing:      │
│   [text area]                │
│                              │
│   Close the day →            │
└──────────────────────────────┘
```

**Triggers:**
- Manual tap ("Wind down")
- When all tasks completed
- Cron-based (optional, 9pm default)

### F6: Better Weekly Review

Current review is text-based. v0.3 adds:

- **Spoon trend** line chart (spoons over 7 days)
- **Task type breakdown** (what kind of tasks used most energy)
- **Habit completion rate** (streak graph)
- **"What worked" note** from wind-down entries
- **One insight** per week generated from patterns

### F7: Soundscape Bundling

We have the configs but no audio. v0.3 bundles:
- Brown noise (focus)
- Light rain (grounding)
- Deep tone + silence (crisis/breathing)

Generated client-side (Web Audio API) — no downloads needed.

### F8: Gentle Desktop Notification

Non-coercive notification when:
- Timer completes (declarative: "The focus session has ended.")
- Wind-down time approaches ("The evening wind-down window is open.")
- Red mode persists ("It's been a red day. That's okay.")

No badges, no sounds, no red dots.

---

## Technical Spec

### Frontend Architecture (HTML/JS)
- Single-page remains (no framework change)
- Web Audio API for soundscape generation
- localStorage for UI state (active tab, timer duration preference)
- View transitions between modes (Green/Amber/Red)

### Backend Additions
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/wind-down` | POST | Save evening reflection |
| `/api/wind-down/today` | GET | Get today's wind-down entry |
| `/api/review/insight` | GET | Generate weekly pattern insight |
| `/api/mode` | GET/PUT | Get/set traffic-light mode |
| `/api/tasks/next` | GET | Get best task for current energy |
| `/api/tasks/single` | POST | Update single-task focus target |

### Database Changes
```sql
ALTER TABLE daily_state ADD COLUMN mode TEXT DEFAULT 'green';
CREATE TABLE IF NOT EXISTS wind_down (
    id TEXT PRIMARY KEY,
    date TEXT UNIQUE,
    went_well TEXT,
    drained TEXT,
    tomorrow_one TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS focus_sessions (
    -- already exists as timer_sessions, add:
    body_doubling BOOLEAN DEFAULT 0,
    started_as TEXT DEFAULT 'focus'  -- 'focus', 'just_start', 'body_doubling'
);
```

### Data Migration Strategy
- All new columns use DEFAULT values — backward compatible
- Old DB files work without changes
- DB version check at startup

---

## UX Principles (Non-Negotiable)

1. **One thing at a time.** No screen shows more than one primary action.
2. **No streaks, no badges, no scores.** The habit check shows "you did it" — no fire emoji for streaks.
3. **Declarative or don't send.** Every prompt must pass the declarative test.
4. **Sensory-safe.** No animations faster than 300ms. No pulsing. No red text.
5. **Keyboard navigable.** Tab order is logical. No mouse-only interactions.
6. **Offline-first.** Everything works without internet. The LLM features are additive.

---

## Why This Version

v0.2 gave you the *tools*. v0.3 gives you the *path*.

The difference between "I can organize my tasks" and "I can actually start doing them" is the gap this version closes. Every feature is designed to lower activation energy, not add complexity.

When you open the app and see one task with a "Start" button — instead of a board full of todos — that's the v0.3 difference.
