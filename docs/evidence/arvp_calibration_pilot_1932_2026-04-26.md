# ARVP Calibration Evidence — Pilot Run 2026-04-26

Status: Repo-backed evidence summary for #1932 Task 3
Source issue: #1932
Related issue: #1905
Evidence class: local calibration output summarized into repo-backed documentation
Live-readiness implication: none
Live/Echtgeld implication: none

## Context

This document records the first ARVP Compare to Calibration pilot evidence generated for #1932.

The original generated artifacts remain local under artifacts/calibration_run_001/ and are not committed because artifacts/ is locally excluded. This file captures the verified evidence summary in a stable repo-backed form.

## Execution context

Replay run: replay-ae0be21cc75e-0001
Date documented: 2026-04-26
Strategy: primary_breakout_v1
Symbol: BTCUSDT
Window: 2026-04-24T00:42:00+00:00 to 2026-04-24T00:43:00+00:00

## Local source artifacts

artifacts/calibration_run_001/compare/replay-ae0be21cc75e-0001/shadow_comparison_summary.md
artifacts/calibration_run_001/calibration/replay-ae0be21cc75e-0001/simulator_calibration_summary.md
artifacts/calibration_run_001/scorecards/replay-ae0be21cc75e-0001/arvp_regime_scorecard_summary.md

These files are local evidence inputs, not committed repo artifacts.

## Summary finding

The pilot run identified pessimistic simulator drift.

Paper produced 1 Order / 1 Fill in the inspected window.
Replay produced 0 Orders / 0 Fills in the same window.

The replay simulator missed a real paper opportunity in this pilot case.

## Count deltas

| Metric | Paper | Replay | Delta replay minus paper | Classification |
|---|---:|---:|---:|---|
| Order count | 1 | 0 | -1 | pessimistic |
| Fill count | 1 | 0 | -1 | pessimistic |

## Verification fingerprints

Comparison fingerprint:
9ef76ba2dfac93c796a256566cc6edf836597abb4a49be434547e4a4d2e4f32a

Calibration fingerprint:
030967e23f655014c3bb94a98d67b73684c2f811b55c005ed7927d69ffa64e61

Scorecard fingerprint:
989297461495a625da79078adf6b5064104c26c0d9286a65c575cd333c07c9d7

## Scorecard result

Scorecard status: unavailable

Reason:
comparison input has no regime_segments

Interpretation:
This is expected for the narrow one-minute pilot window. No robust regime-level conclusion should be drawn from this scorecard.

## Meaning for #1905

#1905 is no longer evidence-empty.

This pilot provides a concrete data-driven anchor for prioritizing simulator / execution-realism gaps. It does not implement an Execution-Realism fix and does not formally unpark or unblock #1905.

Formal #1905 status and label handling remain a separate governance step.

## Guardrails

This evidence does not imply:

- Execution-Realism implementation delivered
- #1905 completed
- #1905 formally unparked
- Live-readiness upgrade
- Live trading approval
- Echtgeld approval
- Paper-success claim
- Regime-level validation

## Remaining red checks

#1905 currently still carries the conflicting label combination status:parked plus stage:strategy-validated.

The source artifacts are local, not committed.

The scorecard is unavailable because the comparison input has no regime_segments.

## Status

#1932 Task 3: repo-backed evidence summary prepared.
