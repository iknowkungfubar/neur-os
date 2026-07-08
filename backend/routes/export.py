"""Export routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from datetime import datetime
from backend.store import DataStore
from backend.deps import get_store
from backend.response import ok
from backend.config import DB_PATH, BACKUP_DIR

router = APIRouter()

@router.get("/api/export/markdown")
async def export_markdown(store: DataStore = Depends(get_store)):
    store.export_all()

@router.get("/api/export/markdown")
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

@router.post("/api/export/backup")
async def backup_db():
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"neur-os_backup_{ts}.db"
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    for old in sorted(BACKUP_DIR.glob("neur-os_backup_*.db"), reverse=True)[30:]:
        old.unlink()
    return ok({"backup": str(backup_path)})

@router.post("/api/import")
async def import_data(data: dict, store: DataStore = Depends(get_store)):
    imported = {}
    for table in ["daily_state", "tasks", "energy_log", "crisis_log", "timer_sessions", "habits", "wind_down"]:
        rows = data.get(table, [])
        imported[table] = store.import_rows(table, rows) if rows else 0
    return ok({"imported": imported})


