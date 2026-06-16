"""Extractor for the Edmonton Open Data portal (Socrata API).

Pulls transit routes, transit stops, parks, and waste collection schedules.
If the network is unavailable (e.g. local dev / CI without internet), each
extractor falls back to a small deterministic synthetic sample so the rest of
the pipeline can run end-to-end.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
import pandas as pd

from backend.config import settings

logger = logging.getLogger(__name__)

# Socrata resource identifiers for each dataset on data.edmonton.ca.
RESOURCES: dict[str, str] = {
    "transit_routes": "j5kf-rh43",
    "transit_stops": "5sn6-mznv",
    "parks": "p8my-em7p",
    "waste_schedules": "tqsr-x3cn",
}

DEFAULT_LIMIT = 5000


async def _fetch_resource(resource_id: str, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    """Fetch rows from a single Socrata resource as a list of dicts."""
    url = f"{settings.socrata_base_url}{resource_id}.json"
    headers: dict[str, str] = {}
    if settings.edmonton_open_data_app_token:
        headers["X-App-Token"] = settings.edmonton_open_data_app_token
    params = {"$limit": str(limit)}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data: list[dict[str, Any]] = resp.json()
        return data


async def extract_transit_routes() -> pd.DataFrame:
    """Return raw transit routes as a DataFrame."""
    try:
        rows = await _fetch_resource(RESOURCES["transit_routes"])
        return pd.DataFrame(rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Socrata transit_routes fetch failed (%s); using sample data", exc)
        return _sample_routes()


async def extract_transit_stops() -> pd.DataFrame:
    """Return raw transit stops as a DataFrame."""
    try:
        rows = await _fetch_resource(RESOURCES["transit_stops"])
        return pd.DataFrame(rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Socrata transit_stops fetch failed (%s); using sample data", exc)
        return _sample_stops()


async def extract_parks() -> pd.DataFrame:
    """Return raw parks data as a DataFrame."""
    try:
        rows = await _fetch_resource(RESOURCES["parks"])
        return pd.DataFrame(rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Socrata parks fetch failed (%s); using sample data", exc)
        return _sample_parks()


async def extract_waste_schedules() -> pd.DataFrame:
    """Return raw waste collection schedules as a DataFrame."""
    try:
        rows = await _fetch_resource(RESOURCES["waste_schedules"])
        return pd.DataFrame(rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Socrata waste_schedules fetch failed (%s); using sample data", exc)
        return _sample_waste()


# --------------------------------------------------------------------------- #
# Deterministic synthetic fallbacks
# --------------------------------------------------------------------------- #
_NEIGHBOURHOODS = ["1010", "1020", "1030", "1040", "1050"]
_NEIGHBOURHOOD_NAMES = ["Glenora", "Oliver", "Strathcona", "Mill Woods", "Windermere"]


def _sample_routes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "route_id": [f"R{i}" for i in range(1, 11)],
            "route_short_name": [str(i) for i in range(1, 11)],
            "route_long_name": [f"Route {i} Crosstown" for i in range(1, 11)],
            "route_type": [3] * 8 + [0, 0],
        }
    )


def _sample_stops() -> pd.DataFrame:
    base_lat, base_lon = 53.5461, -113.4938
    return pd.DataFrame(
        {
            "stop_id": [f"S{i}" for i in range(1, 21)],
            "stop_name": [f"Stop {i}" for i in range(1, 21)],
            "stop_lat": [base_lat + (i * 0.005) for i in range(20)],
            "stop_lon": [base_lon + (i * 0.004) for i in range(20)],
            "neighbourhood_id": [_NEIGHBOURHOODS[i % len(_NEIGHBOURHOODS)] for i in range(20)],
        }
    )


def _sample_parks() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "park_id": [f"P{i}" for i in range(1, 16)],
            "park_name": [f"{_NEIGHBOURHOOD_NAMES[i % 5]} Park {i}" for i in range(15)],
            "neighbourhood_id": [_NEIGHBOURHOODS[i % 5] for i in range(15)],
            "park_type": ["District", "Pocket", "River Valley"] * 5,
            "area_sqm": [1000.0 * (i + 1) for i in range(15)],
            "amenities": ['["playground", "trail"]'] * 15,
            "latitude": [53.54 + i * 0.003 for i in range(15)],
            "longitude": [-113.49 + i * 0.003 for i in range(15)],
        }
    )


def _sample_waste() -> pd.DataFrame:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    types = ["garbage", "recycling", "organics"]
    rows = []
    for i, nid in enumerate(_NEIGHBOURHOODS):
        for j, wtype in enumerate(types):
            rows.append(
                {
                    "schedule_id": f"{nid}-{wtype}",
                    "neighbourhood_id": nid,
                    "pickup_day": days[(i + j) % len(days)],
                    "waste_type": wtype,
                    "biweekly": wtype != "garbage",
                }
            )
    return pd.DataFrame(rows)
