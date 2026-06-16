"""Load cleaned DataFrames into BigQuery via ``pandas_gbq``.

Loads are idempotent:
    * Full-refresh dimension tables use ``if_exists='replace'``.
    * Append-only time-series tables use ``if_exists='append'`` but de-duplicate
      on their primary key first, so re-running the same day is safe.
"""

from __future__ import annotations

import logging

import pandas as pd

from backend.config import settings

logger = logging.getLogger(__name__)

# Tables fully replaced on each run (dimensions / current-state).
FULL_REFRESH = {"transit_routes", "transit_stops", "parks", "waste_schedules", "neighbourhoods"}
# Append-only time-series tables.
TIME_SERIES = {
    "transit_performance",
    "transit_stop_delays",
    "neighbourhood_kpis",
    "delay_predictions",
}

PRIMARY_KEYS = {
    "transit_performance": "perf_id",
    "transit_stop_delays": "delay_id",
    "neighbourhood_kpis": "kpi_id",
    "delay_predictions": "prediction_id",
}


def load_to_bigquery(table: str, df: pd.DataFrame) -> int:
    """Load a DataFrame into ``dataset.table`` in BigQuery.

    Returns the number of rows loaded. Raises ``RuntimeError`` if BigQuery is
    not configured so the caller can fall back to local storage.
    """
    if not settings.bigquery_enabled:
        raise RuntimeError("BigQuery not configured")

    import pandas_gbq

    destination = f"{settings.bigquery_dataset}.{table}"
    if_exists = "replace" if table in FULL_REFRESH else "append"

    if table in TIME_SERIES:
        df = _dedupe_existing(table, df)

    if df.empty:
        logger.info("Skipping BigQuery load for %s (no new rows)", table)
        return 0

    pandas_gbq.to_gbq(
        df,
        destination_table=destination,
        project_id=settings.gcp_project_id,
        if_exists=if_exists,
        progress_bar=False,
    )
    logger.info("Loaded %d rows into BigQuery table %s (%s)", len(df), destination, if_exists)
    return len(df)


def _dedupe_existing(table: str, df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose primary key already exists in the destination table."""
    pk = PRIMARY_KEYS.get(table)
    if pk is None or df.empty:
        return df
    try:
        import pandas_gbq

        existing = pandas_gbq.read_gbq(
            f"SELECT {pk} FROM `{settings.bigquery_dataset}.{table}`",
            project_id=settings.gcp_project_id,
            progress_bar_type=None,
        )
        if not existing.empty:
            df = df[~df[pk].isin(set(existing[pk]))]
    except Exception as exc:  # noqa: BLE001  (table may not exist yet)
        logger.debug("Dedupe skipped for %s: %s", table, exc)
    return df
