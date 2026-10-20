"""Export BigQuery views to files Tableau Public can open (it cannot connect to BigQuery).

    python -m scripts.export_tableau

Writes to ``tableau/data/``:
    neighbourhood_scores.csv / .geojson   from v_neighbourhood_scores (+ stops/parks view)
    route_performance_daily.csv           from v_route_performance_daily
    data_quality.csv                      all sql/quality/*.sql results, plus run time
    export_manifest.json                  row counts and export time

Run ``python -m scripts.bq_sql views`` first so the views exist.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from backend.config import settings
from backend.etl.loaders.bigquery import get_client
from scripts.bq_sql import SQL_DIR, run_file

OUT = Path(__file__).resolve().parent.parent / "tableau" / "data"


def _view(name: str) -> pd.DataFrame:
    ds = f"{settings.gcp_project_id}.{settings.bigquery_dataset}"
    return get_client().query(f"SELECT * FROM `{ds}.{name}`").result().to_dataframe()


def export_neighbourhoods(manifest: dict) -> None:
    scores = _view("v_neighbourhood_scores")
    density = _view("v_stops_per_neighbourhood")[
        ["neighbourhood_id", "stops_per_sqkm", "park_area_share"]
    ]
    df = scores.merge(density, on="neighbourhood_id", how="left")
    df = df.round(4)
    df["overall_score_basis"] = "park score (real data) + transit score (includes simulated on-time)"

    features = [
        {
            "type": "Feature",
            "properties": {c: (None if pd.isna(v) else v) for c, v in row.items() if c != "boundary_geojson"},
            "geometry": json.loads(row["boundary_geojson"]),
        }
        for row in df.to_dict("records")
    ]
    # default=str: dates and numpy scalars from BigQuery are not JSON-native.
    (OUT / "neighbourhood_scores.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"), default=str)
    )
    df.drop(columns=["boundary_geojson"]).to_csv(OUT / "neighbourhood_scores.csv", index=False)
    manifest["neighbourhood_scores"] = len(df)


def export_routes(manifest: dict) -> None:
    df = _view("v_route_performance_daily").sort_values(["route_id", "service_date"]).round(4)
    df.to_csv(OUT / "route_performance_daily.csv", index=False)
    manifest["route_performance_daily"] = len(df)


def export_quality(manifest: dict) -> None:
    frames = [run_file(p) for p in sorted((SQL_DIR / "quality").glob("*.sql"))]
    df = pd.concat(frames, ignore_index=True)
    df.insert(0, "checked_at", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))
    df.to_csv(OUT / "data_quality.csv", index=False)
    manifest["data_quality"] = len(df)


def main() -> None:
    if not settings.bigquery_enabled:
        sys.exit("BigQuery is not configured (set GCP_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS).")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    export_neighbourhoods(manifest)
    export_routes(manifest)
    export_quality(manifest)
    manifest["exported_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    (OUT / "export_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
