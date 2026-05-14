#!/bin/bash
#
# Claire de Binare - Soak Test Monitoring Script
# Issue #428: Zero Restart Policy automation
# Issue #1278: Explicit validation mode
#
# Usage: Run hourly via cron during 72h Soak Test
#   0 * * * * /path/to/scripts/soak_monitor.sh
#
# Run intent (SOAK_RUN_INTENT env var):
#   lr040      (default) — canonical 72h soak for LR-040 evidence
#   lr030                — local raw/operator continuity path for LR-030 reruns
#   validation           — short verification run for monitor mechanics
#
# Example:
#   SOAK_RUN_INTENT=validation ./infrastructure/scripts/soak_monitor.sh
#
# Requirements:
# - Docker running with CDB stack
# - artifacts/ directory writable
# - Write permissions to artifacts directory

set -euo pipefail

# Configuration
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
ARTIFACT_ROOT="${ARTIFACT_ROOT:-artifacts}"

# ---------------------------------------------------------------------------
# LR-040 Runtime Precheck (fail-closed)
# Verifies supported runtime family (Linux/WSL2 only), required tooling,
# and artifact-root writability before any run artifacts are created.
# Exit 1 from the precheck aborts soak_monitor.sh immediately.
# ---------------------------------------------------------------------------
_LR040_PRECHECK="$(dirname "${BASH_SOURCE[0]}")/check_lr040_runtime_env.sh"
if [ -x "$_LR040_PRECHECK" ]; then
  "$_LR040_PRECHECK"
else
  echo "ERROR: LR-040 runtime precheck not found or not executable: $_LR040_PRECHECK" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Run intent: lr040 (default), lr030, or validation
#
# lr040      — canonical 72h soak run for LR-040 evidence
# lr030      — local raw/operator continuity support for LR-030 reruns
# validation — short verification run to test monitor mechanics
#
# Each intent uses its own artifact prefix and active-run pointer file so
# lr030/validation runs can never be confused with canonical LR-040 evidence.
# The LR-040 gate evaluator refuses to produce a PASS verdict for non-lr040 runs.
# ---------------------------------------------------------------------------
SOAK_RUN_INTENT="${SOAK_RUN_INTENT:-lr040}"
case "$SOAK_RUN_INTENT" in
  lr040|lr030|validation) ;;
  *)
    echo "ERROR: SOAK_RUN_INTENT must be 'lr040', 'lr030', or 'validation', got '$SOAK_RUN_INTENT'" >&2
    exit 1
    ;;
esac

case "$SOAK_RUN_INTENT" in
  lr040)
    ARTIFACT_PREFIX="soak_test"
    ;;
  lr030)
    ARTIFACT_PREFIX="soak_lr030"
    ;;
  validation)
    ARTIFACT_PREFIX="soak_validation"
    ;;
esac

# Intent-specific pointer file (Issue #1278): lr040 and validation runs
# each have their own pointer so they never cross-contaminate.
ACTIVE_RUN_FILE="$ARTIFACT_ROOT/soak_active_run_path_${SOAK_RUN_INTENT}.txt"

# Ensure script continues even if individual commands fail
set +e

# ---------------------------------------------------------------------------
# flock portability: Git Bash on Windows does not ship flock.
# _flock_or_direct wraps flock with a fallback that runs the subshell body
# directly when flock is unavailable. On solo-maintainer setups (single cron
# instance) the lock is a best-effort dedup guard, not a correctness
# requirement — missing it is safe. Issue #1420.
# ---------------------------------------------------------------------------
_HAS_FLOCK=0
command -v flock >/dev/null 2>&1 && _HAS_FLOCK=1

_write_active_run_path() {
  local artifact_path="$1"
  mkdir -p "$ARTIFACT_ROOT"
  printf '%s\n' "$artifact_path" > "$ACTIVE_RUN_FILE"
  # Sync generic pointer for lr040 runs (Issue #1283).
  # Validation runs must never touch soak_active_run_path.txt.
  if [ "$SOAK_RUN_INTENT" = "lr040" ]; then
    printf '%s\n' "$artifact_path" > "$ARTIFACT_ROOT/soak_active_run_path.txt"
  fi
}

_validate_existing_run_intent() {
  local artifact_path="$1"
  local run_intent_file="$artifact_path/run_intent.txt"
  local existing_intent=""

  if [ ! -f "$run_intent_file" ]; then
    return 0
  fi

  existing_intent=$(head -n 1 "$run_intent_file" | tr -d '[:space:]')
  if [ -z "$existing_intent" ] || [ "$existing_intent" = "$SOAK_RUN_INTENT" ]; then
    return 0
  fi

  echo "ERROR: Refusing to reuse artifact dir '$artifact_path': run_intent.txt='$existing_intent' expected '$SOAK_RUN_INTENT'" >&2
  return 1
}

_find_latest_artifact_dir() {
  ls -1d "$ARTIFACT_ROOT"/${ARTIFACT_PREFIX}_* 2>/dev/null | sort | tail -1
}

