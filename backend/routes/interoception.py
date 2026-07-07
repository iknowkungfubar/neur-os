"""Interoception routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok

router = APIRouter()

@router.post("/api/interoception")
async def log_interoception(data: dict, store: DataStore = Depends(get_store)):
    store.log_interoception(data.get("signals", []), data.get("mood", ""), data.get("note", ""))
    return ok({"status": "ok"})

@router.get("/api/interoception")
async def get_interoception(store: DataStore = Depends(get_store)):
    return ok({"logs": store.get_interoception()})


