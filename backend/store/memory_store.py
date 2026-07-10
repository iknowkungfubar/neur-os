"""In-memory implementation of DataStore for NeurOS tests."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta

from backend.store.base import DataStore


class InMemoryStore(DataStore):
    """Stores everything in dicts. No file I/O, no SQL. Same interface as SqliteStore."""

    def __init__(self):
        self.state: dict[str, dict] = {}
        self.energy_logs: list[dict] = []
        self.tasks: dict[str, dict] = {}
        self.habits: dict[str, dict] = {}
        self.timers: dict[str, dict] = {}
        self.wind_downs: dict[str, dict] = {}
        self.crises: list[dict] = []
        self.brain_dumps: list[dict] = []
        self.dopamine_menu_items: list[dict] = []
        self.interoception_logs: list[dict] = []
        self.passive_logs: list[dict] = []
        self.onboarding: dict | None = None
        self.sync_data: list[dict] = []
        self.admin_rooms: dict = {}

    def init_schema(self) -> None: pass
    def _seed_defaults(self) -> None: pass

    def _ts(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # ── Daily State ──
    def get_state(self, today: str | None = None) -> dict:
        today = today or date.today().isoformat()
        return self.state.get(today, {"total_spoons": 10, "remaining_spoons": 10, "pain_level": 0, "mode": "green"})

    def get_or_create_state(self, today: str) -> dict:
        return self.get_state(today)

    def upsert_state(self, today: str, data: dict) -> None:
        existing = self.state.get(today, {})
        existing.update(data)
        self.state[today] = existing

    def set_mode(self, today: str, mode: str) -> None:
        s = self.state.get(today, {"total_spoons": 10, "remaining_spoons": 10, "pain_level": 0, "mode": "green"})
        s["mode"] = mode
        self.state[today] = s

    # ── Energy Log ──
    def log_energy(self, spoons: float, pain: int = 0, note: str = "") -> str:
        lid = uuid.uuid4().hex
        self.energy_logs.insert(0, {"id": lid, "timestamp": self._ts(), "spoons_remaining": spoons, "pain_level": pain, "note": note})
        return lid

    def get_energy_log(self, limit: int = 30) -> list[dict]:
        return self.energy_logs[:limit]

    def recent_energy(self, days: int = 7) -> list[dict]:
        since = (date.today() - timedelta(days=days)).isoformat()
        return [e for e in self.energy_logs if e["timestamp"][:10] >= since]

    def energy_patterns(self) -> dict:
        by_hour: dict[int, list[float]] = {}
        by_dow: dict[int, list[float]] = {}
        for e in self.energy_logs:
            try:
                ts = datetime.fromisoformat(e["timestamp"])
                h, d = ts.hour, ts.weekday()
                by_hour.setdefault(h, []).append(e["spoons_remaining"])
                by_dow.setdefault(d, []).append(e["spoons_remaining"])
            except (ValueError, KeyError):
                pass
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        hour_avg = {h: sum(v)/len(v) for h, v in by_hour.items()}
        dow_avg = {days[d]: sum(v)/len(v) for d, v in by_dow.items()}
        best_hour = max(hour_avg, key=hour_avg.get) if hour_avg else 12
        worst_hour = min(hour_avg, key=hour_avg.get) if hour_avg else 3
        best_dow = max(dow_avg, key=dow_avg.get) if dow_avg else "Unknown"
        return {
            "by_hour": [{"hour": h, "avg_energy": round(hour_avg[h], 1)} for h in sorted(hour_avg)],
            "by_day": [{"day": d, "avg_energy": round(dow_avg[d], 1)} for d in days if d in dow_avg],
            "insight": f"Peak energy: {best_hour}:00. Low point: {worst_hour}:00. Best day: {best_dow}.",
        }

    # ── Tasks ──
    def get_tasks(self, status_filter: str | None = None) -> list[dict]:
        all_t = sorted(self.tasks.values(), key=lambda t: (t.get("energy_tag", "medium"), t.get("created_at", "")))
        if status_filter:
            return [t for t in all_t if t["status"] == status_filter]
        return all_t

    def create_task(self, data: dict) -> dict:
        tid = uuid.uuid4().hex
        self.tasks[tid] = {
            "id": tid, "title": data["title"], "description": data.get("description", ""),
            "spoon_cost": data.get("spoon_cost", 1.0),
            "micro_chunks": json.dumps(data.get("micro_chunks", [])),
            "energy_tag": data.get("energy_tag", "medium"),
            "recurring": data.get("recurring", ""), "status": "active",
            "created_at": self._ts(), "completed_at": None,
        }
        return {"id": tid, "spoon_cost": data.get("spoon_cost", 1.0), "micro_chunks": data.get("micro_chunks", [])}

    def get_task(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, updates: dict) -> bool:
        t = self.tasks.get(task_id)
        if not t:
            return False
        if updates.get("status") == "completed":
            t["status"] = "completed"
            t["completed_at"] = self._ts()
        if "spoon_cost" in updates:
            t["spoon_cost"] = updates["spoon_cost"]
        if "micro_chunks" in updates and updates["micro_chunks"] is not None:
            t["micro_chunks"] = json.dumps(updates["micro_chunks"])
        return True

    def complete_task(self, task_id: str, spoon_cost: float = 0) -> dict:
        t = self.tasks.get(task_id)
        if not t:
            return {"status": "error", "error": "Task not found"}
        today = date.today().isoformat()
        s = self.state.get(today)
        cost = spoon_cost or t["spoon_cost"]
        new_remaining = 0
        if s:
            new_remaining = max(0, s["remaining_spoons"] - cost)
            s["remaining_spoons"] = new_remaining
        t["status"] = "completed"
        t["completed_at"] = self._ts()
        self.log_energy(new_remaining, 0, f"Completed: {t['title']}")
        if t.get("recurring"):
            new_t = dict(t)
            new_t["id"] = uuid.uuid4().hex
            new_t["status"] = "active"
            new_t["completed_at"] = None
            self.tasks[new_t["id"]] = new_t
        return {"status": "completed", "spoons_deducted": cost}

    def next_task(self, mode: str, remaining: float) -> dict | None:
        if mode == "red":
            return None
        active = [t for t in self.tasks.values() if t["status"] == "active"]
        if mode == "amber":
            affordable = [t for t in active if t["spoon_cost"] <= min(remaining, 2) and t["energy_tag"] in ("low", "medium")]
            return sorted(affordable, key=lambda t: t["spoon_cost"])[0] if affordable else None
        affordable = [t for t in active if t["spoon_cost"] <= remaining]
        return sorted(affordable, key=lambda t: -t["spoon_cost"])[0] if affordable else None

    # ── Habits ──
    def get_habits(self, today: str) -> list[dict]:
        return [{**h, "done_today": h.get("last_completed") == today} for h in self.habits.values()]

    def create_habit(self, data: dict) -> str:
        hid = uuid.uuid4().hex
        self.habits[hid] = {
            "id": hid, "title": data["title"], "description": data.get("description", ""),
            "frequency": data.get("frequency", "daily"), "spoon_cost": data.get("spoon_cost", 0.5),
            "energy_tag": data.get("energy_tag", "low"), "last_completed": None, "created_at": self._ts(),
        }
        return hid

    def get_habit(self, hid: str) -> dict | None:
        return self.habits.get(hid)

    def check_habit(self, hid: str, today: str) -> None:
        if hid in self.habits:
            self.habits[hid]["last_completed"] = today

    # ── Timer ──
    def stop_all_timers(self) -> None:
        for t in self.timers.values():
            if t["status"] in ("running", "paused"):
                t["status"] = "stopped"
                t["completed_at"] = self._ts()

    def create_timer(self, data: dict) -> dict:
        tid = uuid.uuid4().hex
        self.timers[tid] = {
            "id": tid, "task_id": data.get("task_id"),
            "duration_minutes": data.get("duration_minutes", 25),
            "elapsed_seconds": 0, "status": "running",
            "started_at": self._ts(), "paused_at": None,
            "soundscape": data.get("soundscape", ""),
            "body_doubling": 1 if data.get("body_doubling") else 0,
            "started_as": data.get("started_as", "focus"),
        }
        return {"id": tid, "status": "running", "duration_minutes": data.get("duration_minutes", 25),
                "body_doubling": data.get("body_doubling", False), "started_as": data.get("started_as", "focus")}

    def get_active_timer(self) -> dict | None:
        active = [t for t in self.timers.values() if t["status"] in ("running", "paused")]
        if not active:
            return None
        t = dict(sorted(active, key=lambda x: x.get("started_at", ""), reverse=True)[0])
        elapsed = t["elapsed_seconds"]
        if t["status"] == "running" and t["started_at"]:
            try:
                start = datetime.strptime(t["started_at"][:19], "%Y-%m-%d %H:%M:%S")
                elapsed += int((datetime.utcnow() - start).total_seconds())
            except ValueError:
                pass
        t["current_elapsed"] = elapsed
        return t

    def update_timer(self, tid: str, updates: dict) -> None:
        if tid in self.timers:
            self.timers[tid].update(updates)

    # ── Wind Down ──
    def get_wind_down(self, today: str) -> dict | None:
        return self.wind_downs.get(today)

    def upsert_wind_down(self, today: str, data: dict) -> None:
        existing = self.wind_downs.get(today, {})
        existing.update(data)
        self.wind_downs[today] = existing

    def week_wind_down(self, week_ago: str) -> list[dict]:
        return [wd for d, wd in self.wind_downs.items() if d >= week_ago]

    # ── Crisis ──
    def activate_crisis(self, crisis_type: str = "sensory_overload") -> str:
        cid = uuid.uuid4().hex
        self.crises.append({"id": cid, "crisis_type": crisis_type, "timestamp": self._ts(), "triggered_by": "manual", "resolved_at": None})
        return cid

    def resolve_crisis(self) -> bool:
        for c in self.crises:
            if c["resolved_at"] is None:
                c["resolved_at"] = self._ts()
                return True
        return False

    def get_crises_since(self, since: str) -> list[dict]:
        return [c for c in self.crises if c.get("timestamp", "")[:10] >= since]

    # ── Brain Dump ──
    def save_brain_dump(self, text: str, structured: dict, source: str = "textarea") -> str:
        bid = uuid.uuid4().hex
        self.brain_dumps.append({"id": bid, "raw_text": text, "structured_json": json.dumps(structured), "source": source, "created_at": self._ts()})
        return bid

    def search_brain_dumps(self, q: str) -> list[dict]:
        return [b for b in self.brain_dumps if q.lower() in b["raw_text"].lower() or q.lower() in b["structured_json"].lower()][:10]

    def list_brain_dumps(self, limit: int = 20) -> list[dict]:
        return sorted(self.brain_dumps, key=lambda b: b.get("created_at", ""), reverse=True)[:limit]

    # ── Dopamine Menu ──
    def get_dopamine_menu(self) -> dict[str, list[dict]]:
        menu = {"starters": [], "sides": [], "mains": [], "desserts": []}
        for item in sorted(self.dopamine_menu_items, key=lambda i: i.get("sort_order", 99)):
            d = dict(item)
            cat = d.pop("category")
            if cat in menu:
                menu[cat].append(d)
        return menu

    def add_dopamine_item(self, data: dict) -> None:
        self.dopamine_menu_items.append({
            "id": uuid.uuid4().hex, "name": data["name"], "category": data["category"],
            "energy_required": data.get("energy_required", 0.5), "sort_order": data.get("sort_order", 99),
        })

    def delete_dopamine_item(self, item_id: str) -> None:
        self.dopamine_menu_items = [i for i in self.dopamine_menu_items if i["id"] != item_id]

    # ── Interoception ──
    def log_interoception(self, signals: list, mood: str = "", note: str = "") -> None:
        self.interoception_logs.append({
            "id": uuid.uuid4().hex, "signals": json.dumps(signals), "mood": mood,
            "note": note, "created_at": self._ts(),
        })

    def get_interoception(self, limit: int = 20) -> list[dict]:
        return sorted(self.interoception_logs, key=lambda l: l.get("created_at", ""), reverse=True)[:limit]

    # ── Passive Log ──
    def get_today_passive_log(self) -> list[dict]:
        today = date.today().isoformat()
        return [p for p in self.passive_logs if p.get("timestamp", "")[:10] == today]

    def submit_passive_log(self, response: str, spoons_at_time: float | None = None,
                           current_task_id: str | None = None, source: str = "notification") -> str:
        lid = uuid.uuid4().hex
        self.passive_logs.append({
            "id": lid, "timestamp": self._ts(), "response": response,
            "spoons_at_time": spoons_at_time, "current_task_id": current_task_id, "source": source,
        })
        return lid

    def last_passive_log_today(self) -> dict | None:
        today = date.today().isoformat()
        today_logs = [p for p in self.passive_logs if p.get("timestamp", "")[:10] == today]
        return sorted(today_logs, key=lambda p: p.get("timestamp", ""), reverse=True)[0] if today_logs else None

    # ── Onboarding ──
    def get_onboarding(self) -> dict | None:
        return self.onboarding

    def save_onboarding(self, phase: int, turns: int, profile: dict) -> None:
        self.onboarding = {"phase": phase, "turns": turns, "extracted_profile": json.dumps(profile), "updated_at": self._ts()}

    # ── Templates / Export ──
    def export_all(self) -> dict[str, list[dict]]:
        return {
            "daily_state": list(self.state.values()),
            "tasks": list(self.tasks.values()),
            "energy_log": self.energy_logs,
            "crisis_log": self.crises,
            "timer_sessions": list(self.timers.values()),
            "habits": list(self.habits.values()),
            "wind_down": list(self.wind_downs.values()),
        }

    def import_rows(self, table: str, rows: list[dict]) -> int:
        count = 0
        for row in rows:
            if table == "tasks":
                rid = row.get("id", uuid.uuid4().hex)
                if rid not in self.tasks:
                    self.tasks[rid] = row
                    count += 1
            elif table == "habits":
                rid = row.get("id", uuid.uuid4().hex)
                if rid not in self.habits:
                    self.habits[rid] = row
                    count += 1
        return count

    def get_template(self, type: str) -> dict:
        if type == "dopamine_menu":
            return {"type": type, "items": [{"name": i["name"], "category": i["category"], "energy_required": i.get("energy_required", 0.5)} for i in self.dopamine_menu_items]}
        return {"type": type, "error": "Unknown template type"}

    def import_template_items(self, type: str, items: list[dict]) -> int:
        count = 0
        for item in items:
            self.dopamine_menu_items.append({
                "id": uuid.uuid4().hex, "name": item["name"], "category": item["category"],
                "energy_required": item.get("energy_required", 0.5), "sort_order": 99,
            })
            count += 1
        return count

    # ── Sync ──
    def sync_upload(self, device_id: str, collection: str, encrypted_blob: str, version: int = 1) -> None:
        self.sync_data.append({
            "id": uuid.uuid4().hex, "device_id": device_id, "collection": collection,
            "encrypted_blob": encrypted_blob, "blob_version": version, "created_at": self._ts(),
        })

    def sync_download(self, device_id: str, collection: str, since: str = "") -> list[dict]:
        matches = [s for s in self.sync_data if s["device_id"] == device_id and s["collection"] == collection]
        if since:
            matches = [s for s in matches if s.get("created_at", "") > since]
        return sorted(matches, key=lambda s: s.get("created_at", ""), reverse=True)[:100]

    # ── Review ──
    def weekly_review(self, week_ago: str, today: str) -> dict:
        energy_states = [s for d, s in self.state.items() if week_ago <= d <= today]
        completed = [t for t in self.tasks.values() if t.get("completed_at") and t["completed_at"][:10] >= week_ago]
        crises = [c for c in self.crises if c.get("timestamp", "")[:10] >= week_ago]
        habits = list(self.habits.values())
        wind = [wd for d, wd in self.wind_downs.items() if d >= week_ago]
        timers = [t for t in self.timers.values() if t.get("started_at", "")[:10] >= week_ago]

        avg_spoons = sum(float(s["total_spoons"]) for s in energy_states) / len(energy_states) if energy_states else 0
        avg_pain = sum(s["pain_level"] for s in energy_states) / len(energy_states) if energy_states else 0
        focus_min = sum(t["elapsed_seconds"] // 60 for t in timers if t["status"] in ("completed", "stopped"))

        return {
            "energy_states": energy_states, "completed_tasks": completed,
            "energy_entries": self.energy_logs, "timer_sessions": timers,
            "crises": crises, "habits": habits, "wind_down_entries": wind,
            "insights": {
                "days_tracked": len(energy_states), "avg_spoons": round(avg_spoons, 1),
                "avg_pain": round(avg_pain, 1), "tasks_completed": len(completed),
                "total_focus_minutes": focus_min, "crisis_count": len(crises),
            },
        }

    def review_insight(self, week_ago: str) -> dict:
        energy_states = [s for d, s in self.state.items() if d >= week_ago]
        completed = [t for t in self.tasks.values() if t.get("completed_at") and t["completed_at"][:10] >= week_ago]
        wind = [wd for d, wd in self.wind_downs.items() if d >= week_ago]
        crises = [c for c in self.crises if c.get("timestamp", "")[:10] >= week_ago]

        days = len(energy_states)
        total_tasks = len(completed)
        high_spoon = sum(1 for t in completed if t.get("energy_tag") == "high")
        total_crises = len(crises)

        lines = []
        if days < 2:
            lines.append("Not enough data yet - check in daily to see patterns emerge.")
        else:
            lines.append(f"**{days} days** tracked this week.")
            lines.append(f"Completed **{total_tasks} tasks** ({high_spoon} high-energy)." if total_tasks > 0 else "No tasks completed this week - that's okay.")
            if total_crises:
                lines.append(f"Crisis mode activated **{total_crises} time(s)** this week.")
            if energy_states:
                best = max(energy_states, key=lambda s: s["remaining_spoons"])
                lines.append(f"Highest energy day: **{best['date']}** ({best['remaining_spoons']}/{best['total_spoons']} spoons).")
                worst = min(energy_states, key=lambda s: s["remaining_spoons"])
                if worst["remaining_spoons"] < best["remaining_spoons"]:
                    lines.append(f"Lowest energy day: **{worst['date']}** ({worst['remaining_spoons']}/{worst['total_spoons']} spoons).")
            if wind:
                themes = [e["went_well"].split(".")[0] for e in wind if e.get("went_well")]
                if themes:
                    lines.append(f"Recurring themes: {'; '.join(themes[:3])}.")
        return {"insight": "\n".join(lines)}

    # ── Soundscapes (InMemoryStore) ──
    def get_soundscape_configs(self) -> list[dict]:
        if not hasattr(self, "sound_configs"):
            self.sound_configs = {}
        return [
            {"mode": m, "sound_file": c.get("sound_file", ""),
             "volume": c.get("volume", 0.5), "loop": c.get("loop", 0)}
            for m, c in self.sound_configs.items()
        ]

    def update_soundscape_config(self, mode: str, updates: dict) -> None:
        if not hasattr(self, "sound_configs"):
            self.sound_configs = {}
        if mode not in self.sound_configs:
            self.sound_configs[mode] = {"sound_file": "", "volume": 0.5, "loop": 0}
        self.sound_configs[mode].update(updates)

    def list_sound_files(self) -> list[str]:
        return []
