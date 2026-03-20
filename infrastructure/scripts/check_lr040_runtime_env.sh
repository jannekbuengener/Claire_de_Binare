#!/usr/bin/env bash
#
# Validate the deterministic runtime environment required for an LR-040 72h soak.
# Supported execution path: Linux userland only (native Linux or WSL2 shell).
# Unsupported: native Windows PowerShell/CMD and ad-hoc GNU emulation layers.
#

set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ "$(uname -s)" != "Linux" ]]; then
  fail "LR-040 requires a Linux userland (native Linux or WSL2). Native Windows shells are unsupported."
fi

required_commands=(
  bash
  awk
  curl
  date
  df
  docker
  git
  grep
  head
  ls
  mkdir
  pgrep
  sed
  crontab
)

for cmd in "${required_commands[@]}"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    fail "required command missing: $cmd"
  fi
done

if ! date -u -d "+1 hour" >/dev/null 2>&1; then
  fail "GNU date with -d support is required"
fi

if ! docker version >/dev/null 2>&1; then
  fail "docker CLI/daemon is not reachable from this shell"
fi

if ! pgrep -x cron >/dev/null 2>&1 && ! pgrep -x crond >/dev/null 2>&1; then
  fail "cron daemon is not running; start cron/crond before the LR-040 soak"
fi

required_paths=(
  "$REPO_ROOT/infrastructure/scripts/soak_monitor.sh"
  "$REPO_ROOT/infrastructure/scripts/lr040_soak_gate_eval.py"
  "$REPO_ROOT/infrastructure/scripts/materialize_lr040_verdict_anchor.py"
  "$REPO_ROOT/docs/operations/72H_SOAK_TEST_RUNBOOK.md"
)

for path in "${required_paths[@]}"; do
  if [[ ! -e "$path" ]]; then
    fail "required repo path missing: $path"
  fi
done

echo "LR-040 runtime environment precheck PASS"
echo "repo_root=$REPO_ROOT"
