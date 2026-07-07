"""Brain routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.schemas import BrainDumpRequest
from backend.llm import call_llm

router = APIRouter()

@router.post("/api/brain-dump")
async def brain_dump(data: BrainDumpRequest, store: DataStore = Depends(get_store)):
    text = data.text
    if data.declarative:
        try:
            dec = await call_llm("Rewrite this to be gentle, declarative, and demand-free. Remove urgency, guilt, imperative mood. Keep the meaning.", data.text, max_tokens=200)
            dec = re.sub(r'<think>.*?</think>', '', dec, flags=re.DOTALL).strip()
            if dec and len(dec) > 5: text = dec
        except Exception: pass
    structured = {"tasks": [], "notes": []}
    try:
        resp = await call_llm(
            'Organize this brain dump into tasks and notes. Return JSON: {"tasks": [{"title": str, "spoon_cost": 0.5-5.0, "energy_tag": "low"|"medium"|"high"}], "notes": [{"content": str}]}',
            data.text, max_tokens=500)
        cleaned = re.sub(r'<think>.*?</think>', '', resp, flags=re.DOTALL).strip()
        if cleaned.startswith("{"): structured = json.loads(cleaned)
        elif cleaned.startswith("```"): structured = json.loads(cleaned.strip("`").removeprefix("json").strip())
    except Exception: pass
    if not structured.get("tasks") and not structured.get("notes"):
        structured = {"tasks": [{"title": text, "spoon_cost": 1.0, "energy_tag": "medium"}], "notes": []}
    if structured.get("tasks"):
        for t in structured["tasks"]:
            store.create_task({"title": t.get("title", text), "description": "",
                               "spoon_cost": t.get("spoon_cost", 1.0), "micro_chunks": [],
                               "energy_tag": t.get("energy_tag", "medium"), "recurring": ""})
    bid = store.save_brain_dump(text, structured, data.source)
    return ok({"id": bid, "structured": structured, "original": data.text,
               "declarative_note": text if data.declarative else None})


@router.get("/api/brain-dump")
async def get_brain_dumps(store: DataStore = Depends(get_store)):
    return ok({"dumps": store.list_brain_dumps()})


@router.get("/api/brain-dump/search")
async def search_brain_dumps(q: str = "", store: DataStore = Depends(get_store)):
    if not q: return ok({"dumps": [], "query": q})
    return ok({"dumps": store.search_brain_dumps(q), "query": q})


