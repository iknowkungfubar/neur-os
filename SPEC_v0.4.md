# NeurOS v0.4 — "Ship Ready" (RETROSPECTIVE)

**Status:** Shipped  
**Date:** 2026-07-02 (late)  
**Previous:** v0.3 (activation energy: single-task focus, traffic-light, body doubling, wind-down)  
**Next:** v0.4.1 (gaps: passive logger, auto crisis detection, narrative onboarding)

## Objective

Package v0.3 as a real desktop application with one-command install, system integration, and LM Studio connectivity. Make it something a non-technical user could run.

## Features Built on v0.3

- **Soundscapes v2** — bundled WAV files (brown noise, rain, breathing tone)
- **Data import/restore** endpoint
- **Onboarding first-run wizard** — single-page welcome flow
- **Install script** — `install.sh`: copies files, installs deps, creates systemd service, .desktop entry
- **Tauri v2 desktop shell** — native window (720x900), systemd integration
- **LM Studio wiring** — `call_llm()` function, `POST /api/declarative` endpoint
- **Systemd user service** — auto-start on boot
- **Launcher script** — `~/.local/bin/neur-os` (backend) + `~/.local/bin/neur-os-desktop` (Tauri binary)

## Architecture

```
Web app:     FastAPI + SQLite on :7447 (backend serves HTML/JS frontend)
Desktop:     Tauri v2 native window → loads http://localhost:7447
Install:     install.sh → ~/.local/share/neur-os/ + systemd + .desktop
LM Studio:   httpx → localhost:1234/v1 (qwythos-9b-claude-mythos-5-1m)
```

## Key Decisions

1. Tauri shell wraps the web app (not standalone) — backend must already be running
2. `install.sh` copies files, doesn't symlink — clean separation between dev and installed versions
3. LM Studio default model: `qwythos-9b-claude-mythos-5-1m` — set via `LM_MODEL` env var
4. 15s timeout on LLM calls — 9B model on consumer GPU needs it

## Files

- `install.sh` — one-command installer
- `desktop/src-tauri/` — Tauri v2 Rust project
- `backend/main.py` — updated with `call_llm()`, `POST /api/declarative`
- `frontend/index.html` — onboarding wizard added
