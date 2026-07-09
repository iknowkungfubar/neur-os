"""Declarative routes."""
from __future__ import annotations

from fastapi import APIRouter
from backend.response import ok
from backend.schemas import LLMRequest
from backend.llm import call_llm

router = APIRouter()

@router.post("/api/declarative")
async def declarative_translate(req: LLMRequest):
    system = ("Translate imperative demands into declarative, non-coercive language. "
              "Example: 'You must finish this report by Friday' → 'The report deadline is approaching on Friday.' "
              "Never use 'you need to', 'you must', 'you should'. Keep it factual.")
    result = await call_llm(system, req.prompt, max_tokens=200)
    return ok({"original": req.prompt, "declarative": result})


