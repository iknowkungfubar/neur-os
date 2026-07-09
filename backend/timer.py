"""Timer session — formal state machine for focus/break timers.

States: IDLE -> RUNNING -> PAUSED -> RUNNING -> COMPLETED
         RUNNING -> COMPLETED (on expiry)
         Any -> CANCELLED
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class TimerSession:
    """Timer with formal state machine. Wraps store persistence."""

    VALID_TRANSITIONS = {
        "IDLE": {"start"},
        "RUNNING": {"pause", "complete", "cancel"},
        "PAUSED": {"resume", "cancel"},
        "COMPLETED": set(),
        "CANCELLED": set(),
    }

    def __init__(self, store_data: dict[str, Any] | None = None):
        if store_data:
            self.timer_id = store_data.get("id", "")
            self.state = store_data.get("state", "IDLE")
            self.task_id = store_data.get("task_id")
            self.started_at = store_data.get("started_at")
            self.paused_at = store_data.get("paused_at")
            self.duration_minutes = store_data.get("duration_minutes", 25)
            self.soundscape = store_data.get("soundscape", "")
            self.body_doubling = store_data.get("body_doubling", False)
            self.started_as = store_data.get("started_as", "focus")
            self.count_up = store_data.get("count_up", True)
            self.elapsed_before_pause = store_data.get("elapsed_before_pause", 0.0)
        else:
            self.timer_id = ""
            self.state = "IDLE"
            self.task_id = None
            self.started_at = None
            self.paused_at = None
            self.duration_minutes = 25
            self.soundscape = ""
            self.body_doubling = False
            self.started_as = "focus"
            self.count_up = True
            self.elapsed_before_pause = 0.0

    def can_transition_to(self, action: str) -> bool:
        return action in self.VALID_TRANSITIONS.get(self.state, set())

    def start(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self.can_transition_to("start"):
            raise ValueError(f"Cannot start timer in state {self.state}")
        now = datetime.now(timezone.utc).isoformat()
        return {
            "action": "start", "state": "RUNNING",
            "task_id": data.get("task_id"),
            "duration_minutes": data.get("duration_minutes", 25),
            "soundscape": data.get("soundscape", ""),
            "body_doubling": data.get("body_doubling", False),
            "started_as": data.get("started_as", "focus"),
            "count_up": data.get("count_up", True),
            "started_at": now,
        }

    def pause(self) -> dict[str, Any]:
        if not self.can_transition_to("pause"):
            raise ValueError(f"Cannot pause timer in state {self.state}")
        return {"action": "pause", "state": "PAUSED", "paused_at": datetime.now(timezone.utc).isoformat()}

    def resume(self) -> dict[str, Any]:
        if not self.can_transition_to("resume"):
            raise ValueError(f"Cannot resume timer in state {self.state}")
        now = datetime.now(timezone.utc).isoformat()
        return {"action": "resume", "state": "RUNNING", "resumed_at": now}

    def complete(self) -> dict[str, Any]:
        if not self.can_transition_to("complete"):
            raise ValueError(f"Cannot complete timer in state {self.state}")
        return {"action": "complete", "state": "COMPLETED", "completed_at": datetime.now(timezone.utc).isoformat()}

    def cancel(self) -> dict[str, Any]:
        if not self.can_transition_to("cancel"):
            raise ValueError(f"Cannot cancel timer in state {self.state}")
        return {"action": "cancel", "state": "CANCELLED", "cancelled_at": datetime.now(timezone.utc).isoformat()}
