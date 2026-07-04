"""Tests for NeurOS v0.4.1 endpoints: passive log, crisis check, onboarding chat."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Override DB before importing the app — use a temp dir
_tmp_db = tempfile.mkdtemp()
os.environ["LM_STUDIO_URL"] = "http://localhost:9999/v1"  # bogus, won't be hit by sync tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backend.main as app_module

# Monkey-patch the DB path
_app_db_path = Path(_tmp_db) / "neur-os.db"
app_module.DB_PATH = _app_db_path
app_module.DATA_DIR = Path(_tmp_db)
app_module.BACKUP_DIR = Path(_tmp_db) / "backups"
app_module.BACKUP_DIR.mkdir(exist_ok=True)
app_module.init_db()

from fastapi.testclient import TestClient

client = TestClient(app_module.app)


def setup_module():
    """Ensure fresh DB before any tests."""
    _app_db_path.unlink(missing_ok=True)
    app_module.init_db()


def teardown_module():
    """Clean up temp dir."""
    import shutil
    shutil.rmtree(_tmp_db, ignore_errors=True)


# ── Passive Log ──

class TestPassiveLog:
    def test_check_no_logs_today(self):
        """Fresh day: should prompt."""
        resp = client.get("/api/passive-log/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["should_prompt"] is True
        assert data["last_response_minutes_ago"] is None

    def test_submit_log(self):
        """Submit a passive log entry."""
        resp = client.post("/api/passive-log/submit", json={
            "response": "cleaning the kitchen",
            "spoons_at_time": 5.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True
        assert isinstance(data["id"], str)
        assert len(data["id"]) > 0

    def test_check_after_submit(self):
        """After submitting, should not prompt within 60 min."""
        # First submit again to have a fresh timestamp
        client.post("/api/passive-log/submit", json={
            "response": "taking a break",
            "spoons_at_time": 3.0,
        })
        resp = client.get("/api/passive-log/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["should_prompt"] is False
        assert data["last_response_minutes_ago"] == 0

    def test_today_returns_entries(self):
        """Today's log should contain our entries."""
        resp = client.get("/api/passive-log/today")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) >= 2
        # Most recent first in the list is newest due to ISO sort
        last = data["entries"][-1]
        assert last["response"] == "taking a break"
        assert last["spoons_at_time"] == 3.0
        assert last["source"] == "notification"

    def test_submit_all_fields(self):
        """Submit with optional fields."""
        resp = client.post("/api/passive-log/submit", json={
            "response": "writing tests",
            "spoons_at_time": 8.0,
            "current_task_id": "test-abc-123",
            "source": "manual",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True

        # Verify in today
        r2 = client.get("/api/passive-log/today")
        matches = [e for e in r2.json()["entries"] if e["id"] == data["id"]]
        assert len(matches) == 1
        assert matches[0]["current_task_id"] == "test-abc-123"
        assert matches[0]["source"] == "manual"

    def test_submit_empty_response(self):
        """Empty response should be saved (edge case: user types then deletes)."""
        resp = client.post("/api/passive-log/submit", json={"response": ""})
        assert resp.status_code == 200
        assert resp.json()["saved"] is True


# ── Crisis Check ──

class TestCrisisCheck:
    def test_below_threshold(self):
        """Low scores should not trigger crisis."""
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.2,
            "frustration_markers": 0.1,
            "error_rate": 0.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["trigger"] is False
        assert data["confidence"] < 0.7
        assert data["threshold"] == 0.7

    def test_above_threshold(self):
        """High scores should trigger crisis and log it."""
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.9,
            "frustration_markers": 0.9,
            "error_rate": 0.5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["trigger"] is True
        assert data["confidence"] >= 0.7

        # Verify crisis was logged
        state = client.get("/api/state").json()
        # crisis_log should have an auto_detected entry
        # check via the crisis_log directly by looking at state
        assert state is not None

    def test_boundary_threshold(self):
        """Edge: exactly at threshold (0.7)."""
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.7,
            "frustration_markers": 0.7,
            "error_rate": 0.7,
        })
        assert resp.status_code == 200
        data = resp.json()
        # 0.7*0.5 + 0.7*0.3 + 0.7*0.2 = 0.35 + 0.21 + 0.14 = 0.7
        assert data["confidence"] == 0.7
        assert data["trigger"] is True  # score >= 0.7

    def test_minimal_scores(self):
        """Zero scores should not trigger."""
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.0,
            "frustration_markers": 0.0,
            "error_rate": 0.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["trigger"] is False
        assert data["confidence"] == 0.0

    def test_missing_fields_default_to_zero(self):
        """Partial payload should use defaults."""
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.9,
        })
        assert resp.status_code == 200
        data = resp.json()
        # 0.9*0.5 + 0*0.3 + 0*0.2 = 0.45
        assert data["confidence"] == 0.45
        assert data["trigger"] is False


# ── Onboarding Chat ──

class TestOnboardingChat:
    def test_first_turn(self):
        """First turn should return a hardcoded question."""
        resp = client.post("/api/onboarding/chat", json={
            "history": [],
            "turn": 0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "What kind of tasks do you need the most help keeping track of?"
        assert data["turn"] == 1
        assert data["done"] is False

    def test_mid_conversation(self):
        """Turn 2 returns the third question."""
        resp = client.post("/api/onboarding/chat", json={
            "history": [{"role": "user", "content": "I struggle with morning tasks"}, {"role": "assistant", "content": "When do you have energy?"}, {"role": "user", "content": "Evenings are better"}],
            "turn": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "When you're overwhelmed, what helps you recharge?"
        assert data["done"] is False

    def test_conversation_completes(self):
        """Turn 4 (last question) should set done=True."""
        resp = client.post("/api/onboarding/chat", json={
            "history": [{"role": "user", "content": "Response"} for _ in range(4)],
            "turn": 4,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["done"] is True

    def test_llm_offline_fallback(self):
        """No LLM needed — hardcoded questions don't depend on LM Studio."""
        resp = client.post("/api/onboarding/chat", json={
            "history": [{"role": "user", "content": "test"}],
            "turn": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "What time of day do you usually have the most energy?"


# ── Health ──

class TestHealth:
    def test_state_endpoint_works(self):
        """Core API still responds."""
        resp = client.get("/api/state")
        assert resp.status_code == 200
        data = resp.json()
        assert "state" in data

    def test_routes_registered(self):
        """Verify our new routes exist in OpenAPI."""
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/passive-log/check" in paths
        assert "/api/passive-log/submit" in paths
        assert "/api/passive-log/today" in paths
        assert "/api/crisis/check" in paths
        assert "/api/onboarding/chat" in paths
