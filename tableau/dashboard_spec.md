# Dashboard spec: EdmontonLens Neighbourhoods & Transit

Published: https://public.tableau.com/app/profile/zawad.nafi/viz/EdmontonLens-NeighbourhoodsandTransit/Dashboard1
Embedded in the web app: https://edmonton-lens.vercel.app/dashboard

This file describes what the published workbook contains (as of 2026-10-20).
It was built in Tableau Public web authoring from the files in `data/`.

## Data sources

| Name in workbook | File | BigQuery origin | Grain |
|---|---|---|---|
| neighbourhood_scores | `neighbourhood_scores.geojson` (spatial file) | `v_neighbourhood_scores` + `v_stops_per_neighbourhood` | 1 row per neighbourhood (399) |
| route_performance_daily | `route_performance_daily.csv` | `v_route_performance_daily` | 1 row per route per day (7,290) |
| data_quality | `data_quality.csv` | `sql/quality/*.sql` results | 1 row per check (29) |

## Parameter

**On-Time Target**: float, current value 0.80, range 0.5 to 1.0, step 0.01.
Shown as a slider on Sheet 3. 0.80 is an arbitrary display threshold, not a
City of Edmonton standard.

## Calculated fields (Tableau syntax, as entered in the workbook)

**1. Score Percentile** (neighbourhood_scores; row level)
```
1 - ([Overall Rank] - 1) / { FIXED : COUNTD([Neighbourhood Id]) }
```
Why: 71 of 399 neighbourhoods tie at the maximum score of 10, so the raw score
hides ordering. `Overall Rank` comes from `RANK()` in the BigQuery view, so
tied neighbourhoods share a percentile. A row-level formula is used instead of
`RANK_PERCENTILE()` because a table calculation on a map with no dimensions on
rows/columns does not partition predictably. Shown in the map tooltip.

**2. Transit-Park Quadrant** (neighbourhood_scores; row level, FIXED LOD)
```
IF [Transit Score] >= { FIXED : MEDIAN([Transit Score]) }
   AND [Park Score] >= { FIXED : MEDIAN([Park Score]) }
THEN 'High transit / High parks'
ELSEIF [Transit Score] >= { FIXED : MEDIAN([Transit Score]) }
THEN 'High transit / Low parks'
ELSEIF [Park Score] >= { FIXED : MEDIAN([Park Score]) }
THEN 'Low transit / High parks'
ELSE 'Low transit / Low parks'
END
```
Colours the scatter. The median park score is 10 (capped), so "High parks"
means "at the cap".

**3. On-Time Status** (route_performance_daily; aggregate, uses the parameter)
```
IF AVG([On Time Rate 7D Avg]) >= [On-Time Target]
THEN 'On target' ELSE 'Below target'
END
```
Aggregate because the trend plots the daily average across the selected routes.
Colours the trend line.

**4. Failing Checks** and **Warning Checks** (data_quality; aggregate)
```
SUM(IF [Status] = 'FAIL' THEN 1 ELSE 0 END)
SUM(IF [Status] = 'WARN' THEN 1 ELSE 0 END)
```
Shown on Sheet 5. Current values: 0 failing, 1 warning.

## Sheets

| Sheet | Shows | Encodings | Filters / interactivity |
|---|---|---|---|
| Sheet 1 | Filled map of the 399 neighbourhood polygons | Colour: Overall Score. Detail/tooltip: Neighbourhood Id, Name, Score Percentile, Overall, Park and Transit Score | Overall Score range slider |
| Sheet 2 | Transit score vs park score, one point per neighbourhood | Colour: Transit-Park Quadrant | Target of the highlight action |
| Sheet 3 | Average 7-day on-time rate per day (**SIMULATED**, said in the title) | Colour: On-Time Status | Route Short Name filter (multi-select), On-Time Target slider |
| Sheet 4 | Text table of every data-quality check: table, status, detail, failing rows | | |
| Sheet 5 | Data quality summary: Failing Checks, Warning Checks | | |
| Dashboard 1 | Sheets 1 to 4, Overall Score legend, and a text box saying which data is simulated and which is real | | Highlight action: selecting a neighbourhood on the map highlights it in the scatter |

Every sheet that shows simulated values says "SIMULATED" in its title, and the
dashboard text box explains it.

## Not included, and why
- **Reference lines, mark size and opacity changes:** these need drag-and-drop
  onto the Analytics pane/Marks card, which could not be done through the
  browser automation used to build this. They are cosmetic.
- **Sheet 5 on the dashboard:** adding it squeezed the map unreadably small; it
  is available as its own tab in the embed instead.
