"""Agent API route: POST /api/agent/query — CityBot natural-language interface."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backend.agent import answer_question
from backend.config import settings

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/diagnose")
def diagnose() -> dict[str, Any]:
    """Temporary diagnostic: reports key state and makes one live Gemini call."""
    import httpx

    key = settings.gemini_api_key or ""
    info: dict[str, Any] = {
        "gemini_enabled": settings.gemini_enabled,
        "gemini_model": settings.gemini_model,
        "key_present": bool(key),
        "key_len": len(key),
        "key_prefix": key[:6],
        "key_suffix": key[-4:] if key else "",
    }
    if not key:
        info["gemini_call"] = "skipped — no key"
        return info
    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent"
        )
        resp = httpx.post(
            url,
            params={"key": key},
            json={"contents": [{"parts": [{"text": "say ok"}]}]},
            timeout=20,
        )
        info["http_status"] = resp.status_code
        info["body"] = resp.text[:400]
    except Exception as exc:  # noqa: BLE001
        info["exception"] = f"{type(exc).__name__}: {exc}"
    return info


class AgentQueryIn(BaseModel):
    question: str


class AgentQueryOut(BaseModel):
    answer: str
    sql_used: str
    rows: list[dict[str, Any]]


@router.post("/query", response_model=AgentQueryOut)
def query(payload: AgentQueryIn) -> AgentQueryOut:
    result = answer_question(payload.question)
    return AgentQueryOut(
        answer=result["answer"],
        sql_used=result["sql_used"],
        rows=result["rows"],
    )
