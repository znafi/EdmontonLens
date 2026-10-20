-- Null counts on columns that must be populated. FAIL if any are null.
SELECT 'null_key_or_required_column' AS check_name, t AS table_name,
       IF(n = 0, 'PASS', 'FAIL') AS status, n AS failing_rows, col AS detail
FROM (
  SELECT 'transit_routes' AS t, 'route_id' AS col, COUNTIF(route_id IS NULL) AS n FROM `{{ds}}.transit_routes` UNION ALL
  SELECT 'transit_routes', 'route_long_name', COUNTIF(route_long_name IS NULL) FROM `{{ds}}.transit_routes` UNION ALL
  SELECT 'transit_stops', 'stop_id', COUNTIF(stop_id IS NULL) FROM `{{ds}}.transit_stops` UNION ALL
  SELECT 'transit_stops', 'stop_lat/stop_lon', COUNTIF(stop_lat IS NULL OR stop_lon IS NULL) FROM `{{ds}}.transit_stops` UNION ALL
  SELECT 'transit_stops', 'neighbourhood_id', COUNTIF(neighbourhood_id IS NULL) FROM `{{ds}}.transit_stops` UNION ALL
  SELECT 'parks', 'park_id', COUNTIF(park_id IS NULL) FROM `{{ds}}.parks` UNION ALL
  SELECT 'parks', 'neighbourhood_id', COUNTIF(neighbourhood_id IS NULL) FROM `{{ds}}.parks` UNION ALL
  SELECT 'neighbourhoods', 'boundary_geojson', COUNTIF(boundary_geojson IS NULL) FROM `{{ds}}.neighbourhoods` UNION ALL
  SELECT 'transit_performance', 'on_time_rate', COUNTIF(on_time_rate IS NULL) FROM `{{ds}}.transit_performance` UNION ALL
  SELECT 'neighbourhood_kpis', 'overall_score', COUNTIF(overall_score IS NULL) FROM `{{ds}}.neighbourhood_kpis`
)
ORDER BY table_name, detail;
