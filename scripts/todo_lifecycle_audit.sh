#!/usr/bin/env bash
# todo_lifecycle_audit.sh
#
# Repeatable TODO/Placeholder lifecycle audit for active repo paths.
# Policy: knowledge/governance/CDB_REPO_GUIDELINES.md § 6 (Open Marker Lifecycle)
#
# Usage:
#   bash scripts/todo_lifecycle_audit.sh          # summary only
#   bash scripts/todo_lifecycle_audit.sh --verbose # show all hits
#
# Exit codes:
#   0 = no violations found
#   1 = violations found

set -euo pipefail

VERBOSE=false
[[ "${1:-}" == "--verbose" ]] && VERBOSE=true

# Active paths — archive trees are excluded intentionally
ACTIVE_PATHS=(
  core/ services/ infrastructure/ scripts/ tests/
  knowledge/ docs/ agents/ .github/
)

# Exclude archive snapshots, generated/binary dirs, and this script itself
EXCLUDE_DIRS=(
  "knowledge/archive"
  "docs/archive"
  "docs/archive/docs_hub_snapshot"
  ".git"
  "__pycache__"
  "node_modules"
  ".venv"
  "venv"
)

# Files excluded from specific rules (policy definitions, orchestrator outputs, etc.)
EXCLUDE_POLICY_FILES="CDB_REPO_GUIDELINES.md|todo_lifecycle_audit.sh|\.orchestrator_|TODO_LIFECYCLE_INVENTORY"

build_exclude_args() {
  local args=()
  for d in "${EXCLUDE_DIRS[@]}"; do
    args+=(--exclude-dir="$d")
  done
  echo "${args[@]}"
}

EXCLUDE_ARGS=$(build_exclude_args)

VIOLATIONS=0
WARNINGS=0

echo "=== CDB TODO/Placeholder Lifecycle Audit ==="
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Policy: knowledge/governance/CDB_REPO_GUIDELINES.md § 6"
echo ""

# ─────────────────────────────────────────────────────────────────
# Rule 1: Unreferenced TODO/FIXME/XXX in source code and scripts
# Allowed form: TODO(#<issue>): ...
# ─────────────────────────────────────────────────────────────────
echo "--- Rule 1: Unreferenced TODO/FIXME in code/scripts ---"

PATTERN_UNREF='\b(TODO|FIXME)\b(?!\s*\(#[0-9]+\))'

# Match TODO/FIXME used as directive at start of a comment: "# TODO ..." or "// TODO ..."
# This avoids prose mentions like "# Check if services have proper TODO comments"
# Use grep with Perl regex for precise matching; fall back to basic grep
if grep -P "" /dev/null 2>/dev/null; then
  GREP_UNREF=$(eval grep -rnP "'[#/]+\s+(TODO|FIXME)\b(?!\(#[0-9]+\))'" \
    --include="*.py" --include="*.sh" --include="*.ps1" --include="*.ts" \
    ${EXCLUDE_ARGS} \
    "${ACTIVE_PATHS[@]}" 2>/dev/null \
    | grep -vE "${EXCLUDE_POLICY_FILES}" \
    || true)
else
  GREP_UNREF=$(eval grep -rn "'#\s*TODO\|#\s*FIXME'" \
    --include="*.py" --include="*.sh" --include="*.ps1" --include="*.ts" \
    ${EXCLUDE_ARGS} \
    "${ACTIVE_PATHS[@]}" 2>/dev/null \
    | grep -v "TODO(#" | grep -v "FIXME(#" \
    | grep -vE "${EXCLUDE_POLICY_FILES}" \
    || true)
fi

if [[ -n "$GREP_UNREF" ]]; then
  COUNT=$(echo "$GREP_UNREF" | wc -l)
  echo "VIOLATION: $COUNT unreferenced TODO/FIXME in code/scripts"
  VIOLATIONS=$((VIOLATIONS + COUNT))
  if $VERBOSE; then echo "$GREP_UNREF"; fi
else
  echo "OK"
fi

echo ""

# ─────────────────────────────────────────────────────────────────
# Rule 2: Bare `Issue #TBD` or `#TBD` references in active paths
# ─────────────────────────────────────────────────────────────────
echo "--- Rule 2: Issue #TBD / bare #TBD references ---"