_resolve_artifact_path() {
  local artifact_path=""
  mkdir -p "$ARTIFACT_ROOT"

  if [ -f "$ACTIVE_RUN_FILE" ]; then
    artifact_path=$(head -n 1 "$ACTIVE_RUN_FILE")
    if [ -n "$artifact_path" ] && [ -d "$artifact_path" ]; then
      # Verify the pointer matches the current intent prefix (Issue #1278).
      # Reject cross-intent pointers so lr040 never picks up a validation dir
      # and vice versa.
      _BASENAME=$(basename "$artifact_path")
      if echo "$_BASENAME" | grep -q "^${ARTIFACT_PREFIX}_"; then
        echo "$artifact_path"
        return 0
      fi
      echo "WARNING: Active run pointer '$artifact_path' does not match intent '${SOAK_RUN_INTENT}' (prefix ${ARTIFACT_PREFIX}_*); ignoring" >&2
    else
      echo "WARNING: Active soak run path '$artifact_path' is missing; rebuilding pointer" >&2
    fi
  fi

  artifact_path=$(_find_latest_artifact_dir)
  if [ -n "$artifact_path" ] && [ -d "$artifact_path" ]; then
    echo "INFO: Reusing latest ${ARTIFACT_PREFIX} artifacts directory: $artifact_path" >&2
    echo "$artifact_path"
    return 0
  fi

  echo "WARNING: No ${ARTIFACT_PREFIX} artifacts directory found" >&2
  echo "Expected: artifacts/${ARTIFACT_PREFIX}_YYYYMMDD_HHMMSS/" >&2
  echo "Creating artifacts directory" >&2
  echo "$ARTIFACT_ROOT/${ARTIFACT_PREFIX}_$(date -u +%Y%m%d_%H%M%S)"
}

ARTIFACT_PATH=$(_resolve_artifact_path)
mkdir -p "$ARTIFACT_PATH"

if [ -z "$ARTIFACT_PATH" ] || [ ! -d "$ARTIFACT_PATH" ]; then
  echo "ERROR: artifact directory not available — aborting soak monitor" >&2
  exit 1
fi

if ! _validate_existing_run_intent "$ARTIFACT_PATH"; then
  exit 1
fi
_write_active_run_path "$ARTIFACT_PATH"

# Write run intent marker (Issue #1278). For existing directories, the
# fail-closed check above guarantees the marker already matches the requested
# intent before any pointer is updated.
RUN_INTENT_FILE="$ARTIFACT_PATH/run_intent.txt"
if [ ! -f "$RUN_INTENT_FILE" ]; then
  printf '%s\n' "$SOAK_RUN_INTENT" > "$RUN_INTENT_FILE"
fi

# ---------------------------------------------------------------------------
# Run-start baseline and elapsed-hours checkpoint index (Issue #1271)
#
# Problem with the old approach (HOUR=$(date +%H)):
#   - date +%H has no -u flag → local time, not UTC → off by timezone offset
#   - cycles 0–23 every 24h → duplicate "Hour 00", "Hour 01" labels on day 2
#     and day 3 of a 72-h soak, making the evidence timeline ambiguous
#   - two concurrent cron invocations (e.g. two lr040_soak_monitor containers)
#     each pick a different date +%H value and write back-to-back entries
#
# Fix: derive a monotonically-increasing index from elapsed hours since the
# run started (stored in run_start.txt). Write exactly one log entry per
# checkpoint via an idempotency sentinel (last_checkpoint.txt).
# ---------------------------------------------------------------------------

