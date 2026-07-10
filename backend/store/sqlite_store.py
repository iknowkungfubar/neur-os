"""SQLite implementation of DataStore for NeurOS."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.store.base import DataStore


class SqliteStore(DataStore):
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.db_path))
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        return c

    def _dict(self, row: sqlite3.Row | None) -> dict | None:
        return dict(row) if row else None

    def _list(self, rows: list[sqlite3.Row]) -> list[dict]:
        return [dict(r) for r in rows]

    # ── Schema ──
    def init_schema(self) -> None:
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_state (
                id TEXT PRIMARY KEY, date TEXT NOT NULL UNIQUE,
                total_spoons INTEGER NOT NULL DEFAULT 10,
                remaining_spoons REAL NOT NULL DEFAULT 10,
                pain_level INTEGER DEFAULT 0, notes TEXT DEFAULT '',
                mode TEXT DEFAULT 'green'
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, title TEXT NOT NULL,
                description TEXT DEFAULT '', spoon_cost REAL DEFAULT 1,
                micro_chunks TEXT DEFAULT '[]', status TEXT DEFAULT 'active',
                energy_tag TEXT DEFAULT 'medium', recurring TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')), completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS energy_log (
                id TEXT PRIMARY KEY, timestamp TEXT DEFAULT (datetime('now')),
                spoons_remaining REAL NOT NULL, pain_level INTEGER DEFAULT 0,
                note TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS crisis_log (
                id TEXT PRIMARY KEY, timestamp TEXT DEFAULT (datetime('now')),
                crisis_type TEXT NOT NULL, triggered_by TEXT DEFAULT 'manual',
                resolved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS timer_sessions (
                id TEXT PRIMARY KEY, task_id TEXT,
                duration_minutes INTEGER NOT NULL DEFAULT 25,
                elapsed_seconds INTEGER NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'running',
                started_at TEXT DEFAULT (datetime('now')), paused_at TEXT,
                completed_at TEXT, soundscape TEXT DEFAULT '',
                body_doubling INTEGER DEFAULT 0, started_as TEXT DEFAULT 'focus'
            );
            CREATE TABLE IF NOT EXISTS habits (
                id TEXT PRIMARY KEY, title TEXT NOT NULL,
                description TEXT DEFAULT '', frequency TEXT DEFAULT 'daily',
                spoon_cost REAL DEFAULT 0.5, energy_tag TEXT DEFAULT 'low',
                grace_period INTEGER DEFAULT 3, last_completed TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS soundscape_config (
                id TEXT PRIMARY KEY, mode TEXT NOT NULL UNIQUE,
                sound_file TEXT DEFAULT '', volume REAL DEFAULT 0.5,
                loop INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS wind_down (
                id TEXT PRIMARY KEY, date TEXT NOT NULL UNIQUE,
                went_well TEXT DEFAULT '', drained TEXT DEFAULT '',
                tomorrow_one TEXT DEFAULT '', note TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS passive_log (
                id TEXT PRIMARY KEY, timestamp TEXT DEFAULT (datetime('now')),
                response TEXT NOT NULL, spoons_at_time REAL,
                current_task_id TEXT, source TEXT DEFAULT 'notification'
            );
            CREATE TABLE IF NOT EXISTS onboarding_state (
                id TEXT PRIMARY KEY DEFAULT 'current', phase INTEGER DEFAULT 0,
                turns INTEGER DEFAULT 0, extracted_profile TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS brain_dumps (
                id TEXT PRIMARY KEY, raw_text TEXT NOT NULL,
                structured_json TEXT DEFAULT '{}', source TEXT DEFAULT 'textarea',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS dopamine_menu_items (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
                energy_required REAL DEFAULT 0.5, sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS interoception_log (
                id TEXT PRIMARY KEY, signals TEXT NOT NULL,
                mood TEXT DEFAULT '', note TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sync_data (
                id TEXT PRIMARY KEY, device_id TEXT NOT NULL,
                collection TEXT NOT NULL, encrypted_blob TEXT NOT NULL,
                blob_version INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_sync_device ON sync_data(device_id, collection);
            CREATE TABLE IF NOT EXISTS admin_room_state (
                room_id TEXT PRIMARY KEY, timer_running INTEGER DEFAULT 0,
                timer_elapsed INTEGER DEFAULT 0, timer_started_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.commit()
        conn.close()

    def _seed_defaults(self) -> None:
        conn = self._conn()
        for mode, sound, vol, loop in [
            ("focus", "brown_noise.wav", 0.3, 1),
            ("grounding", "rain.wav", 0.4, 1),
            ("crisis", "breathing_tone.wav", 0.2, 1),
        ]:
            conn.execute(
                "INSERT OR IGNORE INTO soundscape_config (id, mode, sound_file, volume, loop) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), mode, sound, vol, loop),
            )
        for name, cat, energy, order in [
            ("Deep breaths (2 min)", "starters", 0.2, 1),
            ("Stretch break", "starters", 0.3, 2),
            ("Listen to a song", "starters", 0.3, 3),
            ("Podcast while cleaning", "sides", 0.5, 1),
            ("Fidget toy during meeting", "sides", 0.4, 2),
            ("Body doubling (virtual)", "sides", 0.5, 3),
            ("Walk outside", "mains", 2.0, 1),
            ("Nap or rest", "mains", 1.5, 2),
            ("Creative project", "mains", 2.5, 3),
            ("Guilty pleasure show", "desserts", 1.0, 1),
            ("Doomscroll (timered)", "desserts", 0.5, 2),
            ("Online window shopping", "desserts", 0.5, 3),
        ]:
            conn.execute(
                "INSERT OR IGNORE INTO dopamine_menu_items (id, name, category, energy_required, sort_order) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), name, cat, energy, order),
            )
        conn.commit()
        conn.close()

    # ── Daily State ──
    def get_state(self, today: str | None = None) -> dict:
        today = today or date.today().isoformat()
        c = self._conn()
        row = c.execute("SELECT * FROM daily_state WHERE date = ?", (today,)).fetchone()
        c.close()
        return self._dict(row) or {"total_spoons": 10, "remaining_spoons": 10, "pain_level": 0, "mode": "green"}

    def get_or_create_state(self, today: str) -> dict:
        return self.get_state(today)

    def upsert_state(self, today: str, data: dict) -> None:
        c = self._conn()
        existing = c.execute("SELECT id FROM daily_state WHERE date = ?", (today,)).fetchone()
        if existing:
            sets = ", ".join(f"{k} = ?" for k in data)
            vals = list(data.values()) + [today]
            c.execute(f"UPDATE daily_state SET {sets} WHERE date = ?", vals)
        else:
            keys = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            vals = list(data.values())
            c.execute(f"INSERT INTO daily_state (id, date, {keys}) VALUES (?, ?, {placeholders})", [str(uuid.uuid4()), today] + vals)
        c.commit()
        c.close()

    def set_mode(self, today: str, mode: str) -> None:
        c = self._conn()
        c.execute("UPDATE daily_state SET mode = ? WHERE date = ?", (mode, today))
        c.commit()
        c.close()

    # ── Energy Log ──
    def log_energy(self, spoons: float, pain: int = 0, note: str = "") -> str:
        lid = str(uuid.uuid4())
        c = self._conn()
        c.execute("INSERT INTO energy_log (id, spoons_remaining, pain_level, note) VALUES (?, ?, ?, ?)",
                  (lid, spoons, pain, note))
        c.commit()
        c.close()
        return lid

    def get_energy_log(self, limit: int = 30) -> list[dict]:
        c = self._conn()
        rows = c.execute("SELECT * FROM energy_log ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        c.close()
        return self._list(rows)

    def recent_energy(self, days: int = 7) -> list[dict]:
        c = self._conn()
        since = (date.today() - timedelta(days=days)).isoformat()
        rows = c.execute(
            "SELECT * FROM energy_log WHERE date(timestamp) >= ? ORDER BY timestamp", (since,)
        ).fetchall()
        c.close()
        return self._list(rows)

    def energy_patterns(self) -> dict:
        c = self._conn()
        by_hour = c.execute("""
            SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                   AVG(spoons_remaining) as avg_energy, COUNT(*) as days
            FROM energy_log GROUP BY hour ORDER BY hour
        """).fetchall()
        by_dow = c.execute("""
            SELECT CAST(strftime('%w', timestamp) AS INTEGER) as dow,
                   AVG(spoons_remaining) as avg_energy
            FROM energy_log GROUP BY dow ORDER BY dow
        """).fetchall()
        c.close()
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        best_hour = max(by_hour, key=lambda r: r['avg_energy'])['hour'] if by_hour else 12
        worst_hour = min(by_hour, key=lambda r: r['avg_energy'])['hour'] if by_hour else 3
        best_dow = days[max(by_dow, key=lambda r: r['avg_energy'])['dow']] if by_dow else 'Unknown'
        return {
            "by_hour": self._list(by_hour),
            "by_day": [{"day": days[r['dow']], "avg_energy": r['avg_energy']} for r in by_dow],
            "insight": f"Peak energy: {best_hour}:00. Low point: {worst_hour}:00. Best day: {best_dow}.",
        }

    # ── Tasks ──
    def get_tasks(self, status_filter: str | None = None) -> list[dict]:
        c = self._conn()
        if status_filter:
            rows = c.execute("SELECT * FROM tasks WHERE status = ? ORDER BY energy_tag, created_at", (status_filter,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM tasks ORDER BY energy_tag, created_at").fetchall()
        c.close()
        return self._list(rows)

    def create_task(self, data: dict) -> dict:
        tid = str(uuid.uuid4())
        c = self._conn()
        c.execute(
            "INSERT INTO tasks (id, title, description, spoon_cost, micro_chunks, energy_tag, recurring) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tid, data["title"], data.get("description", ""), data.get("spoon_cost", 1.0),
             json.dumps(data.get("micro_chunks", [])), data.get("energy_tag", "medium"), data.get("recurring", "")),
        )
        c.commit()
        c.close()
        return {"id": tid, "spoon_cost": data.get("spoon_cost", 1.0), "micro_chunks": data.get("micro_chunks", [])}

    def get_task(self, task_id: str) -> dict | None:
        c = self._conn()
        row = c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        c.close()
        return self._dict(row)

    def update_task(self, task_id: str, updates: dict) -> bool:
        c = self._conn()
        row = c.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            c.close()
            return False
        if "status" in updates and updates["status"] == "completed":
            c.execute("UPDATE tasks SET status = 'completed', completed_at = datetime('now') WHERE id = ?", (task_id,))
        for key, val in updates.items():
            if key == "micro_chunks" and val is not None:
                c.execute("UPDATE tasks SET micro_chunks = ? WHERE id = ?", (json.dumps(val), task_id))
            elif key in ("spoon_cost",):
                c.execute(f"UPDATE tasks SET {key} = ? WHERE id = ?", (val, task_id))
        c.commit()
        c.close()
        return True

    def complete_task(self, task_id: str, spoon_cost: float = 0) -> dict:
        c = self._conn()
        task = c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            c.close()
            return {"status": "error", "error": "Task not found"}
        task = dict(task)
        today = date.today().isoformat()
        state = c.execute("SELECT * FROM daily_state WHERE date = ?", (today,)).fetchone()
        cost = spoon_cost or task.get("spoon_cost", 1)
        new_remaining = 0
        if state:
            new_remaining = max(0, state["remaining_spoons"] - cost)
            c.execute("UPDATE daily_state SET remaining_spoons = ? WHERE date = ?", (new_remaining, today))
        c.execute("UPDATE tasks SET status = 'completed', completed_at = datetime('now') WHERE id = ?", (task_id,))
        c.execute("INSERT INTO energy_log (id, spoons_remaining, note) VALUES (?, ?, ?)",
                  (str(uuid.uuid4()), new_remaining if state else 0, f"Completed: {task['title']}"))
        if task.get("recurring"):
            new_id = str(uuid.uuid4())
            c.execute(
                "INSERT INTO tasks (id, title, description, spoon_cost, micro_chunks, energy_tag, recurring) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_id, task["title"], task["description"], task["spoon_cost"], task["micro_chunks"], task["energy_tag"], task["recurring"]),
            )
        c.commit()
        c.close()
        return {"status": "completed", "spoons_deducted": cost}

    def next_task(self, mode: str, remaining: float) -> dict | None:
        c = self._conn()
        if mode == "red":
            c.close()
            return None
        if mode == "amber":
            rows = c.execute(
                "SELECT * FROM tasks WHERE status = 'active' AND spoon_cost <= ? AND energy_tag IN ('low','medium') ORDER BY spoon_cost ASC, created_at ASC",
                (min(remaining, 2),),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM tasks WHERE status = 'active' AND spoon_cost <= ? ORDER BY spoon_cost DESC, created_at ASC",
                (remaining,),
            ).fetchall()
        c.close()
        return self._dict(rows[0]) if rows else None

    # ── Habits ──
    def get_habits(self, today: str) -> list[dict]:
        c = self._conn()
        rows = c.execute(
            "SELECT h.*, (h.last_completed = ?) AS done_today FROM habits h ORDER BY h.created_at", (today,)
        ).fetchall()
        c.close()
        return self._list(rows)

    def create_habit(self, data: dict) -> str:
        hid = str(uuid.uuid4())
        c = self._conn()
        c.execute(
            "INSERT INTO habits (id, title, description, frequency, spoon_cost, energy_tag) VALUES (?, ?, ?, ?, ?, ?)",
            (hid, data["title"], data.get("description", ""), data.get("frequency", "daily"),
             data.get("spoon_cost", 0.5), data.get("energy_tag", "low")),
        )
        c.commit()
        c.close()
        return hid

    def get_habit(self, hid: str) -> dict | None:
        c = self._conn()
        row = c.execute("SELECT * FROM habits WHERE id = ?", (hid,)).fetchone()
        c.close()
        return self._dict(row)

    def check_habit(self, hid: str, today: str) -> None:
        c = self._conn()
        c.execute("UPDATE habits SET last_completed = ? WHERE id = ?", (today, hid))
        c.commit()
        c.close()

    # ── Timer ──
    def stop_all_timers(self) -> None:
        c = self._conn()
        c.execute("UPDATE timer_sessions SET status = 'stopped', completed_at = datetime('now') WHERE status IN ('running','paused')")
        c.commit()
        c.close()

    def create_timer(self, data: dict) -> dict:
        tid = str(uuid.uuid4())
        c = self._conn()
        c.execute(
            "INSERT INTO timer_sessions (id, task_id, duration_minutes, soundscape, body_doubling, started_as) VALUES (?, ?, ?, ?, ?, ?)",
            (tid, data.get("task_id"), data.get("duration_minutes", 25),
             data.get("soundscape", ""), 1 if data.get("body_doubling") else 0, data.get("started_as", "focus")),
        )
        c.commit()
        c.close()
        return {"id": tid, "status": "running", "duration_minutes": data.get("duration_minutes", 25),
                "body_doubling": data.get("body_doubling", False), "started_as": data.get("started_as", "focus")}

    def get_active_timer(self) -> dict | None:
        c = self._conn()
        row = c.execute(
            "SELECT * FROM timer_sessions WHERE status IN ('running','paused') ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        c.close()
        if not row:
            return None
        r = dict(row)
        elapsed = r["elapsed_seconds"]
        if r["status"] == "running":
            try:
                elapsed += int((datetime.utcnow() - datetime.strptime(r["started_at"][:19], "%Y-%m-%d %H:%M:%S")).total_seconds())
            except ValueError:
                pass
        r["current_elapsed"] = elapsed
        return r

    def update_timer(self, tid: str, updates: dict) -> None:
        c = self._conn()
        sets = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [tid]
        c.execute(f"UPDATE timer_sessions SET {sets} WHERE id = ?", vals)
        c.commit()
        c.close()

    # ── Wind Down ──
    def get_wind_down(self, today: str) -> dict | None:
        c = self._conn()
        row = c.execute("SELECT * FROM wind_down WHERE date = ?", (today,)).fetchone()
        c.close()
        return self._dict(row)

    def upsert_wind_down(self, today: str, data: dict) -> None:
        c = self._conn()
        existing = c.execute("SELECT id FROM wind_down WHERE date = ?", (today,)).fetchone()
        if existing:
            sets = ", ".join(f"{k} = ?" for k in data)
            vals = list(data.values()) + [today]
            c.execute(f"UPDATE wind_down SET {sets} WHERE date = ?", vals)
        else:
            keys = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            vals = [str(uuid.uuid4()), today] + list(data.values())
            c.execute(f"INSERT INTO wind_down (id, date, {keys}) VALUES (?, ?, {placeholders})", vals)
        c.commit()
        c.close()

    def week_wind_down(self, week_ago: str) -> list[dict]:
        c = self._conn()
        rows = c.execute("SELECT * FROM wind_down WHERE date >= ? ORDER BY date DESC", (week_ago,)).fetchall()
        c.close()
        return self._list(rows)

    # ── Crisis ──
    def activate_crisis(self, crisis_type: str = "sensory_overload") -> str:
        cid = str(uuid.uuid4())
        c = self._conn()
        c.execute("INSERT INTO crisis_log (id, crisis_type) VALUES (?, ?)", (cid, crisis_type))
        c.commit()
        c.close()
        return cid

    def resolve_crisis(self) -> bool:
        c = self._conn()
        row = c.execute("SELECT id FROM crisis_log WHERE resolved_at IS NULL ORDER BY timestamp DESC LIMIT 1").fetchone()
        if row:
            c.execute("UPDATE crisis_log SET resolved_at = datetime('now') WHERE id = ?", (row["id"],))
            c.commit()
            c.close()
            return True
        c.close()
        return False

    def get_crises_since(self, since: str) -> list[dict]:
        c = self._conn()
        rows = c.execute(
            "SELECT * FROM crisis_log WHERE date(timestamp) >= ? ORDER BY timestamp DESC", (since,)
        ).fetchall()
        c.close()
        return self._list(rows)

    # ── Brain Dump ──
    def save_brain_dump(self, text: str, structured: dict, source: str = "textarea") -> str:
        bid = str(uuid.uuid4())
        c = self._conn()
        c.execute("INSERT INTO brain_dumps (id, raw_text, structured_json, source) VALUES (?, ?, ?, ?)",
                  (bid, text, json.dumps(structured), source))
        c.commit()
        c.close()
        return bid

    def search_brain_dumps(self, q: str) -> list[dict]:
        c = self._conn()
        rows = c.execute(
            "SELECT * FROM brain_dumps WHERE raw_text LIKE ? OR structured_json LIKE ? ORDER BY created_at DESC LIMIT 10",
            (f"%{q}%", f"%{q}%"),
        ).fetchall()
        c.close()
        return self._list(rows)

    def list_brain_dumps(self, limit: int = 20) -> list[dict]:
        c = self._conn()
        rows = c.execute(
            "SELECT * FROM brain_dumps WHERE created_at >= datetime('now', '-30 days') ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        c.close()
        return self._list(rows)

    # ── Dopamine Menu ──
    def get_dopamine_menu(self) -> dict[str, list[dict]]:
        c = self._conn()
        items = c.execute("SELECT * FROM dopamine_menu_items ORDER BY sort_order").fetchall()
        c.close()
        menu = {"starters": [], "sides": [], "mains": [], "desserts": []}
        for item in items:
            d = dict(item)
            cat = d.pop("category")
            if cat in menu:
                menu[cat].append(d)
        return menu

    def add_dopamine_item(self, data: dict) -> None:
        c = self._conn()
        c.execute(
            "INSERT INTO dopamine_menu_items (id, name, category, energy_required, sort_order) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), data["name"], data["category"], data.get("energy_required", 0.5), data.get("sort_order", 99)),
        )
        c.commit()
        c.close()

    def delete_dopamine_item(self, item_id: str) -> None:
        c = self._conn()
        c.execute("DELETE FROM dopamine_menu_items WHERE id = ?", (item_id,))
        c.commit()
        c.close()

    # ── Interoception ──
    def log_interoception(self, signals: list, mood: str = "", note: str = "") -> None:
        c = self._conn()
        c.execute("INSERT INTO interoception_log (id, signals, mood, note) VALUES (?, ?, ?, ?)",
                  (str(uuid.uuid4()), json.dumps(signals), mood, note))
        c.commit()
        c.close()

    def get_interoception(self, limit: int = 20) -> list[dict]:
        c = self._conn()
        rows = c.execute("SELECT * FROM interoception_log ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        c.close()
        return self._list(rows)

    # ── Passive Log ──
    def get_today_passive_log(self) -> list[dict]:
        c = self._conn()
        rows = c.execute(
            "SELECT id, timestamp, response, spoons_at_time, current_task_id, source "
            "FROM passive_log WHERE date(timestamp) = date('now') ORDER BY timestamp"
        ).fetchall()
        c.close()
        return self._list(rows)

    def submit_passive_log(self, response: str, spoons_at_time: float | None = None,
                           current_task_id: str | None = None, source: str = "notification") -> str:
        lid = str(uuid.uuid4())
        c = self._conn()
        c.execute(
            "INSERT INTO passive_log (id, response, spoons_at_time, current_task_id, source) VALUES (?, ?, ?, ?, ?)",
            (lid, response, spoons_at_time, current_task_id, source),
        )
        c.commit()
        c.close()
        return lid

    def last_passive_log_today(self) -> dict | None:
        c = self._conn()
        row = c.execute(
            "SELECT timestamp FROM passive_log WHERE date(timestamp) = date('now') ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        c.close()
        return self._dict(row)

    # ── Onboarding ──
    def get_onboarding(self) -> dict | None:
        c = self._conn()
        row = c.execute("SELECT * FROM onboarding_state WHERE id = 'current'").fetchone()
        c.close()
        return self._dict(row)

    def save_onboarding(self, phase: int, turns: int, profile: dict) -> None:
        c = self._conn()
        c.execute(
            "INSERT OR REPLACE INTO onboarding_state (id, phase, turns, extracted_profile, updated_at) "
            "VALUES ('current', ?, ?, ?, datetime('now'))",
            (phase, turns, json.dumps(profile)),
        )
        c.commit()
        c.close()

    # ── Templates / Export ──
    def export_all(self) -> dict[str, list[dict]]:
        c = self._conn()
        data = {}
        for table in ["daily_state", "tasks", "energy_log", "crisis_log", "timer_sessions", "habits", "wind_down"]:
            rows = c.execute(f"SELECT * FROM {table}").fetchall()
            data[table] = self._list(rows)
        c.close()
        return data

    def import_rows(self, table: str, rows: list[dict]) -> int:
        c = self._conn()
        count = 0
        for row in rows:
            cols = ", ".join(row.keys())
            placeholders = ", ".join("?" for _ in row)
            try:
                c.execute(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})", list(row.values()))
                count += 1
            except Exception:
                pass
        c.commit()
        c.close()
        return count

    def get_template(self, type: str) -> dict:
        c = self._conn()
        if type == "dopamine_menu":
            rows = c.execute("SELECT name, category, energy_required FROM dopamine_menu_items ORDER BY sort_order").fetchall()
            c.close()
            return {"type": type, "items": self._list(rows)}
        elif type == "pacing_config":
            rows = c.execute("SELECT mode, sound_file, volume FROM soundscape_config ORDER BY mode").fetchall()
            c.close()
            return {"type": type, "soundscapes": self._list(rows)}
        c.close()
        return {"type": type, "error": "Unknown template type"}

    def import_template_items(self, type: str, items: list[dict]) -> int:
        c = self._conn()
        count = 0
        if type == "dopamine_menu":
            for item in items:
                c.execute(
                    "INSERT OR IGNORE INTO dopamine_menu_items (id, name, category, energy_required) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), item["name"], item["category"], item.get("energy_required", 0.5)),
                )
                count += 1
        c.commit()
        c.close()
        return count

    # ── Sync ──
    def sync_upload(self, device_id: str, collection: str, encrypted_blob: str, version: int = 1) -> None:
        c = self._conn()
        c.execute(
            "INSERT INTO sync_data (id, device_id, collection, encrypted_blob, blob_version) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), device_id, collection, encrypted_blob, version),
        )
        c.commit()
        c.close()

    def sync_download(self, device_id: str, collection: str, since: str = "") -> list[dict]:
        c = self._conn()
        if since:
            rows = c.execute(
                "SELECT * FROM sync_data WHERE device_id = ? AND collection = ? AND created_at > ? ORDER BY created_at",
                (device_id, collection, since),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM sync_data WHERE device_id = ? AND collection = ? ORDER BY created_at DESC LIMIT 100",
                (device_id, collection),
            ).fetchall()
        c.close()
        return self._list(rows)

    # ── Review ──
    def weekly_review(self, week_ago: str, today: str) -> dict:
        c = self._conn()
        energy_states = c.execute("SELECT * FROM daily_state WHERE date >= ? AND date <= ? ORDER BY date", (week_ago, today)).fetchall()
        completed = c.execute("SELECT * FROM tasks WHERE completed_at IS NOT NULL AND date(completed_at) >= ? ORDER BY completed_at DESC", (week_ago,)).fetchall()
        energy_entries = c.execute("SELECT * FROM energy_log WHERE date(timestamp) >= ? ORDER BY timestamp", (week_ago,)).fetchall()
        timer_sessions = c.execute("SELECT * FROM timer_sessions WHERE date(started_at) >= ? ORDER BY started_at", (week_ago,)).fetchall()
        crises = c.execute("SELECT * FROM crisis_log WHERE date(timestamp) >= ? ORDER BY timestamp DESC", (week_ago,)).fetchall()
        habits = c.execute("SELECT title FROM habits ORDER BY created_at").fetchall()
        wind_entries = c.execute("SELECT * FROM wind_down WHERE date >= ? ORDER BY date DESC", (week_ago,)).fetchall()
        c.close()

        avg_spoons = 0
        avg_pain = 0
        if energy_states:
            avg_spoons = sum(float(s["total_spoons"]) for s in energy_states) / len(energy_states)
            avg_pain = sum(s["pain_level"] for s in energy_states) / len(energy_states)

        total_focus_minutes = 0
        for ts in timer_sessions:
            if ts["status"] in ("completed", "stopped"):
                total_focus_minutes += ts["elapsed_seconds"] // 60

        return {
            "energy_states": self._list(energy_states),
            "completed_tasks": self._list(completed),
            "energy_entries": self._list(energy_entries),
            "timer_sessions": self._list(timer_sessions),
            "crises": self._list(crises),
            "habits": self._list(habits),
            "wind_down_entries": self._list(wind_entries),
            "insights": {
                "days_tracked": len(energy_states),
                "avg_spoons": round(avg_spoons, 1),
                "avg_pain": round(avg_pain, 1),
                "tasks_completed": len(completed),
                "total_focus_minutes": total_focus_minutes,
                "crisis_count": len(crises),
            },
        }

    def review_insight(self, week_ago: str) -> dict:
        c = self._conn()
        energy_states = c.execute(
            "SELECT * FROM daily_state WHERE date >= ? ORDER BY date", (week_ago,)
        ).fetchall()
        completed_tasks = c.execute(
            "SELECT title, energy_tag, spoon_cost FROM tasks WHERE completed_at IS NOT NULL AND date(completed_at) >= ?", (week_ago,)
        ).fetchall()
        wind_entries = c.execute(
            "SELECT * FROM wind_down WHERE date >= ? ORDER BY date", (week_ago,)
        ).fetchall()
        crises = c.execute(
            "SELECT date(timestamp) as d FROM crisis_log WHERE date(timestamp) >= ? ORDER BY timestamp", (week_ago,)
        ).fetchall()
        c.close()

        days_with_data = len(energy_states)
        total_tasks = len(completed_tasks)
        total_crises = len(crises)
        high_spoon_tasks = sum(1 for t in completed_tasks if t["energy_tag"] == "high")

        lines = []
        if days_with_data < 2:
            lines.append("Not enough data yet - check in daily to see patterns emerge.")
        else:
            lines.append(f"**{days_with_data} days** tracked this week.")
            if total_tasks > 0:
                lines.append(f"Completed **{total_tasks} tasks** ({high_spoon_tasks} high-energy).")
            else:
                lines.append("No tasks completed this week - that's okay. Some weeks are for rest.")
            if total_crises > 0:
                lines.append(f"Crisis mode activated **{total_crises} time(s)** this week.")
            if energy_states:
                best_day = max(energy_states, key=lambda s: s["remaining_spoons"])
                lines.append(f"Highest energy day: **{best_day['date']}** ({best_day['remaining_spoons']}/{best_day['total_spoons']} spoons).")
                worst_day = min(energy_states, key=lambda s: s["remaining_spoons"])
                if worst_day["remaining_spoons"] < best_day["remaining_spoons"]:
                    lines.append(f"Lowest energy day: **{worst_day['date']}** ({worst_day['remaining_spoons']}/{worst_day['total_spoons']} spoons).")
            if wind_entries:
                themes = []
                for e in wind_entries:
                    if e["went_well"]:
                        themes.append(e["went_well"].split(".")[0])
                if themes:
                    lines.append(f"Recurring themes: {'; '.join(themes[:3])}.")
        return {"insight": "\n".join(lines)}

    # ── Soundscapes (SqliteStore) ──
    def get_soundscape_configs(self) -> list[dict]:
        c = self._conn()
        rows = c.execute("SELECT mode, sound_file, volume, loop FROM soundscape_config ORDER BY mode").fetchall()
        c.close()
        return [dict(r) for r in rows]

    def update_soundscape_config(self, mode: str, updates: dict) -> None:
        c = self._conn()
        if updates:
            sets, vals = [], []
            for key, col in [("sound_file", "sound_file"), ("volume", "volume"), ("loop", "loop")]:
                if key in updates:
                    sets.append(f"{col} = ?")
                    v = updates[key]
                    if key == "volume":
                        v = max(0, min(1, v))
                    elif key == "loop":
                        v = 1 if v else 0
                    vals.append(v)
            if sets:
                vals.append(mode)
                c.execute(f"UPDATE soundscape_config SET {', '.join(sets)} WHERE mode = ?", vals)
                c.connection.commit()
        c.close()

    def list_sound_files(self) -> list[str]:
        from backend.config import SOUNDSCAPES_DIR
        if SOUNDSCAPES_DIR.exists():
            return sorted([f.name for f in SOUNDSCAPES_DIR.iterdir() if f.suffix in (".wav", ".ogg", ".mp3", ".flac")])
        return []
