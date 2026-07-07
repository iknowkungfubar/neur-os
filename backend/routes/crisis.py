"""Crisis routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.schemas import CrisisCheck
from backend.domain.usecases import parse_llm_json

router = APIRouter()

@router.post("/api/crisis/activate")
async def activate_crisis(store: DataStore = Depends(get_store)):
    cid = store.activate_crisis("sensory_overload")
    today = date.today().isoformat()
    store.set_mode(today, "red")
    return ok({"crisis_id": cid, "status": "activated", "actions": ["demand_eradication", "sensory_blackout", "grounding_mode"]})

@router.post("/api/crisis/resolve")
async def resolve_crisis(store: DataStore = Depends(get_store)):
    resolved = store.resolve_crisis()
    return ok({"status": "resolved" if resolved else "none_active"})

@router.post("/api/crisis/check")
async def crisis_check(data: CrisisCheck, store: DataStore = Depends(get_store)):
    score = data.cognitive_load * 0.5 + data.frustration_markers * 0.3 + data.error_rate * 0.2
    trigger = score >= 0.7
    if trigger:
        store.activate_crisis("auto_detected")
    return ok({"trigger": trigger, "confidence": round(score, 2), "threshold": 0.7})


