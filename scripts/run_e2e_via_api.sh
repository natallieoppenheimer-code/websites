#!/usr/bin/env bash
# Run lead pipeline E2E via API: inject one lead, then run pipeline (dry run).
# Requires: API running (e.g. uvicorn clawbot_api:app --port 8000) with .env set.
# Usage: BASE_URL=http://localhost:8000 ./scripts/run_e2e_via_api.sh

set -e
BASE_URL="${BASE_URL:-http://localhost:8000}"
AREA="${AREA:-Morgan Hill CA}"
CATEGORY="${CATEGORY:-plumber}"

echo "[E2E] Injecting one test lead..."
curl -s -X POST "${BASE_URL}/leads/inject" \
  -H "Content-Type: application/json" \
  -d "{\"area\":\"${AREA}\",\"category\":\"${CATEGORY}\",\"business_name\":\"E2E Test Lead\",\"biz_phone\":\"5550000000\"}"
echo ""

echo "[E2E] Running pipeline (max_to_process=1, dry_run=true)..."
# URL-encode area for query string (spaces -> %20)
AREA_ENC=$(echo -n "$AREA" | sed 's/ /%20/g')
curl -s -X POST "${BASE_URL}/leads/run/sync?area=${AREA_ENC}&category=${CATEGORY}&max_to_process=1&dry_run=true"
echo ""

echo ""
echo "[E2E] Done. Check the Leads sheet for the updated row."
