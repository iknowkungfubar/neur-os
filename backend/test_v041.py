"""Tests for NeurOS v0.4.1 endpoints: passive log, crisis check, onboarding chat."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import backend.main as app_module
from conftest import unwrap
from backend.deps import set_store
from backend.store import InMemoryStore

# Use InMemoryStore — no file I/O, each file gets a fresh store
store = InMemoryStore()
app_module.set_store(store)

from fastapi.testclient import TestClient

client = TestClient(app_module.app)


def setup_module():
    from backend.domain import entities, usecases  # noqa: F401


class TestPassiveLog:
    def test_check_no_logs_today(self):
        resp = client.get("/api/passive-log/check")
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["should_prompt"] is True

    def test_submit_log(self):
        resp = client.post("/api/passive-log/submit", json={
            "response": "cleaning the kitchen",
            "spoons_at_time": 5.0,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["saved"] is True

    def test_check_after_submit(self):
        client.post("/api/passive-log/submit", json={
            "response": "taking a break",
            "spoons_at_time": 3.0,
        })
        resp = client.get("/api/passive-log/check")
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["should_prompt"] is False

    def test_today_returns_entries(self):
        resp = client.get("/api/passive-log/today")
        assert resp.status_code == 200
        data = unwrap(resp)
        assert len(data["entries"]) >= 2

    def test_submit_all_fields(self):
        resp = client.post("/api/passive-log/submit", json={
            "response": "writing tests",
            "spoons_at_time": 8.0,
            "current_task_id": "test-abc-123",
            "source": "manual",
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["saved"] is True

    def test_submit_empty_response(self):
        resp = client.post("/api/passive-log/submit", json={"response": ""})
        assert resp.status_code == 200
        assert unwrap(resp)["saved"] is True


class TestCrisisCheck:
    def test_below_threshold(self):
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.2, "frustration_markers": 0.1, "error_rate": 0.0,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["trigger"] is False

    def test_above_threshold(self):
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.9, "frustration_markers": 0.9, "error_rate": 0.5,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["trigger"] is True

    def test_boundary_threshold(self):
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.7, "frustration_markers": 0.7, "error_rate": 0.7,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["confidence"] == 0.7

    def test_minimal_scores(self):
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.0, "frustration_markers": 0.0, "error_rate": 0.0,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["trigger"] is False

    def test_missing_fields_default_to_zero(self):
        resp = client.post("/api/crisis/check", json={
            "cognitive_load": 0.9,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["confidence"] == 0.45


class TestOnboardingChat:
    def test_first_turn(self):
        resp = client.post("/api/onboarding/chat", json={
            "history": [], "turn": 0,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["response"] == "What kind of tasks do you need the most help keeping track of?"

    def test_mid_conversation(self):
        resp = client.post("/api/onboarding/chat", json={
            "history": [{"role": "user", "content": "I struggle with morning tasks"},
                        {"role": "assistant", "content": "When do you have energy?"},
                        {"role": "user", "content": "Evenings are better"}],
            "turn": 2,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["response"] == "When you're overwhelmed, what helps you recharge?"

    def test_conversation_completes(self):
        resp = client.post("/api/onboarding/chat", json={
            "history": [{"role": "user", "content": "Response"} for _ in range(4)],
            "turn": 4,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["done"] is True

    def test_llm_offline_fallback(self):
        resp = client.post("/api/onboarding/chat", json={
            "history": [{"role": "user", "content": "test"}],
            "turn": 1,
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["response"] == "What time of day do you usually have the most energy?"


class TestHealth:
    def test_state_endpoint_works(self):
        resp = client.get("/api/state")
        assert resp.status_code == 200
        data = unwrap(resp)
        assert "state" in data
