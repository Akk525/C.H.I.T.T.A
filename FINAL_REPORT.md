# CHITTA — Final Report

**Climate Heuristics & Intelligent Turbine Terrain Analysis**  
Portfolio project · 9 development phases · Full-stack climate-tech demo

---

## Project Overview

CHITTA is a full-stack AI-assisted wind site screening application built to demonstrate how geospatial data pipelines, multi-agent deterministic reasoning, LLM synthesis with evidence grounding, and domain-specific heuristics can be combined into a single auditable workflow. It targets the first-pass desktop screening step in wind energy development — the point where teams must eliminate poor sites before committing engineering and permitting spend.

The system evaluates candidate turbine coordinates against real NASA POWER wind data, OpenTopoData elevation, and OpenStreetMap infrastructure proximity; runs a 5-agent + coordinator analysis; estimates economic feasibility; generates consultant-style PDFs; screens entire regions in batch; and maintains a persistent history for cross-run comparison via a 6-node LangGraph orchestration graph.

---

## Feature Inventory

| Feature | Phase | Status | Key Files |
|---|---|---|---|
| Site scoring (wind, terrain, infra, env, pop) | 1–3 | ✅ | `services/scoring.py`, `services/analysis.py` |
| NASA POWER + OpenTopoData providers | 1 | ✅ | `providers/nasa_power.py`, `providers/opentopodata.py` |
| OSM Overpass infrastructure | 1 | ✅ | `providers/osm_overpass.py` |
| Suitability heatmap | 1 | ✅ | `services/heatmap.py` |
| PDF site assessment export | 1 | ✅ | `services/pdf_export.py` |
| 5-agent + CoordinatorAgent analysis | 2 | ✅ | `agents/` |
| Regional batch prospecting (2-pass) | 3 | ✅ | `services/prospecting.py` |
| Economic feasibility layer | 4 | ✅ | `services/economics.py` |
| Scenario simulation engine | 4 | ✅ | `services/simulation.py` |
| AI synthesis with evidence grounding | 5.5 | ✅ | `synthesis/`, `llm/` |
| Prospecting PDF dossier export | 6 | ✅ | `services/prospecting_pdf.py` |
| Turbine layout + Jensen wake model | 7 | ✅ | `services/layout.py` |
| Run history (PostgreSQL + LangGraph) | 8A | ✅ | `models/saved_run.py`, `langgraph/` |
| GDELT development signals | 8B | ✅ | `signals/` |
| Provider health check endpoint | 9 | ✅ | `routes.py` |
| React error boundary | 9 | ✅ | `ErrorBoundary.tsx` |
| Demo path on landing page | 9 | ✅ | `LandingPage.tsx` |
| Backend Dockerfile + render.yaml | 9 | ✅ | `Dockerfile`, `render.yaml` |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                  Next.js 16 (TypeScript)                │
│                                                         │
│  /            Landing page + 7-step demo path           │
│  /demo        Site analysis · heatmap · agents          │
│               economics · layout · AI briefing          │
│               development signals · history save        │
│  /prospecting Batch screening · simulation              │
│               PDF export · AI briefing · signals        │
│  /history     Run list · LangGraph comparison           │
└────────────────────────┬────────────────────────────────┘
                         │ REST / JSON + PDF blob
┌────────────────────────▼────────────────────────────────┐
│                 FastAPI (Python 3.10)                   │
│                                                         │
│  Scoring layer    v2.1.0 — 6-dimension weighted sum     │
│  Agent layer      5 specialists + CoordinatorAgent      │
│  Economics        CAPEX/LCOE/payback (order-of-mag.)    │
│  Prospecting      2-pass grid + greedy clustering       │
│  Simulation       7-weight scenario engine (sim-1.0)    │
│  Layout           Jensen/Park wake + grid placement     │
│  AI Synthesis     Evidence packets → LLM narrative      │
│  LangGraph        6-node history comparison graph       │
│  Signals          GDELT DOC API + mock provider         │
│  PDF Export       ReportLab (site + prospecting)        │
└──┬──────────────┬──────────────┬────────────────────────┘
   │              │              │
   ▼              ▼              ▼
NASA POWER    OpenTopoData   OpenStreetMap        GDELT
WS10M/50M     SRTM 90m       Overpass API         DOC API v2
   │              │              │                    │
   └──────────────┴──────────────┘                    │
                  │                                   │
   ┌──────────────▼───────────────────────────────────┘
   │      PostgreSQL + Alembic (optional)
   │      saved_runs table (JSONB payload)
   │      UUID PK · JSONB · ARRAY · TIMESTAMPTZ
   └──────────────────────────────────────────────────
