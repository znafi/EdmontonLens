"""System prompt and shared schema metadata for the CityBot agent."""

from __future__ import annotations

# Canonical table schemas, used by both the prompt and the SchemaInspectorTool.
TABLE_SCHEMAS: dict[str, dict[str, str]] = {
    "transit_routes": {
        "route_id": "VARCHAR — primary key",
        "route_short_name": "VARCHAR — e.g. '8', '512'",
        "route_long_name": "VARCHAR — human-readable route name",
        "route_type": "INTEGER — 3=bus, 0=tram/LRT",
        "ingested_at": "TIMESTAMP",
    },
    "transit_stops": {
        "stop_id": "VARCHAR — primary key",
        "stop_name": "VARCHAR",
        "stop_lat": "DECIMAL",
        "stop_lon": "DECIMAL",
        "neighbourhood_id": "VARCHAR — FK to neighbourhoods",
        "ingested_at": "TIMESTAMP",
    },
    "transit_performance": {
        "perf_id": "VARCHAR — primary key",
        "route_id": "VARCHAR — FK to transit_routes",
        "service_date": "DATE",
        "on_time_rate": "DECIMAL — 0..1",
        "avg_delay_mins": "DECIMAL",
        "total_trips": "INTEGER",
        "delayed_trips": "INTEGER",
        "ingested_at": "TIMESTAMP",
    },
    "transit_stop_delays": {
        "delay_id": "VARCHAR — primary key",
        "stop_id": "VARCHAR — FK to transit_stops",
        "route_id": "VARCHAR — FK to transit_routes",
        "service_date": "DATE",
        "avg_delay_mins": "DECIMAL",
        "incident_count": "INTEGER",
        "ingested_at": "TIMESTAMP",
    },
    "parks": {
        "park_id": "VARCHAR — primary key",
        "park_name": "VARCHAR",
        "neighbourhood_id": "VARCHAR — FK to neighbourhoods",
        "park_type": "VARCHAR",
        "area_sqm": "DECIMAL",
        "amenities": "TEXT — JSON array string",
        "latitude": "DECIMAL",
        "longitude": "DECIMAL",
        "ingested_at": "TIMESTAMP",
    },
    "waste_schedules": {
        "schedule_id": "VARCHAR — primary key",
        "neighbourhood_id": "VARCHAR — FK to neighbourhoods",
        "pickup_day": "VARCHAR — e.g. 'Monday'",
        "waste_type": "VARCHAR — garbage|recycling|organics",
        "biweekly": "BOOLEAN",
        "ingested_at": "TIMESTAMP",
    },
    "neighbourhoods": {
        "neighbourhood_id": "VARCHAR — primary key",
        "neighbourhood_name": "VARCHAR — e.g. 'Glenora'",
        "boundary_geojson": "TEXT — GeoJSON polygon",
        "area_sqkm": "DECIMAL",
        "ingested_at": "TIMESTAMP",
    },
    "neighbourhood_kpis": {
        "kpi_id": "VARCHAR — primary key",
        "neighbourhood_id": "VARCHAR — FK to neighbourhoods",
        "snapshot_date": "DATE",
        "transit_stop_count": "INTEGER",
        "avg_route_on_time": "DECIMAL — 0..1",
        "park_count": "INTEGER",
        "total_park_area_sqm": "DECIMAL",
        "waste_pickup_days": "INTEGER — per month",
        "transit_score": "DECIMAL — 0..10",
        "park_score": "DECIMAL — 0..10",
        "overall_score": "DECIMAL — 0..10",
        "ingested_at": "TIMESTAMP",
    },
    "delay_predictions": {
        "prediction_id": "VARCHAR — primary key",
        "route_id": "VARCHAR — FK to transit_routes",
        "prediction_date": "DATE",
        "hour_of_day": "INTEGER — 0..23",
        "day_of_week": "INTEGER — 0=Mon..6=Sun",
        "delay_probability": "DECIMAL — 0..1",
        "model_version": "VARCHAR",
        "ingested_at": "TIMESTAMP",
    },
}


def _schema_overview() -> str:
    lines: list[str] = []
    for table, cols in TABLE_SCHEMAS.items():
        col_list = ", ".join(cols.keys())
        lines.append(f"- {table}({col_list})")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You are CityBot, the data analyst for EdmontonLens, a civic
analytics platform built on City of Edmonton open data.

You answer resident questions by querying a SQL data warehouse. The available
tables are:

{_schema_overview()}

RULES YOU MUST FOLLOW:
1. ALWAYS call SchemaInspectorTool for a table BEFORE writing any SQL that
   references it, to confirm exact column names and types.
2. Use BigQuerySQLTool to run read-only SELECT queries. Never attempt INSERT,
   UPDATE, DELETE, DROP, or any DDL.
3. ALWAYS add `LIMIT 500` (or less) to every query. Never return more than 500 rows.
4. Use only ANSI-standard SQL so the query is portable.
5. Return your final answer in plain English first, then on a new line append
   the exact SQL you used, prefixed with `SQL:`.
6. NEVER expose internal error messages, stack traces, or credentials to the
   user. If a query fails, apologise briefly and suggest rephrasing.

You can answer questions like:
- "Which bus route had the most delays last month?"
- "Which neighbourhood has the most parks per square kilometre?"
- "What day is garbage pickup in Glenora?"
- "Show me the 5 transit stops with the worst average delays."
"""
