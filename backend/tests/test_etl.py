"""Tests for ETL transformers and extractor fallbacks."""

from __future__ import annotations

import asyncio

import pandas as pd

from backend.etl.extractors import extract_gtfs, extract_transit_routes
from backend.etl.transformers import (
    build_neighbourhood_kpis,
    transform_neighbourhoods,
    transform_parks,
    transform_performance,
    transform_routes,
    transform_stops,
    transform_waste,
)
from backend.etl.transformers.transit import transform_stop_delays


def test_extractor_fallback_returns_dataframe() -> None:
    df = asyncio.run(extract_transit_routes())
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_gtfs_fallback_has_expected_keys() -> None:
    gtfs = asyncio.run(extract_gtfs())
    for key in ["routes", "trips", "stop_times", "stops", "calendar"]:
        assert key in gtfs
        assert isinstance(gtfs[key], pd.DataFrame)


def test_transform_routes_schema() -> None:
    raw = pd.DataFrame(
        {
            "route_id": ["1", "1", "2"],
            "route_short_name": ["1", "1", "2"],
            "route_long_name": ["A", "A", "B"],
            "route_type": ["3", "3", "0"],
        }
    )
    out = transform_routes(raw)
    assert list(out.columns) == [
        "route_id",
        "route_short_name",
        "route_long_name",
        "route_type",
        "ingested_at",
    ]
    assert len(out) == 2  # de-duplicated
    assert out["route_type"].dtype.kind in "iu"


def test_transform_performance_is_bounded() -> None:
    gtfs = asyncio.run(extract_gtfs())
    out = transform_performance(gtfs)
    assert not out.empty
    assert (out["on_time_rate"] >= 0).all() and (out["on_time_rate"] <= 1).all()
    assert {"perf_id", "route_id", "service_date"}.issubset(out.columns)


def test_transform_waste_normalises_types() -> None:
    raw = pd.DataFrame(
        {
            "schedule_id": ["a"],
            "neighbourhood_id": ["1010"],
            "pickup_day": ["monday"],
            "waste_type": ["RECYCLING"],
            "biweekly": ["true"],
        }
    )
    out = transform_waste(raw)
    assert out.loc[0, "waste_type"] == "recycling"
    assert out.loc[0, "pickup_day"] == "Monday"
    assert bool(out.loc[0, "biweekly"]) is True


def test_build_kpis_produces_overall_score() -> None:
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {"neighbourhood_id": "1010", "neighbourhood_name": "Glenora"},
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
            }
        ],
    }
    neigh = transform_neighbourhoods(fc)
    stops = transform_stops(
        pd.DataFrame(
            {
                "stop_id": ["S1"],
                "stop_name": ["x"],
                "stop_lat": [53.5],
                "stop_lon": [-113.5],
                "neighbourhood_id": ["1010"],
            }
        )
    )
    parks = transform_parks(
        pd.DataFrame({"park_id": ["P1"], "neighbourhood_id": ["1010"], "area_sqm": [1000]})
    )
    waste = transform_waste(
        pd.DataFrame(
            {
                "schedule_id": ["a"],
                "neighbourhood_id": ["1010"],
                "pickup_day": ["Monday"],
                "waste_type": ["garbage"],
                "biweekly": [False],
            }
        )
    )
    perf = pd.DataFrame({"route_id": ["1"], "on_time_rate": [0.8], "service_date": ["2024-01-01"]})
    kpis = build_neighbourhood_kpis(neigh, stops, parks, waste, perf)
    assert not kpis.empty
    assert "overall_score" in kpis.columns
    assert (kpis["overall_score"] >= 0).all()


def test_transform_stop_delays_keys() -> None:
    gtfs = asyncio.run(extract_gtfs())
    out = transform_stop_delays(gtfs)
    assert {"delay_id", "stop_id", "route_id", "avg_delay_mins"}.issubset(out.columns)
