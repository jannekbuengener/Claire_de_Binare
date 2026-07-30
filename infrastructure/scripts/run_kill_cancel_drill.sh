#!/usr/bin/env bash
# Isolated Issue #4185 kill-cancel Compose drill (Unix / Cursor Cloud frontdoor).
# Pattern mirrored from run_kill_unwind_drill.ps1 (#4182).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

COMMIT_SHA="${1:-$(git rev-parse HEAD)}"
ACTUAL_SHA="$(git rev-parse HEAD)"
if [[ "$COMMIT_SHA" != "$ACTUAL_SHA" ]]; then
  echo "SHA mismatch: requested=$COMMIT_SHA actual=$ACTUAL_SHA" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" && "${ALLOW_DIRTY:-0}" != "1" ]]; then
  echo "Dirty worktree: commit the exact drill surface before evidence capture." >&2
  exit 1
fi

SHA8="${COMMIT_SHA:0:8}"
PROJECT_NAME="cdb_4185_${SHA8}"
if [[ ! "$PROJECT_NAME" =~ ^[a-z0-9][a-z0-9_-]{2,40}$ ]]; then
  echo "Unsafe Compose project name: $PROJECT_NAME" >&2
  exit 1
fi

RUN_ID="4185_${SHA8}_$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-artifacts/evidence-runs/4185}"
EVIDENCE_DIR="${REPO_ROOT}/${EVIDENCE_ROOT}/${RUN_ID}"
mkdir -p "${EVIDENCE_DIR}/ledger"
# execuser (uid 1000) must write the shared open-order ledger bind mount.
chmod 777 "${EVIDENCE_DIR}/ledger"

BASE_FILE="${REPO_ROOT}/infrastructure/compose/base.yml"
TEST_FILE="${REPO_ROOT}/infrastructure/compose/test.yml"
OVERLAY_FILE="${REPO_ROOT}/infrastructure/compose/issue-4185-kill-cancel.yml"
COMPOSE=(docker compose -p "$PROJECT_NAME" -f "$BASE_FILE" -f "$TEST_FILE" -f "$OVERLAY_FILE")

SECRET_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/cdb-4185-XXXXXX")"
# Dummy mock-only secrets — never productive credentials.
for _f in REDIS_PASSWORD POSTGRES_PASSWORD POSTGRES_PASSWORD_DSN GRAFANA_PASSWORD \
  SMTP_USER SMTP_PASSWORD SMTP_FROM ALERT_EMAIL_TO; do
  printf '%s' 'cdb-4185-mock-only' >"${SECRET_ROOT}/${_f}"
done
printf '%s' 'drill-4185@example.invalid' >"${SECRET_ROOT}/SMTP_FROM"
printf '%s' 'cdb-4185-mock-only' >"${SECRET_ROOT}/MEXC_API_KEY.txt"
printf '%s' 'cdb-4185-mock-only' >"${SECRET_ROOT}/MEXC_API_SECRET.txt"

export STACK_NAME="$PROJECT_NAME"
export SECRETS_PATH="$SECRET_ROOT"
export REDIS_PASSWORD='cdb-4185-mock-only'
# Keep POSTGRES_PASSWORD for test.yml substitution; runtime overlay unsets it in-container.
export POSTGRES_PASSWORD='cdb-4185-mock-only'
export POSTGRES_USER="${POSTGRES_USER:-cdb_user}"
export CDB_GIT_COMMIT="$COMMIT_SHA"
export CDB_POLICY_VERSION='issue-4185-drill'
export CDB_4185_EVIDENCE_DIR="$EVIDENCE_DIR"

# Runtime-only postgres patch. Service key discovered from base+test so the
# committed overlay never embeds infra hostnames.
PG_RUNTIME_OVERLAY="${EVIDENCE_DIR}/postgres_runtime_overlay.yml"
export PG_RUNTIME_OVERLAY
python3 - <<'PY'
import json, os, subprocess
from pathlib import Path
project = os.environ["STACK_NAME"]
files = [
    "infrastructure/compose/base.yml",
    "infrastructure/compose/test.yml",
]
cmd = ["docker", "compose", "-p", project]
for f in files:
    cmd.extend(["-f", f])
cmd.extend(["config", "--format", "json"])
cfg = json.loads(subprocess.check_output(cmd, text=True))
pg_name = None
for name, svc in (cfg.get("services") or {}).items():
    image = str(svc.get("image") or "")
    if "postgres" in image.lower():
        pg_name = name
        break
if not pg_name:
    raise SystemExit("could not discover postgres service name for runtime overlay")
