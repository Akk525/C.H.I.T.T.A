# Deploy CHITTA on Railway

Two options: **automated script** (CLI) or **manual dashboard** setup. Optional **PostgreSQL** for Run History.

## Quick deploy (CLI)

Prerequisites: [Railway CLI](https://docs.railway.com/guides/cli), `railway login`, and local `backend/.env` + `frontend/.env` configured.

```bash
./scripts/railway-deploy.sh
```

The script links the `CHITTA` project (or creates it), deploys `backend/` and `frontend/` with `--path-as-root`, generates domains, sets `CORS_ORIGINS`, and syncs variables from your local `.env` files (never commit those files).

**One-off redeploy** after code changes:

```bash
cd /path/to/C.H.I.T.T.A
railway link -p CHITTA
railway up backend --path-as-root -s chitta-api --detach
railway up frontend --path-as-root -s chitta-web --detach
```

---

## Manual dashboard setup

Manual setup: **backend** + **frontend** on Railway.

## Architecture

| Service | Root directory | Builder |
|---------|----------------|---------|
| `chitta-api` | `backend` | Dockerfile |
| `chitta-web` | `frontend` | Nixpacks (Next.js) |
| `Postgres` (optional) | — | Railway plugin |

---

## 0. Prerequisites

1. Push this repo to GitHub (or GitLab).
2. Generate an API key (use the same value on backend + frontend):

   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. [Mapbox token](https://account.mapbox.com/) for the map (optional but recommended).

---

## 1. Create a Railway project

1. Go to [railway.app](https://railway.app) → **New Project**.
2. Choose **Deploy from GitHub repo** and select the CHITTA repository.

---

## 2. Backend service (`chitta-api`)

### Service settings

1. In the project, click the new service → **Settings**.
2. **Root Directory**: `backend`
3. **Builder**: **Dockerfile** (uses `backend/Dockerfile` automatically).
4. **Watch Paths** (optional): `backend/**`

### Networking

1. **Settings** → **Networking** → **Generate Domain**.
2. Copy the public URL, e.g. `https://chitta-api-production-xxxx.up.railway.app`  
   (no trailing slash — this is your API base URL).

### Health check (optional)

- **Settings** → **Health Check Path**: `/health`

### Variables (Variables tab)

| Variable | Value |
|----------|--------|
| `CHITTA_API_KEY` | Your generated hex key |
| `CORS_ORIGINS` | Your frontend Railway URL (set after step 3), e.g. `https://chitta-web-production-xxxx.up.railway.app` |
| `PERSIST_ANALYSES` | `false` (or `true` if using Postgres below) |
| `CHITTA_LLM_PROVIDER` | `mock` or `gemini` / `claude` / `openai` |
| `GOOGLE_API_KEY` | If using `gemini` |
| `CHITTA_SYNTHESIS_MODEL` | e.g. `gemini-2.5-flash` (optional) |
| `CHITTA_SIGNALS_PROVIDER` | `mock` or `gdelt` |

Do **not** set `DATABASE_URL` unless you added Postgres (step 4).

Redeploy after changing variables.

---

## 3. Frontend service (`chitta-web`)

1. **+ New** → **GitHub Repo** → same repository (second service).
2. **Settings** → **Root Directory**: `frontend`
3. Builder should auto-detect **Next.js** (Nixpacks).

### Variables (must be set before / during build)

`NEXT_PUBLIC_*` values are embedded at **build time**. Set these before the first successful deploy:

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend public URL from step 2, e.g. `https://chitta-api-production-xxxx.up.railway.app` |
| `NEXT_PUBLIC_CHITTA_API_KEY` | **Same** value as `CHITTA_API_KEY` on the backend |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Your Mapbox public token |

### Networking

1. **Generate Domain** for the frontend service.
2. Copy the URL, e.g. `https://chitta-web-production-xxxx.up.railway.app`.

### Fix CORS on backend

1. Open the **backend** service → **Variables**.
2. Set `CORS_ORIGINS` to the **frontend** URL (exact origin, no path).
3. **Redeploy** the backend.

### Redeploy frontend if you change `NEXT_PUBLIC_*`

Any change to `NEXT_PUBLIC_*` requires a **new deploy** (rebuild).

---

## 4. PostgreSQL (Run History)

Production project **CHITTA** includes a **Postgres** plugin. The API uses:

- `DATABASE_URL=${{Postgres.DATABASE_URL}}` (auto-normalized to `postgresql+psycopg://` in app config)
- `PERSIST_ANALYSES=true`
- Migrations on each API deploy (`alembic upgrade head` in `backend/Dockerfile`)

### Manual setup (if adding Postgres to a new project)

1. In the project: **+ New** → **Database** → **PostgreSQL**.
2. On the **backend** service → **Variables** → **Add Reference** → select Postgres → `DATABASE_URL`.
3. Edit the referenced URL if needed: Railway often provides `postgresql://...`  
   SQLAlchemy in this project expects:

   ```
   postgresql+psycopg://USER:PASS@HOST:PORT/railway
   ```

   Replace the leading `postgresql://` with `postgresql+psycopg://`.

4. Set `PERSIST_ANALYSES=true` on the backend.
5. Run migrations once (Railway **backend** service → **Settings** → deploy command, or one-off shell):

   ```bash
   alembic upgrade head
   ```

   If Railway offers a **Run Command** / shell with the backend image:

   ```bash
   cd /app && alembic upgrade head
   ```

---

## 5. Verify

1. Open `https://<backend-domain>/health` → should return JSON OK.
2. Open `https://<backend-domain>/docs` → FastAPI Swagger.
3. Open the frontend URL → launch **Demo**, pick a site, confirm scores load.
4. If requests fail with **401**, check `CHITTA_API_KEY` matches `NEXT_PUBLIC_CHITTA_API_KEY` and redeploy frontend.
5. If the browser shows **CORS** errors, fix `CORS_ORIGINS` on the backend to match the frontend origin exactly.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Backend deploy fails | Check **Root Directory** is `backend`, builder is Dockerfile. |
| Backend unhealthy | Confirm start command uses `$PORT` (Dockerfile in repo handles this). |
| Frontend can’t reach API | `NEXT_PUBLIC_API_BASE_URL` must be the **https** backend URL; rebuild frontend. |
| 401 on all API calls | API keys must match on both services. |
| CORS blocked | `CORS_ORIGINS` = frontend origin only (scheme + host, no `/demo`). |
| History / save fails | Enable Postgres, `PERSIST_ANALYSES=true`, run `alembic upgrade head`. |
| Map empty | Set `NEXT_PUBLIC_MAPBOX_TOKEN` and redeploy frontend. |

---

## 6. GitHub auto-deploy

See [scripts/railway-github-setup.md](../scripts/railway-github-setup.md).

- **GitHub Actions** (`.github/workflows/railway-deploy.yml`): add `RAILWAY_TOKEN` secret; pushes to `main`/`master` redeploy changed services.
- **Railway dashboard**: connect the repo per service and set root directories `backend` / `frontend`.

---

## Cost tips

- Use **one** Railway project with two services to keep billing in one place.
- Start with `PERSIST_ANALYSES=false` to skip Postgres until you need History.
- Use `CHITTA_LLM_PROVIDER=mock` to avoid LLM API costs on demos.
