# neur-os backend v0.3
"""
Neuro-Affirming Cognitive Prosthetic — Backend API
Local-first, privacy-preserving, trauma-informed.
Traffic-light pacing, single-task focus, wind-down, body doubling.
"""

from __future__ import annotations

import json
import os
import sqlite3
import shutil
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "neur-os.db"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)
SOUNDSCAPES_DIR = Path(__file__).parent / "soundscapes"
SOUNDSCAPES_DIR.mkdir(exist_ok=True)
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
LM_MODEL = os.getenv("LM_MODEL", "qwythos-9b-claude-mythos-5-1m")

app = FastAPI(title="NeurOS", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Database ──────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily_state (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL UNIQUE,
            total_spoons INTEGER NOT NULL DEFAULT 10,
            remaining_spoons REAL NOT NULL DEFAULT 10,
            pain_level INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            mode TEXT DEFAULT 'green'
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            spoon_cost REAL DEFAULT 1,
            micro_chunks TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            energy_tag TEXT DEFAULT 'medium',
            recurring TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS energy_log (
            id TEXT PRIMARY KEY,
            timestamp TEXT DEFAULT (datetime('now')),
            spoons_remaining REAL NOT NULL,
            pain_level INTEGER DEFAULT 0,
            note TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS crisis_log (
            id TEXT PRIMARY KEY,
            timestamp TEXT DEFAULT (datetime('now')),
            crisis_type TEXT NOT NULL,
            triggered_by TEXT DEFAULT 'manual',
            resolved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS timer_sessions (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            duration_minutes INTEGER NOT NULL DEFAULT 25,
            elapsed_seconds INTEGER NOT NULL DEFAULT 0,
            status TEXT DEFAULT 'running',
            started_at TEXT DEFAULT (datetime('now')),
            paused_at TEXT,
            completed_at TEXT,
            soundscape TEXT DEFAULT '',
            body_doubling INTEGER DEFAULT 0,
            started_as TEXT DEFAULT 'focus'
        );
        CREATE TABLE IF NOT EXISTS habits (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            frequency TEXT DEFAULT 'daily',
            spoon_cost REAL DEFAULT 0.5,
            energy_tag TEXT DEFAULT 'low',
            grace_period INTEGER DEFAULT 3,  -- Free Days: can miss this many times
            last_completed TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS soundscape_config (
            id TEXT PRIMARY KEY,
            mode TEXT NOT NULL UNIQUE,
            sound_file TEXT DEFAULT '',
            volume REAL DEFAULT 0.5,
            loop INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS wind_down (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL UNIQUE,
            went_well TEXT DEFAULT '',
            drained TEXT DEFAULT '',
            tomorrow_one TEXT DEFAULT '',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS passive_log (
            id TEXT PRIMARY KEY,
            timestamp TEXT DEFAULT (datetime('now')),
            response TEXT NOT NULL,
            spoons_at_time REAL,
            current_task_id TEXT,
            source TEXT DEFAULT 'notification'
        );
        CREATE TABLE IF NOT EXISTS onboarding_state (
            id TEXT PRIMARY KEY DEFAULT 'current',
            phase INTEGER DEFAULT 0,
            turns INTEGER DEFAULT 0,
            extracted_profile TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS brain_dumps (
            id TEXT PRIMARY KEY,
            raw_text TEXT NOT NULL,
            structured_json TEXT DEFAULT '{}',
            source TEXT DEFAULT 'textarea',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS dopamine_menu_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            energy_required REAL DEFAULT 0.5,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS interoception_log (
            id TEXT PRIMARY KEY,
            signals TEXT NOT NULL,
            mood TEXT DEFAULT '',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    # Seed default soundscape configs
    default_sounds = [
        ("focus", "brown_noise.wav", 0.3, 1),
        ("grounding", "rain.wav", 0.4, 1),
        ("crisis", "breathing_tone.wav", 0.2, 1),
    ]
    for mode, sound, vol, loop in default_sounds:
        conn.execute(
            "INSERT OR IGNORE INTO soundscape_config (id, mode, sound_file, volume, loop) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), mode, sound, vol, loop),
        )
    # Seed default dopamine menu items
    defaults = [
        ("Deep breaths (2 min)", "starters", 0.2, 1),
        ("Stretch break", "starters", 0.3, 2),
        ("Listen to a song", "starters", 0.3, 3),
        ("Podcast while cleaning", "sides", 0.5, 1),
        ("Fidget toy during meeting", "sides", 0.4, 2),
        ("Body doubling (virtual)", "sides", 0.5, 3),
        ("Walk outside", "mains", 2.0, 1),
        ("Nap or rest", "mains", 1.5, 2),
        ("Creative project", "mains", 2.5, 3),
        ("Guilty pleasure show", "desserts", 1.0, 1),
        ("Doomscroll (timered)", "desserts", 0.5, 2),
        ("Online window shopping", "desserts", 0.5, 3),
    ]
    for name, cat, energy, order in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO dopamine_menu_items (id, name, category, energy_required, sort_order) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), name, cat, energy, order),
        )
    conn.commit()
    conn.close()

init_db()

# ── Domain Services ─────────────────────────────────
def energy_envelope(current_pct: float, tasks_today: int, history: list[float]) -> dict:
    """Calculate safe energy envelope. Returns {recommended_max, recommended_min, current_usage, status}."""
    avg_daily_drain = 0.3  # default: each task drains ~30% energy (approximate)
    if history and len(history) >= 3:
        avg_daily_drain = sum(history[i] - history[i+1] for i in range(len(history)-1) if history[i] > history[i+1]) / max(len(history)-1, 1)
    current_usage = tasks_today * avg_daily_drain
    recommended_max = current_pct * 0.8  # never use more than 80% of available
    recommended_min = current_pct * 0.15  # always save at least 15%
    status = "ok"
    if tasks_today > 0 and current_usage > recommended_max:
        status = "over"
    elif current_pct <= 20:
        status = "low"
    return {"recommended_max": round(recommended_max, 1), "recommended_min": round(recommended_min, 1), "current_usage": round(current_usage, 1), "status": status}

def detect_boom_bust(history: list[float]) -> dict:
    """Detect boom-bust patterns in energy history."""
    if len(history) < 5:
        return {"pattern": "stable", "confidence": 0.0, "message": "Not enough data yet"}
    # Check for boom (3+ high days) followed by bust (2+ low days)
    high_threshold = 60  # above this is "high energy"
    low_threshold = 30   # below this is "bust"
    recent = history[-5:]
    high_days = sum(1 for h in recent[:3] if h >= high_threshold)
    low_days = sum(1 for h in recent[3:] if h < low_threshold)
    if high_days >= 2 and low_days >= 2:
        confidence = min((high_days + low_days) / 5.0, 1.0)
        return {"pattern": "boom-bust", "confidence": round(confidence, 2), "message": "You've been pushing hard. Tomorrow might feel rough. Want to schedule rest?"}
    # Check declining pattern
    if len(recent) >= 3 and all(recent[i] < recent[i-1] for i in range(1, len(recent))):
        return {"pattern": "declining", "confidence": 0.6, "message": "Your energy has been decreasing. A rest day might help."}
    return {"pattern": "stable", "confidence": 0.5, "message": "Energy pattern looks consistent."}

# ── Models ────────────────────────────────────────────────────────
class SpoonCheckIn(BaseModel):
    spoons: int
    pain_level: int = 0
    note: str = ""

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    spoon_cost: Optional[float] = None
    energy_tag: str = "medium"
    recurring: str = ""

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    spoon_cost: Optional[float] = None
    micro_chunks: Optional[list[str]] = None

class HabitCreate(BaseModel):
    title: str
    description: str = ""
    frequency: str = "daily"
    spoon_cost: float = 0.5
    energy_tag: str = "low"

class TimerAction(BaseModel):
    task_id: Optional[str] = None
    duration_minutes: int = 25
    action: str = "start"
    soundscape: str = ""
    body_doubling: bool = False
    started_as: str = "focus"
    count_up: bool = True  # Count-up timer by default (no reset needed)

class WindDownEntry(BaseModel):
    went_well: str = ""
    drained: str = ""
    tomorrow_one: str = ""
    note: str = ""

class ModeUpdate(BaseModel):
    mode: str  # green, amber, red

class SoundscapeUpdate(BaseModel):
    sound_file: Optional[str] = None
    volume: Optional[float] = None
    loop: Optional[bool] = None

class BrainDumpRequest(BaseModel):
    text: str
    source: str = "textarea"
    declarative: bool = False  # ponytail: pipe through declarative rewrite before organizing

class LLMRequest(BaseModel):
    prompt: str

class PassiveLogSubmit(BaseModel):
    response: str
    spoons_at_time: Optional[float] = None
    current_task_id: Optional[str] = None
    source: str = "notification"

class CrisisCheck(BaseModel):
    cognitive_load: float = 0.0
    frustration_markers: float = 0.0
    error_rate: float = 0.0

class OnboardingChat(BaseModel):
    history: list[dict] = []
    turn: int = 0

# ── LLM Client ────────────────────────────────────────────────────
async def call_llm(system: str, user: str, max_tokens: int = 512, model: str = "") -> str:
    """Call LM Studio's local LLM endpoint with fast timeout."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=2.0)) as client:
            payload = {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.1,
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

# ── Energy Tags ───────────────────────────────────────────────────
ENERGY_TAGS = {"low": 0.5, "medium": 1.0, "high": 2.0}

# ── Check-In ──────────────────────────────────────────────────────
@app.post("/api/check-in")
async def morning_checkin(data: SpoonCheckIn):
    conn = get_db()
    today = date.today().isoformat()
    existing = conn.execute("SELECT id FROM daily_state WHERE date = ?", (today,)).fetchone()
    # Auto-suggest mode based on spoons
    suggested_mode = "green"
    if data.spoons <= 3:
        suggested_mode = "red"
    elif data.spoons <= 5:
        suggested_mode = "amber"

    if existing:
        conn.execute(
            "UPDATE daily_state SET total_spoons = ?, remaining_spoons = ?, pain_level = ?, notes = ? WHERE date = ?",
            (data.spoons, data.spoons, data.pain_level, data.note, today),
        )
    else:
        conn.execute(
            "INSERT INTO daily_state (id, date, total_spoons, remaining_spoons, pain_level, notes, mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), today, data.spoons, data.spoons, data.pain_level, data.note, suggested_mode),
        )
    conn.execute(
        "INSERT INTO energy_log (id, spoons_remaining, pain_level, note) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), data.spoons, data.pain_level, data.note),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "spoons": data.spoons, "pain_level": data.pain_level, "suggested_mode": suggested_mode}

# ── Mode (Traffic Light) ─────────────────────────────────────────
@app.get("/api/mode")
async def get_mode():
    conn = get_db()
    today = date.today().isoformat()
    state = conn.execute("SELECT mode FROM daily_state WHERE date = ?", (today,)).fetchone()
    conn.close()
    return {"mode": state["mode"] if state else "green"}

@app.put("/api/mode")
async def set_mode(data: ModeUpdate):
    if data.mode not in ("green", "amber", "red"):
        raise HTTPException(400, "Mode must be green, amber, or red")
    conn = get_db()
    today = date.today().isoformat()
    existing = conn.execute("SELECT id FROM daily_state WHERE date = ?", (today,)).fetchone()
    if existing:
        conn.execute("UPDATE daily_state SET mode = ? WHERE date = ?", (data.mode, today))
    else:
        conn.execute(
            "INSERT INTO daily_state (id, date, total_spoons, remaining_spoons, mode) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), today, 10, 10, data.mode),
        )
    conn.commit()
    conn.close()
    return {"mode": data.mode, "status": "ok"}

# ── State ─────────────────────────────────────────────────────────
@app.get("/api/state")
async def get_state():
    conn = get_db()
    today = date.today().isoformat()
    state = conn.execute("SELECT * FROM daily_state WHERE date = ?", (today,)).fetchone()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE status = 'active' ORDER BY energy_tag, created_at"
    ).fetchall()
    active_timer = conn.execute(
        "SELECT * FROM timer_sessions WHERE status IN ('running','paused') ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return {
        "state": dict(state) if state else {"total_spoons": 10, "remaining_spoons": 10, "pain_level": 0, "mode": "green"},
        "tasks": [dict(t) for t in tasks],
        "active_timer": dict(active_timer) if active_timer else None,
    }

# ── Next Task (single-task focus) ─────────────────────────────────
@app.get("/api/tasks/next")
async def get_next_task():
    """Return the single best task for the current energy level."""
    conn = get_db()
    today = date.today().isoformat()
    state = conn.execute("SELECT * FROM daily_state WHERE date = ?", (today,)).fetchone()
    mode = state["mode"] if state else "green"
    remaining = state["remaining_spoons"] if state else 10

    # Different task selection per mode
    if mode == "red":
        # Red = show no tasks, suggest rest
        conn.close()
        return {"task": None, "mode": "red", "message": "Today might be a rest day. That's okay."}

    # Get active tasks sorted by best match
    if mode == "amber":
        # Amber = low-spoon tasks first
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE status = 'active' AND spoon_cost <= ? AND energy_tag IN ('low','medium') ORDER BY spoon_cost ASC, created_at ASC",
            (min(remaining, 2),),
        ).fetchall()
    else:
        # Green = highest spoon task you can afford (use energy while you have it)
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE status = 'active' AND spoon_cost <= ? ORDER BY spoon_cost DESC, created_at ASC",
            (remaining,),
        ).fetchall()

    conn.close()
    if not tasks:
        return {"task": None, "mode": mode, "message": "No tasks fit your current energy."}
    return {"task": dict(tasks[0]), "mode": mode, "message": None}

# ── Tasks ─────────────────────────────────────────────────────────
@app.post("/api/tasks")
async def create_task(task: TaskCreate):
    task_id = str(uuid.uuid4())
    spoon_cost = task.spoon_cost or ENERGY_TAGS.get(task.energy_tag, 1.0)

    if task.spoon_cost is None:
        system = "Estimate spoon cost (1-5). 1=easy, 5=exhausting. Reply with JUST a number."
        user = f"Task: {task.title}. {task.description}"
        llm_response = await call_llm(system, user, max_tokens=10)
        try:
            parsed = float(llm_response.strip())
            spoon_cost = max(0.5, min(5.0, parsed))
        except (ValueError, TypeError):
            pass

    system = "Break this task into 2-4 tiny actionable micro-steps. Return as JSON array of strings."
    user = f"Task: {task.title}. {task.description}"
    chunk_response = await call_llm(system, user, max_tokens=300)
    # ponytail: strip think/reasoning tags before parsing
    import re
    chunk_response = re.sub(r'<think>.*?</think>', '', chunk_response, flags=re.DOTALL).strip()
    micro_chunks = []
    try:
        parsed = chunk_response.strip()
        if parsed.startswith("["):
            micro_chunks = json.loads(parsed)
        elif parsed.startswith("```"):
            cleaned = parsed.strip("`").removeprefix("json").strip()
            micro_chunks = json.loads(cleaned)
        else:
            micro_chunks = [line.strip("- ").strip() for line in parsed.split("\n") if line.strip()]
    except (json.JSONDecodeError, Exception):
        micro_chunks = [f"Start: {task.title}"]

    conn = get_db()
    conn.execute(
        "INSERT INTO tasks (id, title, description, spoon_cost, micro_chunks, energy_tag, recurring) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (task_id, task.title, task.description, spoon_cost, json.dumps(micro_chunks), task.energy_tag, task.recurring),
    )
    conn.commit()
    conn.close()
    return {"id": task_id, "spoon_cost": spoon_cost, "micro_chunks": micro_chunks}

@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, update: TaskUpdate):
    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        raise HTTPException(404, "Task not found")
    if update.status == "completed":
        conn.execute("UPDATE tasks SET status = ?, completed_at = datetime('now') WHERE id = ?", ("completed", task_id))
    if update.spoon_cost is not None:
        conn.execute("UPDATE tasks SET spoon_cost = ? WHERE id = ?", (update.spoon_cost, task_id))
    if update.micro_chunks is not None:
        conn.execute("UPDATE tasks SET micro_chunks = ? WHERE id = ?", (json.dumps(update.micro_chunks), task_id))
    conn.commit()
    conn.close()
    return {"status": "updated"}

@app.post("/api/tasks/{task_id}/expend")
async def expend_spoons(task_id: str):
    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        raise HTTPException(404, "Task not found")
    today = date.today().isoformat()
    state = conn.execute("SELECT * FROM daily_state WHERE date = ?", (today,)).fetchone()
    if state:
        cost = task["spoon_cost"]
        new_remaining = max(0, state["remaining_spoons"] - cost)
        conn.execute("UPDATE daily_state SET remaining_spoons = ? WHERE date = ?", (new_remaining, today))

    conn.execute("UPDATE tasks SET status = 'completed', completed_at = datetime('now') WHERE id = ?", (task_id,))
    conn.execute(
        "INSERT INTO energy_log (id, spoons_remaining, note) VALUES (?, ?, ?)",
        (str(uuid.uuid4()), state["remaining_spoons"] - task["spoon_cost"] if state else 0, f"Completed: {task['title']}"),
    )
    if task["recurring"]:
        new_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO tasks (id, title, description, spoon_cost, micro_chunks, energy_tag, recurring) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id, task["title"], task["description"], task["spoon_cost"], task["micro_chunks"], task["energy_tag"], task["recurring"]),
        )
    conn.commit()
    conn.close()
    return {"status": "completed", "spoons_deducted": task["spoon_cost"]}

# ── Habits ────────────────────────────────────────────────────────
@app.get("/api/habits")
async def get_habits():
    conn = get_db()
    today = date.today().isoformat()
    habits = conn.execute(
        "SELECT h.*, (h.last_completed = ?) AS done_today FROM habits h ORDER BY h.created_at",
        (today,),
    ).fetchall()
    conn.close()
    return {"habits": [dict(h) for h in habits]}

@app.post("/api/habits")
async def create_habit(habit: HabitCreate):
    hid = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO habits (id, title, description, frequency, spoon_cost, energy_tag) VALUES (?, ?, ?, ?, ?, ?)",
        (hid, habit.title, habit.description, habit.frequency, habit.spoon_cost, habit.energy_tag),
    )
    conn.commit()
    conn.close()
    return {"id": hid}

@app.post("/api/habits/{hid}/check")
async def check_habit(hid: str):
    """Mark a habit as completed today. No streaks or badges — just completion."""
    conn = get_db()
    habit = conn.execute("SELECT * FROM habits WHERE id = ?", (hid,)).fetchone()
    if not habit:
        raise HTTPException(404, "Habit not found")
    today = date.today().isoformat()
    # Mark as completed — no streak tracking
    conn.execute(
        "UPDATE habits SET last_completed = ? WHERE id = ?",
        (today, hid),
    )
    conn.commit()
    conn.close()
    return {"done_today": True}

# ── Timer / Focus Sessions ────────────────────────────────────────
@app.post("/api/timer")
async def timer_action(data: TimerAction):
    conn = get_db()
    if data.action == "start":
        conn.execute("UPDATE timer_sessions SET status = 'stopped', completed_at = datetime('now') WHERE status IN ('running','paused')")
        tid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO timer_sessions (id, task_id, duration_minutes, soundscape, body_doubling, started_as) VALUES (?, ?, ?, ?, ?, ?)",
            (tid, data.task_id, data.duration_minutes, data.soundscape, 1 if data.body_doubling else 0, data.started_as),
        )
        conn.commit()
        conn.close()
        return {"id": tid, "status": "running", "duration_minutes": data.duration_minutes, "body_doubling": data.body_doubling, "started_as": data.started_as}

    elif data.action == "pause":
        current = conn.execute("SELECT * FROM timer_sessions WHERE status = 'running' ORDER BY started_at DESC LIMIT 1").fetchone()
        if not current:
            raise HTTPException(400, "No running timer")
        try:
            elapsed = int((datetime.utcnow() - datetime.strptime(current["started_at"][:19], "%Y-%m-%d %H:%M:%S")).total_seconds())
        except ValueError:
            elapsed = 0
        total_elapsed = current["elapsed_seconds"] + elapsed
        conn.execute("UPDATE timer_sessions SET status = 'paused', elapsed_seconds = ?, paused_at = datetime('now') WHERE id = ?",
                     (total_elapsed, current["id"]))
        conn.commit()
        conn.close()
        return {"id": current["id"], "status": "paused", "elapsed_seconds": total_elapsed}

    elif data.action == "resume":
        current = conn.execute("SELECT * FROM timer_sessions WHERE status = 'paused' ORDER BY started_at DESC LIMIT 1").fetchone()
        if not current:
            raise HTTPException(400, "No paused timer")
        conn.execute("UPDATE timer_sessions SET status = 'running', paused_at = NULL, started_at = datetime('now') WHERE id = ?", (current["id"],))
        conn.commit()
        conn.close()
        return {"id": current["id"], "status": "running"}

    elif data.action == "stop":
        current = conn.execute("SELECT * FROM timer_sessions WHERE status IN ('running','paused') ORDER BY started_at DESC LIMIT 1").fetchone()
        if not current:
            raise HTTPException(400, "No active timer")
        elapsed = 0
        if current["status"] == "running":
            try:
                elapsed = int((datetime.utcnow() - datetime.strptime(current["started_at"][:19], "%Y-%m-%d %H:%M:%S")).total_seconds())
            except ValueError:
                elapsed = 0
        total_elapsed = current["elapsed_seconds"] + elapsed
        conn.execute("UPDATE timer_sessions SET status = 'completed', elapsed_seconds = ?, completed_at = datetime('now') WHERE id = ?",
                     (total_elapsed, current["id"]))
        conn.commit()
        conn.close()
        return {"id": current["id"], "status": "completed", "elapsed_seconds": total_elapsed}

    raise HTTPException(400, "Invalid action")

@app.get("/api/timer/active")
async def get_active_timer():
    conn = get_db()
    timer = conn.execute("SELECT * FROM timer_sessions WHERE status IN ('running','paused') ORDER BY started_at DESC LIMIT 1").fetchone()
    conn.close()
    if not timer:
        return {"timer": None}
    elapsed = timer["elapsed_seconds"]
    if timer["status"] == "running":
        try:
            elapsed += int((datetime.utcnow() - datetime.strptime(timer["started_at"][:19], "%Y-%m-%d %H:%M:%S")).total_seconds())
        except ValueError:
            pass
    result = dict(timer)
    result["current_elapsed"] = elapsed
    return {"timer": result}

# ── Wind-Down ─────────────────────────────────────────────────────
@app.post("/api/wind-down")
async def save_wind_down(data: WindDownEntry):
    conn = get_db()
    today = date.today().isoformat()
    existing = conn.execute("SELECT id FROM wind_down WHERE date = ?", (today,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE wind_down SET went_well = ?, drained = ?, tomorrow_one = ?, note = ? WHERE date = ?",
            (data.went_well, data.drained, data.tomorrow_one, data.note, today),
        )
    else:
        conn.execute(
            "INSERT INTO wind_down (id, date, went_well, drained, tomorrow_one, note) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), today, data.went_well, data.drained, data.tomorrow_one, data.note),
        )
    conn.commit()
    conn.close()
    return {"status": "ok", "date": today}

@app.get("/api/wind-down/today")
async def get_wind_down():
    conn = get_db()
    today = date.today().isoformat()
    entry = conn.execute("SELECT * FROM wind_down WHERE date = ?", (today,)).fetchone()
    conn.close()
    return {"entry": dict(entry) if entry else None}

@app.get("/api/wind-down/week")
async def get_week_wind_down():
    conn = get_db()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    entries = conn.execute(
        "SELECT * FROM wind_down WHERE date >= ? ORDER BY date DESC", (week_ago,)
    ).fetchall()
    conn.close()
    return {"entries": [dict(e) for e in entries]}

# ── Weekly Review ─────────────────────────────────────────────────
@app.get("/api/review/week")
async def weekly_review():
    conn = get_db()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    today = date.today().isoformat()

    energy_states = conn.execute(
        "SELECT * FROM daily_state WHERE date >= ? AND date <= ? ORDER BY date", (week_ago, today)
    ).fetchall()
    completed = conn.execute(
        "SELECT * FROM tasks WHERE completed_at IS NOT NULL AND date(completed_at) >= ? ORDER BY completed_at DESC", (week_ago,)
    ).fetchall()
    energy_entries = conn.execute(
        "SELECT * FROM energy_log WHERE date(timestamp) >= ? ORDER BY timestamp", (week_ago,)
    ).fetchall()
    timer_sessions = conn.execute(
        "SELECT * FROM timer_sessions WHERE date(started_at) >= ? ORDER BY started_at", (week_ago,)
    ).fetchall()
    crises = conn.execute(
        "SELECT * FROM crisis_log WHERE date(timestamp) >= ? ORDER BY timestamp DESC", (week_ago,)
    ).fetchall()
    habits = conn.execute("SELECT title FROM habits ORDER BY created_at").fetchall()
    wind_entries = conn.execute(
        "SELECT * FROM wind_down WHERE date >= ? ORDER BY date DESC", (week_ago,)
    ).fetchall()
    conn.close()

    avg_spoons = 0
    avg_pain = 0
    if energy_states:
        avg_spoons = sum(float(s["total_spoons"]) for s in energy_states) / len(energy_states)
        avg_pain = sum(s["pain_level"] for s in energy_states) / len(energy_states)

    total_focus_minutes = 0
    for ts in timer_sessions:
        if ts["status"] in ("completed", "stopped"):
            total_focus_minutes += ts["elapsed_seconds"] // 60

    return {
        "energy_states": [dict(s) for s in energy_states],
        "completed_tasks": [dict(t) for t in completed],
        "energy_entries": [dict(e) for e in energy_entries],
        "timer_sessions": [dict(t) for t in timer_sessions],
        "crises": [dict(c) for c in crises],
        "habits": [dict(h) for h in habits],
        "wind_down_entries": [dict(e) for e in wind_entries],
        "insights": {
            "days_tracked": len(energy_states),
            "avg_spoons": round(avg_spoons, 1),
            "avg_pain": round(avg_pain, 1),
            "tasks_completed": len(completed),
            "total_focus_minutes": total_focus_minutes,
            "crisis_count": len(crises),
        },
    }

@app.get("/api/review/insight")
async def generate_insight():
    """Generate a weekly pattern insight from the data."""
    conn = get_db()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    energy_states = conn.execute(
        "SELECT * FROM daily_state WHERE date >= ? ORDER BY date", (week_ago,)
    ).fetchall()
    completed_tasks = conn.execute(
        "SELECT title, energy_tag, spoon_cost FROM tasks WHERE completed_at IS NOT NULL AND date(completed_at) >= ?", (week_ago,)
    ).fetchall()
    wind_entries = conn.execute(
        "SELECT * FROM wind_down WHERE date >= ? ORDER BY date", (week_ago,)
    ).fetchall()
    crises = conn.execute(
        "SELECT date(timestamp) as d FROM crisis_log WHERE date(timestamp) >= ? ORDER BY timestamp", (week_ago,)
    ).fetchall()

    conn.close()

    days_with_data = len(energy_states)
    total_tasks = len(completed_tasks)
    total_crises = len(crises)
    high_spoon_tasks = sum(1 for t in completed_tasks if t["energy_tag"] == "high")

    # Build the insight text locally (LLM-free)
    lines = []
    if days_with_data < 2:
        lines.append("Not enough data yet — check in daily to see patterns emerge.")
    else:
        lines.append(f"**{days_with_data} days** tracked this week.")
        if total_tasks > 0:
            lines.append(f"Completed **{total_tasks} tasks** ({high_spoon_tasks} high-energy).")
        else:
            lines.append("No tasks completed this week — that's okay. Some weeks are for rest.")
        if total_crises > 0:
            lines.append(f"Crisis mode activated **{total_crises} time(s)** this week.")
        if energy_states:
            best_day = max(energy_states, key=lambda s: s["remaining_spoons"])
            lines.append(f"Highest energy day: **{best_day['date']}** ({best_day['remaining_spoons']}/{best_day['total_spoons']} spoons).")
            worst_day = min(energy_states, key=lambda s: s["remaining_spoons"])
            if worst_day["remaining_spoons"] < best_day["remaining_spoons"]:
                lines.append(f"Lowest energy day: **{worst_day['date']}** ({worst_day['remaining_spoons']}/{worst_day['total_spoons']} spoons).")
        if wind_entries:
            themes = []
            for e in wind_entries:
                if e["went_well"]:
                    themes.append(e["went_well"].split(".")[0])
            if themes:
                lines.append(f"Recurring themes: {'; '.join(themes[:3])}.")

    return {"insight": "\n".join(lines)}

# ── Soundscapes ───────────────────────────────────────────────────
@app.get("/api/soundscapes")
async def get_soundscapes():
    conn = get_db()
    configs = conn.execute("SELECT * FROM soundscape_config").fetchall()
    available = []
    if SOUNDSCAPES_DIR.exists():
        available = sorted([f.name for f in SOUNDSCAPES_DIR.iterdir() if f.suffix in (".wav", ".ogg", ".mp3", ".flac")])
    conn.close()
    return {"configs": [dict(c) for c in configs], "available_sounds": available, "soundscape_dir": "/soundscapes/"}

@app.patch("/api/soundscapes/{mode}")
async def update_soundscape(mode: str, update: SoundscapeUpdate):
    conn = get_db()
    existing = conn.execute("SELECT * FROM soundscape_config WHERE mode = ?", (mode,)).fetchone()
    if not existing:
        raise HTTPException(404, f"No config for mode '{mode}'")
    sets = []
    vals = []
    if update.sound_file is not None:
        sets.append("sound_file = ?")
        vals.append(update.sound_file)
    if update.volume is not None:
        sets.append("volume = ?")
        vals.append(max(0, min(1, update.volume)))
    if update.loop is not None:
        sets.append("loop = ?")
        vals.append(1 if update.loop else 0)
    if sets:
        vals.append(mode)
        conn.execute(f"UPDATE soundscape_config SET {', '.join(sets)} WHERE mode = ?", vals)
    conn.commit()
    conn.close()
    return {"status": "updated", "mode": mode}

# ── Declarative Language ──────────────────────────────────────────
@app.post("/api/declarative")
async def declarative_translate(req: LLMRequest):
    system = (
        "Translate imperative demands into declarative, non-coercive language. "
        "Example: 'You must finish this report by Friday' → 'The report deadline is approaching on Friday.' "
        "Never use 'you need to', 'you must', 'you should'. Keep it factual."
    )
    result = await call_llm(system, req.prompt, max_tokens=200)
    return {"original": req.prompt, "declarative": result}

# ── Crisis Mode ───────────────────────────────────────────────────
@app.post("/api/crisis/activate")
async def activate_crisis():
    crisis_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO crisis_log (id, crisis_type) VALUES (?, ?)", (crisis_id, "sensory_overload"))
    # Auto-switch to red mode
    today = date.today().isoformat()
    conn.execute("UPDATE daily_state SET mode = 'red' WHERE date = ?", (today,))
    conn.commit()
    conn.close()
    return {
        "crisis_id": crisis_id,
        "status": "activated",
        "actions": ["demand_eradication", "sensory_blackout", "grounding_mode"],
    }

@app.post("/api/crisis/resolve")
async def resolve_crisis():
    conn = get_db()
    current = conn.execute(
        "SELECT id FROM crisis_log WHERE resolved_at IS NULL ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    if current:
        conn.execute("UPDATE crisis_log SET resolved_at = datetime('now') WHERE id = ?", (current["id"],))
    conn.commit()
    conn.close()
    return {"status": "resolved"}

@app.get("/api/energy-log")
async def get_energy_log():
    conn = get_db()
    rows = conn.execute("SELECT * FROM energy_log ORDER BY timestamp DESC LIMIT 30").fetchall()
    conn.close()
    return {"log": [dict(r) for r in rows]}

# ── Export ────────────────────────────────────────────────────────
@app.get("/api/export/json")
async def export_json():
    conn = get_db()
    data = {}
    for table in ["daily_state", "tasks", "energy_log", "crisis_log", "timer_sessions", "habits", "wind_down"]:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        data[table] = [dict(r) for r in rows]
    conn.close()
    return data

@app.get("/api/export/markdown")
async def export_markdown():
    conn = get_db()
    lines = ["# NeurOS Data Export", f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC", ""]

    lines.append("## Tasks\n")
    tasks = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    for t in tasks:
        icon = "✅" if t["status"] == "completed" else "⬜"
        rec = f" (↻ {t['recurring']})" if t["recurring"] else ""
        lines.append(f"- {icon} **{t['title']}**{rec} — {t['spoon_cost']} spoons [{t['energy_tag']}]")
        lines.append("")

    lines.append("## Daily Energy\n")
    states = conn.execute("SELECT * FROM daily_state ORDER BY date DESC").fetchall()
    for s in states:
        lines.append(f"- **{s['date']}** ({s['mode']}): {s['remaining_spoons']}/{s['total_spoons']} spoons, pain {s['pain_level']}/4")
        if s["notes"]:
            lines.append(f"  - {s['notes']}")
        lines.append("")

    lines.append("## Reflections\n")
    winds = conn.execute("SELECT * FROM wind_down ORDER BY date DESC").fetchall()
    for w in winds:
        lines.append(f"### {w['date']}")
        if w["went_well"]: lines.append(f"- Went well: {w['went_well']}")
        if w["drained"]: lines.append(f"- Drained: {w['drained']}")
        if w["tomorrow_one"]: lines.append(f"- Tomorrow: {w['tomorrow_one']}")
        lines.append("")

    conn.close()
    return PlainTextResponse("\n".join(lines), media_type="text/markdown")

@app.post("/api/export/backup")
async def backup_db():
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"neur-os_backup_{ts}.db"
    shutil.copy2(DB_PATH, backup_path)
    backups = sorted(BACKUP_DIR.glob("neur-os_backup_*.db"), reverse=True)
    for old in backups[30:]:
        old.unlink()
    return {"backup": str(backup_path), "path": str(backup_path)}

# ── Onboarding Chat ─────────────────────────────────────────────
@app.post("/api/onboarding/chat")
async def onboarding_chat(data: OnboardingChat):
    # ponytail: hardcoded questions — deterministic, instant, no LLM dependency
    questions = [
        "What kind of tasks do you need the most help keeping track of?",
        "What time of day do you usually have the most energy?",
        "When you're overwhelmed, what helps you recharge?",
        "What's one thing you'd like to be able to do more consistently?",
    ]
    if data.turn >= len(questions):
        result = "done"
    else:
        result = questions[data.turn]
    # Save onboarding state
    conn = get_db()
    existing = conn.execute("SELECT extracted_profile FROM onboarding_state WHERE id='current'").fetchone()
    profile = {}
    if existing:
        try: profile = json.loads(existing["extracted_profile"])
        except: pass
    if data.history:
        profile[f"turn_{data.turn}"] = data.history[-1]["content"] if data.history else ""
    conn.execute(
        "INSERT OR REPLACE INTO onboarding_state (id, phase, turns, extracted_profile, updated_at) "
        "VALUES ('current', ?, ?, ?, datetime('now'))",
        (min(data.turn + 1, 5), data.turn + 1, json.dumps(profile)),
    )
    conn.commit()
    return {"response": result, "turn": data.turn + 1, "done": data.turn >= len(questions) - 1}

# ── Passive Log ──────────────────────────────────────────────────
@app.get("/api/passive-log/today")
async def get_today_logs():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, timestamp, response, spoons_at_time, current_task_id, source "
        "FROM passive_log WHERE date(timestamp) = date('now') ORDER BY timestamp"
    ).fetchall()
    return {"entries": [dict(r) for r in rows]}

@app.post("/api/passive-log/submit")
async def submit_passive_log(data: PassiveLogSubmit):
    conn = get_db()
    lid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO passive_log (id, response, spoons_at_time, current_task_id, source) VALUES (?, ?, ?, ?, ?)",
        (lid, data.response, data.spoons_at_time, data.current_task_id, data.source),
    )
    conn.commit()
    return {"saved": True, "id": lid}

@app.get("/api/passive-log/check")
async def check_passive_prompt():
    conn = get_db()
    row = conn.execute(
        "SELECT timestamp FROM passive_log WHERE date(timestamp) = date('now') ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return {"should_prompt": True, "last_response_minutes_ago": None}
    from datetime import datetime
    last = datetime.fromisoformat(row["timestamp"])
    mins_ago = (datetime.utcnow() - last).total_seconds() / 60
    return {"should_prompt": mins_ago >= 60, "last_response_minutes_ago": round(mins_ago)}

# ── Crisis Check ─────────────────────────────────────────────────
@app.post("/api/crisis/check")
async def crisis_check(data: CrisisCheck):
    score = data.cognitive_load * 0.5 + data.frustration_markers * 0.3 + data.error_rate * 0.2
    trigger = score >= 0.7
    if trigger:
        conn = get_db()
        conn.execute(
            "INSERT INTO crisis_log (id, crisis_type, triggered_by) VALUES (?, ?, ?)",
            (uuid.uuid4().hex, "auto_detected", "heuristic"),
        )
        conn.commit()
    return {"trigger": trigger, "confidence": round(score, 2), "threshold": 0.7}

# ── Data Import ───────────────────────────────────────────────────
@app.post("/api/import")
async def import_data(data: dict):
    """Import previously exported JSON data. Merges into existing DB."""
    conn = get_db()
    imported = {}
    for table in ["daily_state", "tasks", "energy_log", "crisis_log", "timer_sessions", "habits", "wind_down"]:
        rows = data.get(table, [])
        count = 0
        for row in rows:
            cols = ", ".join(row.keys())
            placeholders = ", ".join("?" for _ in row)
            vals = list(row.values())
            try:
                conn.execute(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})", vals)
                count += 1
            except Exception:
                pass
        imported[table] = count
    conn.commit()
    conn.close()
    return {"status": "ok", "imported": imported}

# ── Brain Dump ──────────────────────────────────────────────

@app.post("/api/brain-dump")
async def brain_dump(data: BrainDumpRequest):
    """Accept a raw text brain dump, optionally organize via LLM."""
    bid = str(uuid.uuid4())
    text = data.text
    # ponytail: optional declarative rewrite before organization
    if data.declarative:
        try:
            dec = await call_llm("Rewrite this to be gentle, declarative, and demand-free. Remove urgency, guilt, imperative mood. Keep the meaning.", data.text, max_tokens=200)
            import re; dec = re.sub(r'<think>.*?</think>', '', dec, flags=re.DOTALL).strip()
            if dec and len(dec) > 5: text = dec
        except Exception: pass
    structured = {"tasks": [], "notes": []}
    try:
        system = "Organize this brain dump into tasks and notes. Return JSON: {\"tasks\": [{\"title\": str, \"spoon_cost\": 0.5-5.0, \"energy_tag\": \"low\"|\"medium\"|\"high\"}], \"notes\": [{\"content\": str}]}"
        resp = await call_llm(system, data.text, max_tokens=500)
        import re
        cleaned = re.sub(r'<think>.*?</think>', '', resp, flags=re.DOTALL).strip()
        if cleaned.startswith("{"):
            structured = json.loads(cleaned)
        elif cleaned.startswith("```"):
            structured = json.loads(cleaned.strip("`").removeprefix("json").strip())
    except Exception:
        pass
    # ponytail: if LLM returned nothing useful, wrap raw text as a task
    if not structured["tasks"] and not structured["notes"]:
        structured = {"tasks": [{"title": text, "spoon_cost": 1.0, "energy_tag": "medium"}], "notes": []}
    conn = get_db()
    conn.execute(
        "INSERT INTO brain_dumps (id, raw_text, structured_json, source) VALUES (?, ?, ?, ?)",
        (bid, text, json.dumps(structured), data.source),
    )
    conn.commit()
    conn.close()
    return {"id": bid, "structured": structured, "original": data.text, "declarative_note": text if data.declarative else None}

@app.get("/api/brain-dump")
async def get_brain_dumps():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM brain_dumps WHERE created_at >= datetime('now', '-30 days') ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return {"dumps": [dict(r) for r in rows]}

# ponytail: LIKE-based brain dump search. Full-text > vectors for personal task recall.
@app.get("/api/brain-dump/search")
async def search_brain_dumps(q: str = ""):
    conn = get_db()
    if not q:
        return search_brain_dumps()
    rows = conn.execute(
        "SELECT * FROM brain_dumps WHERE raw_text LIKE ? OR structured_json LIKE ? ORDER BY created_at DESC LIMIT 10",
        (f"%{q}%", f"%{q}%"),
    ).fetchall()
    conn.close()
    return {"dumps": [dict(r) for r in rows], "query": q}

# ── Pacing ────────────────────────────────────────────────

@app.get("/api/pacing/envelope")
async def pacing_envelope():
    conn = get_db()
    state = conn.execute("SELECT * FROM daily_state WHERE id = (SELECT MAX(id) FROM daily_state)").fetchone()
    tasks = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status != 'done'").fetchone()
    energy_log = conn.execute("SELECT spoons_remaining FROM energy_log ORDER BY timestamp DESC LIMIT 7").fetchall()
    conn.close()
    current = state["remaining_spoons"] / max(state["total_spoons"], 1) * 100 if state else 50
    history = [e["spoons_remaining"] * 10 for e in energy_log]
    return energy_envelope(current, tasks["cnt"] if tasks else 0, history)

@app.get("/api/pacing/boom-bust")
async def boom_bust():
    conn = get_db()
    energy_log = conn.execute("SELECT spoons_remaining FROM energy_log ORDER BY timestamp DESC LIMIT 7").fetchall()
    conn.close()
    history = [e["spoons_remaining"] * 10 for e in energy_log]
    return detect_boom_bust(history)

# ponytail: SQL GROUP BY patterns — no ML needed for energy trends.
@app.get("/api/pacing/patterns")
async def energy_patterns():
    conn = get_db()
    by_hour = conn.execute("""
        SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour,
               AVG(spoons_remaining) as avg_energy,
               COUNT(*) as days
        FROM energy_log GROUP BY hour ORDER BY hour
    """).fetchall()
    by_dow = conn.execute("""
        SELECT CAST(strftime('%w', timestamp) AS INTEGER) as dow,
               AVG(spoons_remaining) as avg_energy
        FROM energy_log GROUP BY dow ORDER BY dow
    """).fetchall()
    conn.close()
    days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
    best_hour = max(by_hour, key=lambda r: r['avg_energy'])['hour'] if by_hour else 12
    worst_hour = min(by_hour, key=lambda r: r['avg_energy'])['hour'] if by_hour else 3
    best_dow = days[max(by_dow, key=lambda r: r['avg_energy'])['dow']] if by_dow else 'Unknown'
    return {
        "by_hour": [dict(r) for r in by_hour],
        "by_day": [{"day": days[r['dow']], "avg_energy": r['avg_energy']} for r in by_dow],
        "insight": f"Peak energy: {best_hour}:00. Low point: {worst_hour}:00. Best day: {best_dow}.",
    }

# ── Dopamine Menu ─────────────────────────────────────────

@app.get("/api/dopamine-menu")
async def get_dopamine_menu():
    conn = get_db()
    items = conn.execute("SELECT * FROM dopamine_menu_items ORDER BY sort_order").fetchall()
    conn.close()
    menu = {"starters": [], "sides": [], "mains": [], "desserts": []}
    for item in items:
        d = dict(item)
        cat = d.pop("category")
        if cat in menu:
            menu[cat].append(d)
    return menu

@app.post("/api/dopamine-menu")
async def add_dopamine_item(data: dict):
    conn = get_db()
    conn.execute(
        "INSERT INTO dopamine_menu_items (id, name, category, energy_required, sort_order) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), data["name"], data["category"], data.get("energy_required", 0.5), data.get("sort_order", 99)),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/dopamine-menu/{item_id}")
async def delete_dopamine_item(item_id: str):
    conn = get_db()
    conn.execute("DELETE FROM dopamine_menu_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# ── Interoception ─────────────────────────────────────────

@app.post("/api/interoception")
async def log_interoception(data: dict):
    conn = get_db()
    conn.execute(
        "INSERT INTO interoception_log (id, signals, mood, note) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), json.dumps(data.get("signals", [])), data.get("mood", ""), data.get("note", "")),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/interoception")
async def get_interoception():
    conn = get_db()
    rows = conn.execute("SELECT * FROM interoception_log ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return {"logs": [dict(r) for r in rows]}

# ── Serve Frontend ────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    return HTMLResponse("<h1>NeurOS</h1><p>Frontend not built yet.</p>")

@app.get("/{path:path}")
async def serve_static(path: str):
    # Check soundscapes (URL /soundscapes/foo.wav → backend/soundscapes/foo.wav)
    if path.startswith("soundscapes/"):
        sound_file = SOUNDSCAPES_DIR / path[len("soundscapes/"):]
        if sound_file.exists() and sound_file.is_file():
            return FileResponse(str(sound_file))
    # Then frontend
    file = FRONTEND_DIR / path
    if file.exists() and file.is_file():
        return FileResponse(str(file))
    # SPA fallback
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    raise HTTPException(404)