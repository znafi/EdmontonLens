"""Extractor for Edmonton neighbourhood boundaries via the ESRI ArcGIS REST API.

Queries the City's ArcGIS feature service for neighbourhood boundary polygons
and returns them as GeoJSON features. Geometry is later serialised to a TEXT
column for storage in BigQuery / local DB.

Falls back to a small set of synthetic polygons when the service is offline.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

# Neighbourhood boundary feature layer (City of Edmonton ArcGIS).
NEIGHBOURHOOD_LAYER = (
    "Neighbourhood_Boundaries/MapServer/0/query"
)


async def _query_features() -> dict[str, Any]:
    """Query the ArcGIS REST endpoint and return the raw GeoJSON FeatureCollection."""
    url = f"{settings.arcgis_base_url}{NEIGHBOURHOOD_LAYER}"
    params = {
        "where": "1=1",
        "outFields": "*",
        "outSR": "4326",
        "f": "geojson",
    }
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def extract_neighbourhood_boundaries() -> dict[str, Any]:
    """Return neighbourhood boundaries as a GeoJSON FeatureCollection dict."""
    try:
        fc = await _query_features()
        if not fc.get("features"):
            raise ValueError("ArcGIS returned no features")
        logger.info("Fetched %d neighbourhood boundary features", len(fc["features"]))
        return fc
    except Exception as exc:  # noqa: BLE001
        logger.warning("ArcGIS fetch failed (%s); using synthetic boundaries", exc)
        return _sample_feature_collection()


def feature_collection_to_geojson_string(geometry: dict[str, Any]) -> str:
    """Serialise a single geometry dict to a compact GeoJSON string."""
    return json.dumps(geometry, separators=(",", ":"))


def _sample_feature_collection() -> dict[str, Any]:
    """Five small square polygons roughly around Edmonton."""
    names = ["Glenora", "Oliver", "Strathcona", "Mill Woods", "Windermere"]
    ids = ["1010", "1020", "1030", "1040", "1050"]
    features = []
    for i, (nid, name) in enumerate(zip(ids, names, strict=True)):
        lat0 = 53.50 + i * 0.04
        lon0 = -113.55 + i * 0.05
        d = 0.02
        ring = [
            [lon0, lat0],
            [lon0 + d, lat0],
            [lon0 + d, lat0 + d],
            [lon0, lat0 + d],
            [lon0, lat0],
        ]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "neighbourhood_id": nid,
                    "neighbourhood_name": name,
                    "area_sqkm": round(2.0 + i * 0.5, 4),
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        )
    return {"type": "FeatureCollection", "features": features}
