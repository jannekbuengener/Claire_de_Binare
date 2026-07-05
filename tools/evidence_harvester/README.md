# Evidence Harvester

Passive, fixture-driven collector, snapshot, and local scheduler wrapper for
ARVP/profitability evidence coverage.

## Scope

- normalizes coverage and gap data
- stays read-only and secret-safe
- does not launch services, background jobs, storage writes, or replay paths
- keeps snapshots paper/research only; no LR-Go, no Live-Go, no Echtgeld-Go
- keeps scheduler installation default-off and explicitly gated

## Usage

Fixture mode:

```powershell
python -m tools.evidence_harvester.collector --fixture path\to\collector_input.json --pretty
```

Optional JSON output file:

```powershell
python -m tools.evidence_harvester.collector --fixture path\to\collector_input.json --output out\collector_report.json
```

Daily snapshot artifacts from a collector-report fixture:

```powershell
python -m tools.evidence_harvester.snapshot --fixture path\to\collector_report.json --json-output out\snapshot.json --markdown-output out\snapshot.md --generated-at-utc 2026-06-19T16:00:00Z --pretty
```

Default-off scheduler plan:

```powershell
python -m tools.evidence_harvester.scheduler
```

Explicit plan with fixture/output paths:

```powershell
python -m tools.evidence_harvester.scheduler plan --fixture path\to\collector_input.json --output-dir artifacts\evidence_harvester\scheduled --pretty
```

One fixture-backed run that writes collector report + snapshot JSON + Markdown:

```powershell
python -m tools.evidence_harvester.scheduler run-once-fixture --fixture path\to\collector_input.json --output-dir artifacts\evidence_harvester\scheduled --generated-at-utc 2026-06-19T16:00:00Z --pretty
```

Artifact-only local status:

```powershell
python -m tools.evidence_harvester.scheduler status --output-dir artifacts\evidence_harvester\scheduled --pretty
```

Deterministic alert report from a snapshot fixture:

```powershell
python -m tools.evidence_harvester.alerts --fixture path\to\snapshot.json --json-output out\alerts.json --markdown-output out\alerts.md --evaluated-at-utc 2026-06-19T18:00:00Z --pretty
```

Optional issue-draft text only:

```powershell
python -m tools.evidence_harvester.alerts --fixture path\to\snapshot.json --issue-draft-output out\issue_draft.md --issue-number 3350 --parent-issue 3345
```

Explicit Windows Task install/uninstall wrappers:

```powershell
python -m tools.evidence_harvester.scheduler install --fixture path\to\collector_input.json --explicit
python -m tools.evidence_harvester.scheduler uninstall --explicit
```

PowerShell wrapper defaults to plan-only:

```powershell
pwsh -NoProfile -File .\scripts\evidence_harvester_task.ps1
```

Actual task installation remains explicit:

```powershell
pwsh -NoProfile -File .\scripts\evidence_harvester_task.ps1 -Action install -Fixture path\to\collector_input.json -Explicit
```

## Fixture shape

Required top-level fields:

- `evidence_class`
- `produced_by`
- `produced_at_utc`
- `candle_coverages`
- `regime_coverages`
- `paper_chain_coverages`
- `provenance_observations`

Each section uses aggregated, read-only rows. The collector validates timestamps,
counts, and evidence-class metadata fail-closed.

The snapshot generator accepts collector-report fixtures only. It validates the
report fail-closed, hard-limits `source_mode` to `fixture|future_readonly`, and
renders both JSON and Markdown from the same normalized snapshot object.

Snapshot JSON sections:

- `metadata`
- `coverage`
- `provenance`
- `paper_chains`
- `gap_findings`
- `safety`

Snapshot Markdown sections:

- `Status`
- `Coverage Summary`
- `Paper Chain Summary`
- `Provenance`
- `Gap Findings`
- `Safety Boundaries`
- `Next Action Hints`

Alert report JSON sections:

- `schema_version`
- `evaluated_at_utc`
- `snapshot_generated_at_utc`
- `collector_report_id`
- `collector_report_hash`
- `snapshot_age_minutes`
- `summary`
- `findings`

Alert issue-draft contract:

- plain text/Markdown only
- local file output only
- no automatic GitHub issue creation, comments, or API writes
- manual escalation remains a human review step

