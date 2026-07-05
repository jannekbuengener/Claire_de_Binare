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
| Write-audit (artifact completeness/consistency) | #3361 | Implemented |
| Boot readiness (reboot- and Docker-ready checks) | #3360 | Implemented |
| 72h ops validation (final composition validator) | #3362 | Implemented |

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
| `coordinator_events.jsonl` | Coordinator lifecycle telemetry stream | Yes (append-only for the run) |
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
| `run_id` | string | Coordinator run identifier |
| `total_cycles_started` | int | Total coordinator cycle attempts |
| `total_cycles_completed` | int | Total coordinator cycles completed |
| `total_successful_cycles` | int | Total completed successful coordinator cycles |
| `total_failed_cycles` | int | Total failed coordinator cycles |
| `last_cycle_started_at_utc` | string | ISO-8601 UTC of last cycle start |
| `next_cycle_due_at_utc` | string | ISO-8601 UTC of the next scheduled cycle while sleeping |
| `last_successful_artifact_stamp` | string | Stamp of the last successful artifact cycle |
| `coordinator_status` | string | Coordinator lifecycle status such as `running`, `sleeping`, `resuming`, `recovering`, `final_validation`, `completed`, or `failed` |

## Coordinator Lifecycle Telemetry

Version: `cdb.evidence_harvester.coordinator_event.v1`

`coordinator_events.jsonl` is the canonical coordinator lifecycle stream for
coordinator-managed runs. Each line is one JSON object with at minimum:

- `schema_version`
- `event_at_utc`
- `run_id`
- `event_type`

When applicable the event also carries `cycle_index`, `artifact_stamp`,
`verdict`, `next_cycle_due_at_utc`, `recovery_attempt`, `error_classification`,
and `coordinator_status`.

## Timestamp Contract

- UTC is canonical.
- Validation uses artifact UTC timestamps.
- Local timezone differences must not affect validation.
- Freshness calculations use UTC only.
- Historical artifacts remain valid evidence even when old.

## Watchdog (#3359)

The watchdog (`watchdog.py`) consumes `runner_heartbeat.json` and
`runner_state.json` plus all stamped artifacts to detect stalls, repeated
failures, missed heartbeats, or stale evidence.

For coordinator-managed runs, Watchdog also treats `coordinator_status=sleeping`
with a valid future `next_cycle_due_at_utc` as an explicit healthy sleep window.

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

## Write-Audit (#3361)

The write-audit (`write_audit.py`) verifies that the evidence harvester actually
produces complete, readable, temporally consistent, and usable artifact sets. It
is a downstream consumer of the runner output directory.

### Supported checks (10 check groups, A001–A010)

| ID   | Check                            | Failure Condition                        |
|------|----------------------------------|------------------------------------------|
| A001 | Required artifacts present       | Missing collector/snapshot/alert/heartbeat/state/watchdog |
| A002 | JSON artifacts parse             | Malformed or non-dict JSON               |
| A003 | Schema versions match            | Unexpected schema_version in any artifact |
| A004 | Hash linkage                     | Snapshot collector_report_hash mismatches no collector report |
| A005 | Safety flags                     | lr_status/live_status/echtgeld_status not NO-GO |
| A006 | Timestamp coherence              | Stale heartbeat/snapshot or invalid timestamps |
| A007 | Source modes valid               | source_mode not in fixture/future_readonly |
| A008 | Artifact sizes sane              | Zero-byte or oversized artifacts         |
| A009 | Markdown companions              | Snapshot/alert/watchdog JSON without MD companion |
| A010 | Metadata fields present          | Missing or empty schema_version/generated_at_utc/source_mode |

### Usage

```powershell
# Default audit
python -m tools.evidence_harvester.write_audit

# Save outputs
python -m tools.evidence_harvester.write_audit ^
    --artifact-dir artifacts\evidence_harvester\runner ^
    --json-output artifacts\evidence_harvester\write_audit_report.json ^
    --markdown-output artifacts\evidence_harvester\write_audit_report.md
```

### Safety boundaries

- Read-only; never modifies artifacts
- No automatic restart, GitHub write, Docker, runtime, DB, Redis, or secrets action
- Feeds #3362 (OPS validation) with structured artifact completeness evidence

### Outputs

- `write_audit_report.json` — machine-readable report with per-check findings + verdict
- `write_audit_report.md` — human-readable Markdown summary

## Recovery Semantics (#3368)

The current recovery contract distinguishes recoverable failures from fatal
failures. Recoverable failures produce audited recovery artifacts and allow the
run to continue within bounded restart and backoff limits. Fatal failures stop
immediately and fail validation.

