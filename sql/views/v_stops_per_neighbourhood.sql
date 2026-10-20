-- One row per neighbourhood: how many transit stops and parks it contains.
-- Real data: stop and park locations (City of Edmonton open data), boundaries.
-- Derived: stops are assigned to the polygon containing them, or to the nearest
-- polygon centroid when they fall outside every polygon (see quality/orphan_stops.sql).
CREATE OR REPLACE VIEW `{{ds}}.v_stops_per_neighbourhood` AS
WITH stop_counts AS (
  SELECT neighbourhood_id, COUNT(*) AS stop_count
  FROM `{{ds}}.transit_stops`
  GROUP BY neighbourhood_id
),
park_counts AS (
  SELECT neighbourhood_id, COUNT(*) AS park_count, SUM(area_sqm) AS park_area_sqm
  FROM `{{ds}}.parks`
  GROUP BY neighbourhood_id
)
SELECT
  n.neighbourhood_id,
  n.neighbourhood_name,
  n.area_sqkm,
  COALESCE(s.stop_count, 0) AS stop_count,
  SAFE_DIVIDE(COALESCE(s.stop_count, 0), n.area_sqkm) AS stops_per_sqkm,
  COALESCE(p.park_count, 0) AS park_count,
  COALESCE(p.park_area_sqm, 0) AS park_area_sqm,
  SAFE_DIVIDE(COALESCE(p.park_area_sqm, 0), n.area_sqkm * 1000000) AS park_area_share
FROM `{{ds}}.neighbourhoods` AS n
LEFT JOIN stop_counts AS s USING (neighbourhood_id)
LEFT JOIN park_counts AS p USING (neighbourhood_id);
