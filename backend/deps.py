"""FastAPI dependency injection for NeurOS.

Provides get_store() as a proper FastAPI dependency, avoiding circular imports
between main.py (app factory) and routes/ (which need the store).
"""

from backend.store import DataStore, SqliteStore
from backend.config import DB_PATH


_store: DataStore | None = None


def get_store() -> DataStore:
    global _store
    if _store is None:
        s = SqliteStore(DB_PATH)
        s.init_schema()
        s._seed_defaults()
        _store = s
    return _store


def reset_store():
    global _store
    _store = None


def set_store(store: DataStore):
    global _store
    _store = store
