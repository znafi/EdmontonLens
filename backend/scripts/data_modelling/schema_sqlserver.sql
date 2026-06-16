-- ============================================================================
-- EdmontonLens -- Data Warehouse DDL (SQL Server / T-SQL dialect)
-- Target engine: SQL Server 2022 (Developer Edition)
-- Co-op roles served: all (Transit Scheduling CG, Parks & Analytics GO,
--                          Waste Training Tech SC, Data Administration NL)
-- ----------------------------------------------------------------------------
-- Differences from schema.sql (ANSI):
--   * BOOLEAN        -> BIT
--   * TEXT           -> NVARCHAR(MAX)
--   * VARCHAR        -> NVARCHAR
--   * TIMESTAMP      -> DATETIME2
--   * GO statement after each CREATE TABLE
-- ============================================================================

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'edmonton_lens')
BEGIN
    CREATE DATABASE edmonton_lens;
END
GO

USE edmonton_lens;
GO

-- TRANSIT TABLES (serves: Transit Scheduling CG role)

IF OBJECT_ID('dbo.transit_routes', 'U') IS NULL
CREATE TABLE dbo.transit_routes (
    route_id          NVARCHAR(50)  NOT NULL,
    route_short_name  NVARCHAR(10)  NULL,
    route_long_name   NVARCHAR(200) NULL,
    route_type        INT           NULL,
    ingested_at       DATETIME2     NULL,
    CONSTRAINT PK_transit_routes PRIMARY KEY (route_id)
);
GO

IF OBJECT_ID('dbo.transit_stops', 'U') IS NULL
CREATE TABLE dbo.transit_stops (
    stop_id           NVARCHAR(50)  NOT NULL,
    stop_name         NVARCHAR(200) NULL,
    stop_lat          DECIMAL(10,7) NULL,
    stop_lon          DECIMAL(10,7) NULL,
    neighbourhood_id  NVARCHAR(50)  NULL,
    ingested_at       DATETIME2     NULL,
    CONSTRAINT PK_transit_stops PRIMARY KEY (stop_id)
);
GO

IF OBJECT_ID('dbo.transit_performance', 'U') IS NULL
CREATE TABLE dbo.transit_performance (
    perf_id           NVARCHAR(100) NOT NULL,
    route_id          NVARCHAR(50)  NULL,
    service_date      DATE          NULL,
    on_time_rate      DECIMAL(5,4)  NULL,
    avg_delay_mins    DECIMAL(6,2)  NULL,
    total_trips       INT           NULL,
    delayed_trips     INT           NULL,
    ingested_at       DATETIME2     NULL,
    CONSTRAINT PK_transit_performance PRIMARY KEY (perf_id)
);
GO

IF OBJECT_ID('dbo.transit_stop_delays', 'U') IS NULL
CREATE TABLE dbo.transit_stop_delays (
    delay_id          NVARCHAR(100) NOT NULL,
    stop_id           NVARCHAR(50)  NULL,
    route_id          NVARCHAR(50)  NULL,
    service_date      DATE          NULL,
    avg_delay_mins    DECIMAL(6,2)  NULL,
    incident_count    INT           NULL,
    ingested_at       DATETIME2     NULL,
    CONSTRAINT PK_transit_stop_delays PRIMARY KEY (delay_id)
);
GO

-- PARKS TABLES (serves: Parks & Analytics GO role)

IF OBJECT_ID('dbo.parks', 'U') IS NULL
CREATE TABLE dbo.parks (
    park_id           NVARCHAR(100)  NOT NULL,
    park_name         NVARCHAR(200)  NULL,
    neighbourhood_id  NVARCHAR(50)   NULL,
    park_type         NVARCHAR(100)  NULL,
    area_sqm          DECIMAL(12,2)  NULL,
    amenities         NVARCHAR(MAX)  NULL,
    latitude          DECIMAL(10,7)  NULL,
    longitude         DECIMAL(10,7)  NULL,
    ingested_at       DATETIME2      NULL,
    CONSTRAINT PK_parks PRIMARY KEY (park_id)
);
GO

-- WASTE TABLES (serves: Waste Training Tech SC role)

IF OBJECT_ID('dbo.waste_schedules', 'U') IS NULL
CREATE TABLE dbo.waste_schedules (
    schedule_id       NVARCHAR(100) NOT NULL,
    neighbourhood_id  NVARCHAR(50)  NULL,
    pickup_day        NVARCHAR(20)  NULL,
    waste_type        NVARCHAR(50)  NULL,
    biweekly          BIT           NULL,
    ingested_at       DATETIME2     NULL,
    CONSTRAINT PK_waste_schedules PRIMARY KEY (schedule_id)
);
GO

-- NEIGHBOURHOOD TABLES (serves: Parks GO + Transit CG roles)

IF OBJECT_ID('dbo.neighbourhoods', 'U') IS NULL
CREATE TABLE dbo.neighbourhoods (
    neighbourhood_id    NVARCHAR(50)   NOT NULL,
    neighbourhood_name  NVARCHAR(200)  NULL,
    boundary_geojson    NVARCHAR(MAX)  NULL,
    area_sqkm           DECIMAL(10,4)  NULL,
    ingested_at         DATETIME2      NULL,
    CONSTRAINT PK_neighbourhoods PRIMARY KEY (neighbourhood_id)
);
GO

IF OBJECT_ID('dbo.neighbourhood_kpis', 'U') IS NULL
CREATE TABLE dbo.neighbourhood_kpis (
    kpi_id               NVARCHAR(100) NOT NULL,
    neighbourhood_id     NVARCHAR(50)  NULL,
    snapshot_date        DATE          NULL,
    transit_stop_count   INT           NULL,
    avg_route_on_time    DECIMAL(5,4)  NULL,
    park_count           INT           NULL,
    total_park_area_sqm  DECIMAL(14,2) NULL,
    waste_pickup_days    INT           NULL,
    transit_score        DECIMAL(4,2)  NULL,
    park_score           DECIMAL(4,2)  NULL,
    overall_score        DECIMAL(4,2)  NULL,
    ingested_at          DATETIME2     NULL,
    CONSTRAINT PK_neighbourhood_kpis PRIMARY KEY (kpi_id)
);
GO

-- ML PREDICTIONS TABLE (serves: Parks GO role -- ML & Algorithms requirement)

IF OBJECT_ID('dbo.delay_predictions', 'U') IS NULL
CREATE TABLE dbo.delay_predictions (
    prediction_id     NVARCHAR(100) NOT NULL,
    route_id          NVARCHAR(50)  NULL,
    prediction_date   DATE          NULL,
    hour_of_day       INT           NULL,
    day_of_week       INT           NULL,
    delay_probability DECIMAL(5,4)  NULL,
    model_version     NVARCHAR(20)  NULL,
    ingested_at       DATETIME2     NULL,
    CONSTRAINT PK_delay_predictions PRIMARY KEY (prediction_id)
);
GO
