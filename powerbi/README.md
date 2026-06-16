# EdmontonLens - Power BI Report

Step-by-step guide to build the three-page Power BI Desktop report backed by
the local PostgreSQL database, publish it to Power BI Service, and embed it
in the Next.js app.

---

## Section 1 - Setup

**Download Power BI Desktop**

Go to <https://powerbi.microsoft.com/desktop> and download Power BI Desktop
(free, Windows only; macOS users can run it via Parallels or a VM).

**Install the Npgsql PostgreSQL connector**

Power BI Desktop ships without a PostgreSQL connector by default. Install it:

1. Close Power BI Desktop if open.
2. Download the Npgsql installer from <https://github.com/npgsql/npgsql/releases>.
   Pick the `.msi` matching your OS (e.g. `Npgsql-8.x.x.msi`).
3. Run the installer. When prompted, check **Npgsql GAC Installation**.
4. Restart Power BI Desktop.

**Connect to EdmontonLens**

1. Open Power BI Desktop, click **Get Data** on the Home ribbon.
2. Search for **PostgreSQL** and click **Connect**.
3. Enter:
   - Server: `localhost:5432`
   - Database: `edmonton_lens`
4. Click **OK**, then enter your credentials:
   - Username: `postgres`
   - Password: `password` (or the value from your `.env`)
5. In the Navigator, tick these tables and click **Load**:
   - `transit_performance`
   - `transit_stop_delays`
   - `transit_stops`
   - `neighbourhood_kpis`
   - `neighbourhoods`
   - `parks`
   - `waste_schedules`

---

## Section 2 - Data Model

Switch to **Model view** (the icon that looks like three connected boxes in the
left sidebar). Create these relationships by dragging fields from one table to
another:

| From (many side) | Field | To (one side) | Field | Cardinality |
|---|---|---|---|---|
| `transit_performance` | `route_id` | `transit_stops` | `stop_id` | Many-to-one |
| `transit_stop_delays` | `stop_id` | `transit_stops` | `stop_id` | Many-to-one |
| `neighbourhood_kpis` | `neighbourhood_id` | `neighbourhoods` | `neighbourhood_id` | Many-to-one |
| `parks` | `neighbourhood_id` | `neighbourhoods` | `neighbourhood_id` | Many-to-one |
| `waste_schedules` | `neighbourhood_id` | `neighbourhoods` | `neighbourhood_id` | Many-to-one |

Set the cross-filter direction on all relationships to **Single** (the default).

---

## Section 3 - DAX Measures

In **Report view**, right-click any table in the Fields pane and choose
**New table**. Name it `_Measures`. Then right-click `_Measures` and add each
measure below using **New measure**:

```dax
City Avg On-Time Rate =
AVERAGE(transit_performance[on_time_rate])

On-Time Rate % =
FORMAT([City Avg On-Time Rate], "0.0%")

Routes Below Target =
CALCULATE(
    DISTINCTCOUNT(transit_performance[route_id]),
    transit_performance[on_time_rate] < 0.85
)

Avg Delay (mins) =
AVERAGE(transit_stop_delays[avg_delay_mins])

Neighbourhood Transit Score =
AVERAGE(neighbourhood_kpis[transit_score])

Neighbourhood Park Score =
AVERAGE(neighbourhood_kpis[park_score])

Overall City Score =
AVERAGE(neighbourhood_kpis[overall_score])
```

---

## Section 4 - Report Pages

### Page 1 - Transit Overview

Right-click the default page tab and rename it **Transit Overview**.

**KPI card - on-time rate**
1. Insert a **Card** visual (from the Visualizations pane).
2. Drag `[City Avg On-Time Rate]` into the **Fields** well.
3. In the Format pane, under **Callout value**, set the format to **Percentage**
   with one decimal place.
4. Add a **Conditional formatting** rule on the font color:
   - Greater than 0.85: green (`#15803d`)
   - 0.75 to 0.85: amber (`#d97706`)
   - Less than 0.75: red (`#dc2626`)

**KPI card - routes below target**
1. Insert another **Card** visual.
2. Drag `[Routes Below Target]` into Fields.

