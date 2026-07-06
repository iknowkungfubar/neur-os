"""Tasks routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.schemas import TaskCreate, TaskUpdate
from backend.domain.usecases import parse_llm_json
from backend.config import ENERGY_TAGS
from backend.llm import call_llm
import json, re

router = APIRouter()

@router.get("/api/tasks/next")
async def get_next_task(store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    state = store.get_state(today)
    mode, remaining = state.get("mode", "green"), state.get("remaining_spoons", 10)
    if mode == "red":
        return ok({"task": None, "mode": "red", "message": "Today might be a rest day. That's okay."})
    task = store.next_task(mode, remaining)
    return ok({"task": task, "mode": mode, "message": None if task else "No tasks fit your current energy."})

@router.post("/api/tasks")
async def create_task(task: TaskCreate, store: DataStore = Depends(get_store)):
    spoon_cost = task.spoon_cost or ENERGY_TAGS.get(task.energy_tag, 1.0)
    if task.spoon_cost is None:
        resp = await call_llm("Estimate spoon cost (1-5). 1=easy, 5=exhausting. Reply with JUST a number.",
                              f"Task: {task.title}. {task.description}", max_tokens=10)
        try: spoon_cost = max(0.5, min(5.0, float(resp.strip())))
        except (ValueError, TypeError): pass
    chunk_response = await call_llm(
        "Break this task into 2-4 tiny actionable micro-steps. Return as JSON array of strings.",
        f"Task: {task.title}. {task.description}", max_tokens=300)
    chunk_response = re.sub(r'<think>.*?</think>', '', chunk_response, flags=re.DOTALL).strip()
    micro_chunks = []
    try:
        cleaned = chunk_response.strip()
        if cleaned.startswith("["):
            micro_chunks = json.loads(cleaned)
        elif cleaned.startswith("```"):
            micro_chunks = json.loads(cleaned.strip("`").removeprefix("json").strip())
        else:
            micro_chunks = [line.strip("- ").strip() for line in cleaned.split("\n") if line.strip()]
    except (json.JSONDecodeError, Exception):
        micro_chunks = [f"Start: {task.title}"]
    task_id = store.create_task({"title": task.title, "description": task.description,
                                  "spoon_cost": spoon_cost, "micro_chunks": micro_chunks,
                                  "energy_tag": task.energy_tag, "recurring": task.recurring})
    return ok(task_id)

@router.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, update: TaskUpdate, store: DataStore = Depends(get_store)):
    if not store.update_task(task_id, update.dict(exclude_unset=True)):
        raise HTTPException(404, "Task not found")
    return ok({"status": "updated"})

@router.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, update: TaskUpdate, store: DataStore = Depends(get_store)):
    if not store.update_task(task_id, update.dict(exclude_unset=True)):
        raise HTTPException(404, "Task not found")
    return ok({"status": "updated"})

@router.post("/api/tasks/{task_id}/expend")
async def expend_spoons(task_id: str, store: DataStore = Depends(get_store)):
    result = store.complete_task(task_id)
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return ok(result)

