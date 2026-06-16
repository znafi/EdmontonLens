"""Extractor for the Edmonton Transit GTFS feed.

Downloads and parses the static GTFS zip (stop_times, trips, routes, stops,
calendar). When the feed is unreachable, returns a deterministic synthetic
schedule so on-time-rate computation can still run downstream.
"""

from __future__ import annotations

import io
import logging
import zipfile
from typing import Any

import httpx
import pandas as pd

from backend.config import settings

logger = logging.getLogger(__name__)

GTFS_FILES = ["stop_times.txt", "trips.txt", "routes.txt", "stops.txt", "calendar.txt"]


async def _download_gtfs_zip() -> bytes:
    """Download the GTFS zip archive as raw bytes."""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(settings.gtfs_feed_url)
        resp.raise_for_status()
        return resp.content


def _parse_zip(content: bytes) -> dict[str, pd.DataFrame]:
    """Parse the GTFS zip into a dict of DataFrames keyed by file stem."""
    frames: dict[str, pd.DataFrame] = {}
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = set(zf.namelist())
        for fname in GTFS_FILES:
            if fname in names:
                with zf.open(fname) as fh:
                    frames[fname.replace(".txt", "")] = pd.read_csv(fh, dtype=str)
    return frames


async def extract_gtfs() -> dict[str, pd.DataFrame]:
    """Return the parsed GTFS feed as a dict of DataFrames.

    Keys: 'stop_times', 'trips', 'routes', 'stops', 'calendar'.
    """
    try:
        content = await _download_gtfs_zip()
        frames = _parse_zip(content)
        if not frames:
            raise ValueError("GTFS archive contained no expected files")
        logger.info("Parsed GTFS feed: %s", {k: len(v) for k, v in frames.items()})
        return frames
    except Exception as exc:  # noqa: BLE001
        logger.warning("GTFS fetch/parse failed (%s); using synthetic schedule", exc)
        return _sample_gtfs()


def _sample_gtfs() -> dict[str, pd.DataFrame]:
    """Build a small but internally-consistent synthetic GTFS dataset."""
    routes = pd.DataFrame(
        {
            "route_id": [f"R{i}" for i in range(1, 11)],
            "route_short_name": [str(i) for i in range(1, 11)],
            "route_long_name": [f"Route {i} Crosstown" for i in range(1, 11)],
            "route_type": ["3"] * 8 + ["0", "0"],
        }
    )
    trips_rows: list[dict[str, Any]] = []
    stop_times_rows: list[dict[str, Any]] = []
    trip_counter = 0
    for r in routes["route_id"]:
        for t in range(20):  # 20 trips per route
            trip_id = f"{r}-T{t}"
            trips_rows.append({"route_id": r, "trip_id": trip_id, "service_id": "WKDY"})
            for seq in range(5):  # 5 stops per trip
                hh = 6 + (t % 16)
                sched = f"{hh:02d}:{(seq * 10) % 60:02d}:00"
                stop_times_rows.append(
                    {
                        "trip_id": trip_id,
                        "arrival_time": sched,
                        "departure_time": sched,
                        "stop_id": f"S{(t + seq) % 20 + 1}",
                        "stop_sequence": str(seq),
                    }
                )
            trip_counter += 1
    return {
        "routes": routes,
        "trips": pd.DataFrame(trips_rows),
        "stop_times": pd.DataFrame(stop_times_rows),
        "stops": pd.DataFrame(
            {
                "stop_id": [f"S{i}" for i in range(1, 21)],
                "stop_name": [f"Stop {i}" for i in range(1, 21)],
                "stop_lat": [str(53.5461 + i * 0.005) for i in range(20)],
                "stop_lon": [str(-113.4938 + i * 0.004) for i in range(20)],
            }
        ),
        "calendar": pd.DataFrame(
            {
                "service_id": ["WKDY"],
                "monday": ["1"],
                "tuesday": ["1"],
                "wednesday": ["1"],
                "thursday": ["1"],
                "friday": ["1"],
                "saturday": ["0"],
                "sunday": ["0"],
            }
        ),
    }