GREP_TBD=$(eval grep -rn "'Issue #TBD\\|#TBD'" \
  --include="*.md" --include="*.yaml" --include="*.yml" --include="*.py" \
  ${EXCLUDE_ARGS} \
  "${ACTIVE_PATHS[@]}" 2>/dev/null \
  | grep -v "knowledge/archive\|docs/archive\|knowledge/logs/sessions\|knowledge/reviews\|knowledge/roadmap\|knowledge/analysis\|knowledge/decisions" \
  | grep -vE "${EXCLUDE_POLICY_FILES}" \
  || true)

if [[ -n "$GREP_TBD" ]]; then
  COUNT=$(echo "$GREP_TBD" | wc -l)
  echo "VIOLATION: $COUNT bare #TBD issue references"
  VIOLATIONS=$((VIOLATIONS + COUNT))
  if $VERBOSE; then echo "$GREP_TBD"; fi
else
  echo "OK"
fi

echo ""

# ─────────────────────────────────────────────────────────────────
# Rule 3: Unreferenced TODO in active docs/runbooks/dashboards
# Knowledge, docs paths: bare TODO not inside allowed archive trees
# ─────────────────────────────────────────────────────────────────
echo "--- Rule 3: Bare TODO in active docs/dashboards (excl. archive, sessions, old roadmaps) ---"

GREP_DOC_TODO=$(eval grep -rn "'\bTODO\b'" \
  --include="*.md" --include="*.json" --include="*.yaml" --include="*.yml" \
  ${EXCLUDE_ARGS} \
  "${ACTIVE_PATHS[@]}" 2>/dev/null \
  | grep -v "TODO(#\|PLACEHOLDER" \
  | grep -v "knowledge/archive\|docs/archive\|knowledge/logs/sessions\|knowledge/reviews\|knowledge/roadmap\|knowledge/analysis\|knowledge/operations\|knowledge/content\|knowledge/decisions\|knowledge/security\|knowledge/ISSUE\|docs/governance\|docs/contracts" \
  | grep -vE "${EXCLUDE_POLICY_FILES}" \
  || true)

if [[ -n "$GREP_DOC_TODO" ]]; then
  COUNT=$(echo "$GREP_DOC_TODO" | wc -l)
  echo "WARNING: $COUNT bare TODO in active docs (may need review)"
  WARNINGS=$((WARNINGS + COUNT))
  if $VERBOSE; then echo "$GREP_DOC_TODO"; fi
else
  echo "OK"
fi

echo ""

# ─────────────────────────────────────────────────────────────────
# Rule 4: Skipped/placeholder tests without Issue reference
# ─────────────────────────────────────────────────────────────────
echo "--- Rule 4: Placeholder tests without issue reference ---"

GREP_SKIP=$(eval grep -rn "'@pytest.mark.skip\b'" \
  --include="*.py" \
  ${EXCLUDE_ARGS} \
  "${ACTIVE_PATHS[@]}" 2>/dev/null \
  | grep -iv "Issue #\|#[0-9]\+\|reason=.*[Ii]ssue" \
  || true)

if [[ -n "$GREP_SKIP" ]]; then
  COUNT=$(echo "$GREP_SKIP" | wc -l)
  echo "VIOLATION: $COUNT skipped tests without issue reference"
  VIOLATIONS=$((VIOLATIONS + COUNT))
  if $VERBOSE; then echo "$GREP_SKIP"; fi
else
  echo "OK"
fi

echo ""

# ─────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────
echo "=== Summary ==="
echo "Violations: $VIOLATIONS"
echo "Warnings:   $WARNINGS"
echo ""

if [[ $VIOLATIONS -gt 0 ]]; then
  echo "FAIL — $VIOLATIONS policy violation(s) found."
  echo "Normalize to TODO(#<issue>):, PLACEHOLDER(#<issue>):, or remove the marker."
  exit 1
elif [[ $WARNINGS -gt 0 ]]; then
  echo "WARN — $WARNINGS warning(s) found. Review and normalize if in active operator paths."
  exit 0
else
  echo "PASS — no TODO lifecycle violations detected."
  exit 0
fi
