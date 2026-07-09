"""Passivelog routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.schemas import PassiveLogSubmit

router = APIRouter()

@router.get("/api/passive-log/today")
async def get_today_logs(store: DataStore = Depends(get_store)):
    return ok({"entries": store.get_today_passive_log()})

@router.post("/api/passive-log/submit")
async def submit_passive_log(data: PassiveLogSubmit, store: DataStore = Depends(get_store)):
    lid = store.submit_passive_log(data.response, data.spoons_at_time, data.current_task_id, data.source)
    return ok({"saved": True, "id": lid})

@router.get("/api/passive-log/check")
async def check_passive_prompt(store: DataStore = Depends(get_store)):
    last = store.last_passive_log_today()
    if last is None:
        return ok({"should_prompt": True, "last_response_minutes_ago": None})
    import datetime as dt
    last_ts = dt.datetime.fromisoformat(last.get("timestamp", ""))
    mins_ago = (dt.datetime.utcnow() - last_ts).total_seconds() / 60
    return ok({"should_prompt": mins_ago >= 60, "last_response_minutes_ago": round(mins_ago)})


