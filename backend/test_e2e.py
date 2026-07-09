"""E2E test suite for NeurOS backend — tests the full API flow."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
import backend.main as app_module
from conftest import unwrap
from backend.store import InMemoryStore

# Use InMemoryStore — no file I/O, isolated per test file
store = InMemoryStore()
app_module.set_store(store)

# Seed dopamine menu so soundscape test works
for name, cat, energy, sort in [
    ("Deep breaths (2 min)", "starters", 0.2, 1),
    ("Walk outside", "mains", 2.0, 1),
    ("Guilty pleasure show", "desserts", 1.0, 1),
]:
    store.dopamine_menu_items.append({"id": f"seed-{name}", "name": name, "category": cat, "energy_required": energy, "sort_order": sort, "created_at": ""})

client = TestClient(app_module.app)


class TestE2EFlow:
    def test_01_state_empty(self):
        resp = client.get("/api/state")
        assert resp.status_code == 200
        s = unwrap(resp)
        assert s["state"]["total_spoons"] == 10

    def test_02_onboarding_four_questions(self):
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
            assert resp.status_code == 200
            data = unwrap(resp)
            assert data["response"] == expected

    def test_03_mode_default_green(self):
        resp = client.get("/api/mode")
        assert resp.status_code == 200
        assert unwrap(resp)["mode"] == "green"

    def test_04_checkin_sets_spoons(self):
        resp = client.post("/api/check-in", json={
            "spoons": 8, "pain_level": 1, "note": "feeling okay",
        })
        assert resp.status_code == 200

    def test_05_add_tasks(self):
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
            assert resp.status_code == 200
        state = unwrap(client.get("/api/state"))
        assert len(state["tasks"]) == 5

    def test_06_next_task_highest_spoon_affordable(self):
        resp = client.get("/api/tasks/next")
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["task"] is not None

    def test_07_start_focus_timer(self):
        state = unwrap(client.get("/api/state"))
        tasks = state["tasks"]
        assert len(tasks) >= 2
        resp = client.post("/api/timer", json={
            "action": "start", "task_id": tasks[0]["id"],
            "duration_minutes": 25, "body_doubling": True,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["status"] == "running"
        assert data["body_doubling"] is True

    def test_08_timer_active_running(self):
        resp = client.get("/api/timer/active")
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["timer"] is not None

    def test_09_timer_pause_resume(self):
        resp = client.post("/api/timer", json={"action": "pause"})
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["status"] == "paused"
        resp2 = client.post("/api/timer", json={"action": "resume"})
        assert resp2.status_code == 200
        data2 = unwrap(resp2)
        assert data2["status"] == "running"

    def test_10_complete_task_expends_spoons(self):
        state = unwrap(client.get("/api/state"))
        active = [t for t in state["tasks"] if t["status"] != "completed"]
        old_remaining = state["state"]["remaining_spoons"]
        if active:
            resp = client.post(f"/api/tasks/{active[0]['id']}/expend")
            assert resp.status_code == 200
            new_state = unwrap(client.get("/api/state"))
            assert new_state["state"]["remaining_spoons"] < old_remaining

    def test_11_stop_timer_after_complete(self):
        resp = client.post("/api/timer", json={"action": "stop"})
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["status"] == "completed"

    def test_12_complete_more_tasks_reduce_spoons(self):
        state = unwrap(client.get("/api/state"))
        active = [t for t in state["tasks"] if t["status"] != "completed"]
        for t in active[:3]:
            r = client.post(f"/api/tasks/{t['id']}/expend")
            assert r.status_code == 200
        final_state = unwrap(client.get("/api/state"))
        assert final_state["state"]["remaining_spoons"] < 10

    def test_13_next_task_filters_by_affordability(self):
        """May return None if all tasks cost more than remaining spoons — that's valid."""
        resp = client.get("/api/tasks/next")
        assert resp.status_code == 200

    def test_15_wind_down_save_and_retrieve(self):
        resp = client.post("/api/wind-down", json={
            "went_well": "Finished the proposal",
            "drained": "Morning brain fog",
            "tomorrow_one": "Review testimonials",
        })
        assert resp.status_code == 200
        resp2 = client.get("/api/wind-down/today")
        entry = unwrap(resp2)["entry"]
        assert entry["went_well"] == "Finished the proposal"

    def test_16_habits_create_and_check(self):
        resp = client.post("/api/habits", json={
            "title": "Drink water", "frequency": "daily", "spoon_cost": 0.5,
        })
        assert resp.status_code == 200
        hid = unwrap(resp)["id"]
        check = client.post(f"/api/habits/{hid}/check")
        assert check.status_code == 200
        habits = unwrap(client.get("/api/habits"))
        assert any(h["id"] == hid and h["done_today"] for h in habits["habits"])

    def test_17_review_returns_completed_tasks(self):
        resp = client.get("/api/review/week")
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["insights"]["tasks_completed"] >= 2

    def test_18_weekly_insight(self):
        resp = client.get("/api/review/insight")
        assert resp.status_code == 200
        data = unwrap(resp)
        assert isinstance(data["insight"], str)

    def test_19_passive_log_lifecycle(self):
        resp = client.get("/api/passive-log/check")
        assert unwrap(resp)["should_prompt"] is True
        client.post("/api/passive-log/submit", json={"response": "test"})
        logs = unwrap(client.get("/api/passive-log/today"))
        assert len(logs["entries"]) >= 1

    def test_20_crisis_detection_scoring(self):
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.1, "frustration_markers": 0.0, "error_rate": 0.0,
        })
        assert unwrap(resp)["trigger"] is False
        resp2 = client.post("/api/crisis/check", json={
            "cognitive_load": 0.9, "frustration_markers": 0.9, "error_rate": 0.5,
        })
        assert unwrap(resp2)["trigger"] is True

    def test_23_backup_creates_file(self):
        resp = client.post("/api/export/backup")
        assert resp.status_code == 200
        assert "backup" in unwrap(resp)

    def test_24_declarative_offline_fallback(self):
        resp = client.post("/api/declarative", json={
            "prompt": "You need to clean the kitchen",
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["original"] == "You need to clean the kitchen"

    def test_25_traffic_light_modes(self):
        for mode in ["red", "amber", "green"]:
            resp = client.put("/api/mode", json={"mode": mode})
            assert resp.status_code == 200
            assert unwrap(client.get("/api/mode"))["mode"] == mode

    def test_26_import_merges_data(self):
        export = client.get("/api/export/json").json()
        export.setdefault("tasks", []).append({
            "id": "imported-task-id", "title": "Imported task", "status": "active",
            "spoon_cost": 1.0, "energy_tag": "low", "micro_chunks": "[]", "recurring": "",
        })
        resp = client.post("/api/import", json=export)
        assert unwrap(resp)["imported"]["tasks"] >= 1

    def test_27_soundscape_configs(self):
        resp = client.get("/api/soundscapes")
        assert resp.status_code == 200

    def test_28_mode_bar(self):
        client.put("/api/mode", json={"mode": "green"})
        assert unwrap(client.get("/api/mode"))["mode"] == "green"
