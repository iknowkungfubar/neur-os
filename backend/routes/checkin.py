"""Checkin routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.schemas import SpoonCheckIn

router = APIRouter()

@router.post("/api/check-in")
async def morning_checkin(data: SpoonCheckIn, store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    suggested_mode = "green"
    if data.spoons <= 3: suggested_mode = "red"
    elif data.spoons <= 5: suggested_mode = "amber"
    store.upsert_state(today, {"total_spoons": data.spoons, "remaining_spoons": data.spoons,
                                "pain_level": data.pain_level, "notes": data.note, "mode": suggested_mode})
    store.log_energy(data.spoons, data.pain_level, data.note)
    return ok({"spoons": data.spoons, "pain_level": data.pain_level, "suggested_mode": suggested_mode})

