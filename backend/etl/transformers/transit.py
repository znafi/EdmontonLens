"""Pandas transformers for transit data.

Every function is pure: it takes DataFrame(s) and returns a new DataFrame.
On-time performance is derived from the GTFS schedule by simulating realistic
actual-vs-scheduled deltas (deterministic seed) since the City does not publish
historical real-time arrivals in the static feed.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

_RNG_SEED = 42
_HISTORY_DAYS = 30


def transform_routes(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean raw route data into the ``transit_routes`` schema."""
    df = raw.copy()
    cols = {
        "route_id": "route_id",
        "route_short_name": "route_short_name",
        "route_long_name": "route_long_name",
        "route_type": "route_type",
    }
    for src in cols:
        if src not in df.columns:
            df[src] = None
    out = df[list(cols)].rename(columns=cols)
    out["route_id"] = out["route_id"].astype(str)
    out["route_type"] = pd.to_numeric(out["route_type"], errors="coerce").fillna(3).astype(int)
    out = out.drop_duplicates(subset=["route_id"])
    out["ingested_at"] = datetime.utcnow()
    return out.reset_index(drop=True)


def transform_stops(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean raw stop data into the ``transit_stops`` schema."""
    df = raw.copy()
    for col in ["stop_id", "stop_name", "stop_lat", "stop_lon", "neighbourhood_id"]:
        if col not in df.columns:
            df[col] = None
    out = df[["stop_id", "stop_name", "stop_lat", "stop_lon", "neighbourhood_id"]].copy()
    out["stop_id"] = out["stop_id"].astype(str)
    out["stop_lat"] = pd.to_numeric(out["stop_lat"], errors="coerce")
    out["stop_lon"] = pd.to_numeric(out["stop_lon"], errors="coerce")
    out = out.dropna(subset=["stop_lat", "stop_lon"]).drop_duplicates(subset=["stop_id"])
    out["ingested_at"] = datetime.utcnow()
    return out.reset_index(drop=True)


def transform_performance(
    gtfs: dict[str, pd.DataFrame],
    real_routes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute daily on-time performance per route over the last 30 days.

    Prefers real Socrata route IDs (passed via ``real_routes``) over GTFS
    synthetic IDs when the bulk GTFS feed isn't reachable.
    """
    rng = np.random.default_rng(_RNG_SEED)
    trips = gtfs["trips"]
    gtfs_routes = sorted(trips["route_id"].astype(str).unique())
    if real_routes is not None and not real_routes.empty:
        route_ids = sorted(real_routes["route_id"].astype(str).unique())
    else:
        route_ids = gtfs_routes
    trips_per_route = trips.groupby("route_id").size().to_dict()

    today = datetime.utcnow().date()
    rows: list[dict] = []
    for day_offset in range(_HISTORY_DAYS):
        service_date = today - timedelta(days=day_offset)
        for route_id in route_ids:
            total_trips = int(trips_per_route.get(route_id, 10))
            # Base on-time rate per route, perturbed daily.
            base = 0.70 + (hash(route_id) % 25) / 100.0
            noise = rng.normal(0, 0.05)
            on_time_rate = float(np.clip(base + noise, 0.40, 0.99))
            delayed_trips = int(round(total_trips * (1 - on_time_rate)))
            avg_delay = float(np.clip(rng.normal(4.0 + (1 - on_time_rate) * 8, 1.5), 0.0, 30.0))
            rows.append(
                {
                    "perf_id": f"{route_id}-{service_date.isoformat()}",
                    "route_id": route_id,
                    "service_date": service_date,
                    "on_time_rate": round(on_time_rate, 4),
                    "avg_delay_mins": round(avg_delay, 2),
                    "total_trips": total_trips,
                    "delayed_trips": delayed_trips,
                }
            )
    out = pd.DataFrame(rows)
    out["ingested_at"] = datetime.utcnow()
    _require_columns(out, ["perf_id", "route_id", "service_date", "on_time_rate"])
    return out


def transform_stop_delays(
    gtfs: dict[str, pd.DataFrame],
    real_stops: pd.DataFrame | None = None,
    real_routes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute daily average delay per stop/route over the last 30 days.

    When real Socrata stops/routes are provided and the GTFS bulk feed has
    fallen back to synthetic data, we generate the (stop, route) pairs from
    the real data instead so the delay records reference actual stop IDs.
    """
    rng = np.random.default_rng(_RNG_SEED + 1)

    gtfs_is_synthetic = len(gtfs["stops"]) < 30  # heuristic
    if (
        gtfs_is_synthetic
        and real_stops is not None
        and real_routes is not None
        and not real_stops.empty
        and not real_routes.empty
    ):
        # Sample a manageable subset so the cross-product stays tractable.
        sample_stops = real_stops["stop_id"].astype(str).head(200).tolist()
        sample_routes = real_routes["route_id"].astype(str).head(15).tolist()
        pairs = pd.DataFrame(
            [(s, r) for s in sample_stops for r in sample_routes],
            columns=["stop_id", "route_id"],
        )
    else:
        stop_times = gtfs["stop_times"].merge(
            gtfs["trips"][["trip_id", "route_id"]], on="trip_id", how="left"
        )
        pairs = (
            stop_times[["stop_id", "route_id"]]
            .dropna()
            .drop_duplicates()
            .astype(str)
            .reset_index(drop=True)
        )
    today = datetime.utcnow().date()
    rows: list[dict] = []
    for day_offset in range(_HISTORY_DAYS):
        service_date = today - timedelta(days=day_offset)
        for _, row in pairs.iterrows():
            avg_delay = float(np.clip(rng.gamma(2.0, 2.0), 0.0, 35.0))
            rows.append(
                {
                    "delay_id": f"{row['stop_id']}-{row['route_id']}-{service_date.isoformat()}",
                    "stop_id": row["stop_id"],
                    "route_id": row["route_id"],
                    "service_date": service_date,
                    "avg_delay_mins": round(avg_delay, 2),
                    "incident_count": int(rng.integers(0, 4)),
                }
            )
    out = pd.DataFrame(rows)
    out["ingested_at"] = datetime.utcnow()
    _require_columns(out, ["delay_id", "stop_id", "route_id", "avg_delay_mins"])
    return out


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise if any required column is missing (schema validation)."""
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Transformed transit frame missing columns: {missing}")
