-- Referential and spatial integrity.
-- 1-3 are hard FAIL checks. 4 is a WARN: the ETL assigns a stop that falls
-- outside every neighbourhood polygon (industrial land, annexed areas) to the
-- nearest polygon centroid, so a "null neighbourhood" test cannot catch it.
SELECT 'orphan_stop_no_neighbourhood' AS check_name, 'transit_stops' AS table_name,
       IF(COUNT(*) = 0, 'PASS', 'FAIL') AS status, COUNT(*) AS failing_rows,
       'stop.neighbourhood_id missing from neighbourhoods' AS detail
FROM `{{ds}}.transit_stops` AS s
LEFT JOIN `{{ds}}.neighbourhoods` AS n USING (neighbourhood_id)
WHERE n.neighbourhood_id IS NULL
UNION ALL
SELECT 'orphan_performance_route', 'transit_performance',
       IF(COUNT(*) = 0, 'PASS', 'FAIL'), COUNT(*),
       'performance.route_id missing from transit_routes'
FROM `{{ds}}.transit_performance` AS p
LEFT JOIN `{{ds}}.transit_routes` AS r USING (route_id)
WHERE r.route_id IS NULL
UNION ALL
SELECT 'orphan_delay_stop', 'transit_stop_delays',
       IF(COUNT(*) = 0, 'PASS', 'FAIL'), COUNT(*),
       'delay.stop_id missing from transit_stops'
FROM `{{ds}}.transit_stop_delays` AS d
LEFT JOIN `{{ds}}.transit_stops` AS s USING (stop_id)
WHERE s.stop_id IS NULL
UNION ALL
SELECT 'stop_outside_assigned_polygon', 'transit_stops',
       IF(COUNT(*) = 0, 'PASS', 'WARN'), COUNT(*),
       'stop not inside its assigned neighbourhood polygon (nearest-centroid fallback)'
FROM `{{ds}}.transit_stops` AS s
JOIN `{{ds}}.neighbourhoods` AS n USING (neighbourhood_id)
WHERE NOT ST_INTERSECTS(
  ST_GEOGFROMGEOJSON(n.boundary_geojson, make_valid => TRUE),
  ST_GEOGPOINT(s.stop_lon, s.stop_lat)
);