RUN_START_FILE="$ARTIFACT_PATH/run_start.txt"
if [ ! -f "$RUN_START_FILE" ]; then
  # Preferred source: parse UTC epoch from the artifact directory name.
  # <intent-prefix>_YYYYMMDD_HHMMSS encodes the exact start time set by the operator
  # at soak launch — more accurate than the first cron invocation, which may
  # arrive up to ~60 s late due to scheduling jitter or a delayed manual start.
  _ARTIFACT_NAME=$(basename "$ARTIFACT_PATH")
  _START_TOKENS=$(echo "$_ARTIFACT_NAME" | grep -oE "[0-9]{8}_[0-9]{6}" | head -1)
  _DERIVED_EPOCH=""
  if [ -n "$_START_TOKENS" ]; then
    _D=${_START_TOKENS%_*}   # YYYYMMDD
    _T=${_START_TOKENS#*_}   # HHMMSS
    _FMT="${_D:0:4}-${_D:4:2}-${_D:6:2} ${_T:0:2}:${_T:2:2}:${_T:4:2}"
    # date -u -d requires GNU date (available in the ubuntu:22.04 monitor container)
    _DERIVED_EPOCH=$(date -u -d "$_FMT" +%s 2>/dev/null || true)
  fi
  if [ -n "$_DERIVED_EPOCH" ] && [ "$_DERIVED_EPOCH" -gt 0 ] 2>/dev/null; then
    echo "$_DERIVED_EPOCH" > "$RUN_START_FILE"
    echo "Derived run_start from artifact directory name: $_FMT UTC"
  else
    # Fallback: use current epoch (first monitor invocation).
    # Logs a warning so the discrepancy is visible in the run output.
    date -u +%s > "$RUN_START_FILE"
    echo "WARNING: could not parse run start from directory name '$_ARTIFACT_NAME';" \
         "using first-invocation time as run_start fallback"
  fi
fi
RUN_START_EPOCH=$(cat "$RUN_START_FILE")
NOW_EPOCH=$(date -u +%s)
# Integer division: floor of elapsed whole hours since run start.
ELAPSED_HOURS=$(( (NOW_EPOCH - RUN_START_EPOCH) / 3600 ))

# Idempotency sentinel: the last checkpoint index that was written to
# hourly_checks.log. Prevents duplicate entries when the monitor runs
# more than once in the same clock-hour (parallel cron instances,
# manual re-runs, or container restarts).
LAST_CHECKPOINT_FILE="$ARTIFACT_PATH/last_checkpoint.txt"
LAST_CHECKPOINT=-1
if [ -f "$LAST_CHECKPOINT_FILE" ]; then
  LAST_CHECKPOINT=$(cat "$LAST_CHECKPOINT_FILE")
fi

# ---------------------------------------------------------------------------
# Auto-stop guard: skip all checks after the monitoring window closes.
# Prevents post-window Docker/host restarts from tainting a valid run.
# SOAK_TARGET_HOURS defaults to 72 (LR-040 requirement).
# lr030 and validation runs skip this guard (no fixed target duration here).
# Issue #1419.
# ---------------------------------------------------------------------------
SOAK_TARGET_HOURS_RAW="${SOAK_TARGET_HOURS:-72}"
case "$SOAK_TARGET_HOURS_RAW" in
  ''|*[!0-9]*)
    echo "ERROR: SOAK_TARGET_HOURS must be an integer, got '$SOAK_TARGET_HOURS_RAW'. Falling back to 72." >&2
    SOAK_TARGET_HOURS=72
    ;;
  *)
    SOAK_TARGET_HOURS="$SOAK_TARGET_HOURS_RAW"
    ;;
esac
if [ "$SOAK_RUN_INTENT" = "lr040" ] && [ "$ELAPSED_HOURS" -ge "$SOAK_TARGET_HOURS" ]; then
  _guard_write() {
    _CK=-1
    [ -f "$LAST_CHECKPOINT_FILE" ] && _CK=$(cat "$LAST_CHECKPOINT_FILE")
    if [ "$_CK" -ge "$SOAK_TARGET_HOURS" ]; then
      : # monitoring window completion already recorded; do not mutate artifacts
    elif [ "$ELAPSED_HOURS" -le "$_CK" ]; then
      : # already written for this or a later hour within the window
    else
      echo "$TIMESTAMP - Hour $ELAPSED_HOURS: Monitoring window complete ($SOAK_TARGET_HOURS h reached)" \
        >> "$ARTIFACT_PATH/hourly_checks.log"
      # Cap the checkpoint at SOAK_TARGET_HOURS to act as a completion sentinel
      echo "$SOAK_TARGET_HOURS" > "$LAST_CHECKPOINT_FILE"
    fi
  }
  if [ "$_HAS_FLOCK" -eq 1 ]; then
    ( flock -x -w 30 200 || exit 0; _guard_write ) 200>"$ARTIFACT_PATH/checkpoint.lock"
  else
    _guard_write
  fi
  echo "LR-040 monitoring window complete (${ELAPSED_HOURS}h >= ${SOAK_TARGET_HOURS}h). Skipping checks."
  echo "Remove cron to stop invocations: crontab -l | grep -v soak_monitor | crontab -"
  exit 0
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# ZRP-relevant SUT services (shared between Check 1 and Check 2).
# BLUE core + data layer + RED signal services.
# Observability, exporter, and infra sidecars are excluded —
# their restarts do not violate the Zero Restart Policy gate.
# Source of truth: compose.blue.yml + compose.red.yml (ws + signal only).
# ---------------------------------------------------------------------------
SUT_SERVICES="cdb_postgres cdb_redis cdb_market cdb_candles cdb_regime cdb_allocation cdb_risk cdb_execution cdb_db_writer cdb_paper_runner cdb_ws cdb_signal"
EXPECTED_SERVICES=12

case "$SOAK_RUN_INTENT" in
  validation)
    _RUN_LABEL="VALIDATION Run"
    ;;
  lr030)
    _RUN_LABEL="LR-030 Shadow/Soak Run"
    ;;
  *)
    _RUN_LABEL="LR-040 Soak Test"
    ;;
esac
echo "========================================="
echo "$_RUN_LABEL Monitoring - Checkpoint $ELAPSED_HOURS (elapsed hours)"
echo "Run Intent: $SOAK_RUN_INTENT"
echo "$TIMESTAMP"
echo "Artifact Path: $ARTIFACT_PATH"
echo "========================================="

