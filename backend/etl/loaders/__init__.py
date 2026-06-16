"""ETL loaders for BigQuery (prod) and the local dev database."""

from backend.etl.loaders.bigquery import load_to_bigquery
from backend.etl.loaders.local_db import load_to_local_db

__all__ = ["load_to_bigquery", "load_to_local_db"]
