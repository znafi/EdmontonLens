# Build guide

> **Untested.** The data files this guide uses were generated and checked
> (valid GeoJSON, row counts, field names). The Tableau steps were written
> without Tableau installed, so menu names may differ slightly by version.
> Fix this file if you find a step that is wrong.

Both routes build the same dashboard from `dashboard_spec.md`.

## Route B: Tableau Public + the exported files (free, recommended first)

Tableau Public cannot connect to BigQuery, so it uses the files in `tableau/data/`.
**Everything you publish to Tableau Public is public.** The data here is open
data plus simulated values, nothing private.

1. Install **Tableau Public** (free, desktop app) from public.tableau.com.
2. *Neighbourhoods:* Connect > **More...** > **Spatial file** > pick
   `tableau/data/neighbourhood_scores.geojson`. Tableau shows a `Geometry`
   field plus every property (`overall_score`, `transit_score`, ...).
3. *Routes:* Data > **New Data Source** > **Text file** >
   `route_performance_daily.csv`. Confirm `service_date` has the Date type.
4. *Quality:* New Data Source > Text file > `data_quality.csv`.
5. Create the parameter **On-Time Target** and the calculated fields exactly as
   written in `dashboard_spec.md`.
6. Build the four sheets, then a dashboard, per the spec. Add the "simulated"
   banner text box before publishing.
7. **File > Save to Tableau Public...** and sign in. Paste the resulting URL
   into the root README.

To refresh: run `python -m scripts.export_tableau`, then in Tableau
**Data > Refresh** (or re-publish).

## Route A: Tableau Desktop trial + live BigQuery

Tableau Desktop has a free trial (about 14 days). It can read the BigQuery
views live.

1. Authenticate: your Google account must have access to project `edmonton-lens`.
2. Connect > **To a Server** > **Google BigQuery** (a JDBC variant may also be listed).
   Sign in with Google in the browser window that opens.
3. Billing Project: `edmonton-lens`. Project: `edmonton-lens`. Dataset: `edmonton_lens`.
4. Drag `v_neighbourhood_scores`, `v_route_performance_daily` onto the canvas
   as **separate data sources** (they have different grains). Use
   *Custom SQL* for the quality panel: paste the contents of each
   `sql/quality/*.sql` file, replacing `{{ds}}` with `` `edmonton-lens.edmonton_lens` ``,
   combined with `UNION ALL`.
5. **The map:** the polygons are stored as a GeoJSON string column
   (`boundary_geojson`), which Tableau will not draw. Options:
   - Add `tableau/data/neighbourhood_scores.geojson` as a spatial file and join it
     to `v_neighbourhood_scores` on `neighbourhood_id`; or
   - build the map from the spatial file only (colours come from its properties).
   I have not verified whether the Tableau BigQuery connector reads native
   `GEOGRAPHY` columns; the views deliberately expose plain strings.
6. Choose **Live** connection, not Extract, to show the live link. BigQuery
   charges (outside the sandbox) are by data scanned; these tables are small.
7. Create the parameter, calculated fields and sheets as in `dashboard_spec.md`.
8. Publishing a Desktop workbook needs Tableau Server/Cloud, which is not
   free; for a public link use Route B.

## What to say honestly
- Route B is a static snapshot of BigQuery, refreshed by re-running the export.
- Route A is the only route where Tableau queries BigQuery directly.
