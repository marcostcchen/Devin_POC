#!/usr/bin/env bash
# One command to run the panel: install both toolchains, build the React app,
# then serve it (and the API) from uvicorn.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

(cd web && npm install --silent && npm run build --silent)

exec ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
