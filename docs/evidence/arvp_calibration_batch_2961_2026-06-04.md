# ARVP Calibration Batch Seed Evidence - 2026-06-04 (Reconciled 2026-06-06)

Status: Repo-backed evidence report for `#2961` — reconciled to 2-window bank after #2968/#2969 closeout
Parent anchor: `#1900`
Pilot source: `#1932`
New window source: `#3028` (merged as `af01c76c`)
Evidence class: committed pilot evidence + new #3028 window, 2-window batch seed
Live-readiness implication: none
Live/Echtgeld implication: none

## Context

This document operationalizes the Phase-1 finding on `#2961` and has been
reconciled after the #2968/#2969 closeout chain:

- originally exactly one comparison-grade replay-vs-paper window was evidenced
- after #2968 (paper runtime) and #2969 (window-bank extraction), a second
  comparison-grade paper reference window has been committed (`#3028`)
- current window bank: 2 comparison-grade windows (pilot + new)
- true multi-window coverage (3+) remains blocked by missing additional
  comparison-grade paper windows

This slice does not run replay, paper, runtime, Docker, workflows, or live data collection.
It formalizes the committed pilot evidence and records the honest batch limits.

## Related Issues

- Parent anchor: `#1900`
- Current issue: `#2961`
- Pilot evidence issue: `#1932`
- New window export: `#2968`, `#2969`, `#3028`

## Window Set

### Included (2 comparison-grade windows)

1. **Pilot**: `replay-ae0be21cc75e-0001`
   - window ID (order_id prefix): `paper_1909_1776991354682`
   - strategy: `primary_breakout_v1`
   - symbol: `BTCUSDT`
   - paper window: `2026-04-24T00:42:00+00:00` to `2026-04-24T00:43:00+00:00`
   - paper evidence type: `paper_reference_window.v1` (docs-backed, no committed `.v1` artifact)
   - paper orders: `1`
   - paper fills: `1`
   - replay orders: `0`
   - replay fills: `0`
   - drift classification: `pessimistic`
   - calibration: pilot only (`artifacts/calibration_run_001/`, local/untracked)

2. **New**: `correlation_id=0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab`
   - strategy: `primary_breakout_v1`
   - symbol: `BTCUSDT`
   - source: `#3028` (merge-SHA `af01c76c`)
   - committed artifact: `artifacts/paper_reference_windows/paper_reference_window.json`
   - evidence copy: `docs/evidence/arvp_paper_reference_window_2968_after_3026.json`
   - events: `SIGNAL + DECISION + ORDER(paper_) + FILL` (complete comparison-grade chain)
   - paper orders: `1`
   - paper fills: `1`
   - calibration: **not yet run** (requires replay runtime → Human-GO)

### Held (3rd window)

`multi_window_coverage=HOLD_MISSING_COMPARISON_GRADE_WINDOWS`

Reason:

- 2 comparison-grade windows now exist (pilot + #3028)
- 3+ target for full multi-window batch calibration not yet met
- additional window requires fresh runtime execution (#2968-style paper run → export → commit)
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

- `batch_seed_count=2` (reconciled 2026-06-06 — was 1)
- `multi_window_coverage=HOLD_MISSING_COMPARISON_GRADE_WINDOWS` (target 3+, currently 2)
- `regime_scorecard=unavailable`
- explicit reject evidence is unavailable in the calibration report notes
- no new paper reference window is invented in this slice
- calibration on window #2 not yet run (requires replay → Human-GO)

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

The repo now has 2 comparison-grade paper reference windows (pilot + #3028).

Before `#2961` can honestly move to a true multi-window batch (3+ windows), the repo needs at least one additional comparison-grade paper reference window with:

- bounded UTC timestamps
- `correlation_ledger`-grade provenance
- paper `ORDER`/`FILL` evidence that satisfies the `paper_reference_window.v1` contract
- replay input that can be mapped without new live/runtime collection

Before calibration can be run on window #2, replay runtime with Docker stack is required (Human-GO-gated).

Until then, the correct status is:

- keep both included seed windows
- keep multi-window coverage (3+) on explicit HOLD
- keep calibration on window #2 HOLD (needs runtime)

## Status

`#2961` Phase 2 has a repo-backed 2-window batch seed (reconciled 2026-06-06 after #2968/#2969/#3028 closeout).