### Recoverable failures

- stale latest snapshot
- transient watchdog failure
- transient write-audit failure

### Recoverable action

- create `recovery_event_<stamp>.json`
- create `recovery_event_<stamp>.md`
- apply bounded restart
- apply backoff
- continue run

Historical snapshots, watchdog reports, and write-audit reports remain
auditable history. Snapshot freshness is evaluated on the latest snapshot, and
a long-lived run does not fail solely because older stamped artifacts are old.

The current coordinator classifier is stricter for core-state freshness:
findings on `runner_heartbeat.json.current_run_at_utc` and
`runner_state.json.last_cycle_ended_at_utc` are currently treated as fatal
`malformed_core_state`, not as recoverable restart events.

### Fatal failures

- safety boundary violation
- live-trading path
- real-money path
- DB mutation risk
- secrets exposure
- stale or invalid latest heartbeat core-state timestamp
- stale or invalid latest runner-state core-state timestamp
- unrecoverable core-state corruption

### Fatal action

- immediate stop
- no recovery
- fail validation

## Coordinator Resume & Sleep-Stall Supervisor (#3634)

### Root cause

Slice-B/C/D all ended `INCONCLUSIVE` with the same signature: the coordinator
process died inside the in-process blocking sleep between the durable
`sleep_started` and `sleep_completed` events. `run_fixture_window` re-initialised
`completed_cycles = 0` on every launch, so there was no safe resume — a restart
either re-ran the whole window or double-counted. `ops_validation` detects the
post-hoc symptom (O264 sleep-lifecycle warn, O303 INCONCLUSIVE) but cannot
recover it.

### Resume-safe coordinator

`resume-fixture-window` (same arguments as `run-fixture-window`) continues an
interrupted run from durable state instead of restarting it:

```powershell
python -m tools.evidence_harvester.coordinator resume-fixture-window ^
    --fixture artifacts\evidence_harvester\24h_dry_run\collector_input.json ^
    --artifact-dir artifacts\evidence_harvester\72h_ops_validation\<run_id> ^
    --iterations 288 ^
    --cadence-seconds 900
```

- Seeds `completed_cycles` from `runner_state.total_cycles_completed` (no
  re-run, no double count).
- Stall predicate: last durable event is `sleep_started` and
  `coordinator_status == "sleeping"`. On match it writes a `sleep_resumed`
  lifecycle event plus an audited `recovery_event_<stamp>.json`
  (`failure_source="sleep_stall"`, `action="resume_cycle_window"`), then
  continues to the next cycle — or straight to final validation if all cycles
  are already complete.
- Idempotent: resuming a fully-cycled window goes directly to
  `final_validation_started`/`final_validation_completed` without repeating
  cycles.
- Fail-closed guards (raise `CoordinatorError`): missing `runner_state.json`,
  `run_id` mismatch vs the artifact directory, or terminal status
  (`completed` / `failed` / `fatal_stop`).

A resumed run that reaches `final_validation_completed` clears both O264 and
O303: the event stream no longer ends on `sleep_started`, and a final validation
marker exists.

### Sleep-stall supervisor

`supervisor.py` is a testable decision + bounded-relaunch layer. It does not
spawn processes, install an OS scheduler, or touch Docker/DB/Redis/secrets.

`decide_supervision(state, events, now, process_alive, relaunch_count,
max_relaunch_count)` returns exactly one action:

| Action | Condition |
|---|---|
| `DONE` | `coordinator_status == "completed"` or a `final_validation_completed` event is present |
| `STOP_FATAL` | terminal status `failed` / `fatal_stop` |
| `RELAUNCH_RESUME` | stalled sleep (`sleep_started` last, status `sleeping`) past `next_cycle_due_at_utc` with a dead process, within relaunch budget |
| `STOP_LIMIT` | relaunch condition met but `relaunch_count >= max_relaunch_count` |
| `WAIT` | process alive, or no relaunch condition met |

Read-only decision preview:

```powershell
python -m tools.evidence_harvester.supervisor status ^
    --artifact-dir artifacts\evidence_harvester\72h_ops_validation\<run_id> ^
    --pretty
```

`supervise` runs the poll/relaunch loop in-process and is fail-closed behind
`--explicit` (without it, only the plan is printed). The loop is fully injectable
(`launcher`, `process_alive_fn`, `now_fn`, `sleep_fn`) and bounded by
`--max-relaunch-count` and optional `--max-polls`.

### External supervisor scaffold (#3733 Phase 1)

