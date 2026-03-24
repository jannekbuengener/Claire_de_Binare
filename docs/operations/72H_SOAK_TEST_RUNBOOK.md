# 72h Zero Restart Soak Test Runbook

Issue #428.

## Goal

Run the full CDB Compose stack for 72 consecutive hours with zero
container restarts. This gate must pass before any live deployment.

This runbook produces raw 72h soak run artifacts under
`artifacts/soak_test_*`. It does not define or create the normative committed
P5 core artifact contract under `reports/p5_canary/<YYYY-MM-DD>/`, and it does
not produce a P5 start authorization by itself.

Terminology used here follows current governance:
- `execution_status.mode` is the canonical runtime-mode field
- the current shadow-/prestart-prereq path expects runtime-mode `mock`
- `shadow` names shadow/probe/evidence semantics
- `full|lean` name soak/collection profiles, not runtime-mode values

Gate criteria:
- Zero container restarts across all `cdb_*` services
- No OOM kills
- Disk free > 10%
- Signal queue length < 1000 (no stalls)

## Pre-Flight: Windows Host

On Windows hosts, automatic OS restarts can invalidate a 72h soak run.
Windows Update Active Hours cover at most 18h and are not sufficient.

**Confirmed behavior (Incident 2026-03-11):** Windows Update triggered
two automatic reboots overnight via `MoUsoCoreWorker.exe` and
`TrustedInstaller.exe`. Docker containers auto-restarted via
`restart: unless-stopped`, but the soak monitor correctly detected the
restart and marked the run as FAILED after only 2h.

Before starting a 72h run on a Windows host:

1. **Check for pending reboots.** If any key exists, reboot first, then
   start the soak run.
   ```powershell
   Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired" -EA SilentlyContinue
   Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending" -EA SilentlyContinue
   ```

2. **Prevent automatic reboots during the run.** Choose one option:

   - **Option A — Pause updates for 4 days** (Settings UI or PowerShell):
     ```powershell
     $pause = (Get-Date).AddDays(4).ToString("yyyy-MM-ddTHH:mm:ssZ")
     Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" `
       -Name "PauseUpdatesExpiryTime" -Value $pause
     ```
   - **Option B — Group Policy registry key** (prevents reboot while a
     user is logged in):
     ```powershell
     New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" -Force
     Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" `
       -Name "NoAutoRebootWithLoggedOnUsers" -Value 1 -Type DWord
     ```
   - **Option C — Keep the session unlocked** so Active Hours apply
     (weakest protection, max 18h).

3. **After the soak run completes or is aborted**, remove any temporary
   reboot blocks to allow normal patching.

> This section applies only to Windows development hosts. Linux hosts
> with `unattended-upgrades` have a similar risk; use
> `apt-config dump | grep Unattended-Upgrade::Automatic-Reboot` to check.

## Start Procedure

```bash
# 1. Pull latest main
git pull origin main

# 2. Start BLUE core stack
docker compose -f infrastructure/compose/compose.blue.yml up -d

# 3. Verify all services healthy
docker ps --filter name=cdb_ --format '{{.Names}}: {{.Status}}'

# 4. Verify monitoring
curl -s http://localhost:9090/-/ready   # Prometheus
curl -s http://localhost:3000/api/health # Grafana

# 5. Create artifacts dir and install hourly monitor
mkdir -p artifacts
chmod +x infrastructure/scripts/soak_monitor.sh

# 6. Dry run
./infrastructure/scripts/soak_monitor.sh

