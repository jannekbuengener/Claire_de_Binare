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
- `runner_heartbeat.json` — latest cycle metadata (overwritten each cycle)
- `runner_state.json` — cumulative run statistics (overwritten each cycle)

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

### Verdict contract

| Verdict | Conditions |
|---------|-----------|
| PASS    | Heartbeat fresh, state reports PASS, required artifacts exist, all JSON parses, safety flags correct |
| WARN    | Artifact age near threshold, last run had failures, optional artifact missing |
| FAIL    | Heartbeat stale, state missing, required artifact missing, malformed JSON, runner FAIL verdict, wrong safety flags |

### Safety boundaries

- Read-only; never modifies artifacts
- No automatic restart, GitHub write, Docker, runtime, DB, Redis, or secrets action
- Escalation draft is local text output only; human review required before any GitHub action
- Feeds #3361 (write-audit) and #3362 (OPS validation) with structured evidence

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

## Future-gated live reads

Later issues may add read-only adapters for:

- storage-backed evidence lookup
- paper runner log reading
- metrics observation

Those adapters are intentionally not required for this slice.
