#!/usr/bin/env bash
# ============================================================================
# scripts/dev.sh — run both products locally with one command.
#
#   bash scripts/dev.sh start     start Redis, API Optimizer (API + dashboard),
#                                 Esone (API + frontend); creates missing .env files
#   bash scripts/dev.sh stop      stop the four app servers (add --with-redis to
#                                 stop the Redis container too)
#   bash scripts/dev.sh restart   stop, then start
#   bash scripts/dev.sh status    health of every service
#   bash scripts/dev.sh logs      follow all logs (Ctrl+C to leave; servers keep running)
#
# Works in Git Bash on Windows and in bash on Linux/macOS. Ports can be
# overridden with environment variables, e.g.  OPTIMIZER_PORT=9000 bash scripts/dev.sh start
#
#   Service               Port   Log
#   Redis (Docker)        6379   docker logs api-optimizer-redis
#   API Optimizer API     8001   .dev/logs/optimizer-api.log
#   API Optimizer site    3001   .dev/logs/optimizer-site.log
#   Esone API             8000   .dev/logs/esone-api.log
#   Esone frontend        4000   .dev/logs/esone-web.log
# ============================================================================
set -euo pipefail

# Refuse to run under WSL: on Windows the `bash` on PATH in PowerShell/cmd is
# WSL's, which cannot see the Windows venv, Node or Docker CLI the same way.
if grep -qi microsoft /proc/version 2>/dev/null; then
  printf '\033[1;31merror:\033[0m this script must run in Git Bash, not WSL.\n' >&2
  printf '  From PowerShell:  & "%s" scripts/dev.sh %s\n' 'C:\Program Files\Git\bin\bash.exe' "${1:-start}" >&2
  printf '  Or open a Git Bash terminal and run:  bash scripts/dev.sh %s\n' "${1:-start}" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OPTIMIZER_PORT="${OPTIMIZER_PORT:-8001}"
SITE_PORT="${SITE_PORT:-3001}"
ESONE_API_PORT="${ESONE_API_PORT:-8000}"
ESONE_WEB_PORT="${ESONE_WEB_PORT:-4000}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_CONTAINER="${REDIS_CONTAINER:-api-optimizer-redis}"

RUN_DIR="$ROOT/.dev"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------- helpers ---

say()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

is_windows() { case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) return 0 ;; *) return 1 ;; esac; }

find_python() {
  if [ -x "$ROOT/venv/Scripts/python.exe" ]; then echo "$ROOT/venv/Scripts/python.exe"
  elif [ -x "$ROOT/venv/bin/python" ]; then echo "$ROOT/venv/bin/python"
  elif [ -x "$ROOT/.venv/bin/python" ]; then echo "$ROOT/.venv/bin/python"
  else return 1; fi
}

port_pid() {  # PID of the process listening on a port, or empty
  local port="$1"
  if is_windows; then
    netstat -ano 2>/dev/null | awk -v p=":$port" '$2 ~ p"$" && $4 == "LISTENING" {print $5; exit}'
  elif command -v lsof >/dev/null 2>&1; then
    lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null | head -1
  else
    ss -ltnp 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" {match($0, /pid=[0-9]+/); print substr($0, RSTART+4, RLENGTH-4); exit}'
  fi
}

port_busy() { [ -n "$(port_pid "$1")" ]; }

kill_port() {  # stop whatever listens on a port (and its children)
  local port="$1" name="$2" pid
  pid="$(port_pid "$port")"
  if [ -z "$pid" ]; then echo "    $name: not running"; return 0; fi
  if is_windows; then taskkill //PID "$pid" //T //F >/dev/null 2>&1 || true
  else kill "$pid" 2>/dev/null || true; sleep 1; kill -9 "$pid" 2>/dev/null || true; fi
  echo "    $name: stopped (pid $pid)"
}

