-- Freshness: when was each table last loaded, and how recent is the newest day
-- of history? Thresholds are 36 hours (daily refresh plus slack).
SELECT 'freshness_ingested_at' AS check_name, t AS table_name,
       IF(hours_old <= 36, 'PASS', 'FAIL') AS status,
       CAST(hours_old AS INT64) AS failing_rows,
       CONCAT('last ingested ', FORMAT_TIMESTAMP('%F %H:%M UTC', last_ts)) AS detail
FROM (
  SELECT 'transit_stops' AS t, MAX(ingested_at) AS last_ts,
         TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(ingested_at), HOUR) AS hours_old
  FROM `{{ds}}.transit_stops`
  UNION ALL
  SELECT 'transit_performance', MAX(ingested_at),
         TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(ingested_at), HOUR)
  FROM `{{ds}}.transit_performance`
  UNION ALL
  SELECT 'neighbourhood_kpis', MAX(ingested_at),
         TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(ingested_at), HOUR)
  FROM `{{ds}}.neighbourhood_kpis`
)
UNION ALL
SELECT 'freshness_latest_service_date', 'transit_performance',
       IF(DATE_DIFF(CURRENT_DATE(), MAX(service_date), DAY) <= 1, 'PASS', 'FAIL'),
       DATE_DIFF(CURRENT_DATE(), MAX(service_date), DAY),
       CONCAT('latest service_date ', CAST(MAX(service_date) AS STRING))
FROM `{{ds}}.transit_performance`;