## Scheduler contract

Allowed commands:

- `plan`
- `status`
- `run-once-fixture`
- `install --explicit`
- `uninstall --explicit`

Default behavior:

- no invocation installs a task unless `--explicit` is present
- bare `python -m tools.evidence_harvester.scheduler` resolves to safe `plan`
- `status` reads local artifacts only; it does not query Docker, DB, Redis, or runtime services
- scheduled action is limited to the safe fixture-backed snapshot path

Recommended cadence:

- collector status review every 15 minutes (manual/read-only recommendation)
- scheduled snapshot once daily via the safe fixture path

Safety boundaries:

- paper/research evidence only
- no background job orchestration
- no Docker
- no runtime start
- no DB execution or mutation
- no secrets
- no Redis live read/write
- no replay or backfill execution
- no LR-Go, no Live-Go, no Echtgeld-Go
- no autostart by default

## Alerting contract

Alerting reads normalized snapshot fixtures only and fails closed on malformed
input. It classifies evidence gaps into deterministic `info`, `warn`, and
`critical` findings, deduplicates repeated findings by stable `finding_id`, and
can optionally render a manual issue draft.

Use the alert report when you want a local, deterministic status artifact.
Use the issue draft when a human has decided the findings should be escalated to
GitHub manually. The module never creates issues, never posts comments, and does
not perform any runtime, Docker, DB, secrets, or network write behavior.

## Runner (managed continuous harvester)

The `runner.py` module provides a managed run loop for the evidence harvester.
It runs the full collector → snapshot → alert pipeline in `plan`, `status`,
`run-once-fixture`, and `loop-fixture` modes.

### Allowed commands:

- `plan` (default — safe dry-run no-op)
- `status` — read local artifact state (heartbeat + state)
- `run-once-fixture` — one complete collector → snapshot → alert cycle
- `loop-fixture` — bounded iterations with configurable interval

### Usage

Safe default (plan):

```powershell
python -m tools.evidence_harvester.runner
```

One complete cycle:

```powershell
python -m tools.evidence_harvester.runner run-once-fixture `
    --fixture path\to\collector_input.json `
    --output-dir artifacts\evidence_harvester\runner `
    --generated-at-utc 2026-06-19T16:00:00Z `
    --pretty
```

Bounded loop (e.g. 5 iterations, 60s apart — no unlimited loop):

```powershell
python -m tools.evidence_harvester.runner loop-fixture `
    --fixture path\to\collector_input.json `
    --output-dir artifacts\evidence_harvester\runner `
    --iterations 5 `
    --interval-seconds 60 `
    --pretty
```

Local status:

```powershell
python -m tools.evidence_harvester.runner status --output-dir artifacts\evidence_harvester\runner --pretty
```

### Output artifacts

Each cycle produces:

- `collector_report_<stamp>.json` — raw collector report
- `snapshot_<stamp>.json` — normalized snapshot
- `snapshot_<stamp>.md` — Markdown snapshot summary
- `alert_<stamp>.json` — alert findings
- `alert_<stamp>.md` — Markdown alert summary
- `coordinator_events.jsonl` — canonical coordinator lifecycle event stream
- `runner_heartbeat.json` — latest cycle metadata (overwritten each cycle)
- `runner_state.json` — cumulative run statistics plus coordinator-managed lifecycle state (overwritten each cycle)

### Safety boundaries

- default-off; bare command resolves to safe `plan`
- `loop-fixture` is bounded only (must pass `--iterations N`)
- no Docker, runtime, DB, Redis, or secrets access
- no LR-Go, no Live-Go, no Echtgeld-Go

### Related issues

- #3358 — runner implementation (this module)
- #3359 — watchdog consumption of runner heartbeat/state
- #3361 — write-audit consumption of runner heartbeat/state
- #3362 — OPS validation

## Watchdog

The `watchdog.py` module detects stalled collection and stale evidence by
inspecting runner heartbeat, state, and artifact files. It produces
deterministic PASS/WARN/FAIL verdicts.

### Allowed commands

- `status` (default) — full heartbeat, state, artifact integrity, and cadence checks
- `check-artifacts` — artifact presence and integrity only (skip heartbeat/state)
- `render-escalation-draft` — render a manual escalation draft from a saved report JSON

### Usage

```powershell
# Full status check
python -m tools.evidence_harvester.watchdog status `
    --artifact-dir artifacts\evidence_harvester\runner `
    --pretty