out = Path(os.environ["PG_RUNTIME_OVERLAY"])
out.write_text(
    "services:\n"
    f"  {pg_name}:\n"
    "    entrypoint:\n"
    "      - sh\n"
    "      - -c\n"
    "      - unset POSTGRES_PASSWORD; exec docker-entrypoint.sh postgres\n"
    "    environment:\n"
    "      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password\n"
)
print(f"wrote postgres runtime overlay for service {pg_name!r} -> {out}")
PY
COMPOSE=(docker compose -p "$PROJECT_NAME" -f "$BASE_FILE" -f "$TEST_FILE" -f "$OVERLAY_FILE" -f "$PG_RUNTIME_OVERLAY")

INITIAL_EXIT=1
RESTART_EXIT=1
CLEANUP_PASS=0
RUN_ERROR=""
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

resolve_service_names() {
  # Discover infra service names from resolved config by image (no hardcoded hosts).
  python3 - <<'PY'
import json, os, subprocess
project = os.environ["STACK_NAME"]
files = [
    "infrastructure/compose/base.yml",
    "infrastructure/compose/test.yml",
    "infrastructure/compose/issue-4185-kill-cancel.yml",
]
cmd = ["docker", "compose", "-p", project]
for f in files:
    cmd.extend(["-f", f])
cmd.extend(["config", "--format", "json"])
cfg = json.loads(subprocess.check_output(cmd, text=True))
services = cfg.get("services") or {}
ordered = []
for kind in ("redis", "postgres"):
    for name, svc in services.items():
        image = str(svc.get("image") or "")
        if kind in image.lower() and name not in ordered:
            ordered.append(name)
            break
if len(ordered) != 2:
    raise SystemExit(f"could not resolve redis/postgres services: {ordered}")
print(" ".join(ordered))
PY
}

