-- Each table's primary key must be unique. failing_rows = surplus rows.
SELECT 'duplicate_primary_key' AS check_name, t AS table_name,
       IF(n = 0, 'PASS', 'FAIL') AS status, n AS failing_rows, key AS detail
FROM (
  SELECT 'transit_routes' AS t, 'route_id' AS key, COUNT(*) - COUNT(DISTINCT route_id) AS n FROM `{{ds}}.transit_routes` UNION ALL
  SELECT 'transit_stops', 'stop_id', COUNT(*) - COUNT(DISTINCT stop_id) FROM `{{ds}}.transit_stops` UNION ALL
  SELECT 'parks', 'park_id', COUNT(*) - COUNT(DISTINCT park_id) FROM `{{ds}}.parks` UNION ALL
  SELECT 'waste_schedules', 'schedule_id', COUNT(*) - COUNT(DISTINCT schedule_id) FROM `{{ds}}.waste_schedules` UNION ALL
  SELECT 'neighbourhoods', 'neighbourhood_id', COUNT(*) - COUNT(DISTINCT neighbourhood_id) FROM `{{ds}}.neighbourhoods` UNION ALL
  SELECT 'transit_performance', 'perf_id', COUNT(*) - COUNT(DISTINCT perf_id) FROM `{{ds}}.transit_performance` UNION ALL
  SELECT 'transit_stop_delays', 'delay_id', COUNT(*) - COUNT(DISTINCT delay_id) FROM `{{ds}}.transit_stop_delays` UNION ALL
  SELECT 'neighbourhood_kpis', 'kpi_id', COUNT(*) - COUNT(DISTINCT kpi_id) FROM `{{ds}}.neighbourhood_kpis` UNION ALL
  SELECT 'delay_predictions', 'prediction_id', COUNT(*) - COUNT(DISTINCT prediction_id) FROM `{{ds}}.delay_predictions`
)
ORDER BY table_name;
