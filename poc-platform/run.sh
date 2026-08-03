#!/usr/bin/env bash
# Start the platform gateway (console + API + reverse proxy).
# Prototypes are started from the console, not here.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

PORT="${PORT:-8080}"
echo "Platform console: http://localhost:${PORT}"
exec ./.venv/bin/uvicorn platform_core.main:app --host 0.0.0.0 --port "${PORT}"