# =============================================================================
# CRITICAL CHECK: Container Restarts (Every Hour)
# =============================================================================

echo -e "\n${YELLOW}[CHECK 1/5]${NC} Container Restart Detection..."

# ---------------------------------------------------------------------------
# Helper: parse Docker uptime status string to approximate seconds.
# Handles all known Docker status variants including:
#   "Up 13 seconds", "Up 2 minutes", "Up About a minute",
#   "Up Less than a second", "Up 2 minutes (healthy)",
#   "Up 2 minutes (health: starting)"
# Returns 0 for unknown formats (conservative: treats as fresh start).
# ---------------------------------------------------------------------------
_parse_uptime_seconds() {
  local raw="$1"
  local status
  # Strip health suffixes like "(healthy)" or "(health: starting)"
  status=$(echo "$raw" | sed 's/([^)]*)//g' | xargs)

  if echo "$status" | grep -qiE "less than a second"; then
    echo 0
  elif echo "$status" | grep -qiE "about a minute"; then
    echo 60
  elif echo "$status" | grep -qiE "minute"; then
    local n; n=$(echo "$status" | grep -oE "[0-9]+" | head -1); echo $(( ${n:-1} * 60 ))
  elif echo "$status" | grep -qiE "second"; then
    local n; n=$(echo "$status" | grep -oE "[0-9]+" | head -1); echo "${n:-0}"
  else
    echo 0
  fi
}

RESTART_DETECTED=0
RESTART_COUNT=0
TOTAL_CONTAINERS=0
UPTIME_MIN=999999
UPTIME_MAX=0

# Snapshot all container statuses once (avoids N docker calls).
_ALL_STATUS=$(docker ps --filter "name=cdb_" --format "{{.Names}} {{.Status}}")

# Check SUT services for restarts (ZRP-relevant only).
# Non-SUT containers (observability, exporters, infra) are checked separately
# below and logged as INFO without triggering a FAIL verdict.
for _svc in $SUT_SERVICES; do
  _SVC_LINE=$(echo "$_ALL_STATUS" | grep "^${_svc} " || true)
  [ -z "$_SVC_LINE" ] && continue
  TOTAL_CONTAINERS=$((TOTAL_CONTAINERS + 1))
  # Use cut to get the full status string (awk '{print $2,$3,$4}' would truncate
  # multi-word statuses like "Up About a minute (health: starting)")
  _SVC_STATUS=$(echo "$_SVC_LINE" | cut -d' ' -f2-)

  # Case-insensitive match to handle "About a minute", "Less than a second", etc.
  if echo "$_SVC_STATUS" | grep -qiE " second| minute"; then
    UPTIME_S=$(_parse_uptime_seconds "$_SVC_STATUS")
    [ "$UPTIME_S" -lt "$UPTIME_MIN" ] && UPTIME_MIN=$UPTIME_S
    [ "$UPTIME_S" -gt "$UPTIME_MAX" ] && UPTIME_MAX=$UPTIME_S

    echo -e "${RED}ALERT: SUT container restart detected!${NC}"
    echo "  Container: $_svc"
    echo "  Status: $_SVC_STATUS"
    echo "  Detected At: $TIMESTAMP"

    echo "$TIMESTAMP - RESTART DETECTED: $_svc ($_SVC_STATUS)" >> "$ARTIFACT_PATH/restart_alerts.log"
    RESTART_COUNT=$((RESTART_COUNT + 1))
    RESTART_DETECTED=1
  fi
done

# Log non-SUT restarts as informational (no FAIL trigger).
while IFS= read -r line; do
  [ -z "$line" ] && continue
  _NS_NAME=$(echo "$line" | awk '{print $1}')
  _NS_STATUS=$(echo "$line" | cut -d' ' -f2-)
  echo "$SUT_SERVICES" | grep -qw "$_NS_NAME" && continue
  if echo "$_NS_STATUS" | grep -qiE " second| minute"; then
    echo -e "${YELLOW}INFO: Non-SUT container restart (not ZRP-relevant): $_NS_NAME${NC}"
    echo "$TIMESTAMP - INFO: Non-SUT restart (ignored for ZRP): $_NS_NAME ($_NS_STATUS)" >> "$ARTIFACT_PATH/restart_alerts.log"
  fi
done <<< "$_ALL_STATUS"

# Check the soak monitor container itself separately.
# lr040_soak_monitor is intentionally NOT named cdb_* to avoid matching the
# SUT filter above. If the monitor itself was restarted, that is the strongest
# signal for an environment-level (Docker-daemon or host) restart.
MONITOR_FRESH=0
MONITOR_STATUS=$(docker ps --filter "name=lr040_soak_monitor" --format "{{.Status}}" 2>/dev/null | head -1)
if [ -n "$MONITOR_STATUS" ] && echo "$MONITOR_STATUS" | grep -qiE " second| minute"; then
  MONITOR_FRESH=1
