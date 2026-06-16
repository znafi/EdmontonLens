# Looker Studio Dashboards — EdmontonLens

This guide explains how to connect the BigQuery dataset `edmonton_lens` to
[Looker Studio](https://lookerstudio.google.com) and rebuild the three core
dashboards, then publish and embed them in the Next.js app.

> Prerequisite: the ETL pipeline (`python -m backend.etl.pipeline`) has run with
> BigQuery enabled, so the dataset `edmonton_lens` contains populated tables in
> your GCP project.

---

## 1. Connect BigQuery as a Data Source

1. Go to <https://lookerstudio.google.com> → **Create** → **Data source**.
2. Choose the **BigQuery** connector (authorise with the Google account that
   owns the GCP project).
3. Select:
   - **Project**: your GCP project (e.g. `edmontonlens-prod`)
   - **Dataset**: `edmonton_lens`
   - **Table**: start with `transit_performance`
4. Click **Connect**. On the fields screen, confirm types:
   - `service_date` → **Date**
   - `on_time_rate`, `avg_delay_mins` → **Number**
   - set `on_time_rate` aggregation to **Average**.
5. Click **Add to report**.
6. Repeat steps 1–5 to add data sources for `neighbourhood_kpis`,
   `transit_stop_delays`, `waste_schedules`, `neighbourhoods`, and
   `delay_predictions` (a report can hold multiple data sources).

---

## 2. Transit Pulse Dashboard

**Goal:** track city-wide on-time performance and the worst stops.

1. Add a **Scorecard**:
   - Data source: `transit_performance`
   - Metric: `on_time_rate` (Average), format as **Percent**
   - Label: "City-wide On-Time Rate".
2. Add a **Date range control** (default: Last 30 days), bound to `service_date`.
3. Add a **Time series / Line chart**:
   - Dimension: `service_date`
   - Breakdown dimension: `route_id`
   - Metric: `on_time_rate` (Average)
   - Filter: top 5 `route_id` by `total_trips` (Sort: descending, Limit 5).
4. Add a **Bar chart** (from `transit_stop_delays`):
   - Dimension: `stop_id`
   - Metric: `avg_delay_mins` (Average), sort descending, limit 10
   - Title: "Top 10 Delay-Prone Stops".

---

## 3. Neighbourhood Snapshot Dashboard

**Goal:** compare neighbourhoods on a composite score.

1. Add **Scorecard tiles** (from `neighbourhood_kpis`, filtered to the latest
   `snapshot_date`):
   - `overall_score` (Average) → "Avg Overall Score"
   - `transit_stop_count` (Sum) → "Total Transit Stops"
   - `park_count` (Sum) → "Total Parks".
2. Add a **Bar chart**:
   - Dimension: `neighbourhood_id`
   - Metric: `overall_score` (Average), sorted descending.
3. Add a **Google Maps / Filled map** chart:
   - Use `neighbourhoods` joined to `neighbourhood_kpis` on `neighbourhood_id`
     (blend the two sources in Looker Studio: **Resource → Manage blends**).
   - Location: a latitude/longitude field or geo dimension; colour metric:
     `overall_score`.
   - (The interactive choropleth lives in the Next.js app; this map is the
     report-friendly equivalent.)

---

## 4. Waste Overview Dashboard

**Goal:** show collection coverage and diversion trend.

1. Add a **Table** (from `waste_schedules`):
   - Dimension: `neighbourhood_id`, `waste_type`, `pickup_day`
   - Metric: Record Count → "Streams".
2. Add a **Pie chart**:
   - Dimension: `waste_type`
   - Metric: Record Count → shows garbage vs recycling vs organics share.
3. Add a **Calculated field** for the diversion rate:
   ```
   Diversion Rate = COUNT_DISTINCT(
     CASE WHEN waste_type IN ('recycling','organics') THEN schedule_id END
   ) / COUNT_DISTINCT(schedule_id)
   ```
   Display it as a Scorecard formatted as **Percent**.
4. Add a **Bar chart** of pickup coverage:
   - Dimension: `neighbourhood_id`
   - Metric: Record Count, title "Collection Streams by Neighbourhood".

---

## 5. Share Publicly & Embed in Next.js

1. Click **Share** (top-right) → **Manage access** → set link sharing to
   **Anyone with the link can view**.
2. Click **File → Embed report** → enable **Enable embedding** → copy the
   `<iframe>` URL.
3. In the Next.js app, drop the iframe into any page, e.g. a new
   `frontend/app/reports/page.tsx`:

   ```tsx
   export default function ReportsPage() {
     return (
       <iframe
         title="EdmontonLens Looker Studio"
         className="h-[80vh] w-full rounded-xl border border-slate-200"
         src="https://lookerstudio.google.com/embed/reporting/REPORT_ID/page/PAGE_ID"
       />
     );
   }
   ```

4. Replace `REPORT_ID`/`PAGE_ID` with the values from your embed URL.