# 7. Install cron (adjust path)
(crontab -l 2>/dev/null; echo "0 * * * * cd $(pwd) && ./infrastructure/scripts/soak_monitor.sh >> artifacts/soak_cron.log 2>&1") | crontab -
```

> **Note:** The CI workflow `shadow-soak-evidence.yml` runs automated
> shadow-soak evidence collection and is not the same as this manual
> 72h runtime soak procedure. In that workflow, `full|lean` are collection
> profiles and not runtime-mode values.

## During the Run

**Dashboards:**
Open the soak test dashboard in Grafana. To find name and file:

```bash
grep -n "title" infrastructure/monitoring/grafana/dashboards/*soak* | head -3
```

**What is normal:**
- Container restart count stays at 0
- Memory usage fluctuates but stays below 80% of limit
- Order flow may pause outside market hours (expected)
- Disk usage grows slowly from logs/DB

**Periodic checks (automated by `soak_monitor.sh`):**
- Hourly: container restarts, service health, disk space
- Every 6h: resource snapshots saved to `artifacts/`
- Every 12h: database row counts

## Abort Triggers

The soak test MUST be aborted if any of these occur:

1. **Container restart** — any `cdb_*` container restarts for any reason
2. **OOM kill** — kernel kills a container for memory
3. **Disk full** — free space drops below 10%
4. **Queue stall** — signal queue > 1000 messages for > 10 min

The script writes `soak_test_FAILED.txt` into the artifacts directory
on restart detection. Prometheus alerts with `soak_test: abort` fire
independently.

To see which alerts are abort-triggers:

```bash
grep -B2 "soak_test: abort" infrastructure/monitoring/alerts.yml
```

## Stop / Abort Procedure

```bash
# 1. Remove cron
crontab -l | grep -v soak_monitor | crontab -

# 2. Capture final state
./infrastructure/scripts/soak_monitor.sh
docker ps --filter name=cdb_ > artifacts/final_container_status.txt
docker stats --no-stream > artifacts/final_resources.txt

# 3. Stop stack (optional — may keep running for investigation)
docker compose -f infrastructure/compose/compose.blue.yml down
```

## Post-run

**Artifacts to preserve** (in `artifacts/soak_test_YYYYMMDD_HHMMSS/`):
- `hourly_checks.log` — full timeline of hourly checks
- `resources_snapshot_YYYYMMDD_HH*.txt` — 6h resource snapshots (date-prefixed, no overwrites)
- `db_growth_YYYYMMDD_HH*.txt` — 12h database growth (date-prefixed, no overwrites)
- `lr040_soak_gate_eval.json` — machine-readable verdict (generated post-run)
- `restart_alerts.log` — empty if test passed
- `soak_test_FAILED.txt` — absent if test passed

These are raw run artifacts for LR-040 evaluation. They are not the committed
P5 core evidence root.

**Evaluate (LR-040 gate):**

```bash
python infrastructure/scripts/lr040_soak_gate_eval.py artifacts/soak_test_YYYYMMDD_HHMMSS/
cat artifacts/soak_test_YYYYMMDD_HHMMSS/lr040_soak_gate_eval.json
```

**Committed P5 reference path (separate, outside this runbook):**
- `reports/p5_canary/<YYYY-MM-DD>/lr040/lr040_soak_gate_eval.json`

**Verdict interpretation (no P5 release decision):**
- PASS: `lr040_soak_gate_eval.json` verdict is `PASS`
- FAIL: any check failed — see `failures` array for root cause before re-attempting
- INCONCLUSIVE: environment interruption detected (Docker-daemon or host restart,
  identified by bulk-restart heuristic). Run is invalid but not a SUT defect.
  Run must be restarted. See `soak_test_INCONCLUSIVE.txt` for details
  (`containers`, `uptime_spread_s`, `monitor_container_fresh`). exit 1 (fail-closed).
- A PASS here is a necessary LR-040 evidence anchor only; it does not, by
  itself, create the committed P5 core artifact set and does not change P5 from
  `NO-GO`

## Troubleshooting: Common Issues

| Symptom | Investigation |
|---|---|
| Service down but no restart | Check `docker logs <service> --tail 200`; may be crash-loop with backoff |
| High memory usage (>80%) | Check for leak: `docker stats --no-stream`; compare 6h snapshots |
| Message queue backlog | `docker exec cdb_redis redis-cli XLEN stream.orders`; check signal/risk logs |
| No orders generated for 1h+ | Verify market data flow: `docker logs cdb_ws --tail 50` |
| Cron not firing | `grep CRON /var/log/syslog`; verify docker group membership for cron user |

## High Memory Usage

If `SoakTest_HighMemoryUsage` fires (container > 80% of limit for 30 min):

1. Identify container: check alert label `name`
2. Compare memory across 6h snapshots in artifacts
3. If monotonically increasing: likely memory leak — abort and file bug
4. If stable plateau: may be normal working set — continue monitoring

## Message Queue Backlog

If `SoakTest_MessageQueueStalled` fires (queue > 1000 for 10 min):

1. Check consumer health: `docker logs cdb_signal --tail 100`
2. Check Redis: `docker exec cdb_redis redis-cli XLEN stream.orders`
3. If consumer is alive but slow: resource contention — check CPU/memory
4. If consumer is dead: abort, capture logs