wait_http() {  # wait_http URL NAME [SECONDS]
  local url="$1" name="$2" secs="${3:-60}" i code
  for i in $(seq 1 "$secs"); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
    if [ "$code" = "200" ]; then return 0; fi
    sleep 1
  done
  warn "$name did not answer at $url within ${secs}s; check the log"
  return 1
}

start_bg() {  # start_bg NAME DIR LOGFILE CMD...
  local name="$1" dir="$2" log="$3"; shift 3
  # Detach fully (stdin from /dev/null too) so the script can exit while the server keeps running.
  ( cd "$dir" && nohup "$@" </dev/null >"$log" 2>&1 & echo $! >"$RUN_DIR/$name.pid" )
}

random_secret() { "$PY" -c "import secrets; print(secrets.token_urlsafe(48))"; }

set_env_var() {  # set_env_var FILE KEY VALUE  (replace the line or append)
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file"; then
    "$PY" - "$file" "$key" "$value" <<'EOF'
import re, sys
path, key, value = sys.argv[1:]
text = open(path, encoding="utf-8").read()
text = re.sub(rf"^{re.escape(key)}=.*$", f"{key}={value}", text, count=1, flags=re.M)
open(path, "w", encoding="utf-8").write(text)
EOF
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
}

env_value() { grep -E "^$2=" "$1" 2>/dev/null | head -1 | cut -d= -f2- ; }

# ------------------------------------------------------------ preparation ---

ensure_env_files() {
  # API Optimizer
  if [ ! -f .env ]; then
    cp .env.example .env
    set_env_var .env SECRET_KEY "$(random_secret)"
    set_env_var .env CORS_ORIGINS "[\"http://localhost:3000\",\"http://localhost:$SITE_PORT\",\"http://localhost:$ESONE_WEB_PORT\"]"
    set_env_var .env PROXY_UPSTREAMS "{\"esone\":\"http://localhost:$ESONE_API_PORT\"}"
    warn "created .env from .env.example (SQLite, admin admin@example.com / see ADMIN_PASSWORD). Add OPENAI_API_KEY for the LLM."
  fi
  if [ -z "$(env_value .env OPENAI_API_KEY)" ]; then
    warn "OPENAI_API_KEY is empty in .env: chat answers use page extracts and word-overlap matching until you add a key"
  fi

  # Esone API
  if [ ! -f esone/backend/.env ]; then
    cp esone/backend/.env.example esone/backend/.env
    set_env_var esone/backend/.env ESONE_SECRET_KEY "$(random_secret)"
    set_env_var esone/backend/.env ESONE_ADMIN_USERNAME admin
    set_env_var esone/backend/.env ESONE_ADMIN_EMAIL admin@example.com
    set_env_var esone/backend/.env ESONE_ADMIN_PASSWORD admin-local-pass
    warn "created esone/backend/.env (admin / admin-local-pass)"
  fi
  set_env_var esone/backend/.env ESONE_OPTIMIZER_URL "http://localhost:$OPTIMIZER_PORT"

  # Esone frontend
  if [ ! -f esone/frontend/.env ]; then
    cp esone/frontend/.env.example esone/frontend/.env
  fi
  # Esone's browser calls go through the Optimizer's reverse proxy so every
  # call is recorded, rate limited and cacheable there (PROXY_UPSTREAMS).
  set_env_var esone/frontend/.env ESONE_WEB_API_URL "http://localhost:$OPTIMIZER_PORT/proxy/esone"

  # Optimizer dashboard
  printf 'NEXT_PUBLIC_API_URL=http://localhost:%s\n' "$OPTIMIZER_PORT" > site/.env.local
}

ensure_node_modules() {
  if [ ! -d site/node_modules ]; then
    say "Installing dashboard dependencies (first run only)"
    ( cd site && npm install --no-audit --no-fund )
  fi
}

