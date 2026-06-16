"""LangChain tool that executes read-only SQL against the warehouse.

Runs on BigQuery when GCP credentials are configured; otherwise transparently
falls back to the local SQLAlchemy database so the agent works in dev. Results
are returned as a Markdown table (capped at 500 rows).
"""

from __future__ import annotations

import logging
import re

import pandas as pd
from langchain_core.tools import BaseTool
from pydantic import PrivateAttr

from backend.config import settings

logger = logging.getLogger(__name__)

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|merge|grant|revoke)\b",
    re.IGNORECASE,
)
MAX_ROWS = 500


def _is_read_only(sql: str) -> bool:
    """Return True only for a single SELECT/WITH statement with no mutations."""
    stripped = sql.strip().rstrip(";")
    if ";" in stripped:  # block stacked statements
        return False
    if _FORBIDDEN.search(stripped):
        return False
    return stripped.lower().startswith(("select", "with"))


def _ensure_limit(sql: str) -> str:
    """Append a LIMIT clause if the query lacks one."""
    if re.search(r"\blimit\b", sql, re.IGNORECASE):
        return sql
    return f"{sql.rstrip().rstrip(';')} LIMIT {MAX_ROWS}"


def run_sql(sql: str) -> pd.DataFrame:
    """Execute a validated SELECT and return up to 500 rows as a DataFrame."""
    if not _is_read_only(sql):
        raise ValueError("Only single read-only SELECT statements are permitted.")
    sql = _ensure_limit(sql)

    if settings.bigquery_enabled:
        from backend.database import get_bigquery_client

        client = get_bigquery_client()
        # Qualify bare table names with the dataset for BigQuery.
        df = client.query(sql).result().to_dataframe()
    else:
        from sqlalchemy import text

        from backend.database import engine

        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
    return df.head(MAX_ROWS)


class BigQuerySQLTool(BaseTool):
    """Tool: takes a SQL string, runs it, returns a Markdown table."""

    name: str = "BigQuerySQLTool"
    description: str = (
        "Execute a read-only ANSI SQL SELECT against the EdmontonLens warehouse "
        "and return results as a Markdown table. Input must be a single SELECT "
        "statement with a LIMIT of 500 or fewer rows."
    )

    _last_rows: list[dict] = PrivateAttr(default_factory=list)
    _last_sql: str = PrivateAttr(default="")

    def _run(self, sql: str) -> str:  # type: ignore[override]
        try:
            df = run_sql(sql)
            self._last_sql = sql
            self._last_rows = df.to_dict(orient="records")
            if df.empty:
                return "Query returned no rows."
            try:
                return df.to_markdown(index=False)
            except ImportError:
                # ``tabulate`` not installed — fall back to a plain text table.
                return df.to_string(index=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SQL tool error: %s", exc)
            return "The query could not be executed. Please rephrase your question."

    async def _arun(self, sql: str) -> str:  # type: ignore[override]
        return self._run(sql)

    @property
    def last_rows(self) -> list[dict]:
        return self._last_rows

    @property
    def last_sql(self) -> str:
        return self._last_sql
