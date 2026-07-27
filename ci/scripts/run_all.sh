#!/usr/bin/env bash
# Portable wrapper — same canonical orchestrator as run_all.ps1.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec python ci/scripts/run.py "$@"
