"""Parks API routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.models import Park

router = APIRouter(prefix="/api/parks", tags=["parks"])


class ParkOut(BaseModel):
    park_id: str
    park_name: str | None = None
    neighbourhood_id: str | None = None
    park_type: str | None = None
    area_sqm: float | None = None
    amenities: list[str] = []
    latitude: float | None = None
    longitude: float | None = None


def _to_out(p: Park) -> ParkOut:
    try:
        amenities = json.loads(p.amenities) if p.amenities else []
    except (json.JSONDecodeError, TypeError):
        amenities = []
    return ParkOut(
        park_id=p.park_id,
        park_name=p.park_name,
        neighbourhood_id=p.neighbourhood_id,
        park_type=p.park_type,
        area_sqm=float(p.area_sqm) if p.area_sqm is not None else None,
        amenities=amenities if isinstance(amenities, list) else [],
        latitude=float(p.latitude) if p.latitude is not None else None,
        longitude=float(p.longitude) if p.longitude is not None else None,
    )


@router.get("/list", response_model=list[ParkOut])
def list_parks(session: Session = Depends(get_session)) -> list[ParkOut]:
    rows = session.execute(select(Park)).scalars().all()
    return [_to_out(p) for p in rows]


@router.get("/neighbourhood/{neighbourhood_id}", response_model=list[ParkOut])
def parks_by_neighbourhood(
    neighbourhood_id: str, session: Session = Depends(get_session)
) -> list[ParkOut]:
    rows = (
        session.execute(select(Park).where(Park.neighbourhood_id == neighbourhood_id))
        .scalars()
        .all()
    )
    return [_to_out(p) for p in rows]
