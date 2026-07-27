#!/usr/bin/env bash
# Unix front door for the trusted local CI status publisher.
# Token from GITHUB_TOKEN / GH_TOKEN / gh auth only — never echoed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

COMMAND="${1:-}"
shift || true

if [[ -z "$COMMAND" ]]; then
  echo "Usage: $0 <validate|publish|inspect|dry-run> [--evidence-dir DIR] ..." >&2
  exit 2
fi

exec "$PYTHON" -m ci.publisher "$COMMAND" "$@"