**Line chart**
1. Insert a **Line chart** visual.
2. X-axis: `transit_performance[service_date]` (set hierarchy to **Date level: Day**)
3. Y-axis: `transit_performance[on_time_rate]` (Average aggregation)
4. Legend: `transit_performance[route_id]`
5. Add a page-level filter: `service_date` is in the **last 30 days**.

**Bar chart**
1. Insert a **Clustered bar chart** visual.
2. Y-axis: `transit_stops[stop_name]`
3. X-axis: `transit_stop_delays[avg_delay_mins]` (Average)
4. Sort by X-axis descending.
5. Add a Top N visual-level filter: **Top 10 by average of avg_delay_mins**.

**Slicer**
1. Insert a **Slicer** visual.
2. Field: `transit_performance[route_id]`
3. In Format, set the slicer style to **Dropdown**.

---

### Page 2 - Neighbourhood Snapshot

Right-click the page tab and add a new page named **Neighbourhood Snapshot**.

**Matrix table**
1. Insert a **Matrix** visual.
2. Rows: `neighbourhoods[neighbourhood_name]`
3. Columns: (leave empty)
4. Values: `[Neighbourhood Transit Score]`, `[Neighbourhood Park Score]`,
   `[Overall City Score]`
5. Enable **Conditional formatting** on each value column using a three-color
   scale (red - yellow - green).

**Bar chart**
1. Insert a **Clustered bar chart**.
2. Y-axis: `neighbourhoods[neighbourhood_name]`
3. X-axis: `[Overall City Score]`
4. Sort descending. Add a Top 20 visual-level filter.

**KPI card**
1. Insert a **Card** showing `[Overall City Score]`.

**Slicer**
1. Insert a **Slicer** on `neighbourhood_kpis[snapshot_date]`.
2. Set style to **Between** (date range picker).

---

### Page 3 - Waste and Parks

Add a third page named **Waste and Parks**.

**Park count bar chart**
1. Insert a **Clustered bar chart**.
2. Y-axis: `neighbourhoods[neighbourhood_name]`
3. X-axis: Count of `parks[park_id]`
4. Title: "Parks by neighbourhood"

**Waste schedule table**
1. Insert a **Table** visual.
2. Columns: `neighbourhoods[neighbourhood_name]`,
   `waste_schedules[waste_type]`, `waste_schedules[pickup_day]`
3. Sort by neighbourhood name ascending.

**KPI cards**
1. Card 1: Count of `parks[park_id]`, label "Total parks"
2. Card 2: Sum of `parks[area_sqm]`, formatted as a large number, label
   "Total park area (sqm)"

---

## Section 5 - Export and Publish

**Save the file**

Go to **File - Save As** and save as `powerbi/edmonton_lens.pbix` inside the
project directory. Commit this file to the repository.

**Export Page 1 as PDF**

1. Make sure **Transit Overview** is the active page.
2. Go to **File - Export - Export to PDF**.
3. Save as `powerbi/transit_overview_screenshot.pdf`.

**Publish to Power BI Service**

Power BI Service is free with a work or school Microsoft 365 account (any
university email works). Personal Microsoft accounts cannot publish.

1. Click **Home - Publish** in the ribbon.
2. Choose **My workspace** as the destination.
3. Once uploaded, go to <https://app.powerbi.com> and open the report.

**Get the embed URL**

1. Open the report in Power BI Service.
2. Click **File - Embed report - Website or portal**.
3. Copy the `<iframe>` `src` URL. It looks like:
   `https://app.powerbi.com/reportEmbed?reportId=...`

**Add the embed to the Next.js app**

Add a new file `frontend/app/reports/page.tsx`:

```tsx
export default function ReportsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold text-slate-900">Power BI report</h1>
      <p className="text-sm text-slate-500">
        Live transit and neighbourhood data, updated daily.
      </p>
      <iframe
        title="EdmontonLens Power BI"
        className="h-[80vh] w-full rounded-xl border border-slate-200"
        src="https://app.powerbi.com/reportEmbed?reportId=YOUR_REPORT_ID"
        allowFullScreen
      />
    </div>
  );
}
```

Replace `YOUR_REPORT_ID` with the actual ID from the embed URL.
