"""Shared configuration for NeurOS.

Globals extracted from main.py so route modules can access them
without circular imports.
"""
from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "neur-os.db"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)
SOUNDSCAPES_DIR = Path(__file__).parent / "soundscapes"
SOUNDSCAPES_DIR.mkdir(exist_ok=True)

ENERGY_TAGS = {"low": 0.5, "medium": 1.0, "high": 2.0}
