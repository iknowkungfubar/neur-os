"""Admin routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pathlib import Path
import uuid
from datetime import date, datetime
from backend.store import DataStore
from backend.response import ok

router = APIRouter()

# In-memory admin night rooms (not persisted — ephemeral by design)
admin_rooms: dict = {}

@router.post("/api/admin-night/rooms")
async def create_admin_room():
    room_id = str(uuid.uuid4())[:8]
    admin_rooms[room_id] = {"connections": [], "timer_running": False, "timer_elapsed": 0, "created_at": datetime.utcnow().isoformat()}
    return ok({"room_id": room_id})

@router.get("/api/admin-night/rooms")
async def list_admin_rooms():
    return ok({"rooms": [{"room_id": k, "user_count": len(v["connections"]), "timer_running": v["timer_running"]} for k, v in admin_rooms.items()]})

@router.websocket("/api/admin-night/ws/{room_id}")
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

