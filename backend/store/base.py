"""Abstract store interface for all persistence operations."""

from __future__ import annotations


class DataStore:
    """Interface for all persistence operations. Subclass must implement every method."""

    # ── Daily State ──
    def get_state(self, today: str | None = None) -> dict: raise NotImplementedError
    def upsert_state(self, today: str, data: dict) -> None: raise NotImplementedError
    def set_mode(self, today: str, mode: str) -> None: raise NotImplementedError

    # ── Energy Log ──
    def log_energy(self, spoons: float, pain: int = 0, note: str = "") -> str: raise NotImplementedError
    def get_energy_log(self, limit: int = 30) -> list[dict]: raise NotImplementedError
    def recent_energy(self, days: int = 7) -> list[dict]: raise NotImplementedError
    def energy_patterns(self) -> dict: raise NotImplementedError

    # ── Tasks ──
    def get_tasks(self, status_filter: str | None = None) -> list[dict]: raise NotImplementedError
    def create_task(self, data: dict) -> dict: raise NotImplementedError
    def get_task(self, task_id: str) -> dict | None: raise NotImplementedError
    def update_task(self, task_id: str, updates: dict) -> bool: raise NotImplementedError
    def complete_task(self, task_id: str, spoon_cost: float = 0) -> dict: raise NotImplementedError
    def next_task(self, mode: str, remaining: float) -> dict | None: raise NotImplementedError

    # ── Habits ──
    def get_habits(self, today: str) -> list[dict]: raise NotImplementedError
    def create_habit(self, data: dict) -> str: raise NotImplementedError
    def get_habit(self, hid: str) -> dict | None: raise NotImplementedError
    def check_habit(self, hid: str, today: str) -> None: raise NotImplementedError

    # ── Timer ──
    def stop_all_timers(self) -> None: raise NotImplementedError
    def create_timer(self, data: dict) -> dict: raise NotImplementedError
    def get_active_timer(self) -> dict | None: raise NotImplementedError
    def update_timer(self, tid: str, updates: dict) -> None: raise NotImplementedError

    # ── Wind Down ──
    def get_wind_down(self, today: str) -> dict | None: raise NotImplementedError
    def upsert_wind_down(self, today: str, data: dict) -> None: raise NotImplementedError
    def week_wind_down(self, week_ago: str) -> list[dict]: raise NotImplementedError

    # ── Crisis ──
    def activate_crisis(self, crisis_type: str = "sensory_overload") -> str: raise NotImplementedError
    def resolve_crisis(self) -> bool: raise NotImplementedError
    def get_crises_since(self, since: str) -> list[dict]: raise NotImplementedError

    # ── Brain Dump ──
    def save_brain_dump(self, text: str, structured: dict, source: str = "textarea") -> str: raise NotImplementedError
    def search_brain_dumps(self, q: str) -> list[dict]: raise NotImplementedError
    def list_brain_dumps(self, limit: int = 20) -> list[dict]: raise NotImplementedError

    # ── Dopamine Menu ──
    def get_dopamine_menu(self) -> dict[str, list[dict]]: raise NotImplementedError
    def add_dopamine_item(self, data: dict) -> None: raise NotImplementedError
    def delete_dopamine_item(self, item_id: str) -> None: raise NotImplementedError

    # ── Interoception ──
    def log_interoception(self, signals: list, mood: str = "", note: str = "") -> None: raise NotImplementedError
    def get_interoception(self, limit: int = 20) -> list[dict]: raise NotImplementedError

    # ── Passive Log ──
    def get_today_passive_log(self) -> list[dict]: raise NotImplementedError
    def submit_passive_log(self, response: str, spoons_at_time: float | None = None,
                          current_task_id: str | None = None, source: str = "notification") -> str: raise NotImplementedError
    def last_passive_log_today(self) -> dict | None: raise NotImplementedError

    # ── Onboarding ──
    def get_onboarding(self) -> dict | None: raise NotImplementedError
    def save_onboarding(self, phase: int, turns: int, profile: dict) -> None: raise NotImplementedError

    # ── Templates / Export / Import ──
    def export_all(self) -> dict[str, list[dict]]: raise NotImplementedError
    def import_rows(self, table: str, rows: list[dict]) -> int: raise NotImplementedError
    def get_template(self, type: str) -> dict: raise NotImplementedError
    def import_template_items(self, type: str, items: list[dict]) -> int: raise NotImplementedError

    # ── Sync ──
    def sync_upload(self, device_id: str, collection: str, encrypted_blob: str, version: int = 1) -> None: raise NotImplementedError
    def sync_download(self, device_id: str, collection: str, since: str = "") -> list[dict]: raise NotImplementedError

    # ── Review ──
    def weekly_review(self, week_ago: str, today: str) -> dict: raise NotImplementedError
    def review_insight(self, week_ago: str) -> dict: raise NotImplementedError

    # ── Soundscapes ──
    def get_soundscape_configs(self) -> list[dict]: raise NotImplementedError
    def update_soundscape_config(self, mode: str, updates: dict) -> None: raise NotImplementedError
    def list_sound_files(self) -> list[str]: raise NotImplementedError

    # ── Check-in / Init ──
    def init_schema(self) -> None: raise NotImplementedError
    def get_or_create_state(self, today: str) -> dict: raise NotImplementedError
