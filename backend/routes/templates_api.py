"""Templates Api routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok

router = APIRouter()

@router.get("/api/templates")
async def get_templates(type: str = "dopamine_menu", store: DataStore = Depends(get_store)):
    return store.get_template(type)

@router.post("/api/templates")
async def import_template(data: dict, store: DataStore = Depends(get_store)):
    count = store.import_template_items(data.get("type", ""), data.get("items", []))
    return ok({"imported": count})


