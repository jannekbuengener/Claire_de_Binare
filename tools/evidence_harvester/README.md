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

## Future-gated live reads

Later issues may add read-only adapters for:

- storage-backed evidence lookup
- paper runner log reading
- metrics observation

Those adapters are intentionally not required for this slice.
