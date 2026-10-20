-- One row per route per service day, with a trailing 7-day on-time average.
-- SIMULATED: on_time_rate, avg_delay_mins, delayed_trips. The City publishes no
-- historical arrival data in the static feed; the pipeline generates these with
-- a fixed-seed random model. Route names and total_trips come from the City.
CREATE OR REPLACE VIEW `{{ds}}.v_route_performance_daily` AS
SELECT
  p.route_id,
  r.route_short_name,
  r.route_long_name,
  r.route_type,
  p.service_date,
  p.on_time_rate,
  AVG(p.on_time_rate) OVER (
    PARTITION BY p.route_id
    ORDER BY p.service_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS on_time_rate_7d_avg,
  p.avg_delay_mins,
  p.total_trips,
  p.delayed_trips,
  'SIMULATED' AS data_origin
FROM `{{ds}}.transit_performance` AS p
LEFT JOIN `{{ds}}.transit_routes` AS r USING (route_id);