Phase 1 adds out-of-process supervision **scaffold only** — no Tier-1 runtime
proof in the merge slice. See
[`docs/evidence/evidence_harvester_host_resilience_tiers.md`](../evidence/evidence_harvester_host_resilience_tiers.md).

| Artifact / command | Purpose |
|---|---|
| `coordinator_pid.json` | PID record for injectable liveness probe |
| `supervision_state.json` | Poll/relaunch durable state |
| `plan-external` | Safe plan JSON (default) |
| `supervise-external --explicit` | PID probe + detached subprocess resume launcher |
| `resume_launch_evidence.jsonl` | Per-relaunch argv/cwd/pid/launch_error audit trail |
| `record-coordinator-pid` | Write PID record after detached coordinator start |

PowerShell wrapper (safe default `plan`):

```powershell
.\scripts\evidence_harvester_supervisor.ps1 -Action plan `
    -ArtifactDir artifacts\evidence_harvester\72h_ops_validation\<run_id> `
    -Fixture artifacts\evidence_harvester\24h_dry_run\collector_input.json `
    -Iterations 293 -Pretty
```

Read-only status with PID probe:

```powershell
python -m tools.evidence_harvester.supervisor status `
    --artifact-dir artifacts\evidence_harvester\72h_ops_validation\<run_id> `
    --use-pid-probe --pretty
```

Execution (`supervise-external`) requires `--explicit` and a separate **Operator
Runtime-GO**. LR remains **NO-GO**. #3345 stays **OPEN** until Tier-1 proof or
accepted downgrade closes #3733.

**Tier-1 retry parameters (recommended after Windows launcher fix):**

| Parameter | Value |
|---|---|
| `cadence-seconds` | **120** (avoid killing before cycle-1 sleep settles) |
| Kill timing | During cycle-1 sleep, after `sleep_started` and before `next_cycle_due_at_utc` |
| Proof dir | `artifacts/evidence_harvester/host_resilience_proof/tier1-retry-<UTC>/` |
| Pass criteria | `relaunch_count >= 1`, supervisor-spawned `run_resumed`, post-resume PASS cycle |

First canonical proof run `tier1-20260705T104800Z` **FAIL** — stall detection and
`relaunch_count=1` worked; subprocess resume child exited without `run_resumed`
(manual identical `Popen` control succeeded). See
[`docs/evidence/evidence_harvester_host_resilience_tiers.md`](../evidence/evidence_harvester_host_resilience_tiers.md).

## Safety Boundaries

- No Docker start/stop, runtime start, DB execution/mutation, secrets access
- No LR-Go, no Live-Go, no Echtgeld-Go
- `resume-fixture-window` reads durable state only; it never rewinds completed cycles
- `supervisor supervise` requires `--explicit`; `supervisor status` is read-only
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

## Boot Readiness (#3360)

The `boot.py` module checks whether the evidence harvester is reboot- and
Docker-ready without performing any mutations. It is the default entry point
after a system restart.

### Modes

| Mode | Description |
|------|-------------|
| `status` (default) | Full readiness: repo root, module imports, artifact dirs, scheduler script, Docker detection, safety boundaries, command plan |
| `preflight` | Quick module-import and path check only |
| `install-plan` | Print safe command plan for Task/Docker setup — no execution |
| `render-operator-handoff` | Complete handoff document for enabling always-on mode |

### Usage

```powershell
# Full status
python -m tools.evidence_harvester.boot status --pretty

# Quick preflight
python -m tools.evidence_harvester.boot preflight --pretty

# Install plan (does NOT execute)
python -m tools.evidence_harvester.boot install-plan --pretty

# Operator handoff
python -m tools.evidence_harvester.boot render-operator-handoff

