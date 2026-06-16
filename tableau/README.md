# EdmontonLens - Tableau Workbook

Step-by-step guide to build and publish the Transit Pulse Tableau workbook
backed by the local PostgreSQL database.

---

## Section 1 - Setup

**Download Tableau Public**

1. Go to <https://public.tableau.com/en-us/s/download> and download Tableau Public
   (free, no licence required).
2. Install it and open it. Sign in with a free Tableau Public account.

**Install the PostgreSQL ODBC driver**

Tableau Public connects to PostgreSQL natively - no separate ODBC driver
install is needed on macOS or Windows when using the built-in connector.
If you see a "driver missing" error on Linux, install `libpq-dev`:
`sudo apt install libpq-dev`.

**Connect to the EdmontonLens database**

1. On the Tableau Public start screen, click **Connect - To a Server - PostgreSQL**.
2. Enter these values:
   - Server: `localhost`
   - Port: `5432`
   - Database: `edmonton_lens`
   - Username: `postgres` (or the value of `POSTGRES_USER` in your `.env`)
   - Password: `password` (or the value of `POSTGRES_PASSWORD` in your `.env`)
3. Click **Sign In**.

Alternatively, open `tableau/transit_pulse_schema.tds` directly in Tableau
Public. It pre-fills the connection details so you only need to click **Sign In**.

---

## Section 2 - Transit On-Time Rate Sheet

1. In the left sidebar, drag the `transit_performance` table into the canvas.
2. Click **Sheet 1** at the bottom to open a blank worksheet.
3. Rename the sheet "On-Time Rate".
4. In **Dimensions**, find `service_date`. Drag it to **Columns**. Right-click
   it on the columns shelf and set the date level to **Day**.
5. In **Measures**, find `on_time_rate`. Drag it to **Rows**.
6. In **Marks**, change the mark type from **Automatic** to **Line**.
7. Drag `route_id` from **Dimensions** onto the **Color** card in the Marks
   panel. Tableau draws one coloured line per route.
8. To filter to the top 5 routes by trip count:
   - Drag `route_id` to the **Filters** shelf.
   - Click **Top** tab, select **By field: Top 5 by sum of total_trips**.
   - Click **OK**.
9. Add a reference line at 85% (the on-time target):
   - Right-click the `on_time_rate` axis and choose **Add Reference Line**.
   - Set **Value** to **Constant: 0.85**, label it "85% target", line style
     to dashed, colour to red.
10. Right-click the chart title and rename it:
    **"How often buses ran on time this month"**

---

## Section 3 - Delay Hotspots Sheet

1. Add a second data source: click **Data - New Data Source** and connect to
   `transit_stop_delays`, then join to `transit_stops` on `stop_id`.
   - In the data source canvas, drag in `transit_stop_delays`. Then drag
     `transit_stops` next to it. Tableau offers a join; set it to
     **Inner Join** on `stop_id = stop_id`.
2. Open **Sheet 2**, rename it "Delay Hotspots".
3. Drag `stop_name` (from `transit_stops`) to **Rows**.
4. Drag `avg_delay_mins` to **Columns**.
5. Sort the `stop_name` axis by `avg_delay_mins` descending:
   - Click the **sort** icon on the Rows shelf, choose **Sort by field**,
     **Descending**, field **avg_delay_mins**, aggregation **Average**.
6. Filter to top 10: drag `stop_name` to Filters, choose **Top 10 by
   average of avg_delay_mins**.
7. Change mark type to **Bar** (horizontal bars appear automatically since
   the measure is on Columns and dimension on Rows).
8. Colour by delay severity:
   - Drag `avg_delay_mins` to **Color**.
   - Click **Color - Edit Colors - Stepped Color** with 3 steps.
   - Set thresholds: 0-2 green, 2-5 yellow, 5+ red using a diverging palette.
9. Rename the title: **"Which stops add the most wait time"**

---

## Section 4 - Neighbourhood KPI Sheet

1. Add a third data source: connect to `neighbourhood_kpis` and join to
   `transit_stops` on `neighbourhood_id`.
2. Open **Sheet 3**, rename it "Neighbourhood Map".
3. Drag `stop_lat` (from `transit_stops`) to **Rows** and `stop_lon` to
   **Columns**. Tableau recognises them as geographic roles automatically.
   If not, right-click each field and assign **Geographic Role - Latitude /
   Longitude**.
4. Change mark type to **Map** (Tableau switches to the map view).
5. Drag `neighbourhood_id` to **Detail** to group stops by neighbourhood.
6. Drag `overall_score` to **Color**. Open **Color - Edit Colors** and pick
   the **Blue-Green Diverging** palette with the midpoint at 5 (out of 10).
7. Customise the tooltip:
   - Click **Tooltip** in the Marks card.
   - Write:
     ```
     <neighbourhood_name>
     Transit score: <transit_score>
     Park score: <park_score>
     Overall: <overall_score>/10
     ```
8. Title: **"How neighbourhoods compare across transit, parks, and waste"**

---

## Section 5 - Assemble the Dashboard

1. Click the **New Dashboard** button (plus icon at the bottom tab bar).
2. Rename it **"EdmontonLens - Transit Overview"**.
3. Set the dashboard size to **Automatic** (fits any screen).
4. Drag **Neighbourhood Map** onto the top-left quadrant of the canvas.
5. Drag **On-Time Rate** to the top-right.
6. Drag **Delay Hotspots** to the bottom, spanning the full width.
7. Add a text object at the very top: click **Objects - Text**, drag it above
   the charts, and type:
   ```
   EdmontonLens - Transit Overview
   Powered by Edmonton Open Data
   Last refreshed: <today's date>
   ```
8. Use **Dashboard - Actions** to link the map to the line chart:
   - Add a **Filter Action**: Source sheet = Neighbourhood Map, Target = On-Time
     Rate, Filter field = `neighbourhood_id`.
   - Now clicking a neighbourhood polygon filters the line chart.

---

## Section 6 - Export and Embed

**Save as a packaged workbook**

1. Go to **File - Save to Tableau Public As...**
2. Log in if prompted, name it **transit_pulse**, and click **Save**.
3. Tableau uploads the workbook. When done, it opens in your browser.
4. To also keep a local copy with the data embedded:
   **File - Export Packaged Workbook** and save it as `tableau/transit_pulse.twbx`.
   Anyone can open this file without a live database connection.

**Copy the embed URL**

1. On your Tableau Public profile page, open the published workbook.
2. Click the **Share** button below the viz, then copy the **Embed Code**.
3. Extract the `src` URL from the `<iframe>` tag - it looks like:
   `https://public.tableau.com/views/transit_pulse/...`

**Add a Tableau toggle to the Transit page**

Open `frontend/app/transit/page.tsx` and add the following below the existing
Recharts components (replace the placeholder URL with your actual embed URL):

```tsx
const [showTableau, setShowTableau] = useState(false);

// ...inside the JSX, after the DelayBarChart card:

<div className="card">
  <div className="mb-4 flex items-center justify-between">
    <h2 className="text-lg font-semibold text-slate-800">Tableau view</h2>
    <button
      onClick={() => setShowTableau((s) => !s)}
      className="rounded-lg border border-slate-300 px-4 py-1 text-sm"
    >
      {showTableau ? "Hide Tableau" : "Open in Tableau"}
    </button>
  </div>
  {showTableau && (
    <iframe
      title="EdmontonLens Tableau"
      src="https://public.tableau.com/views/transit_pulse/EdmontonLens-TransitOverview"
      width="100%"
      height="600"
      className="rounded-lg border border-slate-200"
    />
  )}
</div>
```
