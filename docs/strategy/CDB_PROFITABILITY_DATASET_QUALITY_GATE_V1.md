# CDB Profitability Dataset Quality Gate v1

**Status:** Draft contract surface for #3035  
**Mode:** Docs / schema / example fixture only  
**Parent:** #3032  
**Live-Readiness:** NO-GO  
**Runtime Impact:** none  

## Purpose

This document defines the first dataset quality gate surface for Profitability
Engine candidate validation.

The gate exists because poor market data creates false profitability evidence.
It formalizes the dataset checks that must be explicit before a candidate is
trusted in backtest or ARVP-style comparison work.

## Contract Artifacts

| Artifact | Path | Role |
|---|---|---|
| Dataset quality schema | `docs/contracts/profitability_dataset_quality_report.v1.schema.json` | Machine-readable quality report |
| Valid example | `docs/contracts/examples/profitability_dataset_quality_report_valid.json` | Example report fixture |

## Required Checks

The quality gate v1 defines these checks:

- coverage check
- missing candle check
- duplicate check
- ordering check
- timeframe consistency check
- symbol/window metadata check
- dataset fingerprint check

The report also carries:

- requested window
- observed window
- expected and observed candle counts
- coverage ratio
- missing, duplicate, out-of-order, and timeframe mismatch counts
- overall verdict
- blocking reasons
- limitations

## Verdict Semantics

- `PASS`: dataset quality is clean enough for the scoped research use.
- `WARNING`: dataset is usable only with explicit caution and documented limits.
- `FAIL`: dataset quality is insufficient for the intended research step.
- `BLOCKED`: the dataset cannot be assessed honestly because a prerequisite is
  missing or the underlying data issue stays unresolved.

The quality gate is fail-closed:

- missing data can force `WARNING`, `FAIL`, or `BLOCKED`
- duplicate or out-of-order data cannot be silently normalized away
- timeframe inconsistency cannot be downgraded into a cosmetic note

## Relationship To Existing Replay Surfaces

This gate does not replace the existing replay dataset layer:

- `core/replay/dataset_spec.py` already defines request identity for symbol,
  timeframe, window, and source.
- `core/replay/dataset_provider.py` already validates transport/data-shape
  invariants such as strict ordering and 1m cadence.
- `services/validation/strategy_replay_runner.py` already carries dataset
  fingerprints through replay artifacts.

Dataset Quality Gate v1 sits before or beside those surfaces as a reusable
reporting/evidence layer. It standardizes how quality is expressed, not how
datasets are loaded.

## Relationship To #3031

Issue #3031 remains the concrete active data blocker for replayable 1m candles.
This slice does not backfill data and does not implement a recovery path. It
defines the reusable quality standard that future backfill or data repair work
must satisfy.

## Safety Boundaries

- LR remains NO-GO.
- `trade-capable` is not Live-Go.
- No Echtgeld-Go.
- No runtime change.
- No productive DB write.
- No MCP mutation.
- No Risk, Execution, Allocation, kill-switch, or LR gate change.
- ARVP, backtest, and paper are evidence, not approval.
- AI, dashboard, and docs are not authority.
- No automatic promotion.

## Non-Goals

- no direct backfill implementation
- no DB migration
- no runtime implementation
- no strategy logic change
- no live-readiness uplift

## Validation

For this docs-only slice, validation means:

1. the JSON schema parses and passes `jsonschema` schema checks
2. the valid example fixture validates against the schema
3. the report fields cover the #3035 issue requirements
4. the fail-closed verdict semantics remain explicit

This does not prove any concrete dataset is ready for paper, live, or capital
use.
