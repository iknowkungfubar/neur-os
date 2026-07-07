"""Onboarding routes."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.schemas import OnboardingChat

router = APIRouter()

@router.post("/api/onboarding/chat")
async def onboarding_chat(data: OnboardingChat, store: DataStore = Depends(get_store)):
    questions = [
        "What kind of tasks do you need the most help keeping track of?",
        "What time of day do you usually have the most energy?",
        "When you're overwhelmed, what helps you recharge?",
        "What's one thing you'd like to be able to do more consistently?",
    ]
    result = "done" if data.turn >= len(questions) else questions[data.turn]
    existing = store.get_onboarding()
    profile = json.loads(existing["extracted_profile"]) if existing and existing.get("extracted_profile") else {}
    if data.history:
        profile[f"turn_{data.turn}"] = data.history[-1]["content"] if data.history else ""
    store.save_onboarding(min(data.turn + 1, 5), data.turn + 1, profile)
    return ok({"response": result, "turn": data.turn + 1, "done": data.turn >= len(questions) - 1})

