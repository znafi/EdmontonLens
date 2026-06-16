"""Tests for the FastAPI endpoints using a seeded local SQLite database."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from backend.database import SessionLocal, init_db
from backend.main import app
from backend.models import (
    Neighbourhood,
    NeighbourhoodKpi,
    Park,
    TransitPerformance,
    TransitRoute,
    WasteSchedule,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    init_db()
    _seed()
    return TestClient(app)


def _seed() -> None:
    session = SessionLocal()
    try:
        session.merge(
            TransitRoute(
                route_id="1",
                route_short_name="1",
                route_long_name="Test",
                route_type=3,
                ingested_at=datetime.utcnow(),
            )
        )
        session.merge(
            TransitPerformance(
                perf_id="1-2024-01-01",
                route_id="1",
                service_date=datetime(2024, 1, 1).date(),
                on_time_rate=0.85,
                avg_delay_mins=3.2,
                total_trips=10,
                delayed_trips=2,
                ingested_at=datetime.utcnow(),
            )
        )
        session.merge(
            Neighbourhood(
                neighbourhood_id="1010",
                neighbourhood_name="Glenora",
                boundary_geojson='{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]}',
                area_sqkm=2.5,
                ingested_at=datetime.utcnow(),
            )
        )
        session.merge(
            NeighbourhoodKpi(
                kpi_id="1010-2024-01-01",
                neighbourhood_id="1010",
                snapshot_date=datetime(2024, 1, 1).date(),
                transit_stop_count=5,
                avg_route_on_time=0.85,
                park_count=3,
                total_park_area_sqm=5000,
                waste_pickup_days=8,
                transit_score=7.5,
                park_score=6.0,
                overall_score=6.75,
                ingested_at=datetime.utcnow(),
            )
        )
        session.merge(
            Park(
                park_id="P1",
                park_name="Glenora Park",
                neighbourhood_id="1010",
                park_type="District",
                area_sqm=5000,
                amenities='["trail"]',
                latitude=53.5,
                longitude=-113.5,
                ingested_at=datetime.utcnow(),
            )
        )
        session.merge(
            WasteSchedule(
                schedule_id="1010-garbage",
                neighbourhood_id="1010",
                pickup_day="Monday",
                waste_type="garbage",
                biweekly=False,
                ingested_at=datetime.utcnow(),
            )
        )
        session.commit()
    finally:
        session.close()


def test_root(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_routes(client: TestClient) -> None:
    resp = client.get("/api/transit/routes")
    assert resp.status_code == 200
    assert any(r["route_id"] == "1" for r in resp.json())


def test_transit_predict(client: TestClient) -> None:
    resp = client.get("/api/transit/predict", params={"route_id": "1", "hour": 8, "day": 0})
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["delay_probability"] <= 1.0


def test_neighbourhood_geojson(client: TestClient) -> None:
    resp = client.get("/api/neighbourhoods/geojson")
    assert resp.status_code == 200
    fc = resp.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 1
    assert "overall_score" in fc["features"][0]["properties"]


def test_neighbourhood_snapshot(client: TestClient) -> None:
    resp = client.get("/api/neighbourhoods/1010/snapshot")
    assert resp.status_code == 200
    assert resp.json()["neighbourhood_name"] == "Glenora"


def test_parks_list(client: TestClient) -> None:
    resp = client.get("/api/parks/list")
    assert resp.status_code == 200
    assert resp.json()[0]["amenities"] == ["trail"]


def test_waste_diversion_rate(client: TestClient) -> None:
    resp = client.get("/api/waste/diversion-rate")
    assert resp.status_code == 200
    assert 0.0 <= resp.json()["diversion_rate"] <= 1.0
