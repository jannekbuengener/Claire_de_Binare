#!/bin/bash
#
# Claire de Binare - LR-040 Runtime Environment Precheck
#
# Fail-closed guard called by soak_monitor.sh before any run artifacts
# are created or Docker commands are issued.
#
# Exit 0 = environment OK, soak_monitor.sh may proceed
# Exit 1 = environment NOT OK (clear error printed to stderr)
#
# Runtime family policy:
#   ALLOWED:     native Linux, WSL2 Linux userland
#   NOT ALLOWED: native Windows, PowerShell, Git Bash, MSYS, MINGW, Cygwin
#
# ARTIFACT_ROOT env var is inherited from the caller (soak_monitor.sh).

set -euo pipefail

_PRECHECK_FAIL=0
_ARTIFACT_ROOT="${ARTIFACT_ROOT:-artifacts}"

# ---------------------------------------------------------------------------
# 1. Runtime family
# ---------------------------------------------------------------------------
_UNAME_S=$(uname -s 2>/dev/null || echo "unknown")

case "$_UNAME_S" in
  Linux*)
    # Native Linux or WSL2 Linux userland — both allowed.
    ;;
  MINGW*|MSYS*)
    echo "ERROR [LR-040 precheck]: Unsupported runtime: Git Bash / MSYS / MINGW ('$_UNAME_S')." >&2
    echo "  Run soak_monitor.sh in a native Linux shell or WSL2 Linux userland." >&2
    _PRECHECK_FAIL=1
    ;;
  CYGWIN*)
    echo "ERROR [LR-040 precheck]: Unsupported runtime: Cygwin ('$_UNAME_S')." >&2
    echo "  Run soak_monitor.sh in a native Linux shell or WSL2 Linux userland." >&2
    _PRECHECK_FAIL=1
    ;;
  *)
    echo "ERROR [LR-040 precheck]: Unrecognized runtime family ('$_UNAME_S')." >&2
    echo "  Supported: native Linux or WSL2 Linux userland." >&2
    _PRECHECK_FAIL=1
    ;;
esac

# ---------------------------------------------------------------------------
# 2. Required tooling
# ---------------------------------------------------------------------------

# docker (soak_monitor.sh uses: docker ps, docker stats, docker logs,
#         docker exec, docker inspect, docker system df)
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR [LR-040 precheck]: 'docker' not found in PATH." >&2
  _PRECHECK_FAIL=1
fi

# GNU date: soak_monitor.sh uses `date -u -d` (GNU-only flag) to derive
# the run-start epoch from the artifact directory name.
if ! date -u -d "2000-01-01 00:00:00" +%s >/dev/null 2>&1; then
  echo "ERROR [LR-040 precheck]: GNU date with -d flag required but not available." >&2
  echo "  soak_monitor.sh requires GNU coreutils date (standard on Linux/WSL2)." >&2
  _PRECHECK_FAIL=1
fi

# ---------------------------------------------------------------------------
# 3. Artifact root writability
# ---------------------------------------------------------------------------
if ! mkdir -p "$_ARTIFACT_ROOT" 2>/dev/null; then
  echo "ERROR [LR-040 precheck]: Cannot create ARTIFACT_ROOT '$_ARTIFACT_ROOT'." >&2
  _PRECHECK_FAIL=1
else
  _TEST_FILE="$_ARTIFACT_ROOT/.precheck_write_test_$$"
  if ! touch "$_TEST_FILE" 2>/dev/null; then
    echo "ERROR [LR-040 precheck]: ARTIFACT_ROOT '$_ARTIFACT_ROOT' is not writable." >&2
    _PRECHECK_FAIL=1
  else
    rm -f "$_TEST_FILE"
  fi
fi

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
if [ "$_PRECHECK_FAIL" -ne 0 ]; then
  echo "ERROR [LR-040 precheck]: Runtime environment check FAILED — aborting before run starts." >&2
  exit 1
fi

echo "INFO [LR-040 precheck]: Runtime environment OK ($_UNAME_S, docker available, artifact root writable)."
exit 0
