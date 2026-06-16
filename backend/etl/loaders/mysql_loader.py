"""MySQL loader -- writes cleaned DataFrames to the local MySQL instance.

Mirrors local_db.py but targets MySQL 8.x via PyMySQL. Used to demonstrate
MySQL familiarity for the Data Administration (NL) co-op role.

Loads are idempotent: full-refresh tables are truncated then re-inserted;
time-series tables delete matching primary keys before inserting.
"""

from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from backend.config import settings
from backend.etl.loaders.bigquery import FULL_REFRESH, PRIMARY_KEYS, TIME_SERIES

logger = logging.getLogger(__name__)

_engine: Engine | None = None


def _get_mysql_engine() -> Engine:
    global _engine
    if _engine is None:
        url = settings.mysql_database_url
        _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


def load_to_mysql(table: str, df: pd.DataFrame) -> int:
    """Load a DataFrame into MySQL. Returns rows written, or 0 on skip/error."""
    if not settings.mysql_enabled:
        logger.debug("MySQL not configured, skipping load for %s", table)
        return 0
    if df.empty:
        logger.info("Skipping MySQL load for %s (empty frame)", table)
        return 0

    engine = _get_mysql_engine()
    try:
        with engine.begin() as conn:
            if table in FULL_REFRESH:
                conn.execute(text(f"DELETE FROM `{table}`"))
            elif table in TIME_SERIES:
                pk = PRIMARY_KEYS.get(table)
                if pk and pk in df.columns:
                    _delete_by_keys_mysql(conn, table, pk, df[pk].astype(str).tolist())

        df.to_sql(table, con=engine, if_exists="append", index=False, chunksize=1000)
        logger.info("MySQL: loaded %d rows into %s", len(df), table)
        return len(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("MySQL load skipped for %s (%s)", table, exc)
        return 0


def _delete_by_keys_mysql(conn: object, table: str, pk: str, ids: list[str]) -> None:
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        batch = ids[i : i + batch_size]
        placeholders = ", ".join(f":id{j}" for j in range(len(batch)))
        params = {f"id{j}": v for j, v in enumerate(batch)}
        conn.execute(text(f"DELETE FROM `{table}` WHERE `{pk}` IN ({placeholders})"), params)  # type: ignore[union-attr]
