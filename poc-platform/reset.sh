#!/usr/bin/env bash
# Delete every prototype's local state (databases and logs) so the next start
# re-seeds from scratch. Nothing here is authoritative - see docs/poc-environment.md.
set -euo pipefail
cd "$(dirname "$0")"

if [ -d .data ]; then
  rm -rf .data
  echo "Removed poc-platform/.data (databases + logs)"
else
  echo "Nothing to reset: poc-platform/.data does not exist"
fi
