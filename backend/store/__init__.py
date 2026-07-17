"""Data access layer for NeurOS — all SQL in one place.

Two implementations: SqliteStore (real DB) and InMemoryStore (tests).
Every route calls a store method instead of writing SQL directly.
"""

from backend.store.base import DataStore
from backend.store.sqlite_store import SqliteStore
from backend.store.memory_store import InMemoryStore

__all__ = ["DataStore", "SqliteStore", "InMemoryStore"]
