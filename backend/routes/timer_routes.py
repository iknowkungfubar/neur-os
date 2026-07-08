"""Timer Routes routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.schemas import TimerAction

router = APIRouter()

@router.post("/api/timer")
async def timer_action(data: TimerAction, store: DataStore = Depends(get_store)):
    if data.action == "start":
        store.stop_all_timers()
        return ok(store.create_timer(data.model_dump()))
    elif data.action == "pause":
        t = store.get_active_timer()
        if not t: raise HTTPException(400, "No running timer")
        try:
            elapsed = int((datetime.utcnow() - datetime.strptime(t["started_at"][:19], "%Y-%m-%d %H:%M:%S")).total_seconds())
        except ValueError: elapsed = 0
        total = t["elapsed_seconds"] + elapsed
        store.update_timer(t["id"], {"status": "paused", "elapsed_seconds": total, "paused_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})
        return ok({"id": t["id"], "status": "paused", "elapsed_seconds": total})
    elif data.action == "resume":
        t = store.get_active_timer()
        if not t or t["status"] != "paused": raise HTTPException(400, "No paused timer")
        store.update_timer(t["id"], {"status": "running", "paused_at": None, "started_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})
        return ok({"id": t["id"], "status": "running"})
    elif data.action == "stop":
        t = store.get_active_timer()
        if not t: raise HTTPException(400, "No active timer")
        elapsed = 0
        if t["status"] == "running":
            try: elapsed = int((datetime.utcnow() - datetime.strptime(t["started_at"][:19], "%Y-%m-%d %H:%M:%S")).total_seconds())
            except ValueError: pass
        total = t["elapsed_seconds"] + elapsed
        store.update_timer(t["id"], {"status": "completed", "elapsed_seconds": total, "completed_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})
        return ok({"id": t["id"], "status": "completed", "elapsed_seconds": total})
    raise HTTPException(400, "Invalid action")

@router.get("/api/timer/active")
async def get_active_timer(store: DataStore = Depends(get_store)):
    return ok({"timer": store.get_active_timer()})


