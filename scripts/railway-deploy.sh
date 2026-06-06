#!/usr/bin/env bash
# Deploy CHITTA backend + frontend to Railway (requires: railway login, GitHub repo connected).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_NAME="${RAILWAY_PROJECT_NAME:-CHITTA}"
API_SERVICE="${RAILWAY_API_SERVICE:-chitta-api}"
WEB_SERVICE="${RAILWAY_WEB_SERVICE:-chitta-web}"

red() { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
bold() { printf '\033[1m%s\033[0m\n' "$*"; }

if ! command -v railway >/dev/null 2>&1; then
  red "Railway CLI not found. Install: brew install railway"
  exit 1
fi

if ! railway whoami >/dev/null 2>&1; then
  red "Not logged in to Railway. Run this in your terminal first:"
  echo "  railway login"
  exit 1
fi

load_env_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$file"
  set +a
}

set_service_vars_from_backend_env() {
  local service="$1"
  load_env_file "$ROOT/backend/.env"
  local pairs=(
    "CHITTA_API_KEY=${CHITTA_API_KEY:-}"
    "CHITTA_MAX_BODY_BYTES=${CHITTA_MAX_BODY_BYTES:-2097152}"
    "CHITTA_MAX_HISTORY_PAYLOAD_BYTES=${CHITTA_MAX_HISTORY_PAYLOAD_BYTES:-1048576}"
    "PERSIST_ANALYSES=${PERSIST_ANALYSES:-false}"
    "CHITTA_LLM_PROVIDER=${CHITTA_LLM_PROVIDER:-mock}"
    "CHITTA_SYNTHESIS_MODEL=${CHITTA_SYNTHESIS_MODEL:-}"
    "CHITTA_SIGNALS_PROVIDER=${CHITTA_SIGNALS_PROVIDER:-mock}"
  )
  for pair in "${pairs[@]}"; do
    [[ "$pair" == *"=" ]] && continue
    railway variable set "$pair" --service "$service" --skip-deploys 2>/dev/null || \
      railway variable set "$pair" --service "$service"
  done
  if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
    railway variable set "GOOGLE_API_KEY=${GOOGLE_API_KEY}" --service "$service" --skip-deploys 2>/dev/null || true
  fi
  if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    railway variable set "OPENAI_API_KEY=${OPENAI_API_KEY}" --service "$service" --skip-deploys 2>/dev/null || true
  fi
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    railway variable set "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" --service "$service" --skip-deploys 2>/dev/null || true
  fi
  if [[ "${PERSIST_ANALYSES:-false}" == "true" ]]; then
    railway variable set "PERSIST_ANALYSES=true" --service "$service" --skip-deploys 2>/dev/null || true
    if railway service list 2>/dev/null | grep -qi postgres; then
      railway variable set 'DATABASE_URL=${{Postgres.DATABASE_URL}}' --service "$service" --skip-deploys 2>/dev/null || true
    elif [[ -n "${DATABASE_URL:-}" ]]; then
      railway variable set "DATABASE_URL=${DATABASE_URL}" --service "$service" --skip-deploys 2>/dev/null || true
    fi
  fi
}

set_frontend_vars() {
  local service="$1"
  local api_base="$2"
  load_env_file "$ROOT/frontend/.env"
  railway variable set "NEXT_PUBLIC_API_BASE_URL=${api_base}" --service "$service" --skip-deploys
  railway variable set "NEXT_PUBLIC_CHITTA_API_KEY=${NEXT_PUBLIC_CHITTA_API_KEY:-${CHITTA_API_KEY:-}}" --service "$service" --skip-deploys
  if [[ -n "${NEXT_PUBLIC_MAPBOX_TOKEN:-}" ]]; then
    railway variable set "NEXT_PUBLIC_MAPBOX_TOKEN=${NEXT_PUBLIC_MAPBOX_TOKEN}" --service "$service" --skip-deploys
  fi
}

ensure_project() {
  cd "$ROOT"
  if railway status >/dev/null 2>&1; then
    green "Using linked Railway project."
    return
  fi
  bold "Creating Railway project: ${PROJECT_NAME}"
  railway init -n "$PROJECT_NAME"
}

ensure_service() {
  local name="$1"
  if railway service list 2>/dev/null | grep -q "$name"; then
    return
  fi
  bold "Adding service: ${name}"
  railway add --service "$name" || true
}

generate_domain() {
  local service="$1"
  local url
  url="$(railway domain --service "$service" --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('domain',''))" 2>/dev/null || true)"
  if [[ -z "$url" ]]; then
    url="$(railway domain --service "$service" 2>/dev/null | tail -1 | tr -d '[:space:]' || true)"
  fi
  printf '%s' "$url"
}

bold "=== CHITTA Railway deploy ==="

ensure_project

ensure_service "$API_SERVICE"
ensure_service "$WEB_SERVICE"

bold "Deploying backend (${API_SERVICE})…"
cd "$ROOT"
railway service link "$API_SERVICE"
set_service_vars_from_backend_env "$API_SERVICE"
railway up backend --path-as-root -s "$API_SERVICE" --detach

bold "Generating backend public domain…"
API_DOMAIN="$(generate_domain "$API_SERVICE")"
if [[ -z "$API_DOMAIN" || "$API_DOMAIN" != http* ]]; then
  API_DOMAIN="https://${API_DOMAIN}"
fi
if [[ "$API_DOMAIN" != https://* ]]; then
  API_DOMAIN="https://${API_DOMAIN#https://}"
  API_DOMAIN="https://${API_DOMAIN#http://}"
fi
green "Backend URL: ${API_DOMAIN}"

bold "Deploying frontend (${WEB_SERVICE})…"
cd "$ROOT"
railway service link "$WEB_SERVICE"
set_frontend_vars "$WEB_SERVICE" "$API_DOMAIN"
railway up frontend --path-as-root -s "$WEB_SERVICE" --detach

bold "Generating frontend public domain…"
WEB_DOMAIN="$(generate_domain "$WEB_SERVICE")"
if [[ -n "$WEB_DOMAIN" && "$WEB_DOMAIN" != http* ]]; then
  WEB_DOMAIN="https://${WEB_DOMAIN}"
fi
green "Frontend URL: ${WEB_DOMAIN}"

if [[ -n "$WEB_DOMAIN" ]]; then
  bold "Updating backend CORS…"
  cd "$ROOT"
  railway service link "$API_SERVICE"
  railway variable set "CORS_ORIGINS=${WEB_DOMAIN}" --service "$API_SERVICE"
  railway redeploy --service "$API_SERVICE" 2>/dev/null || railway up backend --path-as-root -s "$API_SERVICE" --detach
fi

echo ""
green "Done."
echo "  Frontend: ${WEB_DOMAIN:-<generate domain in Railway dashboard>}"
echo "  Backend:  ${API_DOMAIN}"
echo "  Health:   ${API_DOMAIN}/health"
echo ""
echo "If the frontend cannot reach the API, redeploy the frontend after confirming variables:"
echo "  cd frontend && railway variable list --service ${WEB_SERVICE}"
