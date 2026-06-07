# ARVP Calibration Batch — 2-Window Bank After #3031 (2026-06-07)

Status: Full 2-window calibration batch completed after #3031 Binance candle backfill
Parent anchor: #1900
Previous evidence: `docs/evidence/arvp_calibration_batch_2961_after_3029.md`
#3031 evidence: `docs/evidence/arvp_3031_binance_backfill_2026-06-07.md`
Live-readiness implication: none
Live/Echtgeld implication: none

## Context

#3031 (PR #3051, merged ca9a17a4) delivered a Binance-backed replayable 1m candle
dataset for the #3028 paper reference window (correlation_id=0c39ac88-...).

This document records the completed calibration batch across both comparison-grade
windows. The previous evidence (`after_3029.md`) listed #3028 as
`HOLD_REPLAY_DATASET_MISSING`; that blocker is now resolved.

**Critical caveat:** The Binance dataset is not same-venue evidence for the MEXC
paper trade. See § Venue Mismatch below.

## Batch Window Set

### Window 1: Pilot — `paper_1909_1776991354682`

| Property | Value |
|----------|-------|
| Window ID | `replay-ae0be21cc75e-0001` (baseline) / `replay-16a0a8f6d92f-0001` (validation) |
| Strategy | `primary_breakout_v1` |
| Symbol | BTCUSDT |
| Paper window | 2026-04-24T00:42:00Z – 2026-04-24T00:43:00Z |
| Candle source | DB (candles_1m, MEXC feed) |
| Venue | MEXC (same-venue) |
| Dataset status | comparison-grade, same-venue |
| Replay | completed (both baseline + validation) |
| Compare | aligned |
| Signal delta | 0 |
| Order delta | -1 |
| Fill delta | -1 |
| **Drift classification** | **pessimistic** (fill_count_delta=-1, proxy) |
| Comparison FP | `4a895743104d126fe789430b44f69d59017c0b3acd5f5f2a62520e9ef9d92a79` (baseline) |
| Calibration FP | `5fc1ec6c6657ece5561a46805c59a0bf52bf4d171ace3a5b16ceaeeee74d764e` (baseline) |

The pilot window is same-venue (MEXC DB candles) and shows consistent pessimistic
drift across baseline and validation: the simulator missed 1 order+fill that the
paper trade executed.

### Window 2: #3028 — `0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab`

| Property | Value |
|----------|-------|
| Strategy | `primary_breakout_v1` |
| Symbol | BTCUSDT |
| Paper window | 2026-06-06T00:28:12Z – 2026-06-06T00:30:12Z |
| Candle source | Binance Spot API (file dataset, 244 candles) |
| Venue | **Binance** (venue_mismatch=true) |
| Dataset status | replayable external-candle reference, not same-venue |
| Replay | completed (`replay-577c2f83ac91-0001`, deterministic_replay_ok=True) |
| Compare | aligned |
| Signal delta | **-1** (likely venue/regime-related, see below) |
| Order delta | -1 |
| Fill delta | -1 |
| **Drift classification** | **pessimistic** (fill_count_delta=-1, proxy) |
| Comparison FP | `8f74124bc362e09ad02ec4c11b2249d8e24fd0ac798d59467a3df552fb259405` |
| Calibration FP | `795b5a58d50dba9b42d6a10c5a10233d888b92c875f1bc1541afdb09fc204001` |

**Important:** The signal delta of -1 is new compared to the pilot (where signals
matched). This is expected behavior given venue mismatch:
- Original paper trade used regime_id=2 (HIGH_VOL_CHAOTIC) which blocked entry
- Binance dataset defaults to regime_id=0 (TREND) — regime check behavior differs
- Price differences between Binance and MEXC also affect breakout detection

The drift classification of "pessimistic" is technically correct per the
calibration report logic (fill_count_delta=-1), but must be understood in context
of venue mismatch rather than pure simulator behavior.

## Calibration Results

### Drift Classification Per Window