start_redis() {
  if port_busy "$REDIS_PORT"; then echo "    Redis: already listening on $REDIS_PORT"; return 0; fi
  command -v docker >/dev/null 2>&1 || die "Redis is not running and Docker is not installed. Start Redis on port $REDIS_PORT and retry."
  if docker start "$REDIS_CONTAINER" >/dev/null 2>&1; then
    echo "    Redis: started container $REDIS_CONTAINER"
  else
    docker run -d --name "$REDIS_CONTAINER" -p "$REDIS_PORT:6379" redis:7-alpine >/dev/null \
      || die "could not start Redis (is Docker Desktop running?)"
    echo "    Redis: created container $REDIS_CONTAINER"
  fi
  for _ in $(seq 1 20); do port_busy "$REDIS_PORT" && return 0; sleep 1; done
  die "Redis did not come up on port $REDIS_PORT"
}

ensure_esone_bot() {
  # Esone needs an account on the Optimizer to forward questions. Create one once.
  local file=esone/backend/.env user pass code
  user="$(env_value "$file" ESONE_OPTIMIZER_USERNAME)"
  if [ -n "$user" ]; then return 0; fi
  pass="$(random_secret)"
  code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "http://localhost:$OPTIMIZER_PORT/api/v1/auth/register" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"esone-bot\",\"email\":\"esone-bot@example.com\",\"password\":\"$pass\"}" || true)"
  if [ "$code" = "200" ]; then
    set_env_var "$file" ESONE_OPTIMIZER_USERNAME esone-bot
    set_env_var "$file" ESONE_OPTIMIZER_PASSWORD "$pass"
    echo "    Esone: created service account esone-bot on the Optimizer"
    return 0
  fi
  warn "could not create the esone-bot account on the Optimizer (HTTP $code). Set ESONE_OPTIMIZER_USERNAME/PASSWORD in $file by hand."
}

# --------------------------------------------------------------- commands ---

cmd_start() {
  PY="$(find_python)" || die "no virtualenv found. Create it first:  python -m venv venv && venv/Scripts/pip install -r requirements.txt -r esone/backend/requirements.txt -r esone/frontend/requirements.txt"
  export PY
  command -v node >/dev/null 2>&1 || die "Node.js is required for the dashboard (site/)"

  say "Preparing environment files"
  ensure_env_files
  ensure_node_modules

  say "Starting Redis"
  start_redis

  say "Applying API Optimizer migrations"
  "$PY" scripts/migrate_db.py >"$LOG_DIR/migrate.log" 2>&1 || { tail -5 "$LOG_DIR/migrate.log"; die "migrations failed, see $LOG_DIR/migrate.log"; }

  say "Starting the API Optimizer"
  if port_busy "$OPTIMIZER_PORT"; then echo "    Optimizer API: already running on $OPTIMIZER_PORT"; else
    start_bg optimizer-api "$ROOT" "$LOG_DIR/optimizer-api.log" "$PY" -m uvicorn app.main:app --port "$OPTIMIZER_PORT"
    echo "    Optimizer API: starting on $OPTIMIZER_PORT"; fi
  if port_busy "$SITE_PORT"; then echo "    Optimizer dashboard: already running on $SITE_PORT"; else
    start_bg optimizer-site "$ROOT/site" "$LOG_DIR/optimizer-site.log" npx next dev -p "$SITE_PORT"
    echo "    Optimizer dashboard: starting on $SITE_PORT"; fi
  wait_http "http://localhost:$OPTIMIZER_PORT/api/v1/health" "Optimizer API" 90 && echo "    Optimizer API: healthy"

  # Esone forwards questions to the Optimizer with a service account; create it
  # before the Esone API starts so it is picked up from esone/backend/.env.
  ensure_esone_bot

  say "Starting Esone"
  if port_busy "$ESONE_API_PORT"; then echo "    Esone API: already running on $ESONE_API_PORT"; else
    start_bg esone-api "$ROOT/esone/backend" "$LOG_DIR/esone-api.log" "$PY" -m uvicorn esone_api.main:app --port "$ESONE_API_PORT"
    echo "    Esone API: starting on $ESONE_API_PORT"; fi
  if port_busy "$ESONE_WEB_PORT"; then echo "    Esone frontend: already running on $ESONE_WEB_PORT"; else
    start_bg esone-web "$ROOT/esone/frontend" "$LOG_DIR/esone-web.log" "$PY" -m uvicorn esone_web.main:app --port "$ESONE_WEB_PORT"
    echo "    Esone frontend: starting on $ESONE_WEB_PORT"; fi

  say "Waiting for health checks"
  wait_http "http://localhost:$ESONE_API_PORT/api/v1/health" "Esone API" 60 && echo "    Esone API: healthy"
  wait_http "http://localhost:$ESONE_WEB_PORT/healthz" "Esone frontend" 60 && echo "    Esone frontend: healthy"
  wait_http "http://localhost:$SITE_PORT/" "Optimizer dashboard" 120 && echo "    Optimizer dashboard: ready"

  cat <<EOF

  Everything is up.

    Esone chat            http://localhost:$ESONE_WEB_PORT        (sign in: admin / admin-local-pass unless you changed esone/backend/.env)
    Esone API             http://localhost:$ESONE_API_PORT/api/v1/health
    Optimizer dashboard   http://localhost:$SITE_PORT        (sign in: ADMIN_EMAIL / ADMIN_PASSWORD from .env)
    Optimizer API         http://localhost:$OPTIMIZER_PORT/api/v1/health
    Redis                 localhost:$REDIS_PORT

  Logs:   bash scripts/dev.sh logs
  Stop:   bash scripts/dev.sh stop
EOF
}

