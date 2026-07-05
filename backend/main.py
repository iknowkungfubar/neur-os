# neur-os backend v1.0
"""
Neuro-Affirming Cognitive Prosthetic — Backend API
Local-first, privacy-preserving, trauma-informed.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from pydantic import BaseModel

from backend.domain.entities import EnergyBattery, Task, BrainDump
from backend.domain.usecases import energy_envelope, detect_boom_bust, parse_llm_json, analyze_energy_patterns
from backend.store import DataStore, SqliteStore
from backend.response import ok, err

# ponytail: backward compat — tests import init_db.
def init_db():
    from backend.store import SqliteStore
    s = SqliteStore(DB_PATH); s.init_schema(); s._seed_defaults()

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "neur-os.db"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)
SOUNDSCAPES_DIR = Path(__file__).parent / "soundscapes"
SOUNDSCAPES_DIR.mkdir(exist_ok=True)
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
LM_MODEL = os.getenv("LM_MODEL", "qwythos-9b-claude-mythos-5-1m")

app = FastAPI(title="NeurOS", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Store — global instance, swap for tests ──
_store: DataStore | None = None

def reset_store():
    """Clear the cached store (used by tests to force re-init)."""
    global _store
    _store = None

def set_store(store: DataStore):
    """Swap the global store (used by tests to inject InMemoryStore)."""
    global _store
    _store = store

def get_store() -> DataStore:
    global _store
    if _store is None:
        s = SqliteStore(DB_PATH)
        s.init_schema()
        s._seed_defaults()
        _store = s
    return _store

# ── Models ──
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

# ── LLM Client ──
async def call_llm(system: str, user: str, max_tokens: int = 512, model: str = "") -> str:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=2.0)) as client:
            payload = {
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": max_tokens, "temperature": 0.1,
            }
            if LM_MODEL or model:
                payload["model"] = model or LM_MODEL
            resp = await client.post(f"{LM_STUDIO_URL}/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except (httpx.ConnectError, httpx.TimeoutException):
        return "[LLM unavailable]"
    except Exception as e:
        return f"[LLM error: {e}]"

ENERGY_TAGS = {"low": 0.5, "medium": 1.0, "high": 2.0}

# ── Check-In ──
@app.post("/api/check-in")
async def morning_checkin(data: SpoonCheckIn, store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    suggested_mode = "green"
    if data.spoons <= 3: suggested_mode = "red"
    elif data.spoons <= 5: suggested_mode = "amber"
    store.upsert_state(today, {"total_spoons": data.spoons, "remaining_spoons": data.spoons,
                                "pain_level": data.pain_level, "notes": data.note, "mode": suggested_mode})
    store.log_energy(data.spoons, data.pain_level, data.note)
    return ok({"spoons": data.spoons, "pain_level": data.pain_level, "suggested_mode": suggested_mode})

# ── Mode ──
@app.get("/api/mode")
async def get_mode(store: DataStore = Depends(get_store)):
    return ok({"mode": store.get_state()["mode"]})

@app.put("/api/mode")
async def set_mode(data: ModeUpdate, store: DataStore = Depends(get_store)):
    if data.mode not in ("green", "amber", "red"):
        raise HTTPException(400, "Mode must be green, amber, or red")
    today = date.today().isoformat()
    store.set_mode(today, data.mode)
    return ok({"mode": data.mode})

# ── State ──
@app.get("/api/state")
async def get_state(store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    state = store.get_state(today)
    tasks = [t for t in store.get_tasks("active")]
    timer = store.get_active_timer()
    return ok({"state": state, "tasks": tasks, "active_timer": timer})

# ── Next Task ──
@app.get("/api/tasks/next")
async def get_next_task(store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    state = store.get_state(today)
    mode, remaining = state.get("mode", "green"), state.get("remaining_spoons", 10)
    if mode == "red":
        return ok({"task": None, "mode": "red", "message": "Today might be a rest day. That's okay."})
    task = store.next_task(mode, remaining)
    return ok({"task": task, "mode": mode, "message": None if task else "No tasks fit your current energy."})

# ── Tasks ──
@app.post("/api/tasks")
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

@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, update: TaskUpdate, store: DataStore = Depends(get_store)):
    if not store.update_task(task_id, update.dict(exclude_unset=True)):
        raise HTTPException(404, "Task not found")
    return ok({"status": "updated"})

@app.post("/api/tasks/{task_id}/expend")
async def expend_spoons(task_id: str, store: DataStore = Depends(get_store)):
    result = store.complete_task(task_id)
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return ok(result)

# ── Habits ──
@app.get("/api/habits")
async def get_habits(store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    return ok({"habits": store.get_habits(today)})

@app.post("/api/habits")
async def create_habit(habit: HabitCreate, store: DataStore = Depends(get_store)):
    hid = store.create_habit(habit.model_dump())
    return ok({"id": hid})

@app.post("/api/habits/{hid}/check")
async def check_habit(hid: str, store: DataStore = Depends(get_store)):
    if not store.get_habit(hid):
        raise HTTPException(404, "Habit not found")
    today = date.today().isoformat()
    store.check_habit(hid, today)
    return ok({"done_today": True})

# ── Timer ──
@app.post("/api/timer")
async def timer_action(data: TimerAction, store: DataStore = Depends(get_store)):
    if data.action == "start":
        store.stop_all_timers()
        return ok(store.create_timer(data.model_dump()))
    elif data.action == "pause":
        t = store.get_active_timer()
        if not t: raise HTTPException(400, "No running timer")
        try:
            elapsed = int((datetime.utcnow() - datetime.strptime(t["started_at"][:19], "%Y-%m-%d %H:%M:%S")).total_seconds())
        except ValueError: elapsed = 0
        total = t["elapsed_seconds"] + elapsed
        store.update_timer(t["id"], {"status": "paused", "elapsed_seconds": total, "paused_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})
        return ok({"id": t["id"], "status": "paused", "elapsed_seconds": total})
    elif data.action == "resume":
        t = store.get_active_timer()
        if not t or t["status"] != "paused": raise HTTPException(400, "No paused timer")
        store.update_timer(t["id"], {"status": "running", "paused_at": None, "started_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})
        return ok({"id": t["id"], "status": "running"})
    elif data.action == "stop":
        t = store.get_active_timer()
        if not t: raise HTTPException(400, "No active timer")
        elapsed = 0
        if t["status"] == "running":
            try: elapsed = int((datetime.utcnow() - datetime.strptime(t["started_at"][:19], "%Y-%m-%d %H:%M:%S")).total_seconds())
            except ValueError: pass
        total = t["elapsed_seconds"] + elapsed
        store.update_timer(t["id"], {"status": "completed", "elapsed_seconds": total, "completed_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})
        return ok({"id": t["id"], "status": "completed", "elapsed_seconds": total})
    raise HTTPException(400, "Invalid action")

@app.get("/api/timer/active")
async def get_active_timer(store: DataStore = Depends(get_store)):
    return ok({"timer": store.get_active_timer()})

# ── Wind-Down ──
@app.post("/api/wind-down")
async def save_wind_down(data: WindDownEntry, store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    store.upsert_wind_down(today, data.model_dump(exclude_unset=True))
    return ok({"date": today})

@app.get("/api/wind-down/today")
async def get_wind_down(store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    return ok({"entry": store.get_wind_down(today)})

@app.get("/api/wind-down/week")
async def get_week_wind_down(store: DataStore = Depends(get_store)):
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    return ok({"entries": store.week_wind_down(week_ago)})

# ── Weekly Review ──
@app.get("/api/review/week")
async def weekly_review(store: DataStore = Depends(get_store)):
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    return ok(store.weekly_review(week_ago, today))

@app.get("/api/review/insight")
async def generate_insight(store: DataStore = Depends(get_store)):
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    return ok(store.review_insight(week_ago))

# ── Soundscapes ──
@app.get("/api/soundscapes")
async def get_soundscapes():
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    configs = conn.execute("SELECT * FROM soundscape_config").fetchall()
    available = sorted([f.name for f in SOUNDSCAPES_DIR.iterdir() if f.suffix in (".wav", ".ogg", ".mp3", ".flac")]) if SOUNDSCAPES_DIR.exists() else []
    conn.close()
    return ok({"configs": [dict(c) for c in configs], "available_sounds": available, "soundscape_dir": "/soundscapes/"})

@app.patch("/api/soundscapes/{mode}")
async def update_soundscape(mode: str, update: SoundscapeUpdate):
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    existing = conn.execute("SELECT * FROM soundscape_config WHERE mode = ?", (mode,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(404, f"No config for mode '{mode}'")
    sets, vals = [], []
    if update.sound_file is not None: sets.append("sound_file = ?"); vals.append(update.sound_file)
    if update.volume is not None: sets.append("volume = ?"); vals.append(max(0, min(1, update.volume)))
    if update.loop is not None: sets.append("loop = ?"); vals.append(1 if update.loop else 0)
    if sets: vals.append(mode); conn.execute(f"UPDATE soundscape_config SET {', '.join(sets)} WHERE mode = ?", vals)
    conn.commit(); conn.close()
    return ok({"mode": mode})

# ── Declarative Language ──
@app.post("/api/declarative")
async def declarative_translate(req: LLMRequest):
    system = ("Translate imperative demands into declarative, non-coercive language. "
              "Example: 'You must finish this report by Friday' → 'The report deadline is approaching on Friday.' "
              "Never use 'you need to', 'you must', 'you should'. Keep it factual.")
    result = await call_llm(system, req.prompt, max_tokens=200)
    return ok({"original": req.prompt, "declarative": result})

# ── Crisis Mode ──
@app.post("/api/crisis/activate")
async def activate_crisis(store: DataStore = Depends(get_store)):
    cid = store.activate_crisis("sensory_overload")
    today = date.today().isoformat()
    store.set_mode(today, "red")
    return ok({"crisis_id": cid, "status": "activated", "actions": ["demand_eradication", "sensory_blackout", "grounding_mode"]})

@app.post("/api/crisis/resolve")
async def resolve_crisis(store: DataStore = Depends(get_store)):
    resolved = store.resolve_crisis()
    return ok({"status": "resolved" if resolved else "none_active"})

@app.get("/api/energy-log")
async def get_energy_log(store: DataStore = Depends(get_store)):
    return ok({"log": store.get_energy_log(30)})

# ── Export ──
@app.get("/api/export/json")
async def export_json(store: DataStore = Depends(get_store)):
    return store.export_all()

@app.get("/api/export/markdown")
async def export_markdown(store: DataStore = Depends(get_store)):
    data = store.export_all()
    lines = ["# NeurOS Data Export", f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC", ""]
    lines.append("## Tasks\n")
    for t in data.get("tasks", []):
        icon = "✅" if t.get("status") == "completed" else "⬜"
        rec = f" (↻ {t['recurring']})" if t.get("recurring") else ""
        lines.append(f"- {icon} **{t['title']}**{rec} — {t['spoon_cost']} spoons [{t['energy_tag']}]")
        lines.append("")
    lines.append("## Daily Energy\n")
    for s in data.get("daily_state", []):
        lines.append(f"- **{s['date']}** ({s['mode']}): {s['remaining_spoons']}/{s['total_spoons']} spoons, pain {s['pain_level']}/4")
        if s.get("notes"): lines.append(f"  - {s['notes']}")
        lines.append("")
    lines.append("## Reflections\n")
    for w in data.get("wind_down", []):
        lines.append(f"### {w['date']}")
        if w.get("went_well"): lines.append(f"- Went well: {w['went_well']}")
        if w.get("drained"): lines.append(f"- Drained: {w['drained']}")
        if w.get("tomorrow_one"): lines.append(f"- Tomorrow: {w['tomorrow_one']}")
        lines.append("")
    return PlainTextResponse("\n".join(lines), media_type="text/markdown")

@app.post("/api/export/backup")
async def backup_db():
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"neur-os_backup_{ts}.db"
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    for old in sorted(BACKUP_DIR.glob("neur-os_backup_*.db"), reverse=True)[30:]:
        old.unlink()
    return ok({"backup": str(backup_path)})

# ── Onboarding Chat ──
@app.post("/api/onboarding/chat")
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

# ── Passive Log ──
@app.get("/api/passive-log/today")
async def get_today_logs(store: DataStore = Depends(get_store)):
    return ok({"entries": store.get_today_passive_log()})

@app.post("/api/passive-log/submit")
async def submit_passive_log(data: PassiveLogSubmit, store: DataStore = Depends(get_store)):
    lid = store.submit_passive_log(data.response, data.spoons_at_time, data.current_task_id, data.source)
    return ok({"saved": True, "id": lid})

@app.get("/api/passive-log/check")
async def check_passive_prompt(store: DataStore = Depends(get_store)):
    last = store.last_passive_log_today()
    if last is None:
        return ok({"should_prompt": True, "last_response_minutes_ago": None})
    import datetime as dt
    last_ts = dt.datetime.fromisoformat(last.get("timestamp", ""))
    mins_ago = (dt.datetime.utcnow() - last_ts).total_seconds() / 60
    return ok({"should_prompt": mins_ago >= 60, "last_response_minutes_ago": round(mins_ago)})

# ── Crisis Check ──
@app.post("/api/crisis/check")
async def crisis_check(data: CrisisCheck, store: DataStore = Depends(get_store)):
    score = data.cognitive_load * 0.5 + data.frustration_markers * 0.3 + data.error_rate * 0.2
    trigger = score >= 0.7
    if trigger:
        store.activate_crisis("auto_detected")
    return ok({"trigger": trigger, "confidence": round(score, 2), "threshold": 0.7})

# ── Data Import ──
@app.post("/api/import")
async def import_data(data: dict, store: DataStore = Depends(get_store)):
    imported = {}
    for table in ["daily_state", "tasks", "energy_log", "crisis_log", "timer_sessions", "habits", "wind_down"]:
        rows = data.get(table, [])
        imported[table] = store.import_rows(table, rows) if rows else 0
    return ok({"imported": imported})

# ── Brain Dump ──
@app.post("/api/brain-dump")
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

@app.get("/api/brain-dump")
async def get_brain_dumps(store: DataStore = Depends(get_store)):
    return ok({"dumps": store.list_brain_dumps()})

@app.get("/api/brain-dump/search")
async def search_brain_dumps(q: str = "", store: DataStore = Depends(get_store)):
    if not q: return ok({"dumps": [], "query": q})
    return ok({"dumps": store.search_brain_dumps(q), "query": q})

# ── Pacing ──
@app.get("/api/pacing/envelope")
async def pacing_envelope(store: DataStore = Depends(get_store)):
    state = store.get_state()
    tasks = store.get_tasks("active")
    recent = store.recent_energy(7)
    current = state["remaining_spoons"] / max(state["total_spoons"], 1) * 100
    history = [e["spoons_remaining"] * 10 for e in recent]
    return ok(energy_envelope(current, len(tasks), history))

@app.get("/api/pacing/boom-bust")
async def boom_bust(store: DataStore = Depends(get_store)):
    recent = store.recent_energy(7)
    history = [e["spoons_remaining"] * 10 for e in recent]
    return ok(detect_boom_bust(history))

@app.get("/api/pacing/patterns")
async def energy_patterns(store: DataStore = Depends(get_store)):
    return ok(store.energy_patterns())

# ── Dopamine Menu ──
@app.get("/api/dopamine-menu")
async def get_dopamine_menu(store: DataStore = Depends(get_store)):
    return store.get_dopamine_menu()

@app.post("/api/dopamine-menu")
async def add_dopamine_item(data: dict, store: DataStore = Depends(get_store)):
    store.add_dopamine_item(data)
    return ok({"status": "ok"})

@app.delete("/api/dopamine-menu/{item_id}")
async def delete_dopamine_item(item_id: str, store: DataStore = Depends(get_store)):
    store.delete_dopamine_item(item_id)
    return ok({"status": "ok"})

# ── Interoception ──
@app.post("/api/interoception")
async def log_interoception(data: dict, store: DataStore = Depends(get_store)):
    store.log_interoception(data.get("signals", []), data.get("mood", ""), data.get("note", ""))
    return ok({"status": "ok"})

@app.get("/api/interoception")
async def get_interoception(store: DataStore = Depends(get_store)):
    return ok({"logs": store.get_interoception()})

# ── Templates ──
@app.get("/api/templates")
async def get_templates(type: str = "dopamine_menu", store: DataStore = Depends(get_store)):
    return store.get_template(type)

@app.post("/api/templates")
async def import_template(data: dict, store: DataStore = Depends(get_store)):
    count = store.import_template_items(data.get("type", ""), data.get("items", []))
    return ok({"imported": count})

# ── E2EE Sync Relay ──
@app.post("/api/sync/upload")
async def sync_upload(data: dict, store: DataStore = Depends(get_store)):
    store.sync_upload(data["device_id"], data.get("collection", "tasks"), data["encrypted_blob"], data.get("version", 1))
    return ok({"status": "ok"})

@app.get("/api/sync/download")
async def sync_download(device_id: str = "", collection: str = "tasks", since: str = "", store: DataStore = Depends(get_store)):
    return ok({"blobs": store.sync_download(device_id, collection, since)})

# ── Admin Night Mode ──
admin_rooms: dict[str, dict] = {}

@app.post("/api/admin-night/rooms")
async def create_admin_room():
    room_id = str(uuid.uuid4())[:8]
    admin_rooms[room_id] = {"connections": [], "timer_running": False, "timer_elapsed": 0, "created_at": datetime.utcnow().isoformat()}
    return ok({"room_id": room_id})

@app.get("/api/admin-night/rooms")
async def list_admin_rooms():
    return ok({"rooms": [{"room_id": k, "user_count": len(v["connections"]), "timer_running": v["timer_running"]} for k, v in admin_rooms.items()]})

@app.websocket("/api/admin-night/ws/{room_id}")
async def admin_night_ws(websocket: WebSocket, room_id: str):
    await websocket.accept()
    if room_id not in admin_rooms:
        admin_rooms[room_id] = {"connections": [], "timer_running": False, "timer_elapsed": 0, "created_at": datetime.utcnow().isoformat()}
    room = admin_rooms[room_id]
    room["connections"].append(websocket)
    try:
        presence = {"type": "presence", "count": len([c for c in room["connections"] if c.client_state.name == "CONNECTED"])}
        for c in room["connections"]:
            try: await c.send_json(presence)
            except: pass
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "timer_sync":
                room["timer_running"] = msg.get("running", room["timer_running"])
                room["timer_elapsed"] = msg.get("elapsed", room["timer_elapsed"])
                for c in room["connections"]:
                    try: await c.send_json({"type": "timer_sync", "running": room["timer_running"], "elapsed": room["timer_elapsed"]})
                    except: pass
            elif msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in room["connections"]:
            room["connections"].remove(websocket)

# ── Serve Frontend ──
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index = FRONTEND_DIR / "index.html"
    return HTMLResponse(index.read_text()) if index.exists() else HTMLResponse("<h1>NeurOS</h1><p>Frontend not built yet.</p>")

@app.get("/{path:path}")
async def serve_static(path: str):
    if path.startswith("soundscapes/"):
        sound_file = SOUNDSCAPES_DIR / path[len("soundscapes/"):]
        if sound_file.exists() and sound_file.is_file():
            return FileResponse(str(sound_file))
    file = FRONTEND_DIR / path
    if file.exists() and file.is_file():
        return FileResponse(str(file))
    index = FRONTEND_DIR / "index.html"
    return HTMLResponse(index.read_text()) if index.exists() else HTTPException(404)
