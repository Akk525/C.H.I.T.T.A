# CHITTA — Climate Heuristics & Intelligent Turbine Terrain Analysis (MVP)

Full-stack MVP:
- **Frontend**: Next.js (Mapbox map + location search + dashboard)
- **Backend**: FastAPI (`POST /api/site-analysis`)
- **DB**: PostgreSQL (PostGIS-ready via `postgis/postgis`)

## Monorepo layout
- `frontend/` — Next.js app
- `backend/` — FastAPI app
- `infra/` — Docker compose for Postgres/PostGIS

## Local development

### 1) Start Postgres/PostGIS (optional for MVP)

```bash
cd infra
docker compose up -d
```

### 2) Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# optional: run migrations if DB is running
alembic upgrade head

uvicorn app.main:app --reload --port 8000
```

### 3) Frontend (Next.js)

```bash
cd frontend

# required for map + location search
export NEXT_PUBLIC_MAPBOX_TOKEN="YOUR_TOKEN"

# where the frontend calls FastAPI
export NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"

npm run dev
```

Open `http://localhost:3000`.

## API contract

### `POST /api/site-analysis`

Request:

```json
{ "latitude": 37.7749, "longitude": -122.4194 }
```

Response (shape):
- `inputs`: normalized lat/lng
- `metrics`: `windScore`, `terrainScore`, `accessibilityScore`, `confidenceScore`, plus `elevationM`, `terrainComplexity`
- `totalSuitabilityScore`: 0–100
- `report`: `executiveSummary`, `siteStrengths`, `risks`, `recommendations`, `confidenceNotes`

## Railway deployment (recommended)

Deploy as **two services** plus a Railway Postgres database.

### Backend service
- **Root directory**: `backend`
- **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment**:
  - `DATABASE_URL`: from Railway Postgres (use the provided URL)
  - `CORS_ORIGINS`: `https://<your-frontend-domain>` (comma-separated allowed)
  - `PERSIST_ANALYSES`: optional (`true`/`false`)
- **Migrations**:
  - After linking Postgres, run `alembic upgrade head` (Railway one-off command) to create tables and enable PostGIS extension.

### Frontend service
- **Root directory**: `frontend`
- **Environment**:
  - `NEXT_PUBLIC_MAPBOX_TOKEN`
  - `NEXT_PUBLIC_API_BASE_URL`: `https://<your-backend-domain>`
 - **Build note**: `NEXT_PUBLIC_*` vars are embedded at build-time in Next.js; set them in Railway before the first build.

## Provider plug-in points (for later real data)
- `backend/app/providers/` contains provider interfaces and mock implementations.\n  Swap `Mock*Provider` for real providers (NASA POWER, OpenTopoData, OSM) without changing API shape.\n+
