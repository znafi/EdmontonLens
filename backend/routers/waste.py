"""Waste API routes: collection schedule and diversion rate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.models import WasteSchedule

router = APIRouter(prefix="/api/waste", tags=["waste"])


class WasteScheduleOut(BaseModel):
    schedule_id: str
    neighbourhood_id: str | None = None
    pickup_day: str | None = None
    waste_type: str | None = None
    biweekly: bool | None = None


class DiversionRateOut(BaseModel):
    diversion_rate: float
    recycling_organics_streams: int
    total_streams: int


@router.get("/schedule", response_model=list[WasteScheduleOut])
def schedule(
    neighbourhood_id: str | None = Query(None),
    session: Session = Depends(get_session),
) -> list[WasteScheduleOut]:
    stmt = select(WasteSchedule)
    if neighbourhood_id:
        stmt = stmt.where(WasteSchedule.neighbourhood_id == neighbourhood_id)
    rows = session.execute(stmt).scalars().all()
    return [
        WasteScheduleOut(
            schedule_id=w.schedule_id,
            neighbourhood_id=w.neighbourhood_id,
            pickup_day=w.pickup_day,
            waste_type=w.waste_type,
            biweekly=w.biweekly,
        )
        for w in rows
    ]


@router.get("/diversion-rate", response_model=DiversionRateOut)
def diversion_rate(session: Session = Depends(get_session)) -> DiversionRateOut:
    """Share of collection streams that are recycling or organics (diverted)."""
    total = session.execute(select(func.count()).select_from(WasteSchedule)).scalar_one()
    diverted = session.execute(
        select(func.count())
        .select_from(WasteSchedule)
        .where(WasteSchedule.waste_type.in_(["recycling", "organics"]))
    ).scalar_one()
    rate = (diverted / total) if total else 0.0
    return DiversionRateOut(
        diversion_rate=round(rate, 4),
        recycling_organics_streams=int(diverted),
        total_streams=int(total),
    )
