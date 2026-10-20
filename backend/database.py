"""Database access layer.

Provides:
    * A SQLAlchemy engine + session factory for the local dev database
      (PostgreSQL in Docker, SQLite by default).

The API and agent always read from this database. BigQuery is an optional
warehouse written by the ETL (see ``backend/etl/loaders/bigquery.py``).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


def _make_engine(database_url: str) -> Any:
    """Create a SQLAlchemy engine, ensuring the SQLite data dir exists."""
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        # Ensure ./data exists for the SQLite file.
        db_path = database_url.replace("sqlite:///", "")
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    return create_engine(database_url, connect_args=connect_args, future=True)


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped SQLAlchemy session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create all tables in the local database (idempotent)."""
    # Importing models registers them on ``Base.metadata``.
    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Local database initialised at %s", settings.database_url)
