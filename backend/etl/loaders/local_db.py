"""Load cleaned DataFrames into the local dev database (PostgreSQL or SQLite).

Uses an idempotent upsert-by-replace strategy:
    * Full-refresh tables are truncated then re-inserted.
    * Time-series tables delete any rows sharing a primary key in the incoming
      batch, then insert — so re-running the same day never duplicates rows.
"""

from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import text

from backend.database import engine, init_db
from backend.etl.loaders.bigquery import FULL_REFRESH, PRIMARY_KEYS, TIME_SERIES

logger = logging.getLogger(__name__)


def load_to_local_db(table: str, df: pd.DataFrame) -> int:
    """Load a DataFrame into the local database table. Returns rows written."""
    init_db()  # ensure tables exist (idempotent)

    if df.empty:
        logger.info("Skipping local load for %s (empty frame)", table)
        return 0

    with engine.begin() as conn:
        if table in FULL_REFRESH:
            conn.execute(text(f"DELETE FROM {table}"))
        elif table in TIME_SERIES:
            pk = PRIMARY_KEYS.get(table)
            if pk and pk in df.columns:
                ids = [str(v) for v in df[pk].tolist()]
                _delete_by_keys(conn, table, pk, ids)

    df.to_sql(table, con=engine, if_exists="append", index=False)
    logger.info("Loaded %d rows into local table %s", len(df), table)
    return len(df)


def _delete_by_keys(conn, table: str, pk: str, ids: list[str]) -> None:
    """Delete rows matching the given primary-key values (batched)."""
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        batch = ids[i : i + batch_size]
        placeholders = ", ".join(f":id{j}" for j in range(len(batch)))
        params = {f"id{j}": v for j, v in enumerate(batch)}
        conn.execute(text(f"DELETE FROM {table} WHERE {pk} IN ({placeholders})"), params)
