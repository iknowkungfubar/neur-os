"""Uniform response envelope for all API endpoints.

Every endpoint returns {"ok": true, "data": ...} on success
or {"ok": false, "error": "..."} on failure.
"""

from typing import Any
from fastapi.responses import JSONResponse


def ok(data: Any = None) -> dict:
    """Success response."""
    return {"ok": True, "data": data}


def err(message: str, status: int = 400) -> JSONResponse:
    """Error response. Pass as `raise HTTPException` or return directly."""
    return JSONResponse({"ok": False, "error": message}, status_code=status)
