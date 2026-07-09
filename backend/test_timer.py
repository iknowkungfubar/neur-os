"""Tests for timer state machine (timer.py)."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.timer import TimerSession


class TestTimerSession:
    """TimerSession state machine tests."""

    def test_initial_state_is_idle(self):
        """A fresh timer starts in IDLE state."""
        t = TimerSession()
        assert t.state == "IDLE"
        assert t.timer_id == ""

    def test_initial_state_from_store_data(self):
        """Timer can be reconstructed from stored dict."""
        data = {
            "id": "abc123",
            "state": "PAUSED",
            "task_id": "task-1",
            "started_at": "2025-01-01T10:00:00",
            "duration_minutes": 25,
            "soundscape": "rain",
            "body_doubling": True,
            "started_as": "focus",
            "count_up": True,
            "elapsed_before_pause": 120.0,
        }
        t = TimerSession(data)
        assert t.timer_id == "abc123"
        assert t.state == "PAUSED"
        assert t.task_id == "task-1"
        assert t.duration_minutes == 25
        assert t.soundscape == "rain"
        assert t.body_doubling is True
        assert t.elapsed_before_pause == 120.0

    def test_can_transition_from_idle(self):
        """IDLE state should only allow 'start'."""
        t = TimerSession()
        assert t.can_transition_to("start") is True
        assert t.can_transition_to("pause") is False
        assert t.can_transition_to("resume") is False
        assert t.can_transition_to("complete") is False
        assert t.can_transition_to("cancel") is False

    def test_can_transition_from_running(self):
        """RUNNING state should allow pause, complete, cancel."""
        t = TimerSession()
        t.state = "RUNNING"
        assert t.can_transition_to("start") is False
        assert t.can_transition_to("pause") is True
        assert t.can_transition_to("complete") is True
        assert t.can_transition_to("cancel") is True
        assert t.can_transition_to("resume") is False

    def test_can_transition_from_paused(self):
        """PAUSED state should allow resume and cancel."""
        t = TimerSession()
        t.state = "PAUSED"
        assert t.can_transition_to("resume") is True
        assert t.can_transition_to("cancel") is True
        assert t.can_transition_to("start") is False
        assert t.can_transition_to("pause") is False
        assert t.can_transition_to("complete") is False

    def test_can_transition_from_completed(self):
        """COMPLETED is a terminal state — no transitions allowed."""
        t = TimerSession()
        t.state = "COMPLETED"
        assert t.can_transition_to("start") is False
        assert t.can_transition_to("pause") is False
        assert t.can_transition_to("resume") is False
        assert t.can_transition_to("complete") is False
        assert t.can_transition_to("cancel") is False

    def test_can_transition_from_cancelled(self):
        """CANCELLED is a terminal state — no transitions allowed."""
        t = TimerSession()
        t.state = "CANCELLED"
        assert t.can_transition_to("start") is False
        assert t.can_transition_to("pause") is False
        assert t.can_transition_to("resume") is False
        assert t.can_transition_to("complete") is False
        assert t.can_transition_to("cancel") is False

    def test_start_transitions_to_running(self):
        """Calling start() should move to RUNNING state."""
        t = TimerSession()
        result = t.start({"task_id": "task-1", "duration_minutes": 15})
        assert result["action"] == "start"
        assert result["state"] == "RUNNING"
        assert result["task_id"] == "task-1"
        assert result["duration_minutes"] == 15
        assert "started_at" in result

    def test_pause_transitions_to_paused(self):
        """Calling pause() from RUNNING should move to PAUSED."""
        t = TimerSession()
        t.state = "RUNNING"
        result = t.pause()
        assert result["action"] == "pause"
        assert result["state"] == "PAUSED"
        assert "paused_at" in result

    def test_resume_transitions_to_running(self):
        """Calling resume() from PAUSED should move to RUNNING."""
        t = TimerSession()
        t.state = "PAUSED"
        result = t.resume()
        assert result["action"] == "resume"
        assert result["state"] == "RUNNING"
        assert "resumed_at" in result

    def test_complete_transitions_to_completed(self):
        """Calling complete() from RUNNING should move to COMPLETED."""
        t = TimerSession()
        t.state = "RUNNING"
        result = t.complete()
        assert result["action"] == "complete"
        assert result["state"] == "COMPLETED"
        assert "completed_at" in result

    def test_cancel_from_running(self):
        """Calling cancel() from RUNNING should move to CANCELLED."""
        t = TimerSession()
        t.state = "RUNNING"
        result = t.cancel()
        assert result["action"] == "cancel"
        assert result["state"] == "CANCELLED"
        assert "cancelled_at" in result

    def test_cancel_from_paused(self):
        """Calling cancel() from PAUSED should move to CANCELLED."""
        t = TimerSession()
        t.state = "PAUSED"
        result = t.cancel()
        assert result["action"] == "cancel"
        assert result["state"] == "CANCELLED"

    def test_invalid_transition_raises_value_error(self):
        """Calling an invalid transition should raise ValueError."""
        t = TimerSession()
        # Cannot pause from IDLE
        try:
            t.pause()
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Cannot pause" in str(e)

    def test_full_idle_to_completed_cycle(self):
        """Full cycle: IDLE → start → RUNNING → pause → PAUSED → resume → RUNNING → complete → COMPLETED."""
        t = TimerSession()
        assert t.state == "IDLE"

        r = t.start({"task_id": "t1"})
        assert r["state"] == "RUNNING"

        t.state = "RUNNING"
        r = t.pause()
        assert r["state"] == "PAUSED"

        t.state = "PAUSED"
        r = t.resume()
        assert r["state"] == "RUNNING"

        t.state = "RUNNING"
        r = t.complete()
        assert r["state"] == "COMPLETED"

    def test_cancel_after_pause(self):
        """IDLE → start → RUNNING → pause → PAUSED → cancel → CANCELLED."""
        t = TimerSession()
        t.start({"task_id": "t1"})
        t.state = "RUNNING"
        t.pause()
        t.state = "PAUSED"

        r = t.cancel()
        assert r["state"] == "CANCELLED"

    def test_start_with_defaults(self):
        """Calling start() with minimal data should use defaults."""
        t = TimerSession()
        result = t.start({})
        assert result["duration_minutes"] == 25
        assert result["soundscape"] == ""
        assert result["body_doubling"] is False
        assert result["started_as"] == "focus"
        assert result["count_up"] is True
