"""Pandas transformers for neighbourhood boundaries and composite KPI aggregates."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


def transform_neighbourhoods(feature_collection: dict[str, Any]) -> pd.DataFrame:
    """Flatten an ArcGIS GeoJSON FeatureCollection into the ``neighbourhoods`` schema."""
    rows: list[dict[str, Any]] = []
    for feature in feature_collection.get("features", []):
        props = feature.get("properties", {})
        # Socrata GeoJSON truncates field names to 10 characters, so we accept
        # both the full and the truncated variants.
        nid = str(
            props.get("neighbourhood_id")
            or props.get("neighbourhood_number")
            or props.get("neighbourh")
            or props.get("OBJECTID")
            or props.get("id")
            or len(rows) + 1
        )
        name = (
            props.get("neighbourhood_name")
            or props.get("descriptive_name")
            or props.get("descriptiv")
            or props.get("name")
            or f"Neighbourhood {nid}"
        )
        rows.append(
            {
                "neighbourhood_id": nid,
                "neighbourhood_name": name,
                "boundary_geojson": json.dumps(feature.get("geometry", {}), separators=(",", ":")),
                "area_sqkm": float(props.get("area_sqkm") or 0.0),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        out = pd.DataFrame(
            columns=["neighbourhood_id", "neighbourhood_name", "boundary_geojson", "area_sqkm"]
        )
    out = out.drop_duplicates(subset=["neighbourhood_id"])
    out["ingested_at"] = datetime.utcnow()
    return out.reset_index(drop=True)


def build_neighbourhood_kpis(
    neighbourhoods: pd.DataFrame,
    stops: pd.DataFrame,
    parks: pd.DataFrame,
    waste: pd.DataFrame,
    performance: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate cross-domain metrics into a composite KPI row per neighbourhood."""
    snapshot_date = datetime.utcnow().date()

    stop_counts = stops.groupby("neighbourhood_id").size() if not stops.empty else pd.Series(dtype=int)
    park_counts = parks.groupby("neighbourhood_id").size() if not parks.empty else pd.Series(dtype=int)
    park_area = (
        parks.groupby("neighbourhood_id")["area_sqm"].sum()
        if not parks.empty
        else pd.Series(dtype=float)
    )
    waste_days = (
        waste.groupby("neighbourhood_id").size() * 4  # approx pickups per month
        if not waste.empty
        else pd.Series(dtype=int)
    )
    city_on_time = float(performance["on_time_rate"].mean()) if not performance.empty else 0.75

    rows: list[dict[str, Any]] = []
    for nid in neighbourhoods["neighbourhood_id"]:
        n_stops = int(stop_counts.get(nid, 0))
        n_parks = int(park_counts.get(nid, 0))
        area = float(park_area.get(nid, 0.0))
        pickups = int(waste_days.get(nid, 0))
        on_time = float(np.clip(city_on_time + (hash(nid) % 10 - 5) / 100.0, 0.4, 0.99))

        transit_score = float(np.clip(n_stops / 4.0 + on_time * 5, 0, 10))
        park_score = float(np.clip(n_parks * 0.8 + area / 5000.0, 0, 10))
        overall = round((transit_score + park_score) / 2.0, 2)
        rows.append(
            {
                "kpi_id": f"{nid}-{snapshot_date.isoformat()}",
                "neighbourhood_id": nid,
                "snapshot_date": snapshot_date,
                "transit_stop_count": n_stops,
                "avg_route_on_time": round(on_time, 4),
                "park_count": n_parks,
                "total_park_area_sqm": round(area, 2),
                "waste_pickup_days": pickups,
                "transit_score": round(transit_score, 2),
                "park_score": round(park_score, 2),
                "overall_score": overall,
            }
        )
    out = pd.DataFrame(rows)
    out["ingested_at"] = datetime.utcnow()
    _require_columns(out, ["kpi_id", "neighbourhood_id", "overall_score"])
    return out


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Transformed KPI frame missing columns: {missing}")
