"""Pydantic request/response models for NeurOS API.

Extracted from main.py to eliminate the inline model definitions.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class SpoonCheckIn(BaseModel):
    spoons: int; pain_level: int = 0; note: str = ""


class TaskCreate(BaseModel):
    title: str; description: str = ""; spoon_cost: Optional[float] = None
    energy_tag: str = "medium"; recurring: str = ""


class TaskUpdate(BaseModel):
    status: Optional[str] = None; spoon_cost: Optional[float] = None
    micro_chunks: Optional[list[str]] = None


class HabitCreate(BaseModel):
    title: str; description: str = ""; frequency: str = "daily"
    spoon_cost: float = 0.5; energy_tag: str = "low"


class TimerAction(BaseModel):
    task_id: Optional[str] = None; duration_minutes: int = 25; action: str = "start"
    soundscape: str = ""; body_doubling: bool = False; started_as: str = "focus"; count_up: bool = True


class WindDownEntry(BaseModel):
    went_well: str = ""; drained: str = ""; tomorrow_one: str = ""; note: str = ""


class ModeUpdate(BaseModel):
    mode: str


class SoundscapeUpdate(BaseModel):
    sound_file: Optional[str] = None; volume: Optional[float] = None; loop: Optional[bool] = None


class BrainDumpRequest(BaseModel):
    text: str; source: str = "textarea"; declarative: bool = False


class LLMRequest(BaseModel):
    prompt: str


class PassiveLogSubmit(BaseModel):
    response: str; spoons_at_time: Optional[float] = None
    current_task_id: Optional[str] = None; source: str = "notification"


class CrisisCheck(BaseModel):
    cognitive_load: float = 0.0; frustration_markers: float = 0.0; error_rate: float = 0.0


class OnboardingChat(BaseModel):
    history: list[dict] = []; turn: int = 0