# Artifact-only check
python -m tools.evidence_harvester.watchdog check-artifacts `
    --artifact-dir artifacts\evidence_harvester\runner `
    --pretty

# Render escalation draft from saved report
python -m tools.evidence_harvester.watchdog render-escalation-draft `
    --report-jango artifacts\evidence_harvester\watchdog_report.json
```

### Output artifacts

- `watchdog_report.json` — machine-readable report with verdict + findings
- `watchdog_report.md` — human-readable Markdown summary
- `manual_escalation_draft.md` — manual escalation text (no automatic GitHub writes)

### Coordinator Liveness Classification

| Classification | Severity | Condition |
|----------------|----------|-----------|
| RUNNING_HEALTHY | PASS | Coordinator status is running/cycle_completed/final_validation and heartbeat is fresh |
| SLEEPING_UNTIL_NEXT_CYCLE | PASS/WARN | Sleeping with next_cycle_due_at_utc in the future (PASS) or within cadence tolerance (WARN) |
| STALE_HEARTBEAT | FAIL | Coordinator status implies active running but heartbeat exceeds max age |
| STALE_NEXT_CYCLE | FAIL | Sleeping but next_cycle_due_at_utc missing, invalid, or exceeded beyond cadence tolerance |
| COORDINATOR_STOPPED | WARN/FAIL | Coordinator has completed or failed its run window |
| COORDINATOR_UNKNOWN | WARN | No coordinator status or lifecycle telemetry available |
| RECOVERY_IN_PROGRESS | WARN | Coordinator status indicates recovery from a failure |
| FATAL_STOP | FAIL | Fatal stop lifecycle event or coordinator_status=fatal_stop |

The classification is derived from `runner_state.json` (`coordinator_status`, `next_cycle_due_at_utc`), `coordinator_events.jsonl` (lifecycle events), and `runner_heartbeat.json` (freshness). Missing lifecycle telemetry never produces silent PASS.

### Verdict contract

| Verdict | Conditions |
|---------|-----------|
| PASS    | Heartbeat fresh, state reports PASS, required artifacts exist, all JSON parses, safety flags correct, coordinator liveness PASS |
| WARN    | Artifact age near threshold, last run had failures, optional artifact missing, next cycle due slightly exceeded, coordinator liveness WARN |
| FAIL    | Heartbeat stale, state missing, required artifact missing, malformed JSON, runner FAIL verdict, wrong safety flags, sleeping schedule exceeded beyond tolerance, or coordinator liveness FAIL |

### Safety boundaries

- Read-only; never modifies artifacts
- No automatic restart, GitHub write, Docker, runtime, DB, Redis, or secrets action
- Escalation draft is local text output only; human review required before any GitHub action
- Feeds #3361 (write-audit) and #3362 (OPS validation) with structured evidence

## Write-Audit

The `write_audit.py` module verifies that the evidence harvester produces complete,
readable, temporally consistent, and usable artifact sets. It is a downstream
consumer of the runner output directory and performs cross-artifact integrity
checks.

### Checks

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

### Verdict contract

| Verdict | Conditions |
|---------|-----------|
| PASS    | All 10 check groups pass; all required artifacts present, all JSON parse, schema versions match, hash linkage valid, safety flags correct, timestamps coherent, source modes valid, sizes sane, MD companions present, metadata fields present |
| WARN    | Optional companion missing (e.g. watchdog_report.md), artifact age near threshold, non-critical metadata gap |
| FAIL    | Required artifact missing, malformed JSON, hash mismatch, missing safety flags, zero-byte artifact, timestamp contradiction, invalid source mode, missing metadata fields |

### Usage

```powershell
# Default audit of the runner output directory
python -m tools.evidence_harvester.write_audit

# Explicit artifact directory
python -m tools.evidence_harvester.write_audit ^
    --artifact-dir artifacts\evidence_harvester\runner ^
    --pretty

# Save outputs
python -m tools.evidence_harvester.write_audit ^
    --artifact-dir artifacts\evidence_harvester\runner ^
    --json-output artifacts\evidence_harvester\write_audit_report.json ^
    --markdown-output artifacts\evidence_harvester\write_audit_report.md

# Deterministic evaluation with fixed timestamps
python -m tools.evidence_harvester.write_audit ^
    --artifact-dir artifacts\evidence_harvester\runner ^
    --evaluated-at-utc "2026-06-19T16:00:00Z"
```

