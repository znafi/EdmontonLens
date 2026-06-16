"""Database access layer.

Provides:
    * A SQLAlchemy engine + session factory for the local dev database
      (PostgreSQL in Docker, SQLite by default).
    * A lazily-initialised BigQuery client for production reads/writes.

The app degrades gracefully: if no GCP credentials are configured, BigQuery
helpers raise a clear error and callers fall back to the local database.
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


# --------------------------------------------------------------------------- #
# BigQuery
# --------------------------------------------------------------------------- #
_bq_client: Any | None = None


def get_bigquery_client() -> Any:
    """Return a cached BigQuery client.

    Raises:
        RuntimeError: if BigQuery is not configured (no GCP credentials).
    """
    global _bq_client
    if not settings.bigquery_enabled:
        raise RuntimeError(
            "BigQuery is not configured. Set GCP_PROJECT_ID and "
            "GOOGLE_APPLICATION_CREDENTIALS, or use the local database fallback."
        )
    if _bq_client is None:
        from google.cloud import bigquery

        _bq_client = bigquery.Client(project=settings.gcp_project_id)
        logger.info("Initialised BigQuery client for project %s", settings.gcp_project_id)
    return _bq_client


def dataset_ref() -> str:
    """Return the fully-qualified ``project.dataset`` reference."""
    return f"{settings.gcp_project_id}.{settings.bigquery_dataset}"
