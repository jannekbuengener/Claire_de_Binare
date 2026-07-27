#!/usr/bin/env bash
# Cleanup only cdb_ci_<run_id> compose projects via canonical orchestrator.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <run_id>" >&2
  exit 2
fi
exec python ci/scripts/run.py --cleanup "$1"
