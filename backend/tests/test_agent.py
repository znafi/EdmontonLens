"""Tests for the CityBot agent (offline fallback path) and its tools."""

from __future__ import annotations

from datetime import datetime

from backend.agent import answer_question
from backend.agent.tools import describe_table
from backend.agent.tools.bigquery_tool import _ensure_limit, _is_read_only
from backend.database import SessionLocal, init_db
from backend.models import Neighbourhood, WasteSchedule


def _seed() -> None:
    init_db()
    session = SessionLocal()
    try:
        session.merge(
            Neighbourhood(
                neighbourhood_id="1010",
                neighbourhood_name="Glenora",
                boundary_geojson="{}",
                area_sqkm=2.5,
                ingested_at=datetime.utcnow(),
            )
        )
        session.merge(
            WasteSchedule(
                schedule_id="1010-garbage",
                neighbourhood_id="1010",
                pickup_day="Monday",
                waste_type="garbage",
                biweekly=False,
                ingested_at=datetime.utcnow(),
            )
        )
        session.commit()
    finally:
        session.close()


def test_schema_tool_known_table() -> None:
    out = describe_table("transit_performance")
    assert "on_time_rate" in out


def test_schema_tool_unknown_table() -> None:
    out = describe_table("does_not_exist")
    assert "Unknown table" in out


def test_sql_guard_blocks_mutations() -> None:
    assert _is_read_only("SELECT * FROM parks") is True
    assert _is_read_only("DELETE FROM parks") is False
    assert _is_read_only("SELECT 1; DROP TABLE parks") is False


def test_ensure_limit_adds_limit() -> None:
    assert "LIMIT" in _ensure_limit("SELECT * FROM parks").upper()


def test_agent_fallback_answers_waste_question() -> None:
    _seed()
    result = answer_question("What day is garbage pickup in Glenora?")
    assert "answer" in result
    assert isinstance(result["rows"], list)
    assert result["sql_used"]
