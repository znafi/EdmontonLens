"""ETL orchestrator for EdmontonLens.

Flow:
    1. Run all extractors concurrently (asyncio.gather).
    2. Transform raw frames with pure Pandas functions.
    3. Validate output schemas (transformers raise on missing columns).
    4. Load every table to BigQuery (if configured) AND the local DB.
    5. Retrain the ML delay predictor on the fresh performance data.
    6. Log timings/row counts throughout; exit(1) on any failure.

Run with: ``python -m backend.etl.pipeline``
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Any

import pandas as pd

from backend.config import settings
from backend.etl.extractors import (
    extract_gtfs,
    extract_neighbourhood_boundaries,
    extract_parks,
    extract_transit_routes,
    extract_transit_stops,
    extract_waste_schedules,
)
from backend.etl.loaders import load_to_bigquery, load_to_local_db
from backend.etl.loaders.mysql_loader import load_to_mysql
from backend.etl.loaders.sqlserver_loader import load_to_sqlserver
from backend.etl.transformers import (
    assign_neighbourhood,
    build_neighbourhood_kpis,
    transform_neighbourhoods,
    transform_parks,
    transform_performance,
    transform_routes,
    transform_stop_delays,
    transform_stops,
    transform_waste,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("edmontonlens.etl")


async def _extract_all() -> dict[str, Any]:
    """Run every extractor concurrently and return a dict of raw outputs.

    Boundaries are fetched first so we can pass real neighbourhood IDs to the
    waste extractor's synthetic fallback, ensuring KPI coverage city-wide.
    """
    logger.info("Starting extraction phase — fetching boundaries first")
    boundaries = await extract_neighbourhood_boundaries()

    # Derive real neighbourhood IDs so the waste fallback covers every
    # neighbourhood in the boundaries dataset rather than 5 hardcoded ones.
    real_nids: list[str] = []
    for feature in boundaries.get("features", []):
        props = feature.get("properties", {})
        nid = (
            props.get("neighbourhood_id")
            or props.get("neighbourhood_number")
            or props.get("neighbourh")
            or props.get("OBJECTID")
            or props.get("id")
        )
        if nid:
            real_nids.append(str(nid))

    logger.info("  found %d neighbourhood IDs for waste fallback", len(real_nids))

    (
        raw_routes,
        raw_stops,
        raw_parks,
        raw_waste,
        gtfs,
    ) = await asyncio.gather(
        extract_transit_routes(),
        extract_transit_stops(),
        extract_parks(),
        extract_waste_schedules(neighbourhood_ids=real_nids or None),
        extract_gtfs(),
    )
    return {
        "raw_routes": raw_routes,
        "raw_stops": raw_stops,
        "raw_parks": raw_parks,
        "raw_waste": raw_waste,
        "gtfs": gtfs,
        "boundaries": boundaries,
    }


def _transform_all(raw: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Apply all transformers and return cleaned frames keyed by table name."""
    logger.info("Starting transform phase")
    routes = transform_routes(raw["raw_routes"])
    stops = transform_stops(raw["raw_stops"])
    parks = transform_parks(raw["raw_parks"])
    waste = transform_waste(raw["raw_waste"])
    performance = transform_performance(raw["gtfs"], real_routes=routes)
    stop_delays = transform_stop_delays(raw["gtfs"], real_stops=stops, real_routes=routes)
    neighbourhoods = transform_neighbourhoods(raw["boundaries"])

    # Spatial enrichment: assign neighbourhood_id to stops and parks using
    # point-in-polygon against the real boundary GeoJSON. Datasets like the
    # GTFS stops and the parks catalog don't carry a neighbourhood field, so
    # this is what unlocks accurate per-neighbourhood KPI aggregation.
    stops = assign_neighbourhood(stops, neighbourhoods, lat_col="stop_lat", lon_col="stop_lon")
    parks = assign_neighbourhood(parks, neighbourhoods)

    kpis = build_neighbourhood_kpis(neighbourhoods, stops, parks, waste, performance)
    return {
        "transit_routes": routes,
        "transit_stops": stops,
        "parks": parks,
        "waste_schedules": waste,
        "transit_performance": performance,
        "transit_stop_delays": stop_delays,
        "neighbourhoods": neighbourhoods,
        "neighbourhood_kpis": kpis,
    }


def _load_all(frames: dict[str, pd.DataFrame]) -> None:
    """Load every frame to BigQuery (if enabled), local DB, MySQL, and SQL Server."""
    logger.info("Starting load phase (bigquery_enabled=%s)", settings.bigquery_enabled)
    for table, df in frames.items():
        if settings.bigquery_enabled:
            try:
                load_to_bigquery(table, df)
            except Exception as exc:  # noqa: BLE001
                logger.error("BigQuery load failed for %s: %s", table, exc)
                raise
        load_to_local_db(table, df)
        load_to_mysql(table, df)
        load_to_sqlserver(table, df)


def run_pipeline() -> None:
    """Execute the full ETL pipeline synchronously."""
    start = time.perf_counter()
    raw = asyncio.run(_extract_all())
    for key, val in raw.items():
        if isinstance(val, pd.DataFrame):
            logger.info("  extracted %s: %d rows", key, len(val))

    frames = _transform_all(raw)
    for table, df in frames.items():
        logger.info("  transformed %s: %d rows", table, len(df))

    _load_all(frames)

    # --- ML retraining step ---
    logger.info("Starting ML training phase")
    from backend.ml.delay_predictor import train_and_persist

    predictions = train_and_persist(frames["transit_performance"], frames["transit_stops"])
    if predictions is not None and not predictions.empty:
        if settings.bigquery_enabled:
            load_to_bigquery("delay_predictions", predictions)
        load_to_local_db("delay_predictions", predictions)
        load_to_mysql("delay_predictions", predictions)
        load_to_sqlserver("delay_predictions", predictions)
        logger.info("  loaded %d delay predictions", len(predictions))

    elapsed = time.perf_counter() - start
    logger.info("Pipeline completed successfully in %.2fs", elapsed)


def main() -> None:
    """CLI entrypoint; exits 1 on any failure for CI visibility."""
    try:
        run_pipeline()
    except Exception:  # noqa: BLE001
        logger.exception("Pipeline FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
