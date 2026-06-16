"""SQLAlchemy ORM models for parks tables.

Serves the Parks & Analytics GO co-op role.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Park(Base):
    __tablename__ = "parks"

    park_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    park_name: Mapped[str | None] = mapped_column(String(200))
    neighbourhood_id: Mapped[str | None] = mapped_column(String(50))
    park_type: Mapped[str | None] = mapped_column(String(100))
    area_sqm: Mapped[float | None] = mapped_column(Numeric(12, 2))
    amenities: Mapped[str | None] = mapped_column(Text)  # JSON array as string
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime)