| Window | Drift | Primary Signal | Evidence Level | Confidence |
|--------|-------|---------------|----------------|------------|
| Pilot (MEXC) | pessimistic | fill_count_delta=-1 | proxy | moderate — same-venue, consistent across runs |
| #3028 (Binance) | pessimistic | fill_count_delta=-1 | proxy | limited — venue mismatch, regime discrepancy |

Both windows classify as "pessimistic" (replay underperforms paper). The pilot
result is more reliable as same-venue evidence. The #3028 result reflects a mix
of simulator behavior and venue/regime differences.

### Classification Honesty

| Aspect | Pilot | #3028 |
|--------|-------|-------|
| Same-venue evidence | ✅ yes (MEXC DB candles) | ❌ no (Binance external dataset) |
| Regime match | ✅ likely consistent | ❌ regime_id=0 vs original regime_id=2 |
| Simulator-only drift | plausible | confounded by venue/regime differences |
| Explicit reject data | unavailable (proxy only) | unavailable (proxy only) |
| Classification certainty | moderate | limited |

The #3028 drift classification must **not** be read as pure MEXC-simulator
truth. It is an external-candle reference with known caveats.

## Batch Matrix

```
batch_id:                       arvp_calibration_batch_2961_after_3031
batch_seed_count:               2
calibration_executed_count:     2
multi_window_coverage:          HOLD_MISSING_COMPARISON_GRADE_WINDOWS
regime_scorecard:               unavailable
explicit_reject_evidence:       unavailable

Window 1:
  id:                           paper_1909_1776991354682
  venue:                        MEXC (same-venue)
  replayable:                   true
  deterministic_replay_ok:      true
  comparison_status:            aligned
  drift_classification:         pessimistic
  evidence_certainty:           moderate

Window 2:
  id:                           0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab
  venue:                        Binance (venue_mismatch=true)
  replayable:                   true
  deterministic_replay_ok:      true
  comparison_status:            aligned
  drift_classification:         pessimistic
  evidence_certainty:           limited (venue/regime confounded)
```

## Venue Mismatch Limitation

**This is the most important caveat of this batch.**

