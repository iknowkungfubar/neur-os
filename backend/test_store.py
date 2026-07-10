"""Tests for SqliteStore -- the real SQLite persistence layer."""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.store import SqliteStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_store() -> SqliteStore:
    """Return a SqliteStore backed by a temporary file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    store = SqliteStore(tmp.name)
    store.init_schema()
    return store, tmp.name


def cleanup(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Daily State
# ---------------------------------------------------------------------------

class TestDailyState:
    """CRUD for the daily_state table -- the core energy tracking state."""

    def test_get_state_returns_defaults_when_empty(self):
        store, path = make_store()
        try:
            state = store.get_state("2026-07-10")
            assert state["total_spoons"] == 10
            assert state["remaining_spoons"] == 10
            assert state["pain_level"] == 0
            assert state["mode"] == "green"
        finally:
            cleanup(path)

    def test_upsert_and_get_state(self):
        store, path = make_store()
        try:
            store.upsert_state("2026-07-10", {
                "total_spoons": 8,
                "remaining_spoons": 5,
                "pain_level": 2,
                "mode": "amber",
            })
            state = store.get_state("2026-07-10")
            assert state["total_spoons"] == 8
            assert state["remaining_spoons"] == 5
            assert state["pain_level"] == 2
            assert state["mode"] == "amber"
        finally:
            cleanup(path)

    def test_upsert_updates_existing(self):
        store, path = make_store()
        try:
            store.upsert_state("2026-07-10", {"remaining_spoons": 10})
            store.upsert_state("2026-07-10", {"remaining_spoons": 3, "pain_level": 1})
            state = store.get_state("2026-07-10")
            assert state["remaining_spoons"] == 3
            assert state["pain_level"] == 1
        finally:
            cleanup(path)

    def test_set_mode_updates_state(self):
        store, path = make_store()
        try:
            store.upsert_state("2026-07-10", {"remaining_spoons": 10})
            store.set_mode("2026-07-10", "red")
            state = store.get_state("2026-07-10")
            assert state["mode"] == "red"
        finally:
            cleanup(path)

    def test_different_dates_independent(self):
        store, path = make_store()
        try:
            store.upsert_state("2026-07-10", {"remaining_spoons": 3})
            store.upsert_state("2026-07-11", {"remaining_spoons": 8})
            assert store.get_state("2026-07-10")["remaining_spoons"] == 3
            assert store.get_state("2026-07-11")["remaining_spoons"] == 8
        finally:
            cleanup(path)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class TestTasks:
    """CRUD for the tasks table."""

    def test_create_and_get_task(self):
        store, path = make_store()
        try:
            result = store.create_task({
                "title": "Write tests",
                "description": "Cover SqliteStore",
                "spoon_cost": 2.0,
                "energy_tag": "medium",
            })
            assert result["id"] is not None
            assert result["spoon_cost"] == 2.0

            task = store.get_task(result["id"])
            assert task is not None
            assert task["title"] == "Write tests"
            assert task["spoon_cost"] == 2.0
        finally:
            cleanup(path)

    def test_create_task_with_micro_chunks(self):
        store, path = make_store()
        try:
            chunks = ["setup", "write", "verify"]
            result = store.create_task({
                "title": "Multi-step task",
                "micro_chunks": chunks,
                "energy_tag": "high",
            })
            task = store.get_task(result["id"])
            assert task is not None
            import json
            assert json.loads(task["micro_chunks"]) == chunks
        finally:
            cleanup(path)

    def test_get_tasks_returns_all(self):
        store, path = make_store()
        try:
            store.create_task({"title": "A", "energy_tag": "low"})
            store.create_task({"title": "B", "energy_tag": "high"})
            tasks = store.get_tasks()
            assert len(tasks) >= 2
        finally:
            cleanup(path)

    def test_get_tasks_filters_by_status(self):
        store, path = make_store()
        try:
            store.create_task({"title": "Active task", "energy_tag": "low"})
            active = store.get_tasks("active")
            assert len(active) >= 1
            completed = store.get_tasks("completed")
            # No completed tasks yet
            assert len(completed) == 0
        finally:
            cleanup(path)

    def test_complete_task_deducts_spoons(self):
        store, path = make_store()
        try:
            today = date.today().isoformat()
            store.upsert_state(today, {"remaining_spoons": 10})
            result = store.create_task({
                "title": "Expensive task",
                "spoon_cost": 4.0,
                "energy_tag": "high",
            })
            task_id = result["id"]
            outcome = store.complete_task(task_id, spoon_cost=4.0)
            assert outcome["status"] == "completed"
            assert outcome["spoons_deducted"] == 4.0

            task = store.get_task(task_id)
            assert task["status"] == "completed"

            state = store.get_state(today)
            assert state["remaining_spoons"] == 6.0
        finally:
            cleanup(path)

    def test_complete_nonexistent_task(self):
        store, path = make_store()
        try:
            outcome = store.complete_task("no-such-id")
            assert outcome["status"] == "error"
        finally:
            cleanup(path)

    def test_next_task_green_mode(self):
        store, path = make_store()
        try:
            store.create_task({"title": "Big task", "spoon_cost": 8.0, "energy_tag": "high"})
            store.create_task({"title": "Small task", "spoon_cost": 1.0, "energy_tag": "low"})
            next_t = store.next_task("green", 5.0)
            assert next_t is not None
            # Green mode returns highest-cost task within budget
            assert next_t["spoon_cost"] <= 5.0
        finally:
            cleanup(path)

    def test_next_task_red_mode_returns_none(self):
        store, path = make_store()
        try:
            store.create_task({"title": "Any", "spoon_cost": 1.0, "energy_tag": "low"})
            assert store.next_task("red", 10.0) is None
        finally:
            cleanup(path)


# ---------------------------------------------------------------------------
# Energy Log
# ---------------------------------------------------------------------------

class TestEnergyLog:
    """Energy log CRUD and queries."""

    def test_log_and_get_energy(self):
        store, path = make_store()
        try:
            lid = store.log_energy(7.5, pain=2, note="Feeling ok")
            assert lid is not None

            logs = store.get_energy_log(limit=10)
            assert len(logs) >= 1
            newest = logs[0]
            assert newest["spoons_remaining"] == 7.5
            assert newest["pain_level"] == 2
        finally:
            cleanup(path)

    def test_get_energy_log_respects_limit(self):
        store, path = make_store()
        try:
            for i in range(5):
                store.log_energy(float(i))
            logs = store.get_energy_log(limit=3)
            assert len(logs) == 3
        finally:
            cleanup(path)

    def test_recent_energy_filters_by_days(self):
        store, path = make_store()
        try:
            store.log_energy(5.0)
            recent = store.recent_energy(days=7)
            assert len(recent) >= 1
        finally:
            cleanup(path)

    def test_energy_patterns_returns_structure(self):
        store, path = make_store()
        try:
            store.log_energy(5.0)
            store.log_energy(3.0)
            patterns = store.energy_patterns()
            assert "by_hour" in patterns
            assert "by_day" in patterns
            assert "insight" in patterns
        finally:
            cleanup(path)


# ---------------------------------------------------------------------------
# Habits
# ---------------------------------------------------------------------------

class TestHabits:
    """Habit CRUD."""

    def test_create_and_get_habit(self):
        store, path = make_store()
        try:
            hid = store.create_habit({
                "title": "Morning stretch",
                "description": "5 min",
                "frequency": "daily",
                "spoon_cost": 0.5,
                "energy_tag": "low",
            })
            habit = store.get_habit(hid)
            assert habit is not None
            assert habit["title"] == "Morning stretch"
        finally:
            cleanup(path)

    def test_check_habit_updates_last_completed(self):
        store, path = make_store()
        try:
            hid = store.create_habit({"title": "Drink water", "frequency": "daily"})
            today = "2026-07-10"
            store.check_habit(hid, today)
            habit = store.get_habit(hid)
            assert habit["last_completed"] == today
        finally:
            cleanup(path)

    def test_get_habits_includes_done_today_flag(self):
        store, path = make_store()
        try:
            hid = store.create_habit({"title": "Meditate", "frequency": "daily"})
            today = date.today().isoformat()
            habits = store.get_habits(today)
            assert len(habits) >= 1
            # check habit, then verify done_today changes
            store.check_habit(hid, today)
            habits = store.get_habits(today)
            target = [h for h in habits if h["id"] == hid]
            assert len(target) == 1
            # done_today is 1 (SQLite bool/INT)
            assert target[0]["done_today"] == 1
        finally:
            cleanup(path)


# ---------------------------------------------------------------------------
# Timer
# ---------------------------------------------------------------------------

class TestTimer:
    """Timer session management."""

    def test_create_and_get_active_timer(self):
        store, path = make_store()
        try:
            result = store.create_timer({
                "duration_minutes": 25,
                "started_as": "focus",
            })
            assert result["id"] is not None
            assert result["status"] == "running"

            active = store.get_active_timer()
            assert active is not None
            assert active["status"] == "running"
        finally:
            cleanup(path)

    def test_stop_all_timers(self):
        store, path = make_store()
        try:
            store.create_timer({"duration_minutes": 10})
            store.stop_all_timers()
            assert store.get_active_timer() is None
        finally:
            cleanup(path)

    def test_update_timer(self):
        store, path = make_store()
        try:
            result = store.create_timer({"duration_minutes": 25})
            tid = result["id"]
            store.update_timer(tid, {"elapsed_seconds": 120})
            timer = store.get_active_timer()
            assert timer is not None
            assert timer["elapsed_seconds"] >= 120
        finally:
            cleanup(path)


# ---------------------------------------------------------------------------
# Crisis
# ---------------------------------------------------------------------------

class TestCrisis:
    """Crisis log operations."""

    def test_activate_and_resolve_crisis(self):
        store, path = make_store()
        try:
            cid = store.activate_crisis("sensory_overload")
            assert cid is not None
            resolved = store.resolve_crisis()
            assert resolved is True
            # resolving again when none open returns False
            assert store.resolve_crisis() is False
        finally:
            cleanup(path)

    def test_get_crises_since(self):
        store, path = make_store()
        try:
            store.activate_crisis("meltdown")
            crises = store.get_crises_since("2026-01-01")
            assert len(crises) >= 1
            assert crises[0]["crisis_type"] == "meltdown"
        finally:
            cleanup(path)


# ---------------------------------------------------------------------------
# Brain Dump
# ---------------------------------------------------------------------------

class TestBrainDump:
    """Brain dump persistence."""

    def test_save_and_search_brain_dump(self):
        store, path = make_store()
        try:
            bid = store.save_brain_dump(
                "I feel overwhelmed with my project deadline",
                {"tasks": ["finish report"], "mood": "anxious"},
                source="textarea",
            )
            assert bid is not None
            dumps = store.list_brain_dumps(limit=5)
            assert len(dumps) >= 1
            assert dumps[0]["raw_text"] == "I feel overwhelmed with my project deadline"
        finally:
            cleanup(path)

    def test_search_brain_dumps(self):
        store, path = make_store()
        try:
            store.save_brain_dump("Need to finish the report", {}, source="voice")
            results = store.search_brain_dumps("report")
            assert len(results) >= 1
        finally:
            cleanup(path)


# ---------------------------------------------------------------------------
# Wind Down
# ---------------------------------------------------------------------------

class TestWindDown:
    """Wind-down journal operations."""

    def test_upsert_and_get_wind_down(self):
        store, path = make_store()
        try:
            store.upsert_wind_down("2026-07-10", {
                "went_well": "Finished tests",
                "drained": "Morning meeting",
                "tomorrow_one": "Start early",
            })
            entry = store.get_wind_down("2026-07-10")
            assert entry is not None
            assert entry["went_well"] == "Finished tests"
        finally:
            cleanup(path)

    def test_upsert_updates_wind_down(self):
        store, path = make_store()
        try:
            store.upsert_wind_down("2026-07-10", {"went_well": "First pass"})
            store.upsert_wind_down("2026-07-10", {"went_well": "Updated", "note": "Better"})
            entry = store.get_wind_down("2026-07-10")
            assert entry["went_well"] == "Updated"
            assert entry["note"] == "Better"
        finally:
            cleanup(path)

    def test_week_wind_down_returns_recent(self):
        store, path = make_store()
        try:
            store.upsert_wind_down("2026-07-10", {"went_well": "Good day"})
            week_ago = (date(2026, 7, 10) - timedelta(days=7)).isoformat()
            entries = store.week_wind_down(week_ago)
            assert len(entries) >= 1
        finally:
            cleanup(path)


# ---------------------------------------------------------------------------
# Passive Log
# ---------------------------------------------------------------------------

class TestPassiveLog:
    """Passive prompt logging."""

    def test_submit_and_get_today(self):
        store, path = make_store()
        try:
            pid = store.submit_passive_log("Taking a break", spoons_at_time=5.0)
            assert pid is not None
            logs = store.get_today_passive_log()
            assert len(logs) >= 1
            assert logs[0]["response"] == "Taking a break"
        finally:
            cleanup(path)

    def test_last_passive_log_returns_most_recent(self):
        store, path = make_store()
        try:
            store.submit_passive_log("First")
            store.submit_passive_log("Second")
            last = store.last_passive_log_today()
            assert last is not None
            assert "timestamp" in last  # method only returns timestamp column
        finally:
            cleanup(path)


# ---------------------------------------------------------------------------
# Interoception
# ---------------------------------------------------------------------------

class TestInteroception:
    """Interoception check-in logging."""

    def test_log_and_get_interoception(self):
        store, path = make_store()
        try:
            store.log_interoception(
                ["tense shoulders", "racing heart"],
                mood="anxious",
                note="Before meeting",
            )
            entries = store.get_interoception(limit=5)
            assert len(entries) >= 1
            assert "tense shoulders" in entries[0]["signals"]
        finally:
            cleanup(path)


# ---------------------------------------------------------------------------
# Soundscapes
# ---------------------------------------------------------------------------

class TestSoundscapes:
    """Soundscape configuration."""

    def _seed_soundscapes(self, store: SqliteStore) -> None:
        """Seed default soundscape configs like _seed_defaults would."""
        import uuid
        c = store._conn()
        for mode, sound, vol, loop in [
            ("focus", "brown_noise.wav", 0.3, 1),
            ("grounding", "rain.wav", 0.4, 1),
            ("crisis", "breathing_tone.wav", 0.2, 1),
        ]:
            c.execute(
                "INSERT OR IGNORE INTO soundscape_config (id, mode, sound_file, volume, loop) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), mode, sound, vol, loop),
            )
        c.commit()
        c.close()

    def test_get_soundscape_configs(self):
        store, path = make_store()
        try:
            self._seed_soundscapes(store)
            configs = store.get_soundscape_configs()
            assert len(configs) >= 3  # focus, grounding, crisis
            modes = [c["mode"] for c in configs]
            assert "focus" in modes
        finally:
            cleanup(path)

    def test_update_soundscape_config(self):
        store, path = make_store()
        try:
            self._seed_soundscapes(store)
            store.update_soundscape_config("focus", {"volume": 0.8})
            configs = store.get_soundscape_configs()
            focus = [c for c in configs if c["mode"] == "focus"][0]
            assert focus["volume"] == 0.8
        finally:
            cleanup(path)
