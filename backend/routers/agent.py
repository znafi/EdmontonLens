"""Agent API route: POST /api/agent/query — CityBot natural-language interface."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backend.agent import answer_question

router = APIRouter(prefix="/api/agent", tags=["agent"])


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
