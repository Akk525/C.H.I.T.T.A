# GitHub → Railway auto-deploy

Two ways to redeploy when you push to GitHub. Use **one** (or both).

## Option A — GitHub Actions (recommended for this monorepo)

The workflow [`.github/workflows/railway-deploy.yml`](../.github/workflows/railway-deploy.yml) deploys with `railway up --path-as-root`, so you do **not** need to set Root Directory in the dashboard.

1. Create a token: [railway.com/account/tokens](https://railway.com/account/tokens)
2. In GitHub: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `RAILWAY_TOKEN`
   - Value: your token
3. Push to `main` (or `master`). Only changed paths redeploy:
   - `backend/**` → `chitta-api`
   - `frontend/**` → `chitta-web`

Manual run: **Actions → Deploy to Railway → Run workflow**.

## Option B — Railway native GitHub integration

Use this if you prefer deploys entirely inside Railway (no Actions).

1. [Connect GitHub to Railway](https://railway.com/account) (account settings).
2. Open project **CHITTA** → each service → **Settings → Source** → connect `Akk525/C.H.I.T.T.A`.
3. Set **Root Directory**:
   - `chitta-api` → `backend`
   - `chitta-web` → `frontend`
4. Set **Config file path** (absolute from repo root):
   - `chitta-api` → `/backend/railway.toml`
   - `chitta-web` → `/frontend/railway.toml`
5. Enable **Deploy on push** for the production branch.

If both Option A and B are enabled, you may get duplicate deploys on each push—pick one.
