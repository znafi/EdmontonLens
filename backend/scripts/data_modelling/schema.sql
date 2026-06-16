-- ============================================================================
-- EdmontonLens — Data Warehouse DDL
-- ----------------------------------------------------------------------------
-- ANSI SQL. Avoids vendor-specific syntax so these statements port cleanly to
-- BigQuery, PostgreSQL, SQL Server, and Oracle. Each table is annotated with
-- the City of Edmonton co-op role it is designed to serve.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TRANSIT TABLES (serves: Transit Scheduling CG role)
-- ----------------------------------------------------------------------------

-- Master list of every ETS bus and LRT route.
CREATE TABLE transit_routes (
    route_id         VARCHAR(50) PRIMARY KEY,
    route_short_name VARCHAR(10),
    route_long_name  VARCHAR(200),
    route_type       INTEGER,
    ingested_at      TIMESTAMP
);

-- Every transit stop with geographic coordinates and its neighbourhood.
CREATE TABLE transit_stops (
    stop_id          VARCHAR(50) PRIMARY KEY,
    stop_name        VARCHAR(200),
    stop_lat         DECIMAL(10,7),
    stop_lon         DECIMAL(10,7),
    neighbourhood_id VARCHAR(50),
    ingested_at      TIMESTAMP
);

-- Daily on-time performance aggregated per route (time-series, append-only).
CREATE TABLE transit_performance (
    perf_id        VARCHAR(100) PRIMARY KEY,
    route_id       VARCHAR(50),
    service_date   DATE,
    on_time_rate   DECIMAL(5,4),   -- 0.0000 to 1.0000
    avg_delay_mins DECIMAL(6,2),
    total_trips    INTEGER,
    delayed_trips  INTEGER,
    ingested_at    TIMESTAMP
);

-- Daily delay metrics per stop/route (time-series, append-only).
CREATE TABLE transit_stop_delays (
    delay_id       VARCHAR(100) PRIMARY KEY,
    stop_id        VARCHAR(50),
    route_id       VARCHAR(50),
    service_date   DATE,
    avg_delay_mins DECIMAL(6,2),
    incident_count INTEGER,
    ingested_at    TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- PARKS TABLES (serves: Parks & Analytics GO role)
-- ----------------------------------------------------------------------------

-- All parks with type, size, amenities, and location.
CREATE TABLE parks (
    park_id          VARCHAR(100) PRIMARY KEY,
    park_name        VARCHAR(200),
    neighbourhood_id VARCHAR(50),
    park_type        VARCHAR(100),
    area_sqm         DECIMAL(12,2),
    amenities        TEXT,           -- JSON array serialised as a string
    latitude         DECIMAL(10,7),
    longitude        DECIMAL(10,7),
    ingested_at      TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- WASTE TABLES (serves: Waste Training Tech SC role)
-- ----------------------------------------------------------------------------

-- Curbside collection schedule by neighbourhood and waste stream.
CREATE TABLE waste_schedules (
    schedule_id      VARCHAR(100) PRIMARY KEY,
    neighbourhood_id VARCHAR(50),
    pickup_day       VARCHAR(20),
    waste_type       VARCHAR(50),    -- 'garbage', 'recycling', 'organics'
    biweekly         BOOLEAN,
    ingested_at      TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- NEIGHBOURHOOD TABLES (serves: Parks & Analytics GO role + Transit CG role)
-- ----------------------------------------------------------------------------

-- Neighbourhood boundary polygons (GeoJSON) and area.
CREATE TABLE neighbourhoods (
    neighbourhood_id   VARCHAR(50) PRIMARY KEY,
    neighbourhood_name VARCHAR(200),
    boundary_geojson   TEXT,        -- serialised GeoJSON polygon
    area_sqkm          DECIMAL(10,4),
    ingested_at        TIMESTAMP
);

-- Composite KPI snapshot per neighbourhood (time-series, append-only).
CREATE TABLE neighbourhood_kpis (
    kpi_id              VARCHAR(100) PRIMARY KEY,
    neighbourhood_id    VARCHAR(50),
    snapshot_date       DATE,
    transit_stop_count  INTEGER,
    avg_route_on_time   DECIMAL(5,4),
    park_count          INTEGER,
    total_park_area_sqm DECIMAL(14,2),
    waste_pickup_days   INTEGER,       -- pickups per month
    transit_score       DECIMAL(4,2),  -- 0-10 composite KPI
    park_score          DECIMAL(4,2),
    overall_score       DECIMAL(4,2),
    ingested_at         TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- ML PREDICTIONS TABLE (serves: Parks GO role — ML & Algorithms requirement)
-- ----------------------------------------------------------------------------

-- Output of the RandomForest delay predictor (time-series, append-only).
CREATE TABLE delay_predictions (
    prediction_id     VARCHAR(100) PRIMARY KEY,
    route_id          VARCHAR(50),
    prediction_date   DATE,
    hour_of_day       INTEGER,
    day_of_week       INTEGER,
    delay_probability DECIMAL(5,4),
    model_version     VARCHAR(20),
    ingested_at       TIMESTAMP
);
