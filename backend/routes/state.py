"""State routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import date
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.schemas import ModeUpdate

router = APIRouter()

@router.get("/api/mode")
async def get_mode(store: DataStore = Depends(get_store)):
    return ok({"mode": store.get_state()["mode"]})

@router.put("/api/mode")
async def set_mode(data: ModeUpdate, store: DataStore = Depends(get_store)):
    if data.mode not in ("green", "amber", "red"):
        raise HTTPException(400, "Mode must be green, amber, or red")
    today = date.today().isoformat()
    store.set_mode(today, data.mode)
    return ok({"mode": data.mode})

@router.get("/api/state")
async def get_state(store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    state = store.get_state(today)
    tasks = [t for t in store.get_tasks("active")]
    timer = store.get_active_timer()
    return ok({"state": state, "tasks": tasks, "active_timer": timer})

