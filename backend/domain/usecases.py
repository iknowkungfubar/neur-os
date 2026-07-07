# ponytail: pure domain use cases. Pure functions, no framework imports.
import json
from datetime import datetime


def energy_envelope(current_pct: float, tasks_today: int, history: list[float]) -> dict:
    """Calculate safe energy envelope. See spec 2.1."""
    avg_daily_drain = 0.3
    if history and len(history) >= 3:
        drops = [history[i] - history[i+1] for i in range(len(history)-1) if history[i] > history[i+1]]
        avg_daily_drain = sum(drops) / max(len(drops), 1)
    current_usage = tasks_today * avg_daily_drain
    recommended_max = current_pct * 0.8
    recommended_min = current_pct * 0.15
    status = "ok"
    if tasks_today > 0 and current_usage > recommended_max:
        status = "over"
    elif current_pct <= 20:
        status = "low"
    return {"recommended_max": round(recommended_max, 1), "recommended_min": round(recommended_min, 1),
            "current_usage": round(current_usage, 1), "status": status}


def detect_boom_bust(history: list[float]) -> dict:
    """Detect boom-bust patterns. See spec 2.2."""
    if len(history) < 5:
        return {"pattern": "stable", "confidence": 0.0, "message": "Not enough data yet"}
    high_threshold, low_threshold = 60, 30
    recent = history[-5:]
    high_days = sum(1 for h in recent[:3] if h >= high_threshold)
    low_days = sum(1 for h in recent[3:] if h < low_threshold)
    if high_days >= 2 and low_days >= 2:
        confidence = min((high_days + low_days) / 5.0, 1.0)
        return {"pattern": "boom-bust", "confidence": round(confidence, 2),
                "message": "You've been pushing hard. Tomorrow might feel rough. Want to schedule rest?"}
    if len(recent) >= 3 and all(recent[i] < recent[i-1] for i in range(1, len(recent))):
        return {"pattern": "declining", "confidence": 0.6,
                "message": "Your energy has been decreasing. A rest day might help."}
    return {"pattern": "stable", "confidence": 0.5, "message": "Energy pattern looks consistent."}


def parse_llm_json(raw: str) -> dict:
    """Extract JSON from LLM response with think tags stripped."""
    import re
    cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
    if cleaned.startswith("{"):
        return json.loads(cleaned)
    if cleaned.startswith("```"):
        return json.loads(cleaned.strip("`").removeprefix("json").strip())
    return {}


def analyze_energy_patterns(energy_log_rows: list) -> dict:
    """Analyze energy patterns from DB rows. See spec 4.3."""
    by_hour = {}
    by_dow = {}
    for row in energy_log_rows:
        try:
            ts = datetime.fromisoformat(row["timestamp"])
            hour = ts.hour
            dow = ts.weekday()
            energy = row["spoons_remaining"]
            by_hour.setdefault(hour, []).append(energy)
            by_dow.setdefault(dow, []).append(energy)
        except (ValueError, KeyError):
            continue
    averages = {}
    if by_hour:
        averages["by_hour"] = {str(h): round(sum(v)/len(v), 1) for h, v in sorted(by_hour.items())}
    if by_dow:
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        averages["by_day"] = {day_names[int(d)]: round(sum(v)/len(v), 1) for d, v in sorted(by_dow.items())}
    return averages
