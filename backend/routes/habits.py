"""Habits routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.schemas import HabitCreate

router = APIRouter()

@router.get("/api/habits")
async def get_habits(store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    return ok({"habits": store.get_habits(today)})

@router.post("/api/habits")
async def create_habit(habit: HabitCreate, store: DataStore = Depends(get_store)):
    hid = store.create_habit(habit.model_dump())
    return ok({"id": hid})

@router.post("/api/habits/{hid}/check")
async def check_habit(hid: str, store: DataStore = Depends(get_store)):
    if not store.get_habit(hid):
        raise HTTPException(404, "Habit not found")
    today = date.today().isoformat()
    store.check_habit(hid, today)
    return ok({"done_today": True})


