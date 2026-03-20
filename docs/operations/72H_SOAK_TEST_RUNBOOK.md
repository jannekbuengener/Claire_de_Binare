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

Boundary for this runbook:
- LR-040 preparation: host preflight, stack health, artifact-dir readiness
- LR-040 operative execution: the real 72h soak run and hourly evidence capture
- LR-040 committed repo materialization: evaluate raw artifacts, then materialize
  `reports/p5_canary/<YYYY-MM-DD>/lr040/lr040_soak_gate_eval.json`
- P5 core handoff: separate prestart/decision artifacts under
  `reports/p5_canary/<YYYY-MM-DD>/`
- Shadow-prereq evidence: separate CI/manual path, not a valid LR-040 PASS source

Gate criteria:
- Zero container restarts across all `cdb_*` services
- No OOM kills
- Disk free > 10%
- Signal queue length < 1000 (no stalls)

## Supported Execution Environment

The normative LR-040 execution path is **Linux userland only**:

- supported: native Linux shell
- supported: WSL2 Linux shell
- unsupported: native Windows PowerShell
- unsupported: `cmd.exe`
- unsupported: Git Bash / MSYS / ad-hoc GNU compatibility layers

Reason:

- `soak_monitor.sh` is a bash/GNU script
- the runbook requires `crontab`
- the scheduler and command semantics are Linux-native
- maintaining a second PowerShell scheduler/tooling path would create dual-path
  drift for a safety-critical 72h gate

If the operator machine is Windows, the LR-040 run must still be launched from a
WSL2 Linux shell. Do not execute LR-040 from native PowerShell.

Hard environment gate before any real 72h run:

```bash
bash infrastructure/scripts/check_lr040_runtime_env.sh
```

If this precheck fails, stop. Do not improvise a Windows-native fallback.

## Host Stability

The 72h soak host must stay up for the full window. Automatic host restarts
invalidate the run.

- native Linux: check unattended-upgrade reboot behavior before the run
- WSL2: keep the Linux distro alive for the full run and prevent the underlying
  Windows host from rebooting during the window

This is an operator prerequisite only. It does not authorize a P5 start.

## Start Procedure

```bash
# 0. Validate deterministic runtime environment
bash infrastructure/scripts/check_lr040_runtime_env.sh

# 1. Pull latest main
git pull origin main

# 2. Start BLUE core stack
docker compose -f infrastructure/compose/compose.blue.yml up -d

# 3. Verify all services healthy
docker ps --filter name=cdb_ --format '{{.Names}}: {{.Status}}'

# 4. Verify monitoring
curl -s http://localhost:9090/-/ready   # Prometheus
curl -s http://localhost:3000/api/health # Grafana

# 5. Create artifacts dir and validate monitor script
mkdir -p artifacts

# 6. Dry run
bash infrastructure/scripts/soak_monitor.sh

# 7. Install cron (adjust path)
(crontab -l 2>/dev/null; echo "0 * * * * cd $(pwd) && bash infrastructure/scripts/soak_monitor.sh >> artifacts/soak_cron.log 2>&1") | crontab -
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
bash infrastructure/scripts/soak_monitor.sh
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

**Materialize committed verdict anchor (repo-only handoff step):**

```bash
python infrastructure/scripts/materialize_lr040_verdict_anchor.py \
  artifacts/soak_test_YYYYMMDD_HHMMSS \
  reports/p5_canary/<YYYY-MM-DD>/
cat reports/p5_canary/<YYYY-MM-DD>/lr040/lr040_soak_gate_eval.json
```

**Committed P5 reference path (separate, outside this runbook):**
- `reports/p5_canary/<YYYY-MM-DD>/lr040/lr040_soak_gate_eval.json`

**Verdict interpretation (no P5 release decision):**
- PASS: `lr040_soak_gate_eval.json` verdict is `PASS`
- FAIL: any check failed — see `failures` array for root cause before re-attempting
- materialization alone is not PASS; PASS must already come from the real raw
  72h evaluator output
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
