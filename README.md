# EdmontonLens

EdmontonLens is a personal project I built to make sense of the data the City of Edmonton publishes. The city puts out a lot of open data, but it's scattered across different portals and formats with no easy way to ask a question and get an answer. So I built something that pulls it all together, cleans it up, and gives you three different ways to look at it: charts for transit, a map for neighbourhoods, and a plain-English chat interface that writes SQL for you.

## Here's what you can do with it

**Transit** shows you how well the bus network is actually running. You get a chart of on-time rates over the last 30 days for the top routes, a bar chart of the stops with the worst delays, and a machine learning model's prediction for delay risk the next morning. The numbers refresh every five minutes. It's the kind of thing you'd check before deciding whether to leave early.

**Ask** is a chat interface where you type a question in plain English. A language model (Google Gemini through a LangChain agent) writes the SQL, runs it, and explains what it found. Ask things like "which neighbourhood has the most parks" or "when does recycling get picked up in Highlands" and get a real answer. If you don't have a Gemini key, built-in queries keep the page working.

**Map** is an interactive neighbourhood map built with Leaflet.js, using boundary polygons from the city's ArcGIS service. Each neighbourhood is coloured by a score combining transit access, park coverage, and waste pickup frequency. Click any area and a panel shows the full breakdown, including a sparkline of how the transit score has changed over the last year.

## How it actually works

There's a Python script that runs once a day. It pulls the transit schedule (a GTFS feed), parks and waste data from the city's Socrata API, and neighbourhood boundaries from ArcGIS, all at the same time. It cleans everything with Pandas, validates the schemas, loads the results, and retrains a random forest classifier on fresh transit data to estimate delay probability by route and time of day.

The data lands in four places: Google BigQuery in production, plus PostgreSQL, MySQL, and SQL Server locally so you can explore with whichever tool you prefer.

In the middle sits a FastAPI server the Next.js frontend calls for everything. It handles data queries, natural-language chat through LangChain, and serves the neighbourhood GeoJSON. The API self-documents at `/docs`.

The daily pipeline runs on GitHub Actions, CI lints and type-checks on every push, and a deploy workflow ships the frontend to Vercel on merge to main.

## The tech behind it

| What it does | Tool used |
|---|---|
| Backend API | FastAPI + Python 3.11 |
| Data processing | Pandas |
| Database ORM | SQLAlchemy |
| Cloud warehouse | Google BigQuery |
| Local relational DB | PostgreSQL |
| Additional local targets | MySQL 8, SQL Server 2022 |
| ML delay predictor | scikit-learn RandomForest |
| Language model agent | LangChain + Google Gemini |
| Geospatial boundaries | ESRI ArcGIS REST API |
| Transit schedule data | GTFS feed (Edmonton Transit) |
| Open data API | Socrata (data.edmonton.ca) |
| Frontend | Next.js 14 with Tailwind and Recharts |
| Map | Leaflet.js + react-leaflet |
| BI dashboards | Tableau Public, Power BI, Looker Studio |
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

Edmonton's open data portal publishes transit, parks, and waste data through an API called Socrata. The transit schedule comes as a GTFS feed, a zip of CSV tables describing every route and timetable that the city updates daily. That's what feeds the on-time calculations. Neighbourhood boundaries come from ArcGIS as polygon geometries. All of it is public and free.

## What I learned building this

The hardest part was the GTFS data. The static feed doesn't include real-time arrivals, so I couldn't compute observed delays directly. I built a simulation layer that adds realistic noise based on time-of-day and route patterns so the ML model has something useful to train on.

BigQuery surprised me in a good way. I expected the query latency to hurt the API response times, but with the BigQuery Storage client for fast reads, it's fine. What I didn't expect was how strict BigQuery is about timestamp types, which meant going back and adjusting the schema a few times.

The Gemini agent prompt took a few rounds to get right. My first version let the model hallucinate table names. The fix was adding a schema inspection tool the agent has to call before writing SQL. It sounds obvious after the fact, but it took a few broken responses to figure out the right constraint to add.

## Questions or ideas

Open an issue on GitHub. I'm happy to talk through anything.