cmd_stop() {
  say "Stopping servers"
  kill_port "$SITE_PORT" "Optimizer dashboard"
  kill_port "$ESONE_WEB_PORT" "Esone frontend"
  kill_port "$ESONE_API_PORT" "Esone API"
  kill_port "$OPTIMIZER_PORT" "Optimizer API"
  rm -f "$RUN_DIR"/*.pid
  if [ "${1:-}" = "--with-redis" ]; then
    docker stop "$REDIS_CONTAINER" >/dev/null 2>&1 && echo "    Redis: container stopped" || echo "    Redis: not running"
  else
    echo "    Redis: left running (use 'stop --with-redis' to stop it)"
  fi
}

cmd_status() {
  local url code
  printf '%-22s %-8s %s\n' "SERVICE" "PORT" "STATUS"
  for entry in \
    "Optimizer API|$OPTIMIZER_PORT|http://localhost:$OPTIMIZER_PORT/api/v1/health" \
    "Optimizer dashboard|$SITE_PORT|http://localhost:$SITE_PORT/" \
    "Esone API|$ESONE_API_PORT|http://localhost:$ESONE_API_PORT/api/v1/health" \
    "Esone frontend|$ESONE_WEB_PORT|http://localhost:$ESONE_WEB_PORT/healthz"; do
    IFS='|' read -r name port url <<<"$entry"
    code="$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
    if [ "$code" = "200" ]; then printf '%-22s %-8s %s\n' "$name" "$port" "healthy"
    elif port_busy "$port"; then printf '%-22s %-8s %s\n' "$name" "$port" "port in use, not healthy (HTTP $code)"
    else printf '%-22s %-8s %s\n' "$name" "$port" "stopped"; fi
  done
  if port_busy "$REDIS_PORT"; then printf '%-22s %-8s %s\n' "Redis" "$REDIS_PORT" "listening"
  else printf '%-22s %-8s %s\n' "Redis" "$REDIS_PORT" "stopped"; fi
}

cmd_logs() {
  ls "$LOG_DIR"/*.log >/dev/null 2>&1 || die "no logs yet; run 'start' first"
  tail -n 20 -f "$LOG_DIR"/*.log
}

usage() { sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; }

case "${1:-}" in
  start)   cmd_start ;;
  stop)    cmd_stop "${2:-}" ;;
  restart) cmd_stop "${2:-}"; cmd_start ;;
  status)  cmd_status ;;
  logs)    cmd_logs ;;
  *)       usage; exit 1 ;;
esac
