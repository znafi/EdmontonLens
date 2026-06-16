"""SQLAlchemy ORM models for waste tables.

Serves the Waste Training Tech SC co-op role.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class WasteSchedule(Base):
    __tablename__ = "waste_schedules"

    schedule_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    neighbourhood_id: Mapped[str | None] = mapped_column(String(50))
    pickup_day: Mapped[str | None] = mapped_column(String(20))
    waste_type: Mapped[str | None] = mapped_column(String(50))  # garbage|recycling|organics
    biweekly: Mapped[bool | None] = mapped_column(Boolean)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime)
