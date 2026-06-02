# CHITTA — Climate Heuristics & Intelligent Turbine Terrain Analysis

**AI-assisted wind site screening for terrain-aware renewable energy planning.**

CHITTA is a full-stack climate-tech demo that helps teams rapidly evaluate candidate wind turbine locations. It combines real wind and elevation data, structured consultant-style reports, suitability heatmaps, PDF export, and a transparent methodology audit trail — designed for portfolio demos and early-stage site diligence.

## What CHITTA does

- Accepts a latitude/longitude (search, map click, or curated demo site)
- Fetches **NASA POWER** wind time series and **OpenTopoData** elevation samples
- Computes suitability scores for wind, terrain, accessibility, and confidence
- Generates an AI-style **consultant report** with strengths, risks, and recommendations
- Builds a **suitability heatmap** over a configurable grid and ranks top candidate zones
- Exports a polished **PDF site assessment**
- Returns **methodology metadata** and an **audit trail** for every analysis

## Why wind site screening matters

Early wind development often commits engineering and permitting spend before basic resource and terrain constraints are understood. CHITTA compresses first-pass desktop screening into minutes — surfacing where to invest deeper met tower studies, GIS work, and field visits.

## System architecture

```
┌─────────────────┐     REST API      ┌──────────────────┐
│  Next.js        │ ◄──────────────► │  FastAPI         │
│  (Mapbox UI)    │                   │  (scoring layer) │
└────────┬────────┘                   └────────┬─────────┘
         │                                       │
         │                              ┌────────▼─────────┐
         │                              │ Provider layer   │
         │                              │ NASA POWER       │
         │                              │ OpenTopoData     │
         │                              │ Mock fallbacks   │
         │                              └────────┬─────────┘
         │                                       │
         │                              ┌────────▼─────────┐
         │                              │ PostgreSQL       │
         │                              │ (PostGIS-ready)  │
         └──────────────────────────────┴──────────────────┘
```

| Layer | Stack |
|-------|-------|
| Frontend | Next.js, Tailwind, Mapbox GL |
| Backend | FastAPI, Pydantic, ReportLab |
| Data | NASA POWER, OpenTopoData, mock providers |
| Persistence | PostgreSQL + PostGIS (optional) |

## Data providers

| Signal | Provider | Notes |
|--------|----------|-------|
| Wind speed | NASA POWER (WS10M daily) | Last 365 days; REAL with mock fallback |
| Elevation | OpenTopoData (SRTM90m) | Point + 1.5 km sample ring |
| Accessibility | Mock (deterministic) | OSM integration planned |

Provider status is labeled **REAL** or **MOCK** in the UI, PDF, and audit trail.

## Scoring methodology (v1.0.0)

- **Wind score** = 70% mean-speed score (3–10 m/s → 0–100) + 30% consistency score (lower variability is better)
- **Terrain score** = buildability derived from elevation sample standard deviation
- **Accessibility score** = mock proxy (road/grid proximity planned via OSM)
- **Confidence score** = based on real provider success and sample completeness
- **Total suitability** = 40% wind + 25% terrain + 20% accessibility + 15% confidence

## Heatmap workflow

1. Select a center coordinate
2. `POST /api/site-heatmap` generates an N×N grid (default 5×5 over 10 km radius)
3. Each cell runs the same real-data-assisted scoring pipeline (with caching)
4. Cells render as colored map overlays; top 3 zones are ranked in the sidebar

## PDF export

`POST /api/site-report/export` accepts the latest analysis (+ optional heatmap) and returns a consultant-style PDF with executive summary, score tables, findings, methodology, audit trail, and disclaimer.

## Audit trail

Every analysis includes:

- Stable `analysisId` (UUID)
- Methodology metadata (sources, date ranges, formula version, fallback status)
- Ordered audit steps from coordinate receipt through report generation

## Demo mode

The landing page and demo app include three curated Indian wind screening sites:

- **Chitradurga, Karnataka**
- **Kutch, Gujarat**
- **Tirunelveli, Tamil Nadu**

Click **Try sample site** to load coordinates and run analysis immediately.

## Known limitations

- Not a bankable wind resource assessment or engineering study
- Accessibility uses mock data; OSM road/grid distance not yet integrated
- NASA POWER and OpenTopoData public APIs can rate-limit or fail (mock fallback applies)
- Heatmap scoring is compute-intensive for large grids
- PostGIS persistence is optional and not required for the demo

## Local setup

### 1) Database (optional)

```bash
cd infra
docker compose up -d
```

### 2) Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head        # optional, if DB running
uvicorn app.main:app --reload --port 8000
```

### 3) Frontend

```bash
cd frontend
cp .env.example .env.local
# Set NEXT_PUBLIC_MAPBOX_TOKEN and NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) for the landing page, or [http://localhost:3000/demo](http://localhost:3000/demo) for the app.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/site-analysis` | Single-site scoring + report |
| POST | `/api/site-heatmap` | Grid suitability heatmap |
| POST | `/api/site-report/export` | PDF export |
| GET | `/health` | Health check |

## Future improvements

- OSM-based accessibility (road and transmission proximity)
- Persistent analysis history with PostGIS spatial queries
- Seasonal wind rose and direction analysis from NASA POWER
- User accounts and saved projects
- Batch screening for portfolio-level site comparison
- Deployment hardening (Redis cache, rate limiting, background heatmap jobs)

## Documentation

- Portfolio case study: [docs/case-study.md](docs/case-study.md)

## License

Portfolio / demo project — adjust licensing as needed for your use case.
