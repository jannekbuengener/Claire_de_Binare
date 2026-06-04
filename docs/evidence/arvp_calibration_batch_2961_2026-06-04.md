# ARVP Calibration Batch Seed Evidence - 2026-06-04

Status: Repo-backed evidence report for `#2961`
Parent anchor: `#1900`
Pilot source: `#1932`
Evidence class: committed pilot evidence formalized as a single-window batch seed
Live-readiness implication: none
Live/Echtgeld implication: none

## Context

This document operationalizes the Phase-1 finding on `#2961`:

- exactly one comparison-grade replay-vs-paper window is currently evidenced
- that window is suitable as a batch seed
- true multi-window coverage remains blocked by missing additional comparison-grade paper windows

This slice does not run replay, paper, runtime, Docker, workflows, or live data collection.
It formalizes the committed pilot evidence and records the honest batch limits.

## Related Issues

- Parent anchor: `#1900`
- Current issue: `#2961`
- Pilot evidence issue: `#1932`

## Window Set

### Included

1. `replay-ae0be21cc75e-0001`
   - strategy: `primary_breakout_v1`
   - symbol: `BTCUSDT`
   - paper window: `2026-04-24T00:42:00+00:00` to `2026-04-24T00:43:00+00:00`
   - paper evidence type: `paper_reference_window.v1`
   - paper orders: `1`
   - paper fills: `1`
   - replay orders: `0`
   - replay fills: `0`
   - drift classification: `pessimistic`

### Held

Additional windows are held as:

`multi_window_coverage=HOLD_MISSING_COMPARISON_GRADE_WINDOWS`

Reason:

- no second comparison-grade paper reference window is currently evidenced in the committed pilot evidence inspected for `#2961`
- no regime-meaningful comparison window is currently evidenced
- no explicit reject-bearing comparison window is currently evidenced

## Normative Sources

- `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md`
- `docs/governance/arvp_paper_reference_contract.md`
- `docs/governance/arvp_platform.md`

## Local Validation Scope

During this `#2961` Phase-2 slice, the existing local JSON artifacts under
`artifacts/calibration_run_001/` were re-read only as a consistency check.
They remain local and untracked, and are not required as normative sources for
the repo-backed claims in this document.

## Batch Result

### Count deltas

| Metric | Paper | Replay | Delta replay minus paper |
|---|---:|---:|---:|
| Orders | 1 | 0 | -1 |
| Fills | 1 | 0 | -1 |
| Signals | n/a explicit paper count | matched compare delta `0` | `0` |

### Interpretation

The included seed window shows pessimistic simulator drift:

- paper produced one order and one fill
- replay produced zero orders and zero fills
- the simulator missed a real paper opportunity in this narrow window

This is sufficient to preserve a real replay-vs-paper seed for `#2961`.
It is not sufficient to claim multi-window coverage, regime-level confidence, or an execution-realism implementation target shortlist.

## Fingerprints

- comparison fingerprint: `9ef76ba2dfac93c796a256566cc6edf836597abb4a49be434547e4a4d2e4f32a`
- calibration fingerprint: `030967e23f655014c3bb94a98d67b73684c2f811b55c005ed7927d69ffa64e61`
- scorecard fingerprint: `989297461495a625da79078adf6b5064104c26c0d9286a65c575cd333c07c9d7`

## Regime Scorecard

Status: `unavailable`

Reason:

- comparison input has no `regime_segments`

Interpretation:

- regime scorecard evidence exists as an artifact surface
- this seed does not support regime-aware batch reading
- regime-aware coverage remains outside the current single-window seed

## Honest Limits

- `batch_seed_count=1`
- `multi_window_coverage=HOLD_MISSING_COMPARISON_GRADE_WINDOWS`
- `regime_scorecard=unavailable`
- explicit reject evidence is unavailable in the calibration report notes
- no new paper reference window is invented in this slice

## Guardrails

This slice does not imply:

- multi-window batch delivered
- additional windows exist
- execution-realism implementation delivered
- LR upgrade
- live-go
- Echtgeld-go
- runtime, paper, or replay execution in this slice

LR remains `NO-GO`.

## Next Evidence Needed

Before `#2961` can honestly move from a single-window batch seed to a true multi-window batch, the repo needs at least one additional comparison-grade paper reference window with:

- bounded UTC timestamps
- `correlation_ledger`-grade provenance
- paper `ORDER`/`FILL` evidence that satisfies the `paper_reference_window.v1` contract
- replay input that can be mapped without new live/runtime collection

Until then, the correct status is:

- keep the single included seed window
- keep multi-window coverage on explicit HOLD

## Status

`#2961` Phase 2 has a repo-backed single-window batch seed.
