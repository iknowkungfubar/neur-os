"""LLM client — local inference via LM Studio-compatible API.

Extracted from main.py to eliminate inline LLM client code.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
LM_MODEL = os.getenv("LM_MODEL", "qwythos-9b-claude-mythos-5-1m")


async def call_llm(system: str, user: str, max_tokens: int = 512, model: str = "") -> str:
    """Call the local LLM endpoint. Returns text response or error message string."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=2.0)) as client:
            payload: dict[str, Any] = {
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
