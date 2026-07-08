"""Winddown routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from datetime import date, timedelta
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.schemas import WindDownEntry

router = APIRouter()

@router.post("/api/wind-down")
async def save_wind_down(data: WindDownEntry, store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    store.upsert_wind_down(today, data.model_dump(exclude_unset=True))
    return ok({"date": today})

@router.get("/api/wind-down/today")
async def get_wind_down(store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    return ok({"entry": store.get_wind_down(today)})

@router.get("/api/wind-down/week")
async def get_week_wind_down(store: DataStore = Depends(get_store)):
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    return ok({"entries": store.week_wind_down(week_ago)})


