"""Load cleaned DataFrames into BigQuery.

Loads are idempotent, and use only load and query jobs (no DML), so they work
in the free BigQuery sandbox, which rejects INSERT/UPDATE/DELETE/MERGE:

    * Full-refresh dimension tables are overwritten with a ``WRITE_TRUNCATE``
      load job.
    * Time-series tables are loaded into a ``_staging_<table>`` table, then the
      target is rebuilt as ``target UNION ALL staging`` keeping one row per
      primary key (the incoming row wins). Re-running the same day therefore
      never adds rows; a new day adds only that day's keys.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from backend.config import settings

if TYPE_CHECKING:
    from google.cloud import bigquery

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

_client: bigquery.Client | None = None


def get_client() -> bigquery.Client:
    """Return a BigQuery client using the credentials file from settings.

    ``GOOGLE_APPLICATION_CREDENTIALS`` is read from ``.env`` by pydantic, which
    does not export it to ``os.environ``, so it is loaded explicitly here. The
    file may be a service-account key or the ``authorized_user`` file written
    by ``gcloud auth application-default login``.
    """
    global _client
    if _client is None:
        import google.auth
        from google.cloud import bigquery

        credentials, _ = google.auth.load_credentials_from_file(
            settings.google_application_credentials,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        _client = bigquery.Client(
            project=settings.gcp_project_id,
            credentials=credentials,
            location=settings.bigquery_location,
        )
    return _client


def load_to_bigquery(table: str, df: pd.DataFrame) -> int:
    """Load a DataFrame into ``project.dataset.table``. Returns rows sent.

    Raises ``RuntimeError`` if BigQuery is not configured.
    """
    if not settings.bigquery_enabled:
        raise RuntimeError("BigQuery not configured")
    if df.empty:
        logger.info("Skipping BigQuery load for %s (empty frame)", table)
        return 0

    from google.cloud import bigquery

    client = get_client()
    dataset = f"{settings.gcp_project_id}.{settings.bigquery_dataset}"
    target = f"{dataset}.{table}"
    df = _arrow_safe(df)

    if table not in TIME_SERIES:
        _load_frame(client, df, target)
        logger.info("BigQuery: replaced %s with %d rows", target, len(df))
        return len(df)

    staging = f"{dataset}._staging_{table}"
    _load_frame(client, df, staging)
    try:
        if not _table_exists(client, target):
            sql = f"SELECT * FROM `{staging}`"
        else:
            pk = PRIMARY_KEYS[table]
            cols = ", ".join(f"`{c}`" for c in df.columns)
            # _src = 1 marks incoming rows so they win ties on the primary key.
            sql = f"""
                SELECT * EXCEPT (_src)
                FROM (
                  SELECT {cols}, 0 AS _src FROM `{target}`
                  UNION ALL
                  SELECT {cols}, 1 AS _src FROM `{staging}`
                )
                WHERE TRUE
                QUALIFY ROW_NUMBER() OVER (PARTITION BY `{pk}` ORDER BY _src DESC) = 1
            """
        job_config = bigquery.QueryJobConfig(
            destination=target,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        client.query(sql, job_config=job_config).result()
    finally:
        client.delete_table(staging, not_found_ok=True)

    total = client.get_table(target).num_rows
    logger.info("BigQuery: merged %d incoming rows into %s (now %d rows)", len(df), target, total)
    return len(df)


def _load_frame(client: bigquery.Client, df: pd.DataFrame, destination: str) -> None:
    from google.cloud import bigquery

    job_config = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
    client.load_table_from_dataframe(df, destination, job_config=job_config).result()


def _table_exists(client: bigquery.Client, table_id: str) -> bool:
    from google.api_core.exceptions import NotFound

    try:
        client.get_table(table_id)
        return True
    except NotFound:
        return False


def _arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Give all-null object columns a string type so pyarrow can infer a schema."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object and df[col].isna().all():
            df[col] = df[col].astype("string")
    return df