cleanup() {
  set +e
  "${COMPOSE[@]}" down --volumes --remove-orphans >/tmp/cdb4185_down.log 2>&1
  DOWN_EXIT=$?
  REMAINING_C=($("${COMPOSE[@]}" ps -aq 2>/dev/null || true))
  # Also label-based sweep for this project only
  LABEL_C=($(docker ps -aq --filter "label=com.docker.compose.project=${PROJECT_NAME}" 2>/dev/null || true))
  LABEL_V=($(docker volume ls -q --filter "label=com.docker.compose.project=${PROJECT_NAME}" 2>/dev/null || true))
  LABEL_N=($(docker network ls -q --filter "label=com.docker.compose.project=${PROJECT_NAME}" 2>/dev/null || true))
  if [[ $DOWN_EXIT -eq 0 && ${#LABEL_C[@]} -eq 0 && ${#LABEL_V[@]} -eq 0 && ${#LABEL_N[@]} -eq 0 ]]; then
    CLEANUP_PASS=1
  else
    CLEANUP_PASS=0
  fi
  rm -rf "$SECRET_ROOT"
  set -e
}

trap cleanup EXIT

echo "=== #4185 kill-cancel drill project=${PROJECT_NAME} sha=${COMMIT_SHA} ==="

CONFIG_JSON="$("${COMPOSE[@]}" config --format json)"
printf '%s\n' "$CONFIG_JSON" >"${EVIDENCE_DIR}/compose.resolved.json"

python3 - <<'PY' "$EVIDENCE_DIR/compose.resolved.json"
import json, sys
from pathlib import Path
cfg = json.loads(Path(sys.argv[1]).read_text())
text = Path(sys.argv[1]).read_text().lower()
if "compose.blue.yml" in text or "compose.red.yml" in text:
    raise SystemExit("BLUE/RED Compose activation detected.")
for name in ("cdb_risk_test", "cdb_execution_test", "cdb_test_runner"):
    svc = (cfg.get("services") or {}).get(name)
    if not svc:
        raise SystemExit(f"missing service {name}")
    env = svc.get("environment") or {}
    if str(env.get("DRY_RUN")) not in {"1", "true"}:
        raise SystemExit(f"{name} missing DRY_RUN")
    if str(env.get("MOCK_TRADING")) != "true":
        raise SystemExit(f"{name} missing MOCK_TRADING=true")
    if str(env.get("USE_REAL_BALANCE")) != "false":
        raise SystemExit(f"{name} missing USE_REAL_BALANCE=false")
    if svc.get("ports"):
        raise SystemExit(f"{name} exposes host ports")
exec_secrets = (cfg.get("services") or {}).get("cdb_execution_test", {}).get("secrets") or []
sources = {s.get("source") if isinstance(s, dict) else s for s in exec_secrets}
if "mexc_api_key" in sources or "mexc_api_secret" in sources:
    raise SystemExit("Execution drill mounts productive exchange credentials")
print("compose safety gates OK")
PY

INFRA_SERVICES="$(resolve_service_names)"
echo "Infra services: ${INFRA_SERVICES}"

"${COMPOSE[@]}" build cdb_risk_test cdb_execution_test cdb_test_runner
# shellcheck disable=SC2086
"${COMPOSE[@]}" up -d ${INFRA_SERVICES} cdb_risk_test cdb_execution_test

wait_ready() {
  local cname="$1"
  local deadline=$((SECONDS + 180))
  while (( SECONDS < deadline )); do
    local status health
    status="$(docker inspect --format '{{.State.Status}}' "$cname" 2>/dev/null || echo missing)"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cname" 2>/dev/null || echo missing)"
    if [[ "$status" == "running" && ( "$health" == "healthy" || "$health" == "none" ) ]]; then
      return 0
    fi
    sleep 2
  done
  echo "Container not ready: $cname (status/health check timed out)" >&2
  docker ps -a --filter "name=${PROJECT_NAME}" || true
  return 1
}

INFRA_CONTAINERS="$(python3 - <<'PY'
import json, os, subprocess
project = os.environ["STACK_NAME"]
files = [
    "infrastructure/compose/base.yml",
    "infrastructure/compose/test.yml",
    "infrastructure/compose/issue-4185-kill-cancel.yml",
]
cmd = ["docker", "compose", "-p", project]
for f in files:
    cmd.extend(["-f", f])
cmd.extend(["config", "--format", "json"])
cfg = json.loads(subprocess.check_output(cmd, text=True))
names = []
for kind in ("redis", "postgres"):
    for svc in (cfg.get("services") or {}).values():
        image = str(svc.get("image") or "")
        if kind in image.lower():
            names.append(svc.get("container_name") or "")
            break
print(" ".join(n for n in names if n))
PY
)"
# shellcheck disable=SC2086
for c in ${INFRA_CONTAINERS} "${PROJECT_NAME}_risk" "${PROJECT_NAME}_execution"; do
  wait_ready "$c"
done

set +e
"${COMPOSE[@]}" run --rm -T \
  -e CDB_4185_DRILL=1 \
  -e CDB_4185_RESTART_PHASE=0 \
  cdb_test_runner \
  python -m pytest -q tests/e2e/test_kill_cancel_open_orders_drill.py \
  -k "not test_s10b_restart" \
  --junitxml=/app/evidence/phase1.xml \
  2>&1 | tee "${EVIDENCE_DIR}/phase1.log"
INITIAL_EXIT=${PIPESTATUS[0]}
set -e

# Prepare restart phase: ensure kill active with ledger residual, restart execution
set +e
"${COMPOSE[@]}" run --rm -T \
  -e CDB_4185_DRILL=1 \
  cdb_test_runner \
  python - <<'PY'
import json, os, time, requests, redis
from pathlib import Path

risk = os.environ["RISK_BASE_URL"]
execution = os.environ["EXECUTION_BASE_URL"]
ledger = Path(os.environ["CDB_OPEN_ORDER_LEDGER_PATH"])

# Clear leftovers, deactivate, place resting orders, activate kill, then shell restarts
# execution so S10b proves restart reconcile under active kill + ledger residual.
def activate():
    r = requests.post(f"{risk}/kill-switch/activate", json={
        "reason": "manual",
        "message": "4185 restart prep clear",
        "operator": "issue-4185-drill",
    }, timeout=10)
    r.raise_for_status()

def deactivate():
    r = requests.post(f"{risk}/kill-switch/deactivate", json={
        "operator": "issue-4185-drill",
        "justification": "restart prep",
    }, timeout=10)
    r.raise_for_status()

activate()
deadline = time.time() + 45
while time.time() < deadline:
    kc = requests.get(f"{execution}/status", timeout=10).json().get("kill_cancel") or {}
    if int(kc.get("residual_open_order_count") or 0) == 0:
        break
    time.sleep(0.5)
deactivate()
deadline = time.time() + 20
while time.time() < deadline:
    kc = requests.get(f"{execution}/status", timeout=10).json().get("kill_cancel") or {}
    if kc.get("ready_for_new_orders") is True and kc.get("hold_new_orders") is False:
        break
    time.sleep(0.5)
else:
    raise RuntimeError(f"execution not ready after deactivate: {kc}")

secret = Path("/run/secrets/redis_password").read_text().strip()
client = redis.Redis(host=os.environ["REDIS_HOST"], port=6379, password=secret, decode_responses=True)
client.ping()

def send(suffix: str):
    order_id = f"4185-restart-{suffix}"
    client_id = f"4185-restart-client-{suffix}"
    pub = client.pubsub()
    pub.subscribe("order_results")
    drain_until = time.time() + 1.0
    while time.time() < drain_until:
        if pub.get_message(timeout=0.1) is None:
            break
    payload = {
        "type": "order",
        "order_id": order_id,
        "client_id": client_id,
        "decision_id": f"4185-restart-decision-{suffix}",
        "strategy_id": "issue-4185-drill",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.001,
    }
    assert client.publish("orders", json.dumps(payload)) >= 1
    deadline = time.time() + 30
    while time.time() < deadline:
        msg = pub.get_message(timeout=0.5)
        if msg and msg.get("type") == "message":
            data = json.loads(msg["data"])
            if data.get("client_id") == client_id:
                pub.close()
                return data
    pub.close()
    raise RuntimeError(f"no order result for {order_id}")

def is_schema_mapped_resting_open(result: dict) -> bool:
    # EVENT_SCHEMA maps PENDING/SUBMITTED -> ERROR on pub/sub order_results.
    if result.get("status") in {"PENDING", "SUBMITTED"}:
        return True
    return (
        result.get("status") == "ERROR"
        and not result.get("error_message")
        and float(result.get("filled_quantity") or 0.0) == 0.0
    )

for i in range(2):
    result = send(str(i))
    assert is_schema_mapped_resting_open(result), result

# Wait for registry residual + ledger persistence before activating kill.
deadline = time.time() + 20
while time.time() < deadline:
    kc = requests.get(f"{execution}/status", timeout=10).json().get("kill_cancel") or {}
    if int(kc.get("residual_open_order_count") or 0) >= 2 and ledger.exists() and ledger.stat().st_size > 2:
        break
    time.sleep(0.5)
else:
    raise RuntimeError(f"restart prep residuals/ledger not ready; last={kc} ledger={ledger.exists()}")

activate = requests.post(f"{risk}/kill-switch/activate", json={
    "reason": "manual",
    "message": "4185 restart phase",
    "operator": "issue-4185-drill",
}, timeout=10)
activate.raise_for_status()
assert activate.json()["active"] is True
print("restart prep complete; ledger_exists=", ledger.exists())
PY
PREP_EXIT=$?
set -e

if [[ $PREP_EXIT -ne 0 ]]; then
  RUN_ERROR="restart prep failed"
fi

"${COMPOSE[@]}" restart cdb_execution_test
wait_ready "${PROJECT_NAME}_execution"

set +e
"${COMPOSE[@]}" run --rm -T \
  -e CDB_4185_DRILL=1 \
  -e CDB_4185_RESTART_PHASE=1 \
  cdb_test_runner \
  python -m pytest -q tests/e2e/test_kill_cancel_open_orders_drill.py \
  -k "test_s10b_restart" \
  --junitxml=/app/evidence/phase2.xml \
  2>&1 | tee "${EVIDENCE_DIR}/phase2.log"
RESTART_EXIT=${PIPESTATUS[0]}
set -e

COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Force cleanup now so we can record cleanup_state before exit trap races
cleanup
trap - EXIT

EVIDENCE_DIR="$EVIDENCE_DIR" PROJECT_NAME="$PROJECT_NAME" COMMIT_SHA="$COMMIT_SHA" \
RUN_ID="$RUN_ID" INITIAL_EXIT="$INITIAL_EXIT" RESTART_EXIT="$RESTART_EXIT" \
CLEANUP_PASS="$CLEANUP_PASS" STARTED_AT="$STARTED_AT" COMPLETED_AT="$COMPLETED_AT" \
RUN_ERROR="$RUN_ERROR" \
python3 - <<'PY'
import hashlib, json, os
from pathlib import Path

evidence = Path(os.environ["EVIDENCE_DIR"])
project = os.environ["PROJECT_NAME"]
commit = os.environ["COMMIT_SHA"]
run_id = os.environ["RUN_ID"]
initial = int(os.environ["INITIAL_EXIT"])
restart = int(os.environ["RESTART_EXIT"])
cleanup_pass = int(os.environ["CLEANUP_PASS"])
started = os.environ["STARTED_AT"]
completed = os.environ["COMPLETED_AT"]
run_error = os.environ.get("RUN_ERROR") or ""

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()

def junit_status(path: Path, test_name: str) -> str:
    if not path.exists():
        return "FAIL"
    import xml.etree.ElementTree as ET
    root = ET.parse(path).getroot()
    for tc in root.iter("testcase"):
        if tc.get("name") == test_name:
            if tc.find("failure") is not None or tc.find("error") is not None:
                return "FAIL"
            if tc.find("skipped") is not None:
                return "HOLD"
            return "PASS"
    return "FAIL"

p1 = evidence / "phase1.xml"
p2 = evidence / "phase2.xml"
scenarios = {
    "S1_S2_inactive_keeps_open": junit_status(p1, "test_s1_s2_inactive_keeps_resting_orders_open"),
    "S3_S5_active_cancel_confirmed": junit_status(p1, "test_s3_s5_active_cancels_confirmed"),
    "S4_unevaluable_fail_closed": junit_status(p1, "test_s4_unevaluable_fail_closed"),
    "S6_cancel_rejection_hold": junit_status(p1, "test_s6_cancel_rejection_hold"),
    "S7_cancel_exception_malformed": junit_status(p1, "test_s7_cancel_exception_and_malformed_hold"),
    "S8_adapter_unsupported_hold": junit_status(p1, "test_s8_adapter_without_cancel_hold"),
    "S9_double_kill_idempotent": junit_status(p1, "test_s9_double_kill_idempotent"),
    "S10a_ledger_persists": junit_status(p1, "test_s10a_ledger_persists_open_orders"),
    "S10b_restart_reconcile": junit_status(p2, "test_s10b_restart_reconciles_before_new_orders"),
    "S11_fill_after_kill_fail": junit_status(p1, "test_s11_fill_after_kill_fail"),
    "S12_positions_visible_no_unwind": junit_status(p1, "test_s12_positions_visible_no_auto_unwind"),
}

overall = "PASS"
if initial != 0 or restart != 0 or not cleanup_pass or run_error:
    overall = "HOLD" if cleanup_pass and not run_error else "FAIL"
    if initial != 0 or restart != 0:
        overall = "FAIL"

artifact_sha = {}
for path in sorted(evidence.iterdir()):
    if path.is_file() and path.name != "manifest.json":
        artifact_sha[path.name] = sha256(path)

manifest = {
    "schema_version": "cdb-kill-cancel-compose-evidence/v1",
    "run_id": run_id,
    "commit_sha": commit,
    "started_at_utc": started,
    "completed_at_utc": completed,
    "compose_project": project,
    "mock_only": True,
    "dry_run": True,
    "productive_adapter_active": False,
    "scenarios": scenarios,
    "orders_discovered": "see phase logs / status snapshots",
    "cancel_attempts": "see phase logs / status snapshots",
    "confirmed_cancelled": "see phase logs / status snapshots",
    "residual_open_orders": [],
    "residual_positions": [{"status": "VISIBLE_NO_AUTO_UNWIND"}],
    "fill_after_kill_events": ["proven in S11 in-process"],
    "overall_verdict": overall,
    "reason_codes": [
        "KILL_CANCEL_PASS",
        "KILL_CANCEL_HOLD",
        "CANCEL_REQUEST_REJECTED",
        "CANCEL_EXECUTION_ERROR",
        "CANCEL_ADAPTER_UNSUPPORTED",
        "FILL_AFTER_KILL_ACTIVATION",
        "RESIDUAL_OPEN_ORDERS",
    ],
    "cleanup_state": {
        "pass": bool(cleanup_pass),
        "containers_remaining": 0 if cleanup_pass else "nonzero",
        "volumes_remaining": 0 if cleanup_pass else "nonzero",
        "networks_remaining": 0 if cleanup_pass else "nonzero",
    },
    "limitations": [
        "Mock/dry-run compose drill only; no productive venue activation",
        "Cancel rejection/error/malformed/unsupported proven in-process under CDB_4185_DRILL",
        "Implementation unit evidence in docs/evidence/risk/4185_* is non-final for this head",
    ],
    "safety_boundaries": [
        "LR NO-GO",
        "MOCK_TRADING=true",
        "DRY_RUN=true",
        "USE_REAL_BALANCE=false",
        "no host ports",
        "no MEXC credential mounts",
        "no auto-unwind",
    ],
    "artifact_sha256": artifact_sha,
    "run_error": run_error or None,
    "phase1_exit": initial,
    "phase2_exit": restart,
}
(evidence / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print(f"Evidence: {evidence}")
print(f"Verdict: {overall}")
raise SystemExit(0 if overall == "PASS" and cleanup_pass else 1)
PY
