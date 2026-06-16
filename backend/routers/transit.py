"""Transit API routes: routes, stops, delays, performance, ML predictions."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.ml.delay_predictor import predict_delay_probability
from backend.models import (
    TransitPerformance,
    TransitRoute,
    TransitStop,
    TransitStopDelay,
)

router = APIRouter(prefix="/api/transit", tags=["transit"])


class RouteOut(BaseModel):
    route_id: str
    route_short_name: str | None = None
    route_long_name: str | None = None
    route_type: int | None = None


class StopOut(BaseModel):
    stop_id: str
    stop_name: str | None = None
    stop_lat: float | None = None
    stop_lon: float | None = None
    neighbourhood_id: str | None = None


class PerformancePointOut(BaseModel):
    route_id: str
    service_date: date | None = None
    on_time_rate: float
    avg_delay_mins: float


class StopDelayOut(BaseModel):
    stop_id: str
    stop_name: str | None = None
    avg_delay_mins: float


class PredictionOut(BaseModel):
    route_id: str
    delay_probability: float


@router.get("/routes", response_model=list[RouteOut])
def list_routes(session: Session = Depends(get_session)) -> list[RouteOut]:
    rows = session.execute(select(TransitRoute)).scalars().all()
    return [
        RouteOut(
            route_id=r.route_id,
            route_short_name=r.route_short_name,
            route_long_name=r.route_long_name,
            route_type=r.route_type,
        )
        for r in rows
    ]


@router.get("/stops", response_model=list[StopOut])
def list_stops(
    limit: int = Query(500, le=2000),
    session: Session = Depends(get_session),
) -> list[StopOut]:
    rows = session.execute(select(TransitStop).limit(limit)).scalars().all()
    return [
        StopOut(
            stop_id=s.stop_id,
            stop_name=s.stop_name,
            stop_lat=float(s.stop_lat) if s.stop_lat is not None else None,
            stop_lon=float(s.stop_lon) if s.stop_lon is not None else None,
            neighbourhood_id=s.neighbourhood_id,
        )
        for s in rows
    ]


@router.get("/performance", response_model=list[PerformancePointOut])
def performance(
    days: int = Query(30, le=90),
    session: Session = Depends(get_session),
) -> list[PerformancePointOut]:
    """Daily on-time performance per route for the last ``days`` days."""
    rows = (
        session.execute(
            select(TransitPerformance).order_by(TransitPerformance.service_date.desc())
        )
        .scalars()
        .all()
    )
    return [
        PerformancePointOut(
            route_id=p.route_id or "",
            service_date=p.service_date,
            on_time_rate=float(p.on_time_rate or 0),
            avg_delay_mins=float(p.avg_delay_mins or 0),
        )
        for p in rows
    ]


@router.get("/delays", response_model=list[StopDelayOut])
def top_delays(
    limit: int = Query(10, le=50),
    session: Session = Depends(get_session),
) -> list[StopDelayOut]:
    """Top stops by average delay (minutes), descending. Joins transit_stops
    so the chart can render the real stop name instead of a cryptic ID."""
    stmt = (
        select(
            TransitStopDelay.stop_id,
            TransitStop.stop_name,
            func.avg(TransitStopDelay.avg_delay_mins).label("mean_delay"),
        )
        .join(
            TransitStop,
            TransitStop.stop_id == TransitStopDelay.stop_id,
            isouter=True,
        )
        .group_by(TransitStopDelay.stop_id, TransitStop.stop_name)
        .order_by(func.avg(TransitStopDelay.avg_delay_mins).desc())
        .limit(limit)
    )
    rows = session.execute(stmt).all()
    return [
        StopDelayOut(
            stop_id=r.stop_id,
            stop_name=r.stop_name,
            avg_delay_mins=float(r.mean_delay or 0),
        )
        for r in rows
    ]


@router.get("/predict", response_model=PredictionOut)
def predict(
    route_id: str = Query(...),
    hour: int = Query(8, ge=0, le=23),
    day: int = Query(0, ge=0, le=6),
) -> PredictionOut:
    """Return the ML model's delay probability for a route/hour/day."""
    proba = predict_delay_probability(route_id, hour, day)
    return PredictionOut(route_id=route_id, delay_probability=proba)
