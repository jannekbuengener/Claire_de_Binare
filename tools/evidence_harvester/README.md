# Evidence Harvester Collector

Passive, fixture-driven collector for ARVP/profitability evidence coverage.

## Scope

- normalizes coverage and gap data
- stays read-only and secret-safe
- does not launch services, background jobs, storage writes, or replay paths
- keeps snapshots paper/research only; no LR-Go, no Live-Go, no Echtgeld-Go

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

## Future-gated live reads

Later issues may add read-only adapters for:

- storage-backed evidence lookup
- paper runner log reading
- metrics observation

Those adapters are intentionally not required for this slice.
