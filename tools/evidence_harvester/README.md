# Evidence Harvester Collector

Passive, fixture-driven collector for ARVP/profitability evidence coverage.

## Scope

- normalizes coverage and gap data
- stays read-only and secret-safe
- does not launch services, background jobs, storage writes, or replay paths

## Usage

Fixture mode:

```powershell
python -m tools.evidence_harvester.collector --fixture path\to\collector_input.json --pretty
```

Optional JSON output file:

```powershell
python -m tools.evidence_harvester.collector --fixture path\to\collector_input.json --output out\collector_report.json
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

## Future-gated live reads

Later issues may add read-only adapters for:

- storage-backed evidence lookup
- paper runner log reading
- metrics observation

Those adapters are intentionally not required for this slice.
