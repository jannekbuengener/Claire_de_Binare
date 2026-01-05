#!/usr/bin/env bash
set -euo pipefail

# CI gate to enforce allowed write zones.
# Allowed (per policy): CDB_KNOWLEDGE_HUB.md, .cdb_agent_workspace/**
# Everything else is protected and must not be mutated by agents.

BASE_REF="${BASE_REF:-origin/main}"
HEAD_REF="${HEAD_REF:-HEAD}"

if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  echo "Base ref '$BASE_REF' not found; provide BASE_REF ref for diff." >&2
  exit 2
fi

changed_files="$(git diff --name-only "$BASE_REF" "$HEAD_REF" | sed '/^$/d')"

if [ -z "$changed_files" ]; then
  echo "No changes detected between $BASE_REF and $HEAD_REF."
  exit 0
fi

violations=()
for path in $changed_files; do
  case "$path" in
    CDB_KNOWLEDGE_HUB.md|.cdb_agent_workspace/*)
      ;; # allowed
    *)
      violations+=("$path")
      ;;
  esac
done

if [ "${#violations[@]}" -gt 0 ]; then
  echo "Write-zone validation failed. Protected files touched:"
  printf '  - %s\n' "${violations[@]}"
  echo "Allowed zones: CDB_KNOWLEDGE_HUB.md, .cdb_agent_workspace/*"
  exit 1
fi

echo "Write-zone validation passed."