fi

if [ "$RESTART_DETECTED" -eq 1 ]; then
  UPTIME_SPREAD=$((UPTIME_MAX - UPTIME_MIN))

  # ---------------------------------------------------------------------------
  # HEURISTIC: environment_interruption classification (Issue #1270)
  #
  # Classify as environment_interruption only when BOTH conditions hold:
  #
  # 1. FRACTION (>=50% of SUT services restarted):
  #    A single SUT defect rarely affects half the stack. 50% is deliberately
  #    conservative — even 6/12 simultaneous SUT failures would constitute an
  #    environment-level problem, not an isolated service defect.
  #
  # 2. TIGHT_SPREAD (max_uptime - min_uptime <= 30 s) OR MONITOR_SELF:
  #    a) A Docker-daemon or host restart brings all containers back within
  #       seconds of each other. A real cascading SUT failure takes minutes.
  #       Threshold 30s covers "Up X seconds" and the "Up About a minute"
  #       (parsed as 60s) edge case when containers start at slightly different
  #       times but still within the same daemon restart window.
  #    b) If lr040_soak_monitor itself shows fresh uptime, the monitor was
  #       not active during the event — the strongest possible signal for an
  #       external (non-SUT) restart.
  #
  # If neither sub-condition holds, classify as sut_restart (fail-closed).
  #
  # operator_abort: reserved cause class for future use (no active code here).
  # ---------------------------------------------------------------------------
  FRACTION_MET=0
  TIGHT_SPREAD_MET=0
  [ "$TOTAL_CONTAINERS" -gt 0 ] && [ "$((RESTART_COUNT * 2))" -ge "$TOTAL_CONTAINERS" ] && FRACTION_MET=1
  [ "$RESTART_COUNT" -gt 0 ] && [ "$UPTIME_SPREAD" -le 30 ] && TIGHT_SPREAD_MET=1

  if [ "$FRACTION_MET" -eq 1 ] && ( [ "$TIGHT_SPREAD_MET" -eq 1 ] || [ "$MONITOR_FRESH" -eq 1 ] ); then
    # environment_interruption: remove any pre-existing FAILED marker so only
    # one verdict marker exists at a time (mutual exclusion).
    rm -f "$ARTIFACT_PATH/soak_test_FAILED.txt"
    echo "$TIMESTAMP - ENVIRONMENT_INTERRUPTION: ${RESTART_COUNT}/${TOTAL_CONTAINERS} SUT services restarted, spread=${UPTIME_SPREAD}s, monitor_fresh=${MONITOR_FRESH}" \
      >> "$ARTIFACT_PATH/restart_alerts.log"
    echo "$TIMESTAMP - INCONCLUSIVE: Environment interruption detected (cause=environment_interruption, sut_services=${RESTART_COUNT}/${TOTAL_CONTAINERS}, uptime_spread_s=${UPTIME_SPREAD}, monitor_container_fresh=${MONITOR_FRESH})" \
      > "$ARTIFACT_PATH/soak_test_INCONCLUSIVE.txt"
    echo -e "${YELLOW}===== INCONCLUSIVE: ENVIRONMENT INTERRUPTION =====${NC}"
    echo "Reason: Bulk restart consistent with Docker-daemon or host restart"
    echo "sut_services=${RESTART_COUNT}/${TOTAL_CONTAINERS}, spread=${UPTIME_SPREAD}s, monitor_fresh=${MONITOR_FRESH}"
  else
    # sut_restart: remove any pre-existing INCONCLUSIVE marker so only one
    # verdict marker exists at a time (mutual exclusion).
    rm -f "$ARTIFACT_PATH/soak_test_INCONCLUSIVE.txt"
    echo "$TIMESTAMP - SUT_RESTART: ${RESTART_COUNT}/${TOTAL_CONTAINERS} SUT services restarted (cause=sut_restart, spread=${UPTIME_SPREAD}s)" \
      >> "$ARTIFACT_PATH/restart_alerts.log"
    echo "$TIMESTAMP - ABORT: SUT service restart detected (cause=sut_restart, sut_services=${RESTART_COUNT}/${TOTAL_CONTAINERS})" \
      > "$ARTIFACT_PATH/soak_test_FAILED.txt"
    echo -e "${RED}===== ABORT: SOAK TEST FAILED =====${NC}"
    echo "Reason: SUT service restart detected (Zero Restart Policy violated)"
    echo "Time: $TIMESTAMP"
  fi

  # Capture failure evidence regardless of cause class.
  echo "Capturing failure evidence..."
  docker ps --all > "$ARTIFACT_PATH/failure_container_status.txt"
  docker stats --no-stream > "$ARTIFACT_PATH/failure_resources.txt"

  for service in cdb_ws cdb_signal cdb_risk cdb_execution cdb_db_writer cdb_paper_runner; do
    if docker ps -a --filter "name=$service" --format "{{.Names}}" | grep -q "$service"; then
      echo "  Capturing logs: $service"
      docker logs "$service" --tail 500 > "$ARTIFACT_PATH/failure_logs_${service}.txt" 2>&1 || true
    fi
  done

  echo -e "${RED}See $ARTIFACT_PATH for evidence.${NC}"
  # Don't exit - continue monitoring to capture full failure timeline
