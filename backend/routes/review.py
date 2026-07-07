"""Review routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime, timedelta
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok

router = APIRouter()

@router.get("/api/review/week")
async def weekly_review(store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    return ok(store.weekly_review(week_ago, today))

@router.get("/api/review/insight")
async def generate_insight(store: DataStore = Depends(get_store)):
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    return ok(store.review_insight(week_ago))


