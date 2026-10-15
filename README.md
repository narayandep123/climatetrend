# Climate Hazard Trend Analyzer

A full-stack climate risk dashboard built in Django + React to analyze historical weather trends for selected regions and visualize climate hazards such as heatwaves, droughts, and heavy rainfall events.

## Project overview

This project helps a user:

- search for a location or region
- select a year range
- choose a climate hazard type
- fetch historical weather data from a public API
- compute hazard-specific signals and trends
- review summary metrics, charts, and geographic context in a premium UI

The app is designed to be deployment-friendly for a free-tier hosting setup such as Vercel + Render, while still demonstrating realistic data handling, climate logic, API integration, and performance-minded caching.

## Tech stack

- Frontend: React + TypeScript + Vite
- Backend: Python + Django
- Charts: Recharts
- Mapping: Leaflet + react-leaflet
- Data source: Open-Meteo public archive and geocoding APIs
- Cache layer: MongoDB-compatible in-memory cache with a lightweight local persistence pattern for repeated queries

## Architecture

### Frontend

The frontend is a single-page dashboard that includes:

- region search and region selection
- hazard selector
- date-range controls
- summary KPIs
- interactive charts
- map view with markers and popups
- CSV export for chart data

### Backend

The Django backend exposes REST-style endpoints for:

- health checking
- default region retrieval
- region search
- climate hazard analysis

The backend validates inputs, enforces supported hazard values, and delegates analysis to service logic.

### Data flow

1. User selects a region and hazard in the UI.
2. Frontend calls a Django endpoint with region, latitude, longitude, year range, and hazard.
3. Backend checks validation and resolves any missing region metadata.
4. The climate service fetches daily weather data from Open-Meteo.
5. Hazard-specific logic identifies clusters or anomalies in the data.
6. Results are aggregated into yearly event counts, duration metrics, and trend labels.
7. The frontend renders the summary cards and charts.

## Data sources

This project uses public, real-world weather APIs rather than synthetic mock data.

### Open-Meteo geocoding API

Used to:

- search for region names
- resolve coordinates for a city or region
- populate the default region list and search suggestions

### Open-Meteo archive API

Used to fetch historical daily weather data, including:

- maximum daily temperature
- daily precipitation totals

These are used for hazard detection across the user-selected year range.

## Hazard logic

The app currently supports the following climate hazard types:

### Heatwave detection

- Fetch historical daily max temperature data.
- Compute a threshold based on the observed temperature distribution for that region and period.
- Mark a heatwave when a sustained run of days exceeds the threshold.
- Aggregate yearly counts and average event duration.
- Detect directional signal using a simple regression/trend estimate.

### Drought detection

- Use precipitation totals as a proxy signal for dryness.
- Detect years or multi-day periods with rainfall deficit relative to the local climatological baseline.
- Aggregate the number of dry anomalies and summarize trend direction.

### Heavy rainfall detection

- Use daily precipitation totals to detect extreme wet events.
- Flag consecutive periods with rainfall above the chosen threshold.
- Summarize event frequency, duration, and intensity.

## Assumptions and constraints

- The app uses publicly available weather data and therefore reflects the limitations of those APIs, including data gaps or coarse coverage in some regions.
- Hazard thresholds are application-level approximations designed to be explainable and transparent rather than climatology-grade official definitions.
- A MongoDB-compatible cache is used in a lightweight local setup to reduce repeated external API calls without requiring a full production database.
- The dashboard focuses on a clear, user-friendly interpretation of trends rather than academic climate modeling complexity.
- The solution is designed to be demo-ready and deployable on free-tier hosting, with room for production hardening.

## Security and performance notes

The app includes the basics of safe implementation:

- input validation for latitude, longitude, year range, and hazard type
- rejection of unsupported hazard names
- query caching to avoid re-fetching the same region and time window repeatedly
- bounded API timeouts to prevent hanging requests
- no private API key required for current public-data usage

For free-tier deployment, these controls are enough to demonstrate safe and reasonably performant behavior. Production hardening could still include rate limiting, stricter host restrictions, and a proper WAF.

## Local setup

### 1) Create and activate Python environment

```bash
cd /Users/deepnarayan/Desktop/CHTrendAnalyzer
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install backend dependencies

```bash
pip install -r backend/requirements.txt
```

### 3) Run the Django backend

```bash
python backend/manage.py runserver 0.0.0.0:8000
```

### 4) Install frontend dependencies

```bash
cd frontend
npm install
```

### 5) Run the React frontend

```bash
npm run dev -- --host 0.0.0.0
```

Then open the local Vite URL shown in the terminal, usually http://localhost:5173.

## Deployment notes

This app is suitable for free-tier deployment using services such as:

- Vercel for the frontend
- Render or Cloud Run for the Django backend
- optional Cloudflare free plan for edge caching and basic protection

This keeps the app accessible while still showing a production-style architecture.

## AI tools used and how

### GitHub Copilot

Used throughout development for:

- scaffolding the project structure
- suggesting reusable component patterns
- creating Django views and service logic
- helping debug map-related issues and API behavior
- drafting and refining the README and project explanations

### Copilot in the editor workflow

Used to:

- iteratively refine frontend logic
- validate build and runtime issues
- reduce repeated implementation mistakes
- improve clarity of the dashboard UX and data presentation

## What I would improve with more time

- add real production database storage and better persistence
- add richer analytics such as rolling anomalies and confidence intervals
- expand map interactivity and region clustering
- add stronger rate limiting and security headers
- support more regional datasets and better geospatial filtering
- improve the model logic with official climate benchmarks and more robust threshold selection

## Checklist coverage

- README covering: setup steps, architecture, data source(s), hazard logic, assumptions, and improvements with more time — Yes
- AI tools used and how — Yes