else
  echo -e "${GREEN}✓ No restarts detected${NC}"
  # Check-and-write the hourly checkpoint with optional flock protection.
  # On platforms with flock (Linux containers), the lock serialises access
  # to prevent duplicate entries from parallel cron instances (Issue #1271).
  # On platforms without flock (Git Bash / MSYS2 on Windows), the checkpoint
  # is written directly — safe for solo-maintainer setups with a single
  # cron instance (Issue #1420).
  _checkpoint_write() {
    _CK=-1
    [ -f "$LAST_CHECKPOINT_FILE" ] && _CK=$(cat "$LAST_CHECKPOINT_FILE")
    if [ "$ELAPSED_HOURS" -le "$_CK" ]; then
      echo "Checkpoint $ELAPSED_HOURS already written (last=$_CK) — skipping duplicate"
    else
      echo "$TIMESTAMP - Hour $ELAPSED_HOURS: No restarts" >> "$ARTIFACT_PATH/hourly_checks.log"
      echo "$ELAPSED_HOURS" > "$LAST_CHECKPOINT_FILE"
    fi
  }
  if [ "$_HAS_FLOCK" -eq 1 ]; then
    (
      flock -x -w 30 200 || {
        echo "WARNING: could not acquire checkpoint lock within 30 s — skipping hourly log write"
        exit 0
      }
      _checkpoint_write
    ) 200>"$ARTIFACT_PATH/checkpoint.lock"
  else
    _checkpoint_write
  fi
fi

# =============================================================================
# CHECK 2: Service Health (Every Hour)
# =============================================================================

echo -e "\n${YELLOW}[CHECK 2/5]${NC} Service Health Status..."

# SUT_SERVICES and EXPECTED_SERVICES are defined at the top of the script
# (shared with Check 1). See the definition near the color variables.

# Snapshot all running container names once (avoids N docker calls in the loop).
_RUNNING_NAMES=$(docker ps --filter "status=running" --format "{{.Names}}" 2>/dev/null || true)

RUNNING_SERVICES=0
MISSING_SVC_LIST=""
for _svc in $SUT_SERVICES; do
  if echo "$_RUNNING_NAMES" | grep -qx "$_svc"; then
    RUNNING_SERVICES=$((RUNNING_SERVICES + 1))
  else
    MISSING_SVC_LIST="$MISSING_SVC_LIST $_svc"
  fi
done

# Inventory count: total cdb_* containers (informational, not a gate).
TOTAL_CDB=$(echo "$_RUNNING_NAMES" | grep -c "^cdb_" || echo 0)

if [ "$RUNNING_SERVICES" -lt "$EXPECTED_SERVICES" ]; then
  echo -e "${RED}⚠️  WARNING: $RUNNING_SERVICES/$EXPECTED_SERVICES SUT services running (inventory: $TOTAL_CDB cdb_* containers)${NC}"
  echo "  Missing:$MISSING_SVC_LIST"
  docker ps --filter "name=cdb_" --format "{{.Names}}: {{.Status}}"
else
  echo -e "${GREEN}✓ All $RUNNING_SERVICES/$EXPECTED_SERVICES SUT services running (inventory: $TOTAL_CDB cdb_* containers)${NC}"
fi

# =============================================================================
# CHECK 3: Resource Snapshot (Every 6 hours)
# =============================================================================

if [ "$((ELAPSED_HOURS % 6))" -eq 0 ]; then
  echo -e "\n${YELLOW}[CHECK 3/5]${NC} Resource Snapshot (6h interval)..."

  SNAPSHOT_FILE="$ARTIFACT_PATH/resources_snapshot_$(date -u +%Y%m%d_%H)h.txt"

  echo "Timestamp: $TIMESTAMP" > "$SNAPSHOT_FILE"
  echo "=========================================" >> "$SNAPSHOT_FILE"
  docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" >> "$SNAPSHOT_FILE"

  echo -e "${GREEN}✓ Snapshot saved to: $SNAPSHOT_FILE${NC}"
else
  echo -e "\n${YELLOW}[CHECK 3/5]${NC} Resource Snapshot (skipped - not 6h interval)"
fi

# =============================================================================
# CHECK 4: Database Growth (Every 12 hours)
# =============================================================================

