"""SQLAlchemy ORM models for transit tables.

Serves the Transit Scheduling CG co-op role.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class TransitRoute(Base):
    __tablename__ = "transit_routes"

    route_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    route_short_name: Mapped[str | None] = mapped_column(String(10))
    route_long_name: Mapped[str | None] = mapped_column(String(200))
    route_type: Mapped[int | None] = mapped_column(Integer)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime)


class TransitStop(Base):
    __tablename__ = "transit_stops"

    stop_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    stop_name: Mapped[str | None] = mapped_column(String(200))
    stop_lat: Mapped[float | None] = mapped_column(Numeric(10, 7))
    stop_lon: Mapped[float | None] = mapped_column(Numeric(10, 7))
    neighbourhood_id: Mapped[str | None] = mapped_column(String(50))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime)


class TransitPerformance(Base):
    __tablename__ = "transit_performance"

    perf_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    route_id: Mapped[str | None] = mapped_column(String(50))
    service_date: Mapped[date | None] = mapped_column(Date)
    on_time_rate: Mapped[float | None] = mapped_column(Numeric(5, 4))
    avg_delay_mins: Mapped[float | None] = mapped_column(Numeric(6, 2))
    total_trips: Mapped[int | None] = mapped_column(Integer)
    delayed_trips: Mapped[int | None] = mapped_column(Integer)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime)


class TransitStopDelay(Base):
    __tablename__ = "transit_stop_delays"

    delay_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    stop_id: Mapped[str | None] = mapped_column(String(50))
    route_id: Mapped[str | None] = mapped_column(String(50))
    service_date: Mapped[date | None] = mapped_column(Date)
    avg_delay_mins: Mapped[float | None] = mapped_column(Numeric(6, 2))
    incident_count: Mapped[int | None] = mapped_column(Integer)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime)
