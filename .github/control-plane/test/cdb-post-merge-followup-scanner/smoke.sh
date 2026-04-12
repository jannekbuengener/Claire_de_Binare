#!/usr/bin/env bash
# Smoke test for unit: cdb-post-merge-followup-scanner
# Thin wrapper — delegates all checks to the central validator.
# Usage: bash .github/control-plane/test/cdb-post-merge-followup-scanner/smoke.sh

set -euo pipefail

UNIT_ID="cdb-post-merge-followup-scanner"
REPO_ROOT="$(git rev-parse --show-toplevel)"
VALIDATOR="$REPO_ROOT/.github/scripts/control_plane_validate.py"

echo "=== Smoke: $UNIT_ID ==="
python3 "$VALIDATOR" --repo-root "$REPO_ROOT" --unit-id "$UNIT_ID"
echo "=== PASS: $UNIT_ID ==="
