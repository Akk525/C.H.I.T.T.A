# CHITTA — Climate Heuristics & Intelligent Turbine Terrain Analysis

**AI-assisted wind site screening for terrain-aware renewable energy planning.**

CHITTA is a full-stack climate-tech demo built across 9 development phases. It combines real geospatial data, deterministic heuristic scoring, multi-agent analysis, LangGraph orchestration, AI synthesis with evidence grounding, GDELT news signals, and a transparent methodology audit trail — designed for portfolio demos and early-stage site diligence.

---

## What CHITTA does

| Capability | Detail |
|---|---|
| Site Analysis | NASA POWER wind + OpenTopoData elevation → 6-dimensional suitability scoring |
| Agent Analysis | 5 specialist agents (Wind, Terrain, Infra, Environmental, Social) + CoordinatorAgent |
| Economic Feasibility | CAPEX, LCOE, payback, capacity factor estimates (order-of-magnitude) |
| Suitability Heatmap | N×N grid scoring + top candidate zone ranking |
| Regional Prospecting | Two-pass batch screening + greedy cluster analysis for up to 50 sites |
| Scenario Simulation | Configurable weight + economic assumption sensitivity analysis |
| Turbine Layout | Wind-aligned grid placement + Jensen/Park wake loss estimation |
| AI Synthesis | LLM-generated consultant narratives grounded strictly in evidence packets |
| Prospecting PDF Export | Multi-page consultant dossier with cluster summaries, economics, AI narrative |
| Run History | PostgreSQL persistence + LangGraph 6-node comparison graph |
| Development Signals | GDELT news query + deterministic agent summary (advisory only) |

---

## Pages

| Route | Purpose |
|---|---|
| `/` | Landing page with 7-step demo path |
| `/demo` | Site analysis with map, scores, agent panel, layout, AI briefing |
| `/prospecting` | Regional batch screening + simulation + signals + export |
| `/history` | Saved run list, timeline, LangGraph comparison |

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Basic health check |
| GET | `/api/health/providers` | Provider connectivity (DB, NASA POWER, OSM, GDELT, LLM) |
| POST | `/api/site-analysis` | Single-site scoring + 5-agent + economics |
| POST | `/api/site-heatmap` | N×N grid suitability heatmap |
| POST | `/api/site-report/export` | PDF site assessment |
| POST | `/api/prospecting/run` | Regional batch screening |
| POST | `/api/simulation/run` | Scenario simulation across candidates |
| POST | `/api/layout/analyze` | Turbine layout + wake loss |
| POST | `/api/ai/synthesize` | Grounded AI narrative from evidence |
| POST | `/api/prospecting-report/export` | PDF prospecting dossier |
| POST | `/api/signals/query` | GDELT development signals |
| POST | `/api/history/save` | Persist a run |
| GET | `/api/history/runs` | List saved runs |
| GET | `/api/history/run/{id}` | Retrieve a saved run |
| GET | `/api/history/compare/{idA}/{idB}` | LangGraph historical comparison |
| POST | `/api/history/summarize` | Summarize or compare runs |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│               Next.js 16 (TypeScript)               │
│  / · /demo · /prospecting · /history                │
│  Mapbox GL · Tailwind · React error boundary        │
└────────────────────┬────────────────────────────────┘
                     │ REST
┌────────────────────▼────────────────────────────────┐
│                   FastAPI (Python 3.10)             │
│                                                     │
│  Scoring · Agents · Economics · Simulation          │
│  Layout (Jensen wake) · PDF (ReportLab)             │
│  AI Synthesis (LLM provider abstraction)            │
│  LangGraph history graph (6 nodes)                  │
│  Signals (GDELT + mock)                             │
└──┬───────────────────┬───────────────────┬──────────┘
   │                   │                   │
   ▼                   ▼                   ▼
NASA POWER         OpenTopoData       OpenStreetMap
WS10M/50M/100M     SRTM 90m           Overpass API
   │                   │                   │
   ▼                   ▼                   ▼
┌──────────────────────────────────────────────────┐
│       PostgreSQL (optional — history only)       │
│       saved_runs table (JSONB payload)           │
└──────────────────────────────────────────────────┘
```

| Layer | Stack |
|---|---|
| Frontend | Next.js 16, Tailwind CSS, Mapbox GL JS |
| Backend | FastAPI, Pydantic v2, ReportLab, httpx |
| LLM | Anthropic Claude / Google Gemini / OpenAI (mock default) |
| Orchestration | LangGraph (history comparison graph) |
| Signals | GDELT DOC API v2 (mock fallback) |
| Persistence | PostgreSQL + SQLAlchemy + Alembic |
| Export | ReportLab (PDF), multi-stage Dockerfile |

---

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (optional — only for `/history` features)

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — at minimum set PERSIST_ANALYSES=false (no DB needed)
uvicorn app.main:app --reload --port 8000
```