### Output artifacts

- `write_audit_report.json` — machine-readable report with 10 check groups + verdict
- `write_audit_report.md` — human-readable Markdown summary

### Safety boundaries

- Read-only; never modifies artifacts
- No automatic restart, GitHub write, Docker, runtime, DB, Redis, or secrets action
- Feeds #3362 (OPS validation) with structured artifact completeness evidence

## Validation

The `validation.py` module validates a 24h dry collection window of evidence
harvester artifacts. See the runbook at
`docs/runbooks/CDB_EVIDENCE_HARVESTER_24H_DRY_VALIDATION.md` for full details.

### Validation-Ready vs Actually Validated

**Validation-ready** means the checker and runbook exist on `main` and are
unit-tested. The checker can validate a directory of fixture artifacts and
produce a PASS/WARN/FAIL verdict with fail-closed reasons.

**Actually validated** means a real 24h background run was executed, artifacts
were collected, and the checker was run against the real output with a PASS
verdict. This requires a separate explicit Runtime-GO from Jannek and is **not**
authorized by this PR alone.

Current status: `VALIDATION_READY` — no real 24h run has been executed yet.

### Quick Start

```powershell
python -m tools.evidence_harvester.validation validate-dir `
    --artifact-dir artifacts\evidence_harvester\fixture_validation `
    --window-start-utc "2026-06-18T16:00:00Z" `
    --window-end-utc "2026-06-19T16:00:00Z" `
    --pretty
```

The module is read-only, does not start any background process, and enforces
the same safety boundaries as the rest of the harvester.

## 72h Ops Validation (#3362)

The `ops_validation.py` module is the final validation surface for the real
always-on `>=72h` dry run. It does not start the run. It validates one finished
artifact directory and composes runner continuity, watchdog history,
write-audit history, boot-readiness evidence, and safety boundaries into one
deterministic PASS/WARN/FAIL verdict.

### Usage

```powershell
python -m tools.evidence_harvester.ops_validation validate-dir `
    --artifact-dir artifacts\evidence_harvester\72h_ops_validation\<run_id> `
    --json-output artifacts\evidence_harvester\72h_ops_validation\<run_id>\ops_validation_report.json `
    --markdown-output artifacts\evidence_harvester\72h_ops_validation\<run_id>\ops_validation_report.md `
    --pretty
```

For non-final bounded validation (e.g. short fixture tests) missing lifecycle
telemetry produces WARN instead of FAIL:

```powershell
python -m tools.evidence_harvester.ops_validation validate-dir `
    --artifact-dir ... --no-final --pretty