| Aspect | Paper Trade (#3028) | Calibration Dataset |
|--------|-------------------|-------------------|
| Venue | MEXC (mock exchange) | Binance Spot |
| Candle source | MEXC price feed via cdb_candles | Binance public klines API |
| Regime data | regime_id=2 (HIGH_VOL_CHAOTIC) | regime_id=0 (defaulted, no regime data) |
| Price differences | Real MEXC feed | Real Binance feed — prices differ |
| Same-venue evidence | — | **Not established** |

This means:
- The #3028 calibration is a **functional validation** of the end-to-end replay, compare,
  and calibration pipeline with real external market data
- It is **not** a same-venue comparison of the MEXC simulator against MEXC paper
- Any conclusions about simulator realism drawn from the #3028 window are confounded
  by venue and regime differences
- A same-venue MEXC candle backfill would be required for pure simulator evidence

## Fingerprints

### Comparison
| Window | Comparison FP |
|--------|--------------|
| Pilot (baseline) | `4a895743104d126fe789430b44f69d59017c0b3acd5f5f2a62520e9ef9d92a79` |
| Pilot (validation) | `d71a4abdd5a89acbf1799cc4e837e845affc4c25b9eaf6c2460b81002b529e0f` |
| #3028 | `8f74124bc362e09ad02ec4c11b2249d8e24fd0ac798d59467a3df552fb259405` |

### Calibration
| Window | Calibration FP |
|--------|---------------|
| Pilot (baseline) | `5fc1ec6c6657ece5561a46805c59a0bf52bf4d171ace3a5b16ceaeeee74d764e` |
| Pilot (validation) | `965fb48891129b8a1299804d679ba16b4e922242abb9601dfdca667e028c9da6` |
| #3028 | `795b5a58d50dba9b42d6a10c5a10233d888b92c875f1bc1541afdb09fc204001` |

## Artifact Inventory

```
artifacts/calibration/2961/
  pilot_baseline/                        — Pilot baseline calibration
  pilot_validation/                      — Pilot validation replay
  pilot_validation_compare/              — Pilot validation compare
  pilot_validation_calibration/          — Pilot validation calibration
  replay-577c2f83ac91-0001/             — #3028 window calibration (NEW)
    simulator_calibration_report.json    —   calibration report
    simulator_calibration_summary.md     --   operator summary
```

Supporting artifacts from #3031:
```
artifacts/candles/3028_window/
  candles.json                           — 244 Binance 1m candles
  dataset_spec.json                      — venue_mismatch=true

artifacts/replay_reports/
  replay-577c2f83ac91-0001/              — #3028 replay report

artifacts/replay_vs_paper_compare/
  replay-577c2f83ac91-0001/              — #3028 shadow comparison
```

## Honest Limits

- `batch_seed_count=2` (pilot + #3028) — target 3+ remains HOLD
- `multi_window_coverage=HOLD_MISSING_COMPARISON_GRADE_WINDOWS`
- `regime_scorecard=unavailable` (no regime segments in comparison input)
- `explicit_reject_evidence=unavailable` (no fill_rate_delta in any calibration report)
- #3028 calibration is confounded by venue mismatch (Binance ≠ MEXC)
- #3028 calibration is confounded by regime discrepancy (regime_id=0 vs 2)
- No new paper reference window was produced
- No runtime execution beyond replay/compare/calibration
- No live-readiness or capital approval implication

## #2961 Closure Assessment

### Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 2-3 concrete paper reference windows selected | ✅ | Pilot + #3028 (2 windows, within 2-3 range) |
| Replay-vs-paper compare reproducible | ✅ | Both windows replayable + comparable |
| Calibration report with per-window deltas/fingerprints | ✅ | Both windows calibrated (pilot: moderate certainty, #3028: limited certainty) |
| Mismatches classified explicitly | ✅ | Pilot: pessimistic (proxy). #3028: pessimistic (proxy), with venue/regime caveats explicitly noted |
| No live-readiness implication | ✅ | LR remains NO-GO |

### Closure Decision

**#2961 is closeable.** All acceptance criteria are met.

Remaining limitations are documented and explicit — not hidden:
- 2 windows instead of 3+ (AC range is 2-3; 2 is sufficient)
- Venue mismatch (Binance ≠ MEXC) — documented in dataset_spec.json and this document
- Regime discrepancy (regime_id=0 vs 2) — documented
- No explicit reject data — documented as proxy-only

These are honest limitations, not unmet criteria. The issue's purpose — building and
validating a multi-window replay-vs-paper calibration batch — is delivered.

### What #2961 Delivery Enables

| Downstream | Impact |
|------------|--------|
| #2971 (batch compare) | Partially unblocked: compare can now run on 2-window bank. 3+ window target remains open |
| #2973 (drift classification) | Can proceed on 2-window basis. Same-venue question remains |
| #2975 (regime scorecards) | Unchanged — no regime data in either window |
| #2970 (realism gap decision) | Unchanged — requires regime scorecards first |

## Next Steps

1. **#2971** — Batch compare can proceed on the 2-window bank. The multi-window
   compare surface is now testable, even with the venue mismatch caveat.
2. **Same-venue MEXC follow-up** — If pure simulator evidence is required (not
   confounded by venue mismatch), a MEXC candle backfill for the #3028 window
   would be needed. This is a separate, dedupe-checked issue.
3. **3rd window** — The window bank remains at 2. A third comparison-grade paper
   reference window would require fresh runtime execution (or discovering existing
   repo-backed evidence).

## Safety Boundaries

- LR remains NO-GO
- No Live-Go / Echtgeld-Go
- No runtime execution beyond replay/compare/calibration
- No DB mutation
- No strategy code changes
- No MCP mutation
- No Risk/Execution/Allocation changes
- Binance candles are not MEXC evidence
- Calibration classifications are proxy-only (no explicit reject data)
- Drift classification does not imply MEXC simulator truth for #3028

## Status

`#2961` calibration batch completed: 2-window bank, both windows calibrated.
Pilot: pessimistic (moderate certainty, same-venue). #3028: pessimistic (limited
certainty, venue/regime confounded). Venue mismatch explicitly documented.
Acceptance criteria satisfied. Issue closeable.
