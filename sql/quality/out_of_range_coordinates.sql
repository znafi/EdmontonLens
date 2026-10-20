-- Points must fall inside a bounding box around Edmonton and its suburbs.
SELECT 'coordinates_out_of_range' AS check_name, t AS table_name,
       IF(n = 0, 'PASS', 'FAIL') AS status, n AS failing_rows,
       'outside lat 53.2-53.8, lon -114.1 to -113.1' AS detail
FROM (
  SELECT 'transit_stops' AS t, COUNTIF(
    stop_lat NOT BETWEEN 53.2 AND 53.8 OR stop_lon NOT BETWEEN -114.1 AND -113.1) AS n
  FROM `{{ds}}.transit_stops`
  UNION ALL
  SELECT 'parks', COUNTIF(
    latitude NOT BETWEEN 53.2 AND 53.8 OR longitude NOT BETWEEN -114.1 AND -113.1)
  FROM `{{ds}}.parks`
)
ORDER BY table_name;
