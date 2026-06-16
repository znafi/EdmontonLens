"""Neighbourhood API routes: list, snapshot, and GeoJSON for the map."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.models import Neighbourhood, NeighbourhoodKpi

router = APIRouter(prefix="/api/neighbourhoods", tags=["neighbourhoods"])


class NeighbourhoodOut(BaseModel):
    neighbourhood_id: str
    neighbourhood_name: str | None = None
    area_sqkm: float | None = None


class SnapshotOut(BaseModel):
    neighbourhood_id: str
    neighbourhood_name: str | None = None
    snapshot_date: date | None = None
    transit_stop_count: int | None = None
    avg_route_on_time: float | None = None
    park_count: int | None = None
    total_park_area_sqm: float | None = None
    waste_pickup_days: int | None = None
    transit_score: float | None = None
    park_score: float | None = None
    overall_score: float | None = None


class TrendPointOut(BaseModel):
    snapshot_date: date
    transit_score: float


@router.get("/list", response_model=list[NeighbourhoodOut])
def list_neighbourhoods(session: Session = Depends(get_session)) -> list[NeighbourhoodOut]:
    rows = session.execute(select(Neighbourhood)).scalars().all()
    return [
        NeighbourhoodOut(
            neighbourhood_id=n.neighbourhood_id,
            neighbourhood_name=n.neighbourhood_name,
            area_sqkm=float(n.area_sqkm) if n.area_sqkm is not None else None,
        )
        for n in rows
    ]


@router.get("/geojson")
def geojson(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Return a GeoJSON FeatureCollection of all neighbourhood boundaries,
    enriched with the latest overall_score for choropleth rendering."""
    neighbourhoods = session.execute(select(Neighbourhood)).scalars().all()
    kpis = session.execute(select(NeighbourhoodKpi)).scalars().all()
    score_by_id: dict[str, dict[str, float | int]] = {}
    for k in kpis:
        nid = k.neighbourhood_id or ""
        score_by_id[nid] = {
            "overall_score": float(k.overall_score or 0),
            "transit_score": float(k.transit_score or 0),
            "park_score": float(k.park_score or 0),
            "park_count": int(k.park_count or 0),
            "transit_stop_count": int(k.transit_stop_count or 0),
            "waste_pickup_days": int(k.waste_pickup_days or 0),
        }

    features: list[dict[str, Any]] = []
    for n in neighbourhoods:
        try:
            geometry = json.loads(n.boundary_geojson) if n.boundary_geojson else {}
        except json.JSONDecodeError:
            geometry = {}
        scores = score_by_id.get(n.neighbourhood_id, {})
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "neighbourhood_id": n.neighbourhood_id,
                    "neighbourhood_name": n.neighbourhood_name,
                    "overall_score": scores.get("overall_score", 0.0),
                    "transit_score": scores.get("transit_score", 0.0),
                    "park_score": scores.get("park_score", 0.0),
                    "park_count": scores.get("park_count", 0),
                    "transit_stop_count": scores.get("transit_stop_count", 0),
                    "waste_pickup_days": scores.get("waste_pickup_days", 0),
                },
                "geometry": geometry,
            }
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/{neighbourhood_id}/snapshot", response_model=SnapshotOut)
def snapshot(
    neighbourhood_id: str, session: Session = Depends(get_session)
) -> SnapshotOut:
    n = session.get(Neighbourhood, neighbourhood_id)
    kpi = (
        session.execute(
            select(NeighbourhoodKpi)
            .where(NeighbourhoodKpi.neighbourhood_id == neighbourhood_id)
            .order_by(NeighbourhoodKpi.snapshot_date.desc())
        )
        .scalars()
        .first()
    )
    if n is None and kpi is None:
        raise HTTPException(status_code=404, detail="Neighbourhood not found")
    return SnapshotOut(
        neighbourhood_id=neighbourhood_id,
        neighbourhood_name=n.neighbourhood_name if n else None,
        snapshot_date=kpi.snapshot_date if kpi else None,
        transit_stop_count=kpi.transit_stop_count if kpi else None,
        avg_route_on_time=float(kpi.avg_route_on_time) if kpi and kpi.avg_route_on_time else None,
        park_count=kpi.park_count if kpi else None,
        total_park_area_sqm=float(kpi.total_park_area_sqm)
        if kpi and kpi.total_park_area_sqm
        else None,
        waste_pickup_days=kpi.waste_pickup_days if kpi else None,
        transit_score=float(kpi.transit_score) if kpi and kpi.transit_score else None,
        park_score=float(kpi.park_score) if kpi and kpi.park_score else None,
        overall_score=float(kpi.overall_score) if kpi and kpi.overall_score else None,
    )


@router.get("/{neighbourhood_id}/trend", response_model=list[TrendPointOut])
def trend(
    neighbourhood_id: str, session: Session = Depends(get_session)
) -> list[TrendPointOut]:
    """Transit-score history for the sparkline (most recent first)."""
    rows = (
        session.execute(
            select(NeighbourhoodKpi)
            .where(NeighbourhoodKpi.neighbourhood_id == neighbourhood_id)
            .order_by(NeighbourhoodKpi.snapshot_date.desc())
            .limit(12)
        )
        .scalars()
        .all()
    )
    return [
        TrendPointOut(
            snapshot_date=r.snapshot_date,
            transit_score=float(r.transit_score or 0),
        )
        for r in rows
        if r.snapshot_date is not None
    ]
