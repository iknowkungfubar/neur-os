"""Sync routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok

router = APIRouter()

@router.post("/api/sync/upload")
async def sync_upload(data: dict, store: DataStore = Depends(get_store)):
    store.sync_upload(data["device_id"], data.get("collection", "tasks"), data["encrypted_blob"], data.get("version", 1))
    return ok({"status": "ok"})

@router.get("/api/sync/download")
async def sync_download(device_id: str = "", collection: str = "tasks", since: str = "", store: DataStore = Depends(get_store)):
    return ok({"blobs": store.sync_download(device_id, collection, since)})

# ── Admin Night Mode ──
admin_rooms: dict[str, dict] = {}

