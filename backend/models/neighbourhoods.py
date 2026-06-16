"""SQLAlchemy ORM models for neighbourhood boundary + KPI tables.

Serves the Parks & Analytics GO and Transit Scheduling CG co-op roles.
Also holds the ML delay-prediction outputs (Parks GO ML requirement).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Neighbourhood(Base):
    __tablename__ = "neighbourhoods"

    neighbourhood_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    neighbourhood_name: Mapped[str | None] = mapped_column(String(200))
    boundary_geojson: Mapped[str | None] = mapped_column(Text)  # serialised GeoJSON
    area_sqkm: Mapped[float | None] = mapped_column(Numeric(10, 4))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime)


class NeighbourhoodKpi(Base):
    __tablename__ = "neighbourhood_kpis"

    kpi_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    neighbourhood_id: Mapped[str | None] = mapped_column(String(50))
    snapshot_date: Mapped[date | None] = mapped_column(Date)
    transit_stop_count: Mapped[int | None] = mapped_column(Integer)
    avg_route_on_time: Mapped[float | None] = mapped_column(Numeric(5, 4))
    park_count: Mapped[int | None] = mapped_column(Integer)
    total_park_area_sqm: Mapped[float | None] = mapped_column(Numeric(14, 2))
    waste_pickup_days: Mapped[int | None] = mapped_column(Integer)
    transit_score: Mapped[float | None] = mapped_column(Numeric(4, 2))
    park_score: Mapped[float | None] = mapped_column(Numeric(4, 2))
    overall_score: Mapped[float | None] = mapped_column(Numeric(4, 2))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime)


class DelayPrediction(Base):
    __tablename__ = "delay_predictions"

    prediction_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    route_id: Mapped[str | None] = mapped_column(String(50))
    prediction_date: Mapped[date | None] = mapped_column(Date)
    hour_of_day: Mapped[int | None] = mapped_column(Integer)
    day_of_week: Mapped[int | None] = mapped_column(Integer)
    delay_probability: Mapped[float | None] = mapped_column(Numeric(5, 4))
    model_version: Mapped[str | None] = mapped_column(String(20))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime)
