# neur-os backend v1.0
"""Neuro-Affirming Cognitive Prosthetic — Backend API

Local-first, privacy-preserving, trauma-informed.

Architecture: routes/ modules handle HTTP, store/ handles persistence,
domain/ handles business logic, timer.py handles focus timer state machine.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "neur-os.db"

# ── App Factory ──
app = FastAPI(title="NeurOS", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Store — FastAPI-managed singleton via backend/depts.py ──
from backend.deps import set_store, reset_store  # noqa: F401 — re-exported for tests
from backend.routes import (
    checkin, state, tasks, habits, timer_routes, winddown, review,
    soundscapes, declarative, crisis, energy, export, onboarding,
    passivelog, dopamine, interoception, templates_api, sync, admin, brain,
)

app.include_router(checkin.router)
app.include_router(state.router)
app.include_router(tasks.router)
app.include_router(habits.router)
app.include_router(timer_routes.router)
app.include_router(winddown.router)
app.include_router(review.router)
app.include_router(soundscapes.router)
app.include_router(declarative.router)
app.include_router(crisis.router)
app.include_router(energy.router)
app.include_router(export.router)
app.include_router(onboarding.router)
app.include_router(passivelog.router)
app.include_router(dopamine.router)
app.include_router(interoception.router)
app.include_router(templates_api.router)
app.include_router(sync.router)
app.include_router(admin.router)
app.include_router(brain.router)

# ── Static file serving ──
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
