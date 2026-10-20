-- CTE: neighbourhoods whose transit score is above the city median but whose
-- park score is below it. Park score is built from real data only; transit
-- score includes a simulated on-time component.
WITH medians AS (
  SELECT
    APPROX_QUANTILES(transit_score, 2)[OFFSET(1)] AS median_transit,
    APPROX_QUANTILES(park_score, 2)[OFFSET(1)] AS median_park
  FROM `{{ds}}.v_neighbourhood_scores`
)
SELECT s.neighbourhood_name, s.transit_score, s.park_score, s.park_count,
       ROUND(s.park_score - m.median_park, 2) AS park_gap_vs_median
FROM `{{ds}}.v_neighbourhood_scores` AS s
CROSS JOIN medians AS m
WHERE s.transit_score > m.median_transit AND s.park_score < m.median_park
ORDER BY park_gap_vs_median ASC, s.neighbourhood_name
LIMIT 10;
