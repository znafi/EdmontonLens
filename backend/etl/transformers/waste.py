"""Pandas transformer for waste collection schedules. Pure function."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

_VALID_TYPES = {"garbage", "recycling", "organics"}


def transform_waste(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean raw waste schedule data into the ``waste_schedules`` schema."""
    df = raw.copy()
    columns = ["schedule_id", "neighbourhood_id", "pickup_day", "waste_type", "biweekly"]
    for col in columns:
        if col not in df.columns:
            df[col] = None
    out = df[columns].copy()
    out["schedule_id"] = out["schedule_id"].astype(str)
    out["waste_type"] = (
        out["waste_type"].astype(str).str.lower().where(lambda s: s.isin(_VALID_TYPES), "garbage")
    )
    out["pickup_day"] = out["pickup_day"].astype(str).str.title()
    out["biweekly"] = out["biweekly"].apply(_to_bool)
    out = out.drop_duplicates(subset=["schedule_id"])
    out["ingested_at"] = datetime.utcnow()
    _require_columns(out, columns)
    return out.reset_index(drop=True)


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "biweekly"}
    return bool(value)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Transformed waste frame missing columns: {missing}")