```

### PASS requirements (final >=72h validation)

- Coordinator lifecycle telemetry (`coordinator_events.jsonl`) must be present
  and contain all required event types
- Lifecycle cycle counts must be consistent with `runner_state.json` and
  artifact counts
- Watchdog `coordinator_liveness` must not report FATAL_STOP or
  STALE_NEXT_CYCLE
- Heartbeat/state counters, window coverage, cadence, and safety boundaries
  must all pass

### Phase-2 runtime contract

- seed fixture: `artifacts/evidence_harvester/24h_dry_run/collector_input.json`
- artifact dir: `artifacts/evidence_harvester/72h_ops_validation/<run_id>/`
- cadence: every `900` seconds
- watchdog: after each runner cycle
- write-audit: after each runner cycle
- final validation: after `>=72h` over the whole artifact directory

### Required phase-2 artifacts

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

### Safety boundaries

- no actual 72h run in this PR
- no Windows Task install in this PR
- no Docker/runtime/DB/secrets mutation
- no GitHub writes from module code
- no LR-Go, no Live-Go, no Echtgeld-Go

### Always-On Acceptance Criteria

- Evidence is produced continuously.
- Recoverable failures do not permanently stop the run.
- Watchdog continuously monitors the harvester.
- Write-audit continuously validates artifacts.
- Boot readiness remains valid.
- Ops validation proves `>=72h` operation.
- LR remains NO-GO.
- Live remains NO-GO.
- Echtgeld remains NO-GO.

## Boot Readiness ( #3360 )

The `boot.py` module checks whether the evidence harvester is reboot- and
Docker-ready without performing any mutations. It is the entry point for
verifying system state after a restart, before enabling always-on mode.

### Allowed modes

| Mode | Description |
|------|-------------|
| `status` (default) | Full readiness assessment: repo root, module imports, artifact dirs, scheduler script, Docker detection, safety boundaries, command plan |
| `preflight` | Quick module-import and path check |
| `install-plan` | Print safe command plan for Docker/Task setup without executing anything |
| `render-operator-handoff` | Render a complete operator handoff document explaining how to enable reboot-resilient always-on mode |

### Boot readiness checks (B001–B007)

| ID   | Check                            | Failure Condition                        |
|------|----------------------------------|------------------------------------------|
| B001 | Repo root valid                  | Repo root missing or no `.git` directory |
| B002 | Harvester modules importable     | Any of 8 core modules fails to import    |
| B003 | Artifact dirs available          | Required artifact directory cannot be created |
| B004 | Scheduler script present         | `scripts/evidence_harvester_task.ps1` missing |
| B005 | Docker available                 | Docker not on PATH (warn, not required for fixture mode) |
| B006 | Safety boundaries ok             | Missing safety banner in runner module   |
| B007 | Command plan available           | Safe command list can be produced        |

### Verdict contract

| Verdict | Conditions |
|---------|-----------|
| PASS    | All B001–B007 pass: repo valid, all modules importable, artifact dirs ok, scheduler present (or warn only), Docker detected or warn, safety ok, command plan available |
| WARN    | Docker not found, scheduler script missing, artifact dir created during check, safety banner not verified |
| FAIL    | Repo root invalid, module import failure, artifact dir not creatable, safety boundary violation |

### Usage

```powershell
# Default: full status
python -m tools.evidence_harvester.boot

# Full status with pretty output
python -m tools.evidence_harvester.boot status --pretty

# Quick preflight
python -m tools.evidence_harvester.boot preflight --pretty

# Safe install-plan (prints steps, does NOT execute)
python -m tools.evidence_harvester.boot install-plan --pretty

# Operator handoff document
python -m tools.evidence_harvester.boot render-operator-handoff

# Save outputs
python -m tools.evidence_harvester.boot status ^
    --json-output artifacts\evidence_harvester\boot_readiness_report.json ^
    --markdown-output artifacts\evidence_harvester\boot_readiness_report.md

# PowerShell wrapper (default: status)
pwsh -NoProfile -File .\scripts\evidence_harvester_boot.ps1

# PowerShell wrapper with explicit action
pwsh -NoProfile -File .\scripts\evidence_harvester_boot.ps1 -Action status -Pretty
```

### Safety boundaries

- Default mode is `status` (read-only assessment)
- No Docker start/stop, runtime start, DB mutation, secrets access, or network write
- `install-plan` prints steps but does not execute them
- Docker mutation requires separate Infra-Mutation-Gate approval
- Windows Task install requires separate GO (see #3733 Operator Runtime-GO)
- No LR-Go, no Live-Go, no Echtgeld-Go

### Related issues

- #3360 — boot readiness (this module)
- #3362 — OPS validation (`>=72h` dry proof; CLOSED via Slice-E PASS)
- #3733 — external supervisor scaffold + host-resilience tiers (OPEN)

## External Supervisor Scaffold (#3733 Phase 1)

Out-of-process supervision for sleep-stall recovery. Phase 1 is **scaffold +
tests + docs only** — Tier-1 runtime proof requires a separate Operator
Runtime-GO. LR remains **NO-GO**. #3345 stays **OPEN** until #3733 closes.

Tier model:
[`docs/evidence/evidence_harvester_host_resilience_tiers.md`](../docs/evidence/evidence_harvester_host_resilience_tiers.md)

Safe plan (default):

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

Execution requires `-Explicit` on the PowerShell wrapper or `--explicit` on
`supervise-external`. No Windows Task install in Phase 1.

## Future-gated live reads

Later issues may add read-only adapters for:

- storage-backed evidence lookup
- paper runner log reading
- metrics observation

Those adapters are intentionally not required for this slice.
