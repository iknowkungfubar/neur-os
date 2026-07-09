"""Dopamine routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok

router = APIRouter()

@router.get("/api/dopamine-menu")
async def get_dopamine_menu(store: DataStore = Depends(get_store)):
    return store.get_dopamine_menu()

@router.post("/api/dopamine-menu")
async def add_dopamine_item(data: dict, store: DataStore = Depends(get_store)):
    store.add_dopamine_item(data)
    return ok({"status": "ok"})

@router.delete("/api/dopamine-menu/{item_id}")
async def delete_dopamine_item(item_id: str, store: DataStore = Depends(get_store)):
    store.delete_dopamine_item(item_id)
    return ok({"status": "ok"})