```

---

## API Endpoint Listing

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Basic liveness probe |
| `GET` | `/api/health/providers` | Full provider connectivity status |
| `POST` | `/api/site-analysis` | Single-site scoring + agents + economics |
| `POST` | `/api/site-heatmap` | N×N grid suitability heatmap |
| `POST` | `/api/site-report/export` | PDF site assessment (ReportLab) |
| `POST` | `/api/prospecting/run` | Regional batch screening (2-pass) |
| `POST` | `/api/simulation/run` | Scenario simulation |
| `POST` | `/api/layout/analyze` | Turbine grid placement + wake loss |
| `POST` | `/api/ai/synthesize` | Evidence-grounded AI narrative |
| `POST` | `/api/prospecting-report/export` | PDF prospecting dossier |
| `POST` | `/api/signals/query` | GDELT/mock development signals |
| `POST` | `/api/history/save` | Persist a run to PostgreSQL |
| `GET` | `/api/history/runs` | List saved runs (paginated) |
| `GET` | `/api/history/run/{id}` | Full saved run with payload |
| `GET` | `/api/history/compare/{idA}/{idB}` | LangGraph comparison |
| `POST` | `/api/history/summarize` | Summarize or compare runs |

---

## Data Sources and Quality

| Source | Data | Accuracy | Status |
|---|---|---|---|
| NASA POWER | WS10M/WS50M/WS100M (2014–2023 means) | ±15–20% vs met tower | Live |
| OpenTopoData | SRTM 90m elevation + slope | ±10–30m | Live |
| OpenStreetMap | Roads, powerlines, settlements | Community quality | Live |
| GDELT DOC API | News article titles (90-day) | Advisory only | Live (rate-limited) |
| ESA WorldCover | Land cover (heuristic proxy) | Estimated | Heuristic |

All providers have deterministic mock fallbacks. Provider status is labeled REAL/MOCK throughout the UI and PDF exports.

---

## Known Limitations

1. **Not bankable** — economic estimates (LCOE, CAPEX, payback) are ±30–50% order-of-magnitude. Not suitable for investment decisions.
2. **Jensen wake model** — simplified top-hat, single prevailing wind direction. Real wake losses with multi-directional analysis would differ significantly.
3. **GDELT signals are advisory** — keyword-classified news titles. Not fact-checked or verified.
4. **AI synthesis is mock by default** — OpenAI provider requires API key and billing. Mock provider gives deterministic deterministic narratives.
5. **History requires PostgreSQL** — all other features work without a database. `PERSIST_ANALYSES=false` disables cleanly.
6. **Agent reasoning is deterministic** — no LLM in the agent layer. Findings are rule-based from scores. This is intentional for auditability.
7. **No real-time wind data** — NASA POWER provides climatological means, not current conditions.

---

## Demo Flow (7 Steps)

| Step | Action | What to show |
|---|---|---|
| 1 | Open `/demo` → click Karnataka Wind Corridor | NASA POWER wind data fetch, 6-dimension score breakdown |
| 2 | Click "Generate suitability heatmap" | Grid of candidate zones, top 3 ranked |
| 3 | Open `/prospecting` → Karnataka preset → Run | 25-site batch screening, cluster analysis, enriched top candidates |
| 4 | Open Scenario Simulation → adjust tariff/weights | Ranking changes, sensitivity analysis |
| 5 | In Site Analysis → Layout Intelligence → Generate | Amber turbine markers on map, wake loss %, efficiency score |
| 6 | AI Briefing → Generate AI Briefing | Evidence-grounded narrative with citations drawer |
| 7 | Export Prospecting Report → Save to History → compare | Multi-page PDF download; LangGraph comparison narrative |

---

## Technical Highlights

**1. Grounded AI Synthesis (Phase 5.5)**  
The LLM synthesis layer is built around evidence packets with stable IDs (e.g., `wind:score`, `economic:lcoe`, `agent:coordinator`). The LLM can only reference evidenceIds from the provided payload. Citation validation runs post-generation; any invented evidenceId triggers a fallback to the deterministic mock provider. This makes the system safe to demo without hallucination risk.

**2. Jensen/Park Wake Loss (Phase 7)**  
The layout service implements the Jensen 1983 top-hat wake model with Katic RSS superposition for multiple upstream wakes. Turbines are placed on a wind-aligned rectangular grid using flat-Earth coordinate conversion. The efficiency score uses `100 − wake_loss% × 2 − violations × 3`. Clearly labelled as preliminary screening, not CFD.

**3. LangGraph History Comparison (Phase 8A)**  
The 6-node graph (`load_snapshot → compare_runs → ranking_delta → simulation_delta → narrative_delta → historical_summary`) uses conditional routing: single-run path skips comparison nodes; prospecting runs route through the ranking delta node. Node functions are pure (no side effects); DB access is resolved before graph invocation.

**4. Provider Abstraction (Phases 1, 5.5, 8B)**  
All external dependencies (NASA POWER, OpenTopoData, OSM, LLM, GDELT) follow the same pattern: a real provider + a deterministic mock provider. The mock is always the default. This means the full application can be demonstrated without any external API keys or internet access.

---

## Future Work

- **Real-time wind data** — integrate ERA5 hourly reanalysis for time-series aware scoring
- **GIS polygon input** — accept site boundary polygons instead of point coordinates
- **Bankable wind resource** — P50/P90 exceedance probability from multi-year time series
- **Noise and shadow modelling** — IEC-compliant setback calculations from turbine layout
- **Grid connection costing** — OSM-derived powerline distance + HVAC/HVDC cost models
- **User accounts** — project organisation, shared runs, team annotations
- **Redis caching** — site-level cache for NASA POWER and OpenTopoData to reduce latency
- **Phase 8B GDELT expansion** — full-text article analysis using the GDELT Knowledge Graph
