# NeurOS v0.2 — "Functional Core" (RETROSPECTIVE)

**Status:** Shipped  
**Date:** 2026-07-02  
**Previous:** v0.1 (research + check-in/task/crisis base)  
**Next:** v0.3 (activation energy)

## Objective

Take the v0.1 foundation (spoon check-in, task board, crisis mode) and turn it into a genuinely useful daily tool with tracking, habits, and visualization.

## Features Built

- **5-tab UI** — Ready / Focus / All / Habits / Review
- **Focus timer** — 5/15/25/45/60 min with pause/resume/stop
- **Recurring tasks** — daily, weekday, weekly, monthly recurrence
- **Habit tracking** — check-off with streak counting
- **Weekly review dashboard** — energy trends, completed tasks, focus minutes, crisis count
- **Data export** — JSON + Markdown
- **Auto-backup** — on timer stop and shutdown
- **Soundscapes** — Web Audio API (brown noise, rain, breathing tone)

## Architecture

```
Frontend: single HTML/JS SPA (inline CSS, no framework)
Backend: FastAPI + SQLite
Timer: Server-side session with start/pause/resume/stop
Sound: Client-side Web Audio API oscillator + noise generators
```

## Key Decisions

1. No JS framework — single HTML file with vanilla JS to minimize cognitive load on development
2. Server-side timer (not client-side) — survives browser close
3. Streaks without gamification — shows "you did it" text, no badges/explosions
4. Soundscapes as Web Audio API — no audio file downloads needed

## Files

- `backend/main.py` — all endpoints (check-in, tasks, timer, habits, review, export)
- `frontend/index.html` — complete SPA
- `backend/soundscapes/` — (placeholder, Web Audio API generates sounds)
- `ROADMAP.md` — project roadmap