To enable history features (optional):
```bash
# Start PostgreSQL (Homebrew or Docker)
createdb chitta
alembic upgrade head
# Set PERSIST_ANALYSES=true in .env
```

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local
# Set NEXT_PUBLIC_MAPBOX_TOKEN (free at mapbox.com)
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Required | Description |
|---|---|---|---|
| `CHITTA_API_KEY` | — | **Prod** | Shared API key sent as `X-Api-Key`. Generate with `secrets.token_hex(32)`. Unset = unauthenticated dev mode. |
| `DATABASE_URL` | postgres://… | No | PostgreSQL DSN. Only needed for history. |
| `PERSIST_ANALYSES` | `false` | No | Set `true` to enable run persistence. |
| `CORS_ORIGINS` | `http://localhost:3000` | Yes | Comma-separated allowed origins. |
| `CHITTA_LLM_PROVIDER` | `mock` | No | `mock`, `claude`, `gemini`, or `openai`. Mock needs no key. |
| `ANTHROPIC_API_KEY` | — | No | Required when `CHITTA_LLM_PROVIDER=claude`. |
| `GOOGLE_API_KEY` | — | No | Required when `CHITTA_LLM_PROVIDER=gemini` (`GEMINI_API_KEY` also accepted). |
| `OPENAI_API_KEY` | — | No | Required when `CHITTA_LLM_PROVIDER=openai`. |
| `CHITTA_SYNTHESIS_MODEL` | (provider default) | No | e.g. `claude-sonnet-4-20250514`, `gemini-2.5-flash`, `gpt-4.1-mini`. |
| `CHITTA_SIGNALS_PROVIDER` | `mock` | No | `mock` or `gdelt`. GDELT is free, rate-limited. |

### Frontend (`frontend/.env.local`)

| Variable | Default | Required | Description |
|---|---|---|---|
| `NEXT_PUBLIC_CHITTA_API_KEY` | — | **Prod** | Must match backend `CHITTA_API_KEY`. Sent as `X-Api-Key` on all requests. Demo-level shared key, not per-user auth. |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | — | No | Required for map. Free at mapbox.com. |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Yes | Backend API URL. |

---

## Data Sources

| Source | Data | Quality |
|---|---|---|
| NASA POWER | WS10M/WS50M/WS100M daily 2014–2023 | Measured satellite reanalysis |
| OpenTopoData | SRTM 90m elevation | Measured (30m SRTM accuracy) |
| OpenStreetMap | Roads, powerlines, settlements | Community-mapped |
| GDELT DOC API | News article titles + metadata (90-day window) | Advisory — not verified facts |
| ESA WorldCover | Land cover classification (heuristic proxy) | Estimated |

---

## Limitations

1. **Not engineering-grade** — economic estimates (LCOE, CAPEX, payback) are ±30–50% order-of-magnitude. Not bankable.
2. **Jensen wake model** — simplified top-hat single-direction model. Real wake CFD would give substantially different results.
3. **GDELT signals are advisory** — news titles are classified by keyword, not verified. Treat as directional intelligence only.
4. **AI synthesis is grounded but LLM-dependent** — the mock provider gives deterministic narratives; Claude, Gemini, or OpenAI require an API key and may incur usage costs.
5. **History requires PostgreSQL** — all other features work without a database.
6. **GDELT rate limit** — 1 request per 5 seconds. Hitting the limit falls back to mock signals automatically.
7. **NASA POWER / OpenTopoData** — public APIs that may rate-limit or fail. Mock fallbacks apply; always labeled REAL vs MOCK.

---

## Deployment

### Backend (Docker + Render)

```bash
# Build
docker build -t chitta-backend backend/

# Run locally
docker run -p 8000:8000 \
  -e PERSIST_ANALYSES=false \
  -e CORS_ORIGINS=http://localhost:3000 \
  chitta-backend

# Deploy to Render — push render.yaml to repo root,
# connect repo in Render dashboard, set DATABASE_URL secret
```

### Frontend (Vercel)

```bash
# From frontend/ directory or via Vercel dashboard
vercel --prod

# Set env vars in Vercel dashboard:
# NEXT_PUBLIC_MAPBOX_TOKEN
# NEXT_PUBLIC_API_BASE_URL=https://your-chitta-backend.onrender.com
```

---

## Recommended Demo Path

1. **Site Analysis** — open `/demo`, click Karnataka Wind Corridor, observe 6-agent scoring + economics
2. **Heatmap** — click "Generate suitability heatmap", see top candidate zones
3. **Prospecting** — open `/prospecting`, run Karnataka preset (5×5 grid, 75 km)
4. **Simulation** — in Prospecting results, open Scenario Simulation, adjust weights
5. **Layout** — in Site Analysis, open Layout Intelligence, generate turbine grid
6. **AI Briefing** — click Generate AI Briefing, see grounded evidence-backed narrative
7. **Export PDF** — click Export Prospecting Report, download multi-page dossier
8. **History** — Save to History on both pages, visit `/history`, compare two runs

---

## Documentation

- [Portfolio case study](docs/case-study.md)
- [Final report](FINAL_REPORT.md)
- [Render deployment config](render.yaml)

---

## License

MIT — see [LICENSE](LICENSE).
