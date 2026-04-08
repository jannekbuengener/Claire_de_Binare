#!/usr/bin/env bash
# pre_close_sweep.sh — Pre-close guard for canonical versioned artifact trees.
#
# Checks whether untracked, non-ignored files exist in the canonical session
# artifact paths before a session is closed. If any are found, it prints them
# and exits non-zero so the operator can commit or explicitly ignore them.
#
# Sweep scope is derived from the #1450 batch (commit 39c5d864):
#   knowledge/logs/sessions/   — session evidence logs (20 of 40 files)
#   docs/runbooks/evidence/    — runbook drill evidence (3 files)
#   reports/                   — reports and canary output (2 files)
#   docs/operations/           — operational verification docs (1 file)
#
# This script does NOT introduce any .gitignore entries and does NOT flag
# files that are already covered by existing ignore rules.
#
# Usage:
#   bash scripts/pre_close_sweep.sh
#   make pre-close

set -euo pipefail

SWEEP_PATHS=(
  "knowledge/logs/sessions"
  "docs/runbooks/evidence"
  "reports"
  "docs/operations"
)

untracked=()

for path in "${SWEEP_PATHS[@]}"; do
  if [ -d "$path" ]; then
    while IFS= read -r file; do
      [[ -n "$file" ]] && untracked+=("$file")
    done < <(git ls-files --others --exclude-standard -- "$path")
  fi
done

if [ ${#untracked[@]} -gt 0 ]; then
  echo "ERROR: pre-close sweep found untracked files in canonical artifact paths."
  echo ""
  echo "Untracked files:"
  for f in "${untracked[@]}"; do
    echo "  $f"
  done
  echo ""
  echo "Action required before session close:"
  echo "  - Commit these files if they belong in the repo, OR"
  echo "  - Add them to .gitignore if they are local-only artifacts."
  echo "  Do not leave them silently untracked."
  exit 1
fi

echo "pre-close sweep: OK — no untracked files in canonical artifact paths."
exit 0
