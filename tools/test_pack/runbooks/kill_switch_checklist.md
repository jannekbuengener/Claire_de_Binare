# Kill-Switch Operator Drill Checklist

Goal: stop order flow safely and verifiably via kill-switch drill.

## Prerequisites

- You are in the CDB repo root directory.
- Python 3.12 with `core/` importable (deps installed).
- Docker stack running (optional — needed for stack logs only).
- Evidence directory path ready (e.g., `evidence-drill/YYYY-MM-DD_operator-drill/`).

## Run the Drill

```powershell
pwsh tools/test_pack/tools/drills/trigger-operator-drill.ps1 `
  -EvidenceDir "evidence-drill/$(Get-Date -Format 'yyyy-MM-dd')_operator-drill" `
  -WaitSeconds 60
```

Add `-SkipStackLogs` if no Docker stack is running.
Add `-SkipLr003` to skip the repo-local fail-closed gate drill.

## Steps (record timestamps)

1. **See the alert**: The script emits a `Write-Warning` console alert.
   - Artifact: `alert_trigger.json` (written automatically).

2. **Activate kill-switch** (operator action):
   ```bash
   python -c "from core.safety.kill_switch import activate_kill_switch, KillSwitchReason; activate_kill_switch(KillSwitchReason.MANUAL, 'Operator drill', 'drill-operator')"
   ```
   - The script waits `-WaitSeconds` for you to complete this step.

3. **Verification** (automated by script):
   - Script calls `get_kill_switch_details()` and writes result to
     `reports/kill_switch_verification.json`.
   - Expected: `kill_switch_active: true`.

4. **LR-003 fail-closed gate evidence** (automated, unless `-SkipLr003`):
   - Runs `scripts/drills/lr003_kill_switch_limit_controls_runner.py`.
   - Artifacts: `reports/lr003/lr003_summary.json`, `reports/lr003/lr003_report.md`.
   - Proves that risk and execution gates block when kill-switch is active.

5. **Stack logs** (automated, unless `-SkipStackLogs`):
   - Artifact: `service_logs/stack.log` or `service_logs/stack_logs_error.txt`.

6. **Screenshots** (manual):
   - Place operator screenshots in `screenshots/`.
   - Examples: Grafana dashboard, terminal output, alert notification.

## Evidence Pack Contents

After a successful drill, the evidence directory contains:

```
<EvidenceDir>/
  README.md                              # from template (if available)
  run_config.json                        # drill parameters
  sources_manifest.txt                   # script + source hashes
  timeline.json                          # timestamped drill events
  alert_trigger.json                     # alert payload
  reports/
    kill_switch_verification.json        # kill-switch state check
    lr003/                               # fail-closed gate evidence
      lr003_summary.json
      lr003_report.md
  service_logs/
    stack.log                            # or stack_logs_error.txt
  screenshots/                           # manual operator screenshots
```

## Post-Drill

- [ ] Was the alert visible and clear?
- [ ] Was the kill-switch activation command unambiguous?
- [ ] Did verification confirm `kill_switch_active: true`?
- [ ] Did LR-003 drill pass (all fail-closed gates verified)?
- [ ] Any ambiguous runbook step?

### Deactivate kill-switch after drill

```bash
python -c "from core.safety.kill_switch import KillSwitch; ks = KillSwitch(); ks.deactivate('drill-operator', 'Drill complete, resuming normal operation')"
```

## Known Blockers

- **Alert channel**: No active external alert trigger (Alertmanager is `NOT used`
  per `docs/operations/ALERTING_FIX_SUMMARY.md`). The drill uses a local console
  alert. A real alert channel requires upstream work outside #661.
- **Runtime order-flow-stop verification**: Verifying that order flow actually
  stopped at runtime (via metrics/logs) requires a running stack with active
  order flow and depends on #657. The drill verifies kill-switch state
  (the canonical gate) and uses LR-003 for deterministic fail-closed proof.
