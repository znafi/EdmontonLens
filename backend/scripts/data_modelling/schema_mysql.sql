-- ============================================================================
-- EdmontonLens -- Data Warehouse DDL (MySQL 8.x dialect)
-- Target engine: MySQL 8.3+
-- Co-op roles served: all (Transit Scheduling CG, Parks & Analytics GO,
--                          Waste Training Tech SC, Data Administration NL)
-- ----------------------------------------------------------------------------
-- Differences from schema.sql (ANSI):
--   * BOOLEAN -> TINYINT(1)
--   * TEXT retained (MySQL supports it natively)
--   * Every table ends with ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
--   * All PKs are VARCHAR so no AUTO_INCREMENT is needed
-- ============================================================================

-- TRANSIT TABLES (serves: Transit Scheduling CG role)

CREATE TABLE IF NOT EXISTS transit_routes (
    route_id          VARCHAR(50)  NOT NULL,
    route_short_name  VARCHAR(10)  DEFAULT NULL,
    route_long_name   VARCHAR(200) DEFAULT NULL,
    route_type        INT          DEFAULT NULL,
    ingested_at       DATETIME     DEFAULT NULL,
    PRIMARY KEY (route_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transit_stops (
    stop_id           VARCHAR(50)  NOT NULL,
    stop_name         VARCHAR(200) DEFAULT NULL,
    stop_lat          DECIMAL(10,7) DEFAULT NULL,
    stop_lon          DECIMAL(10,7) DEFAULT NULL,
    neighbourhood_id  VARCHAR(50)  DEFAULT NULL,
    ingested_at       DATETIME     DEFAULT NULL,
    PRIMARY KEY (stop_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transit_performance (
    perf_id           VARCHAR(100) NOT NULL,
    route_id          VARCHAR(50)  DEFAULT NULL,
    service_date      DATE         DEFAULT NULL,
    on_time_rate      DECIMAL(5,4) DEFAULT NULL,
    avg_delay_mins    DECIMAL(6,2) DEFAULT NULL,
    total_trips       INT          DEFAULT NULL,
    delayed_trips     INT          DEFAULT NULL,
    ingested_at       DATETIME     DEFAULT NULL,
    PRIMARY KEY (perf_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transit_stop_delays (
    delay_id          VARCHAR(100) NOT NULL,
    stop_id           VARCHAR(50)  DEFAULT NULL,
    route_id          VARCHAR(50)  DEFAULT NULL,
    service_date      DATE         DEFAULT NULL,
    avg_delay_mins    DECIMAL(6,2) DEFAULT NULL,
    incident_count    INT          DEFAULT NULL,
    ingested_at       DATETIME     DEFAULT NULL,
    PRIMARY KEY (delay_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- PARKS TABLES (serves: Parks & Analytics GO role)

CREATE TABLE IF NOT EXISTS parks (
    park_id           VARCHAR(100) NOT NULL,
    park_name         VARCHAR(200) DEFAULT NULL,
    neighbourhood_id  VARCHAR(50)  DEFAULT NULL,
    park_type         VARCHAR(100) DEFAULT NULL,
    area_sqm          DECIMAL(12,2) DEFAULT NULL,
    amenities         TEXT,
    latitude          DECIMAL(10,7) DEFAULT NULL,
    longitude         DECIMAL(10,7) DEFAULT NULL,
    ingested_at       DATETIME     DEFAULT NULL,
    PRIMARY KEY (park_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- WASTE TABLES (serves: Waste Training Tech SC role)

CREATE TABLE IF NOT EXISTS waste_schedules (
    schedule_id       VARCHAR(100) NOT NULL,
    neighbourhood_id  VARCHAR(50)  DEFAULT NULL,
    pickup_day        VARCHAR(20)  DEFAULT NULL,
    waste_type        VARCHAR(50)  DEFAULT NULL,
    biweekly          TINYINT(1)   DEFAULT NULL,
    ingested_at       DATETIME     DEFAULT NULL,
    PRIMARY KEY (schedule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- NEIGHBOURHOOD TABLES (serves: Parks GO + Transit CG roles)

CREATE TABLE IF NOT EXISTS neighbourhoods (
    neighbourhood_id    VARCHAR(50)   NOT NULL,
    neighbourhood_name  VARCHAR(200)  DEFAULT NULL,
    boundary_geojson    TEXT,
    area_sqkm           DECIMAL(10,4) DEFAULT NULL,
    ingested_at         DATETIME      DEFAULT NULL,
    PRIMARY KEY (neighbourhood_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS neighbourhood_kpis (
    kpi_id               VARCHAR(100) NOT NULL,
    neighbourhood_id     VARCHAR(50)  DEFAULT NULL,
    snapshot_date        DATE         DEFAULT NULL,
    transit_stop_count   INT          DEFAULT NULL,
    avg_route_on_time    DECIMAL(5,4) DEFAULT NULL,
    park_count           INT          DEFAULT NULL,
    total_park_area_sqm  DECIMAL(14,2) DEFAULT NULL,
    waste_pickup_days    INT          DEFAULT NULL,
    transit_score        DECIMAL(4,2) DEFAULT NULL,
    park_score           DECIMAL(4,2) DEFAULT NULL,
    overall_score        DECIMAL(4,2) DEFAULT NULL,
    ingested_at          DATETIME     DEFAULT NULL,
    PRIMARY KEY (kpi_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ML PREDICTIONS TABLE (serves: Parks GO role -- ML & Algorithms requirement)

CREATE TABLE IF NOT EXISTS delay_predictions (
    prediction_id     VARCHAR(100) NOT NULL,
    route_id          VARCHAR(50)  DEFAULT NULL,
    prediction_date   DATE         DEFAULT NULL,
    hour_of_day       INT          DEFAULT NULL,
    day_of_week       INT          DEFAULT NULL,
    delay_probability DECIMAL(5,4) DEFAULT NULL,
    model_version     VARCHAR(20)  DEFAULT NULL,
    ingested_at       DATETIME     DEFAULT NULL,
    PRIMARY KEY (prediction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
