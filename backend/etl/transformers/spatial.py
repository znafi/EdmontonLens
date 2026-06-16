"""Spatial assignment helpers.

Used to enrich point datasets (parks, stops) with the ``neighbourhood_id``
of the polygon they fall inside, so cross-domain KPI aggregation works on
real Edmonton open data even when the source datasets don't carry a
neighbourhood field of their own.

Uses Shapely for point-in-polygon checks. Falls back to a nearest-centroid
match if no polygon contains the point (covers boundary edge cases).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def _load_polygons(neighbourhoods: pd.DataFrame) -> list[tuple[str, Any, Any]]:
    """Return a list of (neighbourhood_id, shapely_polygon, centroid)."""
    try:
        from shapely.geometry import shape  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        logger.warning("Shapely not installed; skipping spatial assignment")
        return []

    polys: list[tuple[str, Any, Any]] = []
    for _, row in neighbourhoods.iterrows():
        nid = row.get("neighbourhood_id")
        gjs = row.get("boundary_geojson")
        if not nid or not gjs:
            continue
        try:
            geom = shape(json.loads(gjs))
            if not geom.is_valid:
                geom = geom.buffer(0)
            polys.append((str(nid), geom, geom.centroid))
        except Exception:  # noqa: BLE001
            continue
    return polys


def assign_neighbourhood(
    points: pd.DataFrame,
    neighbourhoods: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    target_col: str = "neighbourhood_id",
) -> pd.DataFrame:
    """Fill ``target_col`` for rows whose lat/lon falls inside a neighbourhood polygon.

    Existing non-null values in ``target_col`` are left alone, so this is a
    safe enrichment step. Returns the same frame (with the column populated).
    """
    if points.empty or neighbourhoods.empty:
        return points
    if lat_col not in points.columns or lon_col not in points.columns:
        return points

    try:
        from shapely.geometry import Point  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        logger.warning("Shapely not installed; skipping spatial assignment")
        return points

    polys = _load_polygons(neighbourhoods)
    if not polys:
        return points

    out = points.copy()
    if target_col not in out.columns:
        out[target_col] = None

    new_ids: list[str | None] = []
    missing_target = pd.isna(out[target_col]) | (out[target_col].astype(str) == "")

    lat_series = pd.to_numeric(out[lat_col], errors="coerce")
    lon_series = pd.to_numeric(out[lon_col], errors="coerce")

    for idx, (lat, lon, current) in enumerate(zip(lat_series, lon_series, out[target_col])):
        if not bool(missing_target.iloc[idx]):
            new_ids.append(str(current))
            continue
        if pd.isna(lat) or pd.isna(lon):
            new_ids.append(None)
            continue
        pt = Point(float(lon), float(lat))
        match: str | None = None
        for nid, poly, _centroid in polys:
            if poly.contains(pt):
                match = nid
                break
        if match is None:
            # Fall back to nearest centroid for points just outside any polygon.
            try:
                nearest = min(polys, key=lambda p: p[2].distance(pt))
                match = nearest[0]
            except Exception:  # noqa: BLE001
                match = None
        new_ids.append(match)

    out[target_col] = new_ids
    return out
