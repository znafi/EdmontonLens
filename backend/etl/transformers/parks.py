"""Pandas transformer for parks data. Pure function: DataFrame in, DataFrame out."""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd


def transform_parks(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean raw parks data into the ``parks`` schema and normalise amenities."""
    df = raw.copy()
    columns = [
        "park_id",
        "park_name",
        "neighbourhood_id",
        "park_type",
        "area_sqm",
        "amenities",
        "latitude",
        "longitude",
    ]
    for col in columns:
        if col not in df.columns:
            df[col] = None
    out = df[columns].copy()
    out["park_id"] = out["park_id"].astype(str)
    out["area_sqm"] = pd.to_numeric(out["area_sqm"], errors="coerce").fillna(0.0)
    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")
    out["amenities"] = out["amenities"].apply(_normalise_amenities)
    out = out.drop_duplicates(subset=["park_id"])
    out["ingested_at"] = datetime.utcnow()
    _require_columns(out, columns)
    return out.reset_index(drop=True)


def _normalise_amenities(value: object) -> str:
    """Coerce an amenities value into a JSON-array string."""
    if isinstance(value, list):
        return json.dumps(value)
    if isinstance(value, str):
        v = value.strip()
        if v.startswith("["):
            return v
        if v:
            return json.dumps([part.strip() for part in v.split(",") if part.strip()])
    return "[]"


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Transformed parks frame missing columns: {missing}")