# PowerShell wrapper
pwsh -NoProfile -File .\scripts\evidence_harvester_boot.ps1 -Action status -Pretty
```

### Verdict contract

| Verdict | Conditions |
|---------|-----------|
| PASS    | All B001–B007 checks pass: repo valid, modules importable, artifact dirs ok, scheduler present (or warn), Docker detected or warn, safety ok, command plan available |
| WARN    | Docker not on PATH, scheduler script missing, artifact dir created during check, safety banner not verified |
| FAIL    | Repo root invalid, module import fails, artifact dir not creatable, safety boundary violated |

### Checks (B001–B007)

| ID   | Check                            | Failure Condition                        |
|------|----------------------------------|------------------------------------------|
| B001 | Repo root valid                  | Repo root missing or no `.git` directory |
| B002 | Harvester modules importable     | Any of 8 core modules fails to import    |
| B003 | Artifact dirs available          | Required artifact directory not creatable |
| B004 | Scheduler script present         | `scripts/evidence_harvester_task.ps1` missing |
| B005 | Docker available (detect only)   | Docker not on PATH (warn only)          |
| B006 | Safety boundaries ok             | Missing safety banner in runner module   |
| B007 | Command plan available           | Safe command list can be produced        |

### Boot readiness vs OPS validation (#3362)

Boot readiness (#3360) is the precondition for #3362:

1. Run `boot status` to verify the system is ready.
2. If PASS, proceed to #3362 OPS validation for Windows Task installation
   and Docker enablement.
3. If WARN, review findings before proceeding.
4. If FAIL, fix root causes before any OPS validation.

### Docker boundary

- Boot readiness **detects** Docker availability (`Docker available: yes/no`).
- Boot readiness does **not** start Docker, run `docker compose up`, or perform
  any Docker mutation.
- Docker enablement requires a separate Infra-Mutation-Gate approval as part of #3362.
- The `install-plan` mode prints the intended Docker command but does not
  execute it.

### Safety boundaries

- Default mode is `status` — read-only assessment.
- No Docker start/stop, runtime start, DB mutation, secrets access.
- No Windows Task installation — that requires `scheduler install --explicit`
  under #3362.
- No LR-Go, no Live-Go, no Echtgeld-Go.

## 72h Ops Validation (#3362)

The `ops_validation.py` module is the final read-only validation surface for the
real `>=72h` always-on dry run. It validates one finished artifact directory and
composes runner continuity, snapshot/alert coverage, watchdog history,
write-audit history, boot readiness, and safety boundaries into a final
PASS/WARN/FAIL verdict.

### Phase-2 artifact contract

- `artifacts/evidence_harvester/72h_ops_validation/<run_id>/`
- `collector_report_<stamp>.json`
- `snapshot_<stamp>.json`
- `snapshot_<stamp>.md`
- `alert_<stamp>.json`
- `alert_<stamp>.md`
- `runner_heartbeat.json`
- `runner_state.json`
- `watchdog_report_<stamp>.json`
- `watchdog_report_<stamp>.md`
- `write_audit_report_<stamp>.json`
- `write_audit_report_<stamp>.md`
- `boot_readiness_report.json`
- `boot_readiness_report.md`
- `ops_validation_report.json`
- `ops_validation_report.md`

### Phase-2 runtime contract

- Seed fixture: `artifacts/evidence_harvester/24h_dry_run/collector_input.json`
- Cadence: every `900` seconds / `15` minutes
- Watchdog: after each runner cycle
- Write-audit: after each runner cycle
- Final validation: after `>=72h` over the whole artifact directory

### Usage

```powershell
python -m tools.evidence_harvester.ops_validation validate-dir ^
    --artifact-dir artifacts\evidence_harvester\72h_ops_validation\<run_id> ^
    --json-output artifacts\evidence_harvester\72h_ops_validation\<run_id>\ops_validation_report.json ^
    --markdown-output artifacts\evidence_harvester\72h_ops_validation\<run_id>\ops_validation_report.md ^
    --pretty
```

### Safety boundaries

- Read-only validation only; does not start the 72h run
- No Windows Task install, Docker/runtime/DB/secrets mutation, or GitHub writes
- No LR-Go, no Live-Go, no Echtgeld-Go

## Always-On Acceptance Criteria

- Evidence is produced continuously.
- Recoverable failures do not permanently stop the run.
- Watchdog continuously monitors the harvester.
- Write-audit continuously validates artifacts.
- Boot readiness remains valid.
- Ops validation proves `>=72h` operation.
- LR remains NO-GO.
- Live remains NO-GO.
- Echtgeld remains NO-GO.

## Lessons Learned

Reserved for post-72h validation findings.

Do not populate until the replacement run has completed.

## Related Documents

- `tools/evidence_harvester/README.md` — module-level documentation
- `tools/evidence_harvester/runner.py` — source
- `tools/evidence_harvester/coordinator.py` — coordinator + resume source (#3634)
- `tools/evidence_harvester/supervisor.py` — sleep-stall supervisor source (#3634)
- `tools/evidence_harvester/boot.py` — boot readiness source
- `docs/runbooks/CDB_EVIDENCE_HARVESTER_24H_DRY_VALIDATION.md` — 24h dry validation runbook
- `docs/runbooks/CDB_EVIDENCE_HARVESTER_72H_OPS_VALIDATION.md` — final >=72h validation runbook
