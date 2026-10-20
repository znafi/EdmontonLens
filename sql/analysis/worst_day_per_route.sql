-- Window function (QUALIFY + ROW_NUMBER): each route's single worst day, then
-- the 10 worst of those. Uses SIMULATED on-time rates; illustrates the pattern.
SELECT route_short_name, route_long_name, service_date, on_time_rate, avg_delay_mins,
       ROW_NUMBER() OVER (PARTITION BY route_id ORDER BY on_time_rate ASC, service_date DESC) AS rn
FROM `{{ds}}.v_route_performance_daily`
WHERE TRUE
QUALIFY rn = 1
ORDER BY on_time_rate ASC
LIMIT 10;
