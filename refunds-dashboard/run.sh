#!/usr/bin/env bash
# One command to run the dashboard as a single process: install both toolchains,
# build the React client, then serve it (and the API) from Express.
#
# This is the entrypoint the POC platform uses. For frontend work use
# `npm run dev` instead, which runs the API and the Vite dev server separately.
set -euo pipefail
cd "$(dirname "$0")"

npm install --silent --prefix server
npm install --silent --prefix client
node scripts/init-env.js

# Empty when standalone: the client then builds for the root of its own origin.
export PLATFORM_BASE_PATH="${PLATFORM_BASE_PATH:-}"
(cd client && npm run build --silent)

export SERVE_CLIENT=true
export PORT="${PORT:-4000}"
echo "Refunds dashboard: http://localhost:${PORT}${PLATFORM_BASE_PATH}"
exec npm start --prefix server
