# ponytail: pure domain entities. Zero framework imports — no fastapi, sqlite3, httpx.
# These are plain Python classes and functions that can be tested without infrastructure.

class EnergyBattery:
    """0-100% battery model. Has drain rate, charge efficiency, background drain."""
    def __init__(self, percentage: float = 50, drain_rate: float = 0.5, charge_rate: float = 0.3):
        self.percentage = max(0.0, min(100.0, percentage))
        self.drain_rate = max(0.0, min(1.0, drain_rate))
        self.charge_rate = max(0.0, min(1.0, charge_rate))

    def drain(self, amount: float):
        self.percentage = max(0.0, self.percentage - amount)
        return self.percentage

    def charge(self, amount: float):
        self.percentage = min(100.0, self.percentage + amount * self.charge_rate)
        return self.percentage

    def tick(self, hours: float = 1.0):
        """Background drain — body keeps running even when idle."""
        self.percentage = max(0.0, self.percentage - self.drain_rate * hours)
        return self.percentage

    @property
    def traffic_light(self) -> str:
        if self.percentage >= 60: return "green"
        if self.percentage >= 20: return "amber"
        return "red"

    @property
    def as_dict(self) -> dict:
        return {"percentage": round(self.percentage, 1), "drain_rate": self.drain_rate,
                "charge_rate": self.charge_rate, "traffic_light": self.traffic_light}


class Task:
    def __init__(self, title: str, energy_cost: float = 1.0, energy_tag: str = "medium", status: str = "active"):
        self.title = title
        self.energy_cost = max(0.5, min(5.0, energy_cost))
        self.energy_tag = energy_tag if energy_tag in ("low", "medium", "high") else "medium"
        self.status = status

    @property
    def energy_percent(self) -> float:
        """Map energy_cost (0.5-5.0) to battery percentage drain (5%-50%)."""
        return self.energy_cost * 10

    def is_affordable(self, battery: EnergyBattery) -> bool:
        return battery.percentage >= self.energy_percent


class BrainDump:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.tasks: list[dict] = []
        self.notes: list[dict] = []

    def add_task(self, title: str, energy_cost: float = 1.0, energy_tag: str = "medium"):
        self.tasks.append({"title": title, "spoon_cost": energy_cost, "energy_tag": energy_tag})

    def add_note(self, content: str):
        self.notes.append({"content": content})

    @property
    def as_dict(self) -> dict:
        return {"tasks": self.tasks, "notes": self.notes}
