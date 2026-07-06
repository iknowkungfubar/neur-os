"""Soundscape routes. Uses store for persistence."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from backend.deps import get_store
from backend.config import SOUNDSCAPES_DIR
from backend.schemas import SoundscapeUpdate
from backend.response import ok

router = APIRouter()


@router.get("/api/soundscapes")
async def get_soundscapes(store=Depends(get_store)):
    configs = store.get_soundscape_configs()
    available = sorted([
        f.name for f in SOUNDSCAPES_DIR.iterdir()
        if f.suffix in (".wav", ".ogg", ".mp3", ".flac")
    ]) if SOUNDSCAPES_DIR.exists() else []
    return ok({"configs": configs, "available_sounds": available, "soundscape_dir": "/soundscapes/"})


@router.patch("/api/soundscapes/{mode}")
async def update_soundscape(mode: str, update: SoundscapeUpdate, store=Depends(get_store)):
    store.update_soundscape_config(mode, update.dict(exclude_unset=True))
    return ok({"mode": mode})
