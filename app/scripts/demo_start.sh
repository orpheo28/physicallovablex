#!/usr/bin/env bash
# Local restitution demo: API + PRODUCTION web build, demo data reset, every demo route pre-warmed. Ctrl-C stops both.
#   scripts/demo_start.sh                       # API :8000, web :3000, default DB (api/data/app.db)
#   API_PORT=8119 WEB_PORT=3119 DB_PATH=api/data/t.db FILES_DIR=api/data/t_files FACTORY_MCP_DB=api/data/t_net.db scripts/demo_start.sh
# Env passthrough: API_SHARED_KEY (if set, the web proxy sends it too), APP_PASSWORD (web password screen; unset = no screen).
# SKIP_BUILD=1 reuses the last `npm run build` (only if it was built for the same API_PORT). CHECK_CREDITS=0 skips the OpenRouter check.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
LOG_DIR="${LOG_DIR:-${TMPDIR:-/tmp}/plx-demo}"
API="http://localhost:$API_PORT"
WEB="http://localhost:$WEB_PORT"
mkdir -p "$LOG_DIR"
cd "$ROOT"

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die() { printf '\033[31mSTOP: %s\033[0m\n' "$*" >&2; exit 1; }
PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done; }
trap cleanup EXIT INT TERM

for port in "$API_PORT" "$WEB_PORT"; do
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1 && die "port $port is already in use (stop it, or set API_PORT / WEB_PORT)"
done
command -v uv >/dev/null || die "uv not found"
command -v npm >/dev/null || die "npm not found"
[ -d web/node_modules ] || (say "npm install" && (cd web && npm install)) || die "npm install failed"

# ---------------------------------------------------------------- API
say "API on :$API_PORT"
uv run uvicorn api.main:app --port "$API_PORT" --timeout-keep-alive 75 >"$LOG_DIR/api.log" 2>&1 &
PIDS+=($!)
for _ in $(seq 1 60); do curl -sf "$API/health" >/dev/null && break; sleep 1; done
curl -sf "$API/health" >/dev/null || { tail -20 "$LOG_DIR/api.log"; die "API did not start (log: $LOG_DIR/api.log)"; }

KEYHDR=()
[ -n "${API_SHARED_KEY:-}" ] && KEYHDR=(-H "X-App-Key: $API_SHARED_KEY")
curl -sf -X POST "${KEYHDR[@]}" "$API/demo/reset" >/dev/null || die "POST /demo/reset failed (API_SHARED_KEY set but wrong?)"
echo "demo data reset (demo_desk_lamp, demo_tracker_card, 8 fictional factories)"
HEALTH="$(curl -s "$API/health")"
LLM="$(printf '%s' "$HEALTH" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("llm_configured"))' 2>/dev/null)"

# ---------------------------------------------------------------- key + credits (no LLM call: OpenRouter key-info endpoint)
say "Live AI check"
echo "llm_configured (key + main model set): $LLM"
if [ "${CHECK_CREDITS:-1}" = "1" ] && [ "$LLM" = "True" ]; then
  KEY="${OPENROUTER_API_KEY:-$(grep -E '^OPENROUTER_API_KEY=' .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'"' ')}"
  if [ -n "$KEY" ]; then
    curl -s -m 8 -H "Authorization: Bearer $KEY" https://openrouter.ai/api/v1/key 2>/dev/null | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)["data"]
except Exception:
    print("could not read OpenRouter key info (offline or invalid key) -> check openrouter.ai manually"); sys.exit()
print("OpenRouter key: usage $%.2f, limit %s, remaining %s" % (d.get("usage") or 0, d.get("limit"), d.get("limit_remaining")))
' || true
  fi
else
  echo "(live runs will serve cached examples: fine for the demo of the two examples)"
fi

# ---------------------------------------------------------------- web (production)
say "Web (production build) on :$WEB_PORT"
export NEXT_PUBLIC_API_URL="$API"          # baked into the build (rewrite target): rebuild if you change API_PORT
if [ "${SKIP_BUILD:-0}" != "1" ]; then
  (cd web && npm run build) >"$LOG_DIR/web-build.log" 2>&1 || { tail -30 "$LOG_DIR/web-build.log"; die "npm run build failed (log: $LOG_DIR/web-build.log)"; }
  echo "build OK"
fi
(cd web && exec npm start -- -p "$WEB_PORT") >"$LOG_DIR/web.log" 2>&1 &
PIDS+=($!)
for _ in $(seq 1 60); do curl -s -o /dev/null "$WEB/about" && break; sleep 1; done
curl -s -o /dev/null "$WEB/about" || { tail -20 "$LOG_DIR/web.log"; die "web did not start (log: $LOG_DIR/web.log)"; }

# ---------------------------------------------------------------- warm-up
say "Pre-warming"
FAIL=0
COOKIE=""
if [ -n "${APP_PASSWORD:-}" ]; then   # password screen on: sign in once so the warm-up requests pass
  JAR="$LOG_DIR/jar"; curl -s -o /dev/null -c "$JAR" -d "password=$APP_PASSWORD" "$WEB/auth/login"; COOKIE="-b $JAR"
fi
warm() {  # url [label]
  local code t
  read -r code t < <(curl -s -o /dev/null $COOKIE -w '%{http_code} %{time_total}' -m 120 "$1")
  case "$code" in 2*|3*) printf '  ok   %s  %ss  %s\n' "$code" "$t" "${2:-$1}";; *) printf '  FAIL %s  %s\n' "$code" "${2:-$1}"; FAIL=$((FAIL+1));; esac
}
warm "$WEB/" "/"
warm "$WEB/about" "/about"
warm "$WEB/new" "/new"
warm "$WEB/projects" "/projects"
warm "$WEB/factories" "/factories"
for ex in demo_desk_lamp demo_tracker_card; do
  warm "$WEB/projects/$ex/wow" "$ex /wow"
  for n in $(seq 1 13); do
    warm "$WEB/projects/$ex?stage=$n" "$ex page ?stage=$n"
    warm "$WEB/backend/projects/$ex/stages/$n" "$ex API stage $n (via proxy)"
  done
  warm "$WEB/projects/$ex/factory-pack" "$ex /factory-pack"
  warm "$WEB/backend/projects/$ex/factory-pack" "$ex API factory-pack"
  warm "$WEB/backend/projects/$ex/export" "$ex PDF export"
  for f in d1.glb d2.glb d3.glb enclosure.glb; do warm "$WEB/backend/files/$ex/$f" "$ex file $f"; done
done
for id in $(curl -s "$API/factories" "${KEYHDR[@]}" | python3 -c 'import json,sys;print(" ".join(f["id"] for f in json.load(sys.stdin)))' 2>/dev/null); do
  warm "$WEB/factories/$id" "/factories/$id"
done

if [ "$FAIL" -gt 0 ]; then
  printf '\n\033[31m%d warm-up request(s) failed — see above and %s/*.log\033[0m\n' "$FAIL" "$LOG_DIR"
else
  printf '\n\033[32mREADY\033[0m\n'
fi
cat <<EOM
  Web (open this):  $WEB/?mode=idea
  Desk lamp:        $WEB/projects/demo_desk_lamp/wow
  Tracker card:     $WEB/projects/demo_tracker_card/wow
  Factories:        $WEB/factories
  API health:       $API/health
  Logs:             $LOG_DIR   (Ctrl-C here stops API + web)
EOM
wait
