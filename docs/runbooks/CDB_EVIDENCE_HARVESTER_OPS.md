# CDB Evidence Harvester Ops Runbook

## Purpose

Operational guide for the evidence harvester runner, watchdog, and write-audit
pipelines. This runbook covers the managed continuous harvester (`runner.py`),
its state/heartbeat artifacts, and the downstream consumers (watchdog #3359,
write-audit #3361).

## Status

| Component | Issue | Status |
|-----------|-------|--------|
| Runner (collector -> snapshot -> alert) | #3358 | Implemented |
| Watchdog (heartbeat/state consumption) | #3359 | Implemented |
| Write-audit (heartbeat/state consumption) | #3361 | Planned |

## LR Status

**LR remains NO-GO.** No runner invocation, no artifact, and no downstream
consumer authorizes live trading, Echtgeld trading, or any runtime action.

## Runner Usage

The runner supports four modes. Default is `plan` (safe dry-run).

```powershell
# Safe default — prints plan
python -m tools.evidence_harvester.runner

# One complete collector + snapshot + alert cycle
python -m tools.evidence_harvester.runner run-once-fixture `
    --fixture path\to\collector_input.json `
    --output-dir artifacts\evidence_harvester\runner `
    --generated-at-utc 2026-06-19T16:00:00Z `
    --pretty

# Bounded loop (no unlimited loop)
python -m tools.evidence_harvester.runner loop-fixture `
    --fixture path\to\collector_input.json `
    --output-dir artifacts\evidence_harvester\runner `
    --iterations 5 `
    --interval-seconds 60 `
    --pretty

# Local artifact status
python -m tools.evidence_harvester.runner status --output-dir artifacts\evidence_harvester\runner --pretty
```

## Artifacts

Each runner cycle writes to the configured `--output-dir`:

| File | Description | Overwritten? |
|------|-------------|-------------|
| `collector_report_<stamp>.json` | Raw collector report | No (stamped) |
| `snapshot_<stamp>.json` | Normalized snapshot | No (stamped) |
| `snapshot_<stamp>.md` | Markdown snapshot summary | No (stamped) |
| `alert_<stamp>.json` | Alert findings | No (stamped) |
| `alert_<stamp>.md` | Markdown alert summary | No (stamped) |
| `runner_heartbeat.json` | Latest cycle metadata | Yes (per cycle) |
| `runner_state.json` | Cumulative run statistics | Yes (per cycle) |

## Heartbeat Schema

Version: `cdb.evidence_harvester.runner_heartbeat.v1`

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Fixed heartbeat schema version |
| `runner_mode` | string | `run-once-fixture` or `loop-fixture` |
| `iteration` | int | Current iteration (0 for single run, 1-based for loop) |
| `started_at_utc` | string | ISO-8601 UTC session start |
| `current_run_at_utc` | string | ISO-8601 UTC of this heartbeat |
| `last_success_at_utc` | string | ISO-8601 UTC of last successful cycle (empty if none) |
| `last_failure_at_utc` | string | ISO-8601 UTC of last failed cycle (empty if none) |
| `last_error` | string | Error message from last failure (empty if all ok) |
| `last_collector_report` | string | Path to last collector report artifact |
| `last_snapshot_json` | string | Path to last snapshot JSON artifact |
| `last_snapshot_markdown` | string | Path to last snapshot Markdown artifact |
| `last_alert_json` | string | Path to last alert JSON artifact |
| `last_alert_markdown` | string | Path to last alert Markdown artifact |

## State Schema

Version: `cdb.evidence_harvester.runner_state.v1`

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Fixed state schema version |
| `total_runs` | int | Total cycles attempted |
| `successful_runs` | int | Cycles that completed without error |
| `failed_runs` | int | Cycles that raised an exception |
| `last_cycle_verdict` | string | `PASS` or `FAIL` |
| `last_cycle_ended_at_utc` | string | ISO-8601 UTC of last cycle end |

## Watchdog (#3359)

The watchdog (`watchdog.py`) consumes `runner_heartbeat.json` and
`runner_state.json` plus all stamped artifacts to detect stalls, repeated
failures, missed heartbeats, or stale evidence.

### Modes

- `status` — full read-only inspection: heartbeat freshness, runner state,
  required artifact presence, JSON integrity, safety flags, and snapshot cadence
- `check-artifacts` — artifact presence and integrity only (skip heartbeat/state)
- `render-escalation-draft` — render a manual escalation draft from a saved report JSON

### Verdicts

| Verdict | Meaning |
|---------|---------|
| PASS    | All checks clean: heartbeat fresh, state PASS, required artifacts present, no malformed JSON, safety flags correct |
| WARN    | Some non-critical thresholds exceeded: artifact age near limit, runner has historical failures, snapshot cadence slightly exceeded |
| FAIL    | Critical issue: stale heartbeat, missing heartbeat/state, missing required artifact, malformed JSON, runner FAIL verdict, or wrong safety flag |

### Usage

```powershell
# Full status check (default)
python -m tools.evidence_harvester.watchdog status ^
    --artifact-dir artifacts\evidence_harvester\runner ^
    --pretty

# Save outputs
python -m tools.evidence_harvester.watchdog status ^
    --artifact-dir artifacts\evidence_harvester\runner ^
    --json-output artifacts\evidence_harvester\watchdog_report.json ^
    --markdown-output artifacts\evidence_harvester\watchdog_report.md ^
    --escalation-draft-output artifacts\evidence_harvester\manual_escalation_draft.md

# Deterministic evaluation
python -m tools.evidence_harvester.watchdog status ^
    --artifact-dir artifacts\evidence_harvester\runner ^
    --evaluated-at-utc "2026-06-19T16:00:00Z"
```

### Safety boundaries

- Read-only; never modifies heartbeat, state, or artifact files
- No automatic restart, GitHub write, Docker, runtime, DB, Redis, or secrets action
- Escalation draft is local text output only; human review required
- Feeds #3361 (write-audit) and #3362 (OPS validation)

### Incident Response for Watchdog

#### Watchdog reports FAIL

1. Run `python -m tools.evidence_harvester.watchdog status --pretty` to see which check failed.
2. Check `runner_heartbeat.json` exists and has recent `current_run_at_utc`.
3. Check `runner_state.json` exists and `last_cycle_verdict` is `PASS`.
4. Verify required artifact files exist in the artifact directory.
5. If heartbeat is stale, check whether the runner is still running.
6. If artifacts are missing, check the runner output directory permissions and paths.
7. If JSON is malformed, inspect the file manually.
8. Fix the root cause and re-run the watchdog to verify PASS.

#### Watchdog reports WARN

1. Review the warn-level findings.
2. If heartbeat age is near threshold, the runner may be running slower than expected.
3. If failed_runs > 0, inspect the runner error log or heartbeat `last_error`.
4. If snapshot cadence is exceeded, check whether the snapshot interval needs adjustment.
5. Take corrective action within the next operational window.

#### Watchdog escalation draft

1. Use `render-escalation-draft` after a FAIL to produce human-readable escalation text.
2. Review the draft before creating any GitHub issue manually.
3. No automatic GitHub writes are performed by the watchdog.

## Write-Audit (Planned, #3361)

The write-audit consumer will use the heartbeat's `last_alert_json` path to
read alert findings and, after human confirmation, produce GitHub issue drafts
or comments. Design note:

- Default-off; no automatic GitHub writes
- Human gate required before any GitHub action
- Separate module with its own safety boundaries

## Safety Boundaries

- No Docker start/stop, runtime start, DB execution/mutation, secrets access
- No LR-Go, no Live-Go, no Echtgeld-Go
- `loop-fixture` is always bounded (`--iterations N` required)
- Failure in one loop iteration raises immediately (fail-closed)
- Signal handling: SIGTERM/SIGINT cleanly stop the loop at the next iteration boundary

## Incident Response

### Runner fails with `AssertionError` or `CollectorValidationError`

1. Check the fixture JSON is valid and matches the expected schema.
2. Check `runner_heartbeat.json` for the error message.
3. Re-run with `run-once-fixture --pretty` to see the full error trace.

### Runner exits with non-zero exit code

1. Run `status` to check the last verdict and error.
2. If `failed_runs > 0`, inspect the error from the heartbeat.
3. Fix the underlying issue (usually malformed fixture or missing path) and retry.

### Loop stops early (SIGTERM/SIGINT)

1. Verify which iteration stopped via the final heartbeat.
2. Restart with `--iterations` adjusted for remaining cycles if needed.

## Related Documents

- `tools/evidence_harvester/README.md` — module-level documentation
- `tools/evidence_harvester/runner.py` — source
- `docs/runbooks/CDB_EVIDENCE_HARVESTER_24H_DRY_VALIDATION.md` — 24h dry validation runbook
