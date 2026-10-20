# Dashboard spec: EdmontonLens Neighbourhood & Transit

Four sheets on one dashboard. All fields below exist in the files in `data/`
(see `README.md` for the field dictionary).

> **Status:** the data files and every calculated field below are real and were
> generated/validated from BigQuery. The `.twbx` workbook itself has **not**
> been built or published yet; `BUILD_GUIDE.md` is how to build it.

## Data sources

| Name | File / BigQuery view | Grain |
|---|---|---|
| Neighbourhoods | `neighbourhood_scores.geojson` (or `.csv` + geometry, see guide) / `v_neighbourhood_scores` | 1 row per neighbourhood (399) |
| Routes | `route_performance_daily.csv` / `v_route_performance_daily` | 1 row per route per day (243 routes x 30 days) |
| Quality | `data_quality.csv` / output of `sql/quality/*.sql` | 1 row per check (29) |

## Parameter

**On-Time Target**: float, default `0.80`, range 0.5 to 1.0, step 0.01.
The 0.80 is an arbitrary display threshold, not a City of Edmonton standard.

## Calculated fields (Tableau syntax)

**1. Score Percentile** (Neighbourhoods; table calculation, compute using *Neighbourhood Name*)
```
RANK_PERCENTILE(AVG([overall_score]))
```
Why: 71 of 399 neighbourhoods tie at the maximum score of 10 (the park and
transit scores are capped), so colouring by raw score alone hides ordering.

**2. Transit-Park Quadrant** (Neighbourhoods; row level)
```
IF [transit_score] >= { FIXED : MEDIAN([transit_score]) }
   AND [park_score] >= { FIXED : MEDIAN([park_score]) }
THEN 'High transit / High parks'
ELSEIF [transit_score] >= { FIXED : MEDIAN([transit_score]) }
THEN 'High transit / Low parks'
ELSEIF [park_score] >= { FIXED : MEDIAN([park_score]) }
THEN 'Low transit / High parks'
ELSE 'Low transit / Low parks'
END
```
Note: the median park score is 10 (capped), so "High parks" means "at the cap".

**3. On-Time Status** (Routes; row level, uses the parameter)
```
IF [on_time_rate_7d_avg] >= [On-Time Target]
THEN 'On target' ELSE 'Below target'
END
```

**4. Failing Checks** and **Warning Checks** (Quality; aggregate)
```
SUM(IF [status] = 'FAIL' THEN 1 ELSE 0 END)
SUM(IF [status] = 'WARN' THEN 1 ELSE 0 END)
```

## Sheets

### 1. Neighbourhood Map
- **Marks:** Map (filled). `Geometry` (from the GeoJSON) on Detail.
- **Colour:** `AVG(overall_score)`, sequential, fixed range 0 to 10.
- **Detail / tooltip:** `neighbourhood_name`, `overall_score`, `Score Percentile`,
  `transit_score`, `park_score`, `transit_stop_count`, `park_count`.
- **Filter:** `overall_score` range slider.
- **Label:** caption "Overall score = park score (real) + transit score (partly simulated)".

### 2. Transit vs Park Score
- **Columns:** `AVG(transit_score)`. **Rows:** `AVG(park_score)`.
- **Detail:** `neighbourhood_name`. **Colour:** `Transit-Park Quadrant`.
  **Size:** `transit_stop_count`.
- Reference lines: median of each axis. Set mark opacity to about 50%: many
  points sit at exactly (10, 10) and overlap.
- Highlight action from the map sheet (select a polygon, highlight its point).
- **Label:** "transit score includes simulated on-time rates".

### 3. Route On-Time Trend (SIMULATED)
- **Columns:** `service_date` (continuous day). **Rows:** `AVG(on_time_rate_7d_avg)`.
- **Detail:** `route_short_name`. **Colour:** `On-Time Status` (circle marks) or a single average line.
- **Filters:** `route_short_name` (multi-select, show filter), `route_type`, `service_date`.
- Reference line at `[On-Time Target]`.
- **Title must say "SIMULATED".** The `data_origin` field (always `SIMULATED`)
  goes on Tooltip.

### 4. Data Quality Panel
- Top: two KPI tiles, `Failing Checks` and `Warning Checks`.
- Below: text table. Rows `table_name`, `check_name`, `detail`; Text/Colour
  `status` (PASS green, WARN amber, FAIL red); Text `failing_rows`.
- Caption: `MAX(checked_at)` ("Checks last run ...").
- Expected today: 28 PASS, 1 WARN (`stop_outside_assigned_polygon`, 1,012 stops).

## Dashboard layout
- Title: "Edmonton neighbourhoods & transit".
- Banner text box (always visible, top):
  **"Simulated data: route on-time rates, delays and the on-time part of the transit score are generated, not measured. Real: stops, routes, parks, neighbourhood boundaries (City of Edmonton Open Data)."**
- Row 1: Map (left, 60%) | Scatter (right, 40%).
- Row 2: Route trend (left, 60%) | Data quality (right, 40%).
- Footer: source attribution and "Source: City of Edmonton Open Data Portal (data.edmonton.ca), used under the portal's Terms of Use."
