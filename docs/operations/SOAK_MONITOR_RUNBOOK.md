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

## Disable / Rollback

```bash
# Remove cron entry
crontab -e   # delete the soak_monitor line

# Or comment out temporarily
# 0 * * * * cd /path/to/repo && ./infrastructure/scripts/soak_monitor.sh ...
```

No rollback needed for the script itself; it is read-only against the stack.
