# Soak Monitor Runbook

Operational guide for `infrastructure/scripts/soak_monitor.sh` (Issue #428).

## Purpose

Hourly monitoring script for the 72h Zero Restart Soak Test.
Runs 5 checks per invocation: container restarts, service health,
resource snapshots (6h), database growth (12h), and disk space.
On restart detection the script writes a `soak_test_FAILED.txt` marker
and captures failure evidence.

## Preconditions

| Requirement | How to verify |
|---|---|
| Docker + Compose running | `docker ps --filter name=cdb_` shows services (script expects `EXPECTED_SERVICES=8`, see `soak_monitor.sh:108`) |
| Prometheus scraping | `curl -s http://localhost:9090/-/ready` returns 200 |
| Grafana reachable | `curl -s http://localhost:3000/api/health` returns `ok` |
| Write permissions | `touch artifacts/.probe && rm artifacts/.probe` succeeds |

## Pre-start Checklist

```bash
# 1. Create artifacts directory (script auto-creates if missing,
#    but pre-creating avoids the warning in the first run)
mkdir -p artifacts

# 2. Make script executable
chmod +x infrastructure/scripts/soak_monitor.sh

# 3. Verify Compose stack is healthy
docker ps --filter name=cdb_ --format '{{.Names}}: {{.Status}}'
```

## Manual / Dry Run

```bash
# Run once to verify output and artifact creation
./infrastructure/scripts/soak_monitor.sh

# Expected output:
#   [CHECK 1/5] Container Restart Detection... No restarts detected
#   [CHECK 2/5] Service Health Status... All 8/8 services running
#   [CHECK 3/5] Resource Snapshot (skipped - not 6h interval)
#   [CHECK 4/5] Database Growth Check (skipped - not 12h interval)
#   [CHECK 5/5] Disk Space Check... Disk usage: <N>%

# Expected artifacts (in artifacts/soak_test_YYYYMMDD_HHMMSS/):
#   hourly_checks.log   — one line per successful check
#   restart_alerts.log   — only if restarts detected
#   soak_test_FAILED.txt — only if Zero Restart violated
```

For the isolated LR-030 local monitor path:

```bash
SOAK_RUN_INTENT=lr030 ./infrastructure/scripts/soak_monitor.sh
```

- Artifacts land under `artifacts/soak_lr030_*`.
- Only `soak_active_run_path_lr030.txt` is updated.
- The generic pointer `soak_active_run_path.txt` stays LR-040-only.
- This path is raw/operator continuity support only and does not replace the
  workflow-backed LR-030 evidence chain.

## Cron Installation (Linux)

```bash
# Open crontab
crontab -e

# Add (adjust /absolute/path/to/repo):
SHELL=/bin/bash
0 * * * * cd /absolute/path/to/repo && ./infrastructure/scripts/soak_monitor.sh >> artifacts/soak_cron.log 2>&1
```

**Notes:**
- Use absolute path to the repo root (cron has minimal `$PATH`).
- `cd` into the repo so relative `artifacts/` paths resolve correctly.
- Redirect output to `soak_cron.log` for debugging cron issues.
- The script uses `docker` CLI; ensure the cron user is in the `docker` group.

## Prometheus Alerts

Soak-test alerts live in `infrastructure/monitoring/alerts.yml`,
group `soak_test_gates`. To list current alert names and thresholds:

```bash
grep -n "alert: SoakTest_" infrastructure/monitoring/alerts.yml
grep -n "soak_test_gates" infrastructure/monitoring/alerts.yml
```

Alerts with `soak_test: abort` are hard-stop criteria (soak test fails).
Alerts with `soak_test: investigate` require manual triage but do not
auto-abort.

## Grafana Dashboard

**Dashboard:** `Claire - 72h Soak Test Monitor`
**File:** `infrastructure/monitoring/grafana/dashboards/claire_soak_test_v1.json`

Key panels: Container Restarts (must be 0), Disk Space Remaining,
Test Duration, per-service health (redis, postgres, ws, signal,
risk, execution, db_writer, paper_runner).

## Troubleshooting

| Problem | Fix |
|---|---|
| `No soak test artifacts directory found` | Script auto-creates; for clean start: `mkdir -p artifacts` |
| Cron not running | `grep CRON /var/log/syslog`; check crontab user, PATH, docker group |
| Targets DOWN in Prometheus | `docker ps --filter name=cdb_` + check compose health |
| Disk usage critical (>90%) | `docker system prune -f`; review log volume mounts |
| DB query fails | Verify cdb_postgres is running; check DB user/name in compose |
| Monitor logs "No restarts" after FAILED | Host rebooted: containers auto-restarted, monitor detects restart only once. Check `cat artifacts/soak_test_*/soak_test_FAILED.txt`. Run is invalid; deactivate monitor or let it continue for timeline data (lines will show `ALREADY_FAILED`). |
| Soak run failed by Windows Update reboot | See `docs/operations/72H_SOAK_TEST_RUNBOOK.md` section "Pre-Flight: Windows Host" for prevention. Verify via `Get-WinEvent -LogName System` for Event ID 1074 (User32). |

## Post-Failure Monitoring Behavior

After `soak_test_FAILED.txt` is written, the monitor continues running
to collect timeline and resource data. Its hourly log entries change:

- **First failure detection:** `RESTART DETECTED - FAILED`
- **Subsequent runs (no new restarts):** `ALREADY_FAILED - no new restarts (original failure: ...)`
- **Subsequent runs (new restarts):** `RESTART DETECTED (run already failed)`

The normal `No restarts` line is never written once a failure marker
exists. This ensures `hourly_checks.log` is unambiguous about run state.

The monitor does **not** self-terminate after failure. To stop it,
deactivate the cron job or scheduled task manually.

## LR-030 Early-Fail Supervisor

`infrastructure/scripts/lr030_soak_supervisor.py` catches a broken or failing LR-030
run within the first hour instead of surfacing the problem only after a >24h review.
It is read-only — no Docker interaction, no GitHub writes, no runtime mutation.

**Usage:**

```bash
# Check a live or completed LR-030 run directory
python infrastructure/scripts/lr030_soak_supervisor.py \
    artifacts/soak_lr030_YYYYMMDD_HHMMSS/

# Require shadow-block-probe evidence (optional gate)
python infrastructure/scripts/lr030_soak_supervisor.py \
    artifacts/soak_lr030_YYYYMMDD_HHMMSS/ \
    --require-shadow-block-probe

# Override the hourly-log deadline (default 75 min)
python infrastructure/scripts/lr030_soak_supervisor.py \
    artifacts/soak_lr030_YYYYMMDD_HHMMSS/ \
    --hourly-deadline-minutes 90
```

**Exit codes:**

| Code | Status | Meaning |
|---|---|---|
| 0 | `RUNNING_VALID` | All checks pass so far |
| 1 | `ARTIFACT_CONTRACT_BROKEN` | Wrong path prefix or wrong `run_intent.txt` |
| 1 | `FAILED_EARLY` | `soak_test_FAILED.txt` or `SUT_RESTART` in logs |
| 1 | `INCONCLUSIVE_EARLY` | `soak_test_INCONCLUSIVE.txt` or `ENVIRONMENT_INTERRUPTION` |
| 1 | `INVALID_EVIDENCE` | Template placeholders in checkpoint files |
| 1 | `MONITOR_DEAD` | `hourly_checks.log` missing/invalid after deadline |
| 2 | *(CLI error)* | Missing or invalid arguments |

**Checks performed:**
1. Artifact directory name matches `soak_lr030_YYYYMMDD_HHMMSS`.
2. `run_intent.txt` contains exactly `lr030` (catches RC-2 intent drift from #2440).
3. `soak_test_FAILED.txt` absent.
4. `restart_alerts.log` free of `SUT_RESTART` patterns.
5. `soak_test_INCONCLUSIVE.txt` absent.
6. `restart_alerts.log` free of `ENVIRONMENT_INTERRUPTION`/`RESTART DETECTED`.
7. No un-expanded template variables (`$runId`, `$artifactDir`, `${checkpoint}`, etc.)
   in `.txt` or `.json` files (catches RC-3 checkpoint scripting errors from #2440).
8. `hourly_checks.log` present after `--hourly-deadline-minutes` (default 75) with
   at least one monotonically increasing `Hour N:` entry.
9. `shadow_block_probe.json` with auditable `REJECTED` result when
   `--require-shadow-block-probe` is set.

**Integration with cron runs:** Run the supervisor after each hourly cron invocation:

```bash
# Combined cron line (adjust path)
0 * * * * cd /path/to/repo && \
  SOAK_RUN_INTENT=lr030 ./infrastructure/scripts/soak_monitor.sh >> artifacts/soak_cron.log 2>&1 && \
  python infrastructure/scripts/lr030_soak_supervisor.py \
    "$(cat artifacts/soak_active_run_path_lr030.txt)" >> artifacts/soak_cron.log 2>&1
```

**Output:** Always JSON to stdout. Example for a passing run:

```json
{
  "schema_version": "1.0",
  "status": "RUNNING_VALID",
  "artifact_path": "artifacts/soak_lr030_20260516_120000",
  "run_intent": "lr030",
  "elapsed_minutes": 90.0,
  "hourly_check_count": 1,
  "hourly_hours_logged": [1],
  "checks": { "artifact_path_prefix_valid": true, "run_intent_is_lr030": true, "..." },
  "failures": []
}
```

## Disable / Rollback

```bash
# Remove cron entry
crontab -e   # delete the soak_monitor line

# Or comment out temporarily
# 0 * * * * cd /path/to/repo && ./infrastructure/scripts/soak_monitor.sh ...
```

No rollback needed for the script itself; it is read-only against the stack.