if [ "$((ELAPSED_HOURS % 12))" -eq 0 ]; then
  echo -e "\n${YELLOW}[CHECK 4/5]${NC} Database Growth Check (12h interval)..."

  DB_FILE="$ARTIFACT_PATH/db_growth_$(date -u +%Y%m%d_%H)h.txt"

  # Check if postgres is running
  if docker ps --filter "name=cdb_postgres" --filter "status=running" | grep -q "cdb_postgres"; then
    echo "Timestamp: $TIMESTAMP" > "$DB_FILE"
    echo "=========================================" >> "$DB_FILE"

    # Resolve non-sensitive runtime config from target container (Issue #1281).
    # Uses docker inspect to read POSTGRES_USER and POSTGRES_DB — no /bin/sh
    # dependency inside the container, no password or connection-string access.
    _INSPECT_ENV=$(docker inspect cdb_postgres --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null)
    _INSPECT_EXIT=$?

    if [ "$_INSPECT_EXIT" -ne 0 ]; then
      echo "[CHECK 4] ENV_RESOLUTION_FAILED" >> "$DB_FILE"
      echo "  container=cdb_postgres" >> "$DB_FILE"
      echo "  resolved_user=<empty>" >> "$DB_FILE"
      echo "  resolved_db=<empty>" >> "$DB_FILE"
      echo "  context_source=docker_inspect_env" >> "$DB_FILE"
      echo "  exit_status=$_INSPECT_EXIT" >> "$DB_FILE"
      echo -e "${RED}⚠️  Check 4 fail-closed: docker inspect failed (exit $_INSPECT_EXIT)${NC}"
    else
      PG_USER=$(echo "$_INSPECT_ENV" | grep '^POSTGRES_USER=' | cut -d= -f2-)
      PG_DB=$(echo "$_INSPECT_ENV"   | grep '^POSTGRES_DB='   | cut -d= -f2-)

      if [ -z "$PG_USER" ] || [ -z "$PG_DB" ]; then
        echo "[CHECK 4] ENV_RESOLUTION_FAILED" >> "$DB_FILE"
        echo "  container=cdb_postgres" >> "$DB_FILE"
        echo "  resolved_user=${PG_USER:-<empty>}" >> "$DB_FILE"
        echo "  resolved_db=${PG_DB:-<empty>}" >> "$DB_FILE"
        echo "  context_source=docker_inspect_env" >> "$DB_FILE"
        echo "  exit_status=0" >> "$DB_FILE"
        echo "  failure_reason=missing_keys" >> "$DB_FILE"
        echo -e "${RED}⚠️  Check 4 fail-closed: POSTGRES_USER or POSTGRES_DB not set in cdb_postgres${NC}"
      else
        docker exec cdb_postgres psql -U "$PG_USER" -d "$PG_DB" -t -c "
          SELECT 'orders', COUNT(*) FROM orders UNION ALL
          SELECT 'trades', COUNT(*) FROM trades UNION ALL
          SELECT 'signals', COUNT(*) FROM signals;
        " >> "$DB_FILE" 2>&1
        _PSQL_EXIT=$?

        if [ "$_PSQL_EXIT" -ne 0 ]; then
          echo "[CHECK 4] PSQL_QUERY_FAILED" >> "$DB_FILE"
          echo "  container=cdb_postgres" >> "$DB_FILE"
          echo "  resolved_user=$PG_USER" >> "$DB_FILE"
          echo "  resolved_db=$PG_DB" >> "$DB_FILE"
          echo "  context_source=docker_inspect_env" >> "$DB_FILE"
          echo "  exit_status=$_PSQL_EXIT" >> "$DB_FILE"
          echo -e "${RED}⚠️  Check 4: psql query failed (exit $_PSQL_EXIT) — see $DB_FILE${NC}"
        else
          echo -e "${GREEN}✓ Database metrics saved to: $DB_FILE${NC}"
        fi
      fi
    fi
  else
    echo -e "${RED}⚠️  PostgreSQL not running - skipping DB check${NC}"
  fi
else
  echo -e "\n${YELLOW}[CHECK 4/5]${NC} Database Growth Check (skipped - not 12h interval)"
fi

# =============================================================================
# CHECK 5: Disk Space (Every Hour)
# =============================================================================

echo -e "\n${YELLOW}[CHECK 5/5]${NC} Disk Space Check..."

# ---------------------------------------------------------------------------
# The monitor runs inside a container (ubuntu:22.04) with /repo and
# /var/run/docker.sock mounted. /var/lib/docker is NOT present inside the
# container — measuring it via df fails silently and produced the misleading
# "Could not determine disk usage" message (Issue #1264).
#
# Two evidence sources that ARE reachable from inside the container:
#   1. df /repo   — the partition where run artifacts are written
#   2. docker system df — Docker image/container/volume space via socket
#
# A disk_evidence file is written at every checkpoint regardless of threshold
# so the evidence chain always has a disk record, not just at Critical level.
# ---------------------------------------------------------------------------

DISK_EVIDENCE_FILE="$ARTIFACT_PATH/disk_evidence_$(date -u +%Y%m%d_%H)h.txt"

