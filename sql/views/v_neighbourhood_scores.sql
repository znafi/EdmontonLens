-- One row per neighbourhood from the latest KPI snapshot, with name, size and
-- boundary geometry (for a Tableau map or BigQuery GIS).
-- REAL inputs: stop counts, park counts and area, boundaries.
-- SIMULATED input: avg_route_on_time (so transit_score and overall_score are
-- partly simulated). park_score is computed from real data only.
CREATE OR REPLACE VIEW `{{ds}}.v_neighbourhood_scores` AS
SELECT
  k.neighbourhood_id,
  n.neighbourhood_name,
  n.area_sqkm,
  k.snapshot_date,
  k.transit_stop_count,
  k.park_count,
  k.total_park_area_sqm,
  k.avg_route_on_time AS avg_route_on_time_simulated,
  k.transit_score,
  k.park_score,
  k.overall_score,
  RANK() OVER (ORDER BY k.overall_score DESC) AS overall_rank,
  n.boundary_geojson
FROM `{{ds}}.neighbourhood_kpis` AS k
JOIN `{{ds}}.neighbourhoods` AS n USING (neighbourhood_id)
WHERE TRUE
QUALIFY k.snapshot_date = MAX(k.snapshot_date) OVER ();
