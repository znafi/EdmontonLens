# EdmontonLens

EdmontonLens is a personal project I built to make sense of the data the City of Edmonton publishes. The city puts out a lot of open data, but it's scattered across different portals and formats with no easy way to ask a question and get an answer. So I built something that pulls it all together, cleans it up, and gives you three different ways to look at it: charts for transit, a map for neighbourhoods, and a plain-English chat interface that writes SQL for you.

## Here's what you can do with it

**Transit** shows real ETS routes and stops with a chart of on-time rates over the last 30 days, a bar chart of the stops with the worst delays, and a machine learning model's delay-risk prediction. **The on-time rates and delays are simulated**: the City doesn't publish historical arrival times, so the pipeline generates them with a fixed-seed model. Treat this page as a demonstration of the pipeline and charts, not as a measure of how ETS performs. The page re-polls the API every five minutes; the data itself changes when the pipeline runs.

**Ask** is a chat interface where you type a question in plain English. A language model (Google Gemini through a LangChain agent) writes the SQL, runs it, and explains what it found. Ask things like "which neighbourhood has the most parks" or "when does recycling get picked up in Highlands" and get a real answer. If you don't have a Gemini key, built-in queries keep the page working.

**Map** is an interactive neighbourhood map built with Leaflet.js, using the City's 2019 neighbourhood boundary polygons. Each neighbourhood is coloured by an overall score: the average of a park score (real park counts and areas) and a transit score (real stop counts plus the simulated on-time rate). Click any area for the breakdown, and a history chart once the pipeline has run on several days.

**Dashboard** embeds the [Tableau Public dashboard](https://public.tableau.com/app/profile/zawad.nafi/viz/EdmontonLens-NeighbourhoodsandTransit/Dashboard1) built from the BigQuery views: neighbourhood scores on a map, transit vs park scores, the simulated route trend, and the data-quality checks.

## How it actually works

There's a Python pipeline (`python -m backend.etl.pipeline`). It pulls transit routes, transit stops, parks and neighbourhood boundaries from the City's Socrata API concurrently, paging through every row. It cleans everything with Pandas, assigns stops and parks to neighbourhoods by point-in-polygon, loads the results, and retrains a random forest classifier on the (simulated) performance data.

Where the data lands:
- **SQLite**: what the live demo serves. The database is built into the Docker image at build time.
- **Google BigQuery** (optional, `edmonton-lens.edmonton_lens`, free sandbox): loaded when `GCP_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS` are set. Loads are idempotent; re-running the same day leaves row counts unchanged. SQL views, data-quality checks and analysis queries live in [`sql/`](sql/).
- **PostgreSQL, MySQL, SQL Server**: optional local loaders, skipped when those servers aren't running.

The live demo does not read from BigQuery; BigQuery is the warehouse for analysis and Tableau. A [Tableau Public dashboard](https://public.tableau.com/app/profile/zawad.nafi/viz/EdmontonLens-NeighbourhoodsandTransit/Dashboard1) (neighbourhood map, transit vs park scores, simulated route trend, data-quality checks) is built from files exported from the BigQuery views by `scripts/export_tableau.py`.

In the middle sits a FastAPI server the Next.js frontend calls for everything. It handles data queries, natural-language chat through LangChain, and serves the neighbourhood GeoJSON. The API self-documents at `/docs`.

A GitHub Actions workflow schedules the pipeline daily; its BigQuery step needs a `GCP_SA_KEY` secret that isn't configured yet, so BigQuery is currently refreshed by running the pipeline locally. CI lints and type-checks on every push, and a deploy workflow ships the frontend to Vercel on merge to main.

## The tech behind it

| What it does | Tool used |
|---|---|
| Backend API | FastAPI + Python 3.11 |
| Data processing | Pandas |
| Database ORM | SQLAlchemy |
| Cloud warehouse | Google BigQuery (optional; sandbox) |
| Live demo database | SQLite |
| Optional local targets | PostgreSQL, MySQL 8, SQL Server 2022 |
| ML delay predictor | scikit-learn RandomForest |
| Language model agent | LangChain + Google Gemini |
| Open data API | Socrata (data.edmonton.ca) |
| Spatial joins | Shapely, pyproj |
| Frontend | Next.js 14 with Tailwind and Recharts |
| Map | Leaflet.js + react-leaflet |
| BI | Tableau Public ([live dashboard](https://public.tableau.com/app/profile/zawad.nafi/viz/EdmontonLens-NeighbourhoodsandTransit/Dashboard1), docs in [`tableau/`](tableau/)); `powerbi/` and `looker_studio/` are untested guides |
| Automation | GitHub Actions |

## Getting it running

Here's everything you need to get this running locally.

1. `git clone <repo-url> edmontonlens && cd edmontonlens`
2. `cp .env.example .env`
3. `python3 -m venv .venv && source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `python -m backend.etl.pipeline`
6. `uvicorn backend.main:app --reload`
7. `cd frontend && npm install && npm run dev`

`docker compose up` spins up all four databases, the backend, and the frontend at once without installing anything locally.

## The data

| Real (City of Edmonton Open Data) | Simulated or sample |
|---|---|
| 243 transit routes (`d577-xky7`) | Route on-time rates, delays, per-stop delays |
| 6,790 transit stops (`4vt2-8zrq`) | Trip counts (a fallback constant; the bulk GTFS URL returns 404) |
| 1,043 parks (`gdd9-eqv9`; 1,196 rows with duplicate IDs) | Waste schedules (the dataset `vkpg-2sa6` returns HTTP 403) |
| 399 neighbourhood boundaries, 2019 (`xu6q-xcmj`) | |

Field-level lineage, cleaning steps, refresh and known limitations are documented in [`tableau/README.md`](tableau/README.md).

## What I learned building this

The hardest part was the transit performance data. The static schedule doesn't include real arrivals, so I couldn't compute observed delays. I built a simulation layer instead, and I label everything it produces as simulated.

Loading BigQuery from the free sandbox taught me that it rejects DML, so `MERGE` isn't available. Idempotent loads use a staging table plus a `QUALIFY ROW_NUMBER()` rebuild instead. Writing data-quality checks also surfaced real bugs: a placeholder API token that made every request fail with 403 and silently fall back to sample data, a 5,000-row cap that dropped 1,790 stops, neighbourhood areas that were all zero, and 1,012 stops that fall outside the polygon they're assigned to.

The Gemini agent prompt took a few rounds to get right. My first version let the model hallucinate table names. The fix was adding a schema inspection tool the agent has to call before writing SQL. It sounds obvious after the fact, but it took a few broken responses to figure out the right constraint to add.

## Questions or ideas

Open an issue on GitHub. I'm happy to talk through anything.
