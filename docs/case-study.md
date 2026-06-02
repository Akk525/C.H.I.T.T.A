# CHITTA — Technical Case Study

**Climate Heuristics & Intelligent Turbine Terrain Analysis**

> AI-assisted wind site screening for terrain-aware renewable energy planning.

---

## Executive summary

CHITTA is a full-stack climate-tech application that demonstrates how geospatial data pipelines, heuristic scoring, and consultant-style reporting can be combined into a single auditable workflow for early-stage wind site screening. Built as a portfolio project, it showcases full-stack engineering, API design, real external data integration, and product thinking oriented toward renewable energy developers and climate-tech teams.

The system evaluates candidate turbine coordinates in seconds, surfaces REAL vs MOCK data provenance, generates suitability heatmaps, exports PDF assessments, and records a methodology audit trail suitable for stakeholder and recruiter review.

---

## Problem statement

Wind project development begins with a large funnel of candidate coordinates. Teams must quickly eliminate sites with poor wind resource, prohibitive terrain, or logistics constraints — before committing to met towers, environmental studies, and grid interconnection work.

Traditional approaches scatter this work across:

- Wind atlases and reanalysis datasets
- DEM / slope analysis in GIS desktop tools
- Spreadsheets with opaque scoring logic
- Ad-hoc consultant memos without reproducible metadata

CHITTA addresses the **first-pass screening gap**: fast, transparent, and repeatable coordinate-level evaluation with clear data lineage.

---

## Solution overview

CHITTA provides:

1. **Interactive site explorer** — Mapbox map, geocoding search, click-to-select coordinates
2. **Real-data-assisted scoring** — NASA POWER wind + OpenTopoData elevation with mock fallbacks
3. **Consultant report** — Executive summary, strengths, risks, recommendations
4. **Suitability heatmap** — Grid-based screening with top candidate zone ranking
5. **PDF export** — Portfolio-ready site assessment document
6. **Methodology & audit trail** — analysisId, formula version, provider status, ordered steps
7. **Demo mode** — Curated Indian wind sites for instant recruiter demos

---

## Architecture

### Monorepo layout

```
CHITTA/
├── frontend/          # Next.js 15, Tailwind, Mapbox GL
├── backend/           # FastAPI, provider layer, scoring, PDF
├── infra/             # Docker Compose (PostGIS)
└── docs/              # Case study, future specs
```

### Request flow (single-site analysis)

```
User selects coordinate
        │
        ▼
POST /api/site-analysis
        │
        ├── NASA POWER ──► wind time series (WS10M daily)
        ├── OpenTopoData ─► elevation + sample ring
        ├── Mock accessibility provider
        │
        ▼
Scoring layer (v1.0.0)
        │
        ├── Consultant report builder
        ├── Methodology metadata
        └── Audit trail + analysisId
        │
        ▼
JSON response → Dashboard + report UI
```

### Heatmap flow

```
POST /api/site-heatmap { lat, lng, radiusKm, gridSize }
        │
        ▼
Generate N×N grid points
        │
        ▼
For each cell (concurrency-limited, cached):
  └── analyze_site_realdata()
        │
        ▼
Rank bestCells + return cells + methodology
```

---

## Data providers

| Provider | Signal | Usage |
|----------|--------|-------|
| NASA POWER | WS10M daily | Mean wind speed + consistency scoring |
| OpenTopoData (SRTM90m) | Elevation | Point height + terrain roughness ring |
| Mock providers | All signals | Deterministic fallback on API failure |

**Design principle:** External APIs are treated as unreliable. Timeouts, validation, per-cell fallback, and REAL/MOCK labeling ensure the application never crashes and always communicates data quality.

---

## Scoring methodology (v1.0.0)

### Wind score
- Mean speed score: linear map from 3 m/s (0) to 10 m/s (100)
- Consistency score: coefficient of variation over daily series (lower CV → higher score)
- **Wind score = 0.7 × mean + 0.3 × consistency**

### Terrain score
- Sample 12 elevation points in 1.5 km ring
- Standard deviation → terrain complexity scalar (0.15–2.0)
- Invert to buildability score

### Confidence score
- Base 35 + bonuses for real wind/elevation success + sample count penalties

### Total suitability
- **40% wind + 25% terrain + 20% accessibility + 15% confidence**

All formulas are exposed in the UI methodology panel and exported PDF.

---

## Key engineering decisions

### Modular provider layer
`backend/app/providers/` defines interfaces for wind, elevation, terrain, and accessibility. Mock and real implementations swap without changing API contracts — enabling incremental integration of OSM, local DEM tiles, or proprietary datasets.

### Caching strategy
- Provider-level TTL cache (wind series, elevation samples)
- Cell-level cache for heatmap results
- Reduces NASA POWER / OpenTopoData hammering on repeated demos

### Auditability first
Every response includes `analysisId`, `methodology`, and `auditTrail`. This was a deliberate product choice for consultancy-like trust and portfolio storytelling.

### PDF as first-class output
ReportLab generates structured PDFs server-side from the same analysis payload the UI consumes — no client-side print hacks.

---

## Demo mode

Three curated sites accelerate recruiter demos without manual coordinate entry:

| Site | Region | Rationale |
|------|--------|-----------|
| Chitradurga | Karnataka | Established inland wind corridor |
| Kutch | Gujarat | High-potential arid/coastal belt |
| Tirunelveli | Tamil Nadu | Southern coastal comparison point |

Landing page → `/demo?sample=kutch` loads the site and triggers analysis automatically.

---

## API surface

| Endpoint | Purpose |
|----------|---------|
| `POST /api/site-analysis` | Single-site scoring + report |
| `POST /api/site-heatmap` | Grid heatmap + best cells |
| `POST /api/site-report/export` | PDF download |
| `GET /health` | Liveness |

---

## Known limitations

1. **Not bankable** — Screening tool only; no IEC-compliant energy yield
2. **Accessibility is mock** — OSM road/grid distance not yet implemented
3. **Public API dependency** — Rate limits may trigger mock fallbacks
4. **Heatmap latency** — 5×5 grid = 25 external data calls (mitigated by cache)
5. **No auth / persistence in demo** — PostGIS schema exists but optional

---

## Future roadmap

- [ ] OSM Overpass for road and transmission proximity
- [ ] Wind direction / seasonal rose from NASA POWER
- [ ] Redis-backed cache for production deployments
- [ ] Background heatmap jobs with progress polling
- [ ] Saved projects and comparison dashboards
- [ ] Batch CSV upload for portfolio screening

---

## Tech stack summary

| Component | Technology |
|-----------|------------|
| Frontend | Next.js, React, Tailwind CSS, Mapbox GL |
| Backend | FastAPI, Pydantic, httpx, ReportLab |
| Database | PostgreSQL + PostGIS (SQLAlchemy, Alembic) |
| Deployment target | Railway (2 services + managed Postgres) |

---

## Conclusion

CHITTA demonstrates end-to-end climate-tech product engineering: from geospatial data ingestion through scoring transparency to consultant-grade outputs. It is designed to be demoed in under two minutes, explained in a technical interview, and extended toward production-grade wind screening with clear upgrade paths for data providers, caching, and persistence.

**Live demo:** `/demo` · **Sample sites:** Chitradurga, Kutch, Tirunelveli
