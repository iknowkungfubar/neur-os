"""Energy routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.domain.usecases import energy_envelope, detect_boom_bust, analyze_energy_patterns

router = APIRouter()

@router.get("/api/energy-log")
async def get_energy_log(store: DataStore = Depends(get_store)):
    return ok({"log": store.get_energy_log(30)})


@router.get("/api/pacing/envelope")
async def pacing_envelope(store: DataStore = Depends(get_store)):
    state = store.get_state()
    tasks = store.get_tasks("active")
    recent = store.recent_energy(7)
    current = state["remaining_spoons"] / max(state["total_spoons"], 1) * 100
    history = [e["spoons_remaining"] * 10 for e in recent]
    return ok(energy_envelope(current, len(tasks), history))

@router.get("/api/pacing/boom-bust")
async def boom_bust(store: DataStore = Depends(get_store)):
    recent = store.recent_energy(7)
    history = [e["spoons_remaining"] * 10 for e in recent]
    return ok(detect_boom_bust(history))

@router.get("/api/pacing/patterns")
async def energy_patterns(store: DataStore = Depends(get_store)):
    return ok(store.energy_patterns())


