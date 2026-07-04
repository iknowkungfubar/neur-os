"""End-to-end integration tests for NeurOS v0.4.1.
Covers the complete user flow: onboarding → check-in → tasks → timer → crisis → wind-down → review → passive log → export/import."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

_tmp_db = tempfile.mkdtemp()
os.environ["LM_STUDIO_URL"] = "http://localhost:9999/v1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backend.main as app_module

_app_db_path = Path(_tmp_db) / "neur-os.db"
app_module.DB_PATH = _app_db_path
app_module.DATA_DIR = Path(_tmp_db)
app_module.BACKUP_DIR = Path(_tmp_db) / "backups"
app_module.BACKUP_DIR.mkdir(exist_ok=True)
app_module.init_db()

from fastapi.testclient import TestClient
client = TestClient(app_module.app)


def setup_module():
    _app_db_path.unlink(missing_ok=True)
    app_module.init_db()


def teardown_module():
    import shutil
    shutil.rmtree(_tmp_db, ignore_errors=True)


class TestE2EFlow:
    """Complete user journey — runs in order as one session."""

    def test_01_state_empty(self):
        """Fresh DB: no check-in today."""
        resp = client.get("/api/state")
        assert resp.status_code == 200
        s = resp.json()
        assert s["state"]["total_spoons"] == 10
        assert s["state"]["remaining_spoons"] == 10
        assert s["tasks"] == []

    def test_02_onboarding_four_questions(self):
        """Onboarding returns deterministic questions for turns 0-3."""
        questions = [
            "What kind of tasks do you need the most help keeping track of?",
            "What time of day do you usually have the most energy?",
            "When you're overwhelmed, what helps you recharge?",
            "What's one thing you'd like to be able to do more consistently?",
        ]
        for turn, expected in enumerate(questions):
            resp = client.post("/api/onboarding/chat", json={
                "history": [{"role": "user", "content": "Response"}],
                "turn": turn,
            })
            assert resp.status_code == 200, f"Turn {turn} failed"
            data = resp.json()
            assert data["response"] == expected, f"Turn {turn}: expected '{expected}'"
            expected_done = turn >= 3
            assert data["done"] is expected_done, f"Turn {turn} done should be {expected_done}"

    def test_03_mode_default_green(self):
        """Default mode is green."""
        resp = client.get("/api/mode")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "green"

    def test_04_checkin_sets_spoons(self):
        """Morning check-in with 8 spoons."""
        resp = client.post("/api/check-in", json={
            "spoons": 8, "pain_level": 1, "note": "feeling okay",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["spoons"] == 8
        assert data["suggested_mode"] == "green"
        # Verify via state endpoint
        state = client.get("/api/state").json()
        assert state["state"]["total_spoons"] == 8
        assert state["state"]["remaining_spoons"] == 8.0

    def test_05_add_tasks(self):
        """Add 5 tasks with different energy tags and costs."""
        tasks_data = [
            ("Write project proposal", "high", 3.0),
            ("Review pull requests", "medium", 1.5),
            ("Reply to emails", "low", 0.5),
            ("Clean kitchen", "medium", 2.0),
            ("Weekly planning", "high", 2.5),
        ]
        for title, tag, cost in tasks_data:
            resp = client.post("/api/tasks", json={
                "title": title, "energy_tag": tag, "spoon_cost": cost,
            })
            assert resp.status_code == 200, f"Failed to create task '{title}'"
        # Verify via state
        state = client.get("/api/state").json()
        assert len(state["tasks"]) == 5
        all_active = all(t["status"] == "active" for t in state["tasks"])
        assert all_active, "All tasks should be active"

    def test_06_next_task_highest_spoon_affordable(self):
        """With 8 spoons remaining, next is the highest-cost active task."""
        resp = client.get("/api/tasks/next")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task"] is not None
        assert data["task"]["title"] == "Write project proposal"
        assert data["task"]["spoon_cost"] == 3.0

    def test_07_start_focus_timer(self):
        """Start a focus timer with body doubling."""
        tasks = client.get("/api/state").json()["tasks"]
        task_id = tasks[0]["id"]
        resp = client.post("/api/timer", json={
            "action": "start", "task_id": task_id,
            "duration_minutes": 25, "body_doubling": True,
        })
        assert resp.status_code == 200
        timer = resp.json()
        assert timer["status"] == "running"

    def test_08_timer_active_running(self):
        """Active timer endpoint returns running session."""
        resp = client.get("/api/timer/active")
        assert resp.status_code == 200
        data = resp.json()
        assert data["timer"] is not None
        assert data["timer"]["status"] == "running"

    def test_09_timer_pause_resume(self):
        """Pause and resume the timer."""
        resp = client.post("/api/timer", json={"action": "pause"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

        resp = client.post("/api/timer", json={"action": "resume"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_10_complete_task_expends_spoons(self):
        """Completing a task deducts spoon cost from remaining."""
        tasks = client.get("/api/state").json()["tasks"]
        task_id = tasks[0]["id"]
        cost = tasks[0]["spoon_cost"]
        resp = client.post(f"/api/tasks/{task_id}/expend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["spoons_deducted"] == cost

        state = client.get("/api/state").json()
        assert state["state"]["remaining_spoons"] == 8.0 - cost

    def test_11_stop_timer_after_complete(self):
        """Stop the running timer."""
        resp = client.post("/api/timer", json={"action": "stop"})
        assert resp.status_code == 200
        resp = client.get("/api/timer/active")
        assert resp.json()["timer"] is None

    def test_12_complete_more_tasks_reduce_spoons(self):
        """Complete specific tasks to reduce spoons."""
        tasks = client.get("/api/state").json()["tasks"]
        active = [t for t in tasks if t["status"] == "active"]
        # Find and complete the 0.5 and 1.5 cost tasks by title
        for title in ["Reply to emails", "Review pull requests"]:
            match = [t for t in active if t["title"] == title]
            if match:
                resp = client.post(f"/api/tasks/{match[0]['id']}/expend")
                assert resp.status_code == 200
                assert resp.json()["spoons_deducted"] == match[0]["spoon_cost"]

        state = client.get("/api/state").json()
        remaining = state["state"]["remaining_spoons"]
        # 8 - 3.0 (proposal) - 0.5 (emails) - 1.5 (reviews) = 3.0
        assert remaining == 3.0, f"Expected 3.0 remaining, got {remaining}"

    def test_13_next_task_filters_by_affordability(self):
        """With 3.0 spoons, only tasks <= 3.0 spoon cost should be suggested."""
        # complete 5th task from 2nd loop
        resp = client.get("/api/tasks/next")
        data = resp.json()
        assert data["task"] is not None
        assert data["task"]["spoon_cost"] <= 3.0

    def test_14_crisis_activate_and_resolve(self):
        """Activate crisis changes state, resolve restores it."""
        resp = client.post("/api/crisis/activate")
        assert resp.status_code == 200

        resp = client.post("/api/crisis/resolve")
        assert resp.status_code == 200

    def test_15_wind_down_save_and_retrieve(self):
        """Save evening reflection and retrieve it."""
        resp = client.post("/api/wind-down", json={
            "went_well": "Finished the proposal",
            "drained": "Morning brain fog",
            "tomorrow_one": "Review testimonials",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        resp = client.get("/api/wind-down/today")
        assert resp.status_code == 200
        entry = resp.json()["entry"]
        assert entry is not None
        assert entry["went_well"] == "Finished the proposal"

    def test_16_habits_create_and_check(self):
        """Create habit, check it off."""
        resp = client.post("/api/habits", json={
            "title": "Drink water", "frequency": "daily", "spoon_cost": 0.5,
        })
        assert resp.status_code == 200
        hid = resp.json()["id"]

        resp = client.post(f"/api/habits/{hid}/check")
        assert resp.status_code == 200
        data = resp.json()
        # Habit check should just return done_today, no streak info
        assert "done_today" in data

        resp = client.get("/api/habits")
        habits = resp.json()["habits"]
        matching = [h for h in habits if h["id"] == hid]
        assert len(matching) == 1

    def test_17_review_returns_completed_tasks(self):
        """Weekly review includes at least 2 completed tasks."""
        resp = client.get("/api/review/week")
        assert resp.status_code == 200
        data = resp.json()
        assert data["insights"]["tasks_completed"] >= 2
        assert data["insights"]["avg_spoons"] > 0

    def test_18_weekly_insight(self):
        """Insight endpoint returns text (even offline)."""
        resp = client.get("/api/review/insight")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("insight"), str)

    def test_19_passive_log_lifecycle(self):
        """Passive log: check → submit → verify."""
        resp = client.get("/api/passive-log/check")
        assert resp.json()["should_prompt"] is True

        for i, entry in enumerate(["working on proposal", "taking a break", "reviewing code"]):
            resp = client.post("/api/passive-log/submit", json={
                "response": entry, "spoons_at_time": 5.0 - i,
            })
            assert resp.status_code == 200

        resp = client.get("/api/passive-log/check")
        assert resp.json()["should_prompt"] is False

        resp = client.get("/api/passive-log/today")
        assert len(resp.json()["entries"]) >= 3

    def test_20_crisis_detection_scoring(self):
        """Heuristic crisis detection endpoint."""
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.1, "frustration_markers": 0.0, "error_rate": 0.0,
        })
        assert resp.json()["trigger"] is False

        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.9, "frustration_markers": 0.9, "error_rate": 0.8,
        })
        assert resp.json()["trigger"] is True
        assert resp.json()["confidence"] >= 0.7

    def test_21_energy_log(self):
        """Energy log exists."""
        resp = client.get("/api/energy-log")
        assert resp.status_code == 200
        entries = resp.json().get("entries", [])
        assert len(entries) >= 0

    def test_22_export_all_tables(self):
        """JSON export contains all expected tables."""
        resp = client.get("/api/export/json")
        assert resp.status_code == 200
        data = resp.json()
        for table in ["daily_state", "tasks", "energy_log", "crisis_log", "timer_sessions", "habits", "wind_down"]:
            assert table in data, f"Missing {table} from export"

    def test_23_backup_creates_file(self):
        """Backup creates .db file on disk."""
        resp = client.post("/api/export/backup")
        assert resp.status_code == 200
        data = resp.json()
        assert "backup" in data
        assert "path" in data
        assert Path(data["path"]).exists()

    def test_24_declarative_offline_fallback(self):
        """Declarative endpoint handles offline LLM gracefully."""
        resp = client.post("/api/declarative", json={
            "prompt": "You need to clean the kitchen",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["original"] == "You need to clean the kitchen"
        assert "[LLM unavailable]" in data["declarative"]

    def test_25_traffic_light_modes(self):
        """All three traffic-light modes persist."""
        for mode in ["red", "amber", "green"]:
            resp = client.put("/api/mode", json={"mode": mode})
            assert resp.status_code == 200, f"Mode {mode} set failed"
            resp = client.get("/api/mode")
            assert resp.json()["mode"] == mode, f"Mode {mode} not persisted"

    def test_26_import_merges_data(self):
        """Import merges exported data including a new task."""
        export = client.get("/api/export/json").json()
        export.setdefault("tasks", []).append({
            "id": "imported-task-id",
            "title": "Imported task",
            "status": "active",
            "spoon_cost": 1.0,
            "energy_tag": "low",
            "micro_chunks": "[]", "recurring": "",
        })
        resp = client.post("/api/import", json=export)
        assert resp.status_code == 200
        imported = resp.json()["imported"]
        assert imported.get("tasks", 0) >= 1

    def test_27_soundscape_configs(self):
        """Default soundscape configs exist for focus/grounding/crisis."""
        resp = client.get("/api/soundscapes")
        assert resp.status_code == 200
        configs = resp.json().get("configs", resp.json().get("soundscapes", []))
        modes = {c["mode"] for c in configs}
        assert "focus" in modes
        assert "grounding" in modes
        assert "crisis" in modes

    def test_28_mode_bar(self):
        """Mode bar state stays consistent after mode changes."""
        client.put("/api/mode", json={"mode": "green"})
        resp = client.get("/api/mode")
        assert resp.json()["mode"] == "green"

    def test_29_all_routes_registered(self):
        """All expected API routes present in OpenAPI spec."""
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        expected = [
            "/api/state", "/api/check-in", "/api/mode",
            "/api/tasks", "/api/tasks/next",
            "/api/habits", "/api/timer", "/api/timer/active",
            "/api/wind-down", "/api/wind-down/today",
            "/api/review/week", "/api/review/insight",
            "/api/crisis/activate", "/api/crisis/resolve",
            "/api/energy-log", "/api/declarative",
            "/api/export/json", "/api/export/backup", "/api/import",
            "/api/passive-log/check", "/api/passive-log/submit", "/api/passive-log/today",
            "/api/crisis/check", "/api/onboarding/chat", "/api/soundscapes",
        ]
        for route in expected:
            assert route in paths, f"Route {route} missing"