# Source 1: artifact filesystem (/repo partition — always mounted)
# Issue #1282: capture raw output first so we can distinguish command failure
# (DF_REPO_RC != 0) from parse failure (exit 0 but unparseable output).
DF_REPO_RAW=""
DF_REPO_RC=0
DISK_UNAVAILABLE_REASON=""
DF_REPO_RAW=$(df -h /repo 2>&1) || DF_REPO_RC=$?

if [ "$DF_REPO_RC" -ne 0 ]; then
  ARTIFACT_DISK_PCT=""
  ARTIFACT_DISK_FREE=""
  DISK_UNAVAILABLE_REASON="df /repo exited ${DF_REPO_RC}: $(printf '%s' "$DF_REPO_RAW" | head -1)"
else
  ARTIFACT_DISK_PCT=$(printf '%s\n' "$DF_REPO_RAW" | awk 'NR==2 {print $5}' | sed 's/%//')
  ARTIFACT_DISK_FREE=$(printf '%s\n' "$DF_REPO_RAW" | awk 'NR==2 {print $4}')
  if [ -z "$ARTIFACT_DISK_PCT" ]; then
    DISK_UNAVAILABLE_REASON="df output not parseable: $(printf '%s' "$DF_REPO_RAW" | head -2 | tr '\n' ' ')"
  fi
fi

# Source 2: Docker space via socket (images, containers, volumes, build cache)
DOCKER_DF_OUT=$(docker system df 2>/dev/null || echo "  [docker system df not available]")

# Determine whether Docker disk evidence is usable (Issue #1427).
# A valid docker system df output contains "Images" in the table header.
# The fallback string "[docker system df not available]" does not.
DOCKER_DF_VALID=0
echo "$DOCKER_DF_OUT" | grep -q "Images" && DOCKER_DF_VALID=1

# Persist disk evidence at every checkpoint
{
  echo "Timestamp: $TIMESTAMP"
  echo "Elapsed hours: $ELAPSED_HOURS"
  echo "========================================="
  echo ""
  echo "Artifact filesystem (/repo — partition where run artifacts are stored):"
  if [ -n "$ARTIFACT_DISK_PCT" ]; then
    echo "  Used: ${ARTIFACT_DISK_PCT}%  |  Free: ${ARTIFACT_DISK_FREE:-unknown}"
  else
    echo "  NOT_AVAILABLE: ${DISK_UNAVAILABLE_REASON:-df /repo returned no parseable output}"
    echo "  raw_output: $(printf '%s' "$DF_REPO_RAW" | head -3 | tr '\n' ' ')"
  fi
  echo ""
  echo "Docker space (images / containers / volumes / build cache):"
  echo "$DOCKER_DF_OUT"
} > "$DISK_EVIDENCE_FILE"

# Console output + alert log
if [ -n "$ARTIFACT_DISK_PCT" ]; then
  if [ "$ARTIFACT_DISK_PCT" -gt 90 ] 2>/dev/null; then
    echo -e "${RED}⚠️  CRITICAL: Artifact filesystem ${ARTIFACT_DISK_PCT}% full (free: ${ARTIFACT_DISK_FREE})${NC}"
    echo "$TIMESTAMP - CRITICAL: Artifact filesystem ${ARTIFACT_DISK_PCT}% full" >> "$ARTIFACT_PATH/disk_alerts.log"
  elif [ "$ARTIFACT_DISK_PCT" -gt 80 ] 2>/dev/null; then
    echo -e "${YELLOW}⚠️  WARNING: Artifact filesystem ${ARTIFACT_DISK_PCT}% (free: ${ARTIFACT_DISK_FREE})${NC}"
  else
    echo -e "${GREEN}✓ Artifact filesystem: ${ARTIFACT_DISK_PCT}% used (free: ${ARTIFACT_DISK_FREE})${NC}"
  fi
else
  # Issue #1427: distinguish partial evidence (Docker available) from total
  # evidence failure. Host-FS status is already in disk_evidence_*.txt —
  # only write to disk_alerts.log when evidence is truly degraded.
  if [ "$DOCKER_DF_VALID" -eq 1 ]; then
    echo -e "${YELLOW}⚠️  Host filesystem unavailable — Docker disk evidence present${NC}"
  else
    echo -e "${RED}⚠️  Disk evidence degraded — host filesystem and Docker disk both unavailable${NC}"
    echo "$TIMESTAMP - DISK_UNAVAILABLE: ${DISK_UNAVAILABLE_REASON:-df /repo returned no parseable output}, Docker disk evidence also unavailable" >> "$ARTIFACT_PATH/disk_alerts.log"
  fi
fi
echo "  Evidence: $DISK_EVIDENCE_FILE"

# =============================================================================
# Summary
# =============================================================================

echo -e "\n========================================="
echo -e "${GREEN}Checkpoint $ELAPSED_HOURS monitoring checks complete${NC}"
echo "$TIMESTAMP"
echo "Next check: $(date -d '+1 hour' -u +"%Y-%m-%d %H:%M:%S UTC")"
echo "========================================="

exit 0
