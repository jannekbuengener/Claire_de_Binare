# ARVP Multi-Window Drift Classification Report (2026-06-07)

Status: Multi-window drift classification for #2973 across the 2-window bank
Parent anchor: #1900 / #2961 / #2971 / #3031
Previous evidence: `docs/evidence/arvp_batch_compare_2971_after_2961.md`
Batch compare: `artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json`
Live-readiness implication: none
Live/Echtgeld implication: none

---

## Executive Summary

This report classifies replay-vs-paper drift across the available 2-window bank,
producing per-window classification, aggregate drift summary, ranked findings,
and an execution-realism candidate gap.

**Aggregate result:** Direction=pessimistic, Certainty=limited

Both windows show pessimistic drift (replay underperforms paper). The pilot
window provides moderate-certainty same-venue MEXC evidence. The #3028 window
provides limited-certainty external-candle reference with venue/regime confounds.
The aggregate certainty is downgraded to limited because 50% of the window bank
is confounded by venue mismatch and regime discrepancy, and only 2 windows exist.

**Critical caveat:** This report does NOT claim CDB has a clean same-venue
multi-window simulator truth. The honest statement is: drift tendency is
pessimistic, but confidence is limited by 2 windows, one of which is
venue-/regime-confounded.

---

## Inputs

### Committed Evidence Artifacts

| Artifact | Type | Source Issue |
|----------|------|-------------|
| `docs/evidence/arvp_calibration_batch_2961_after_3031.md` | Calibration batch summary | #2961, #3031 |
| `docs/evidence/arvp_batch_compare_2971_after_2961.md` | Batch compare summary | #2971 |
| `docs/evidence/arvp_3031_binance_backfill_2026-06-07.md` | Candle backfill evidence | #3031 |
| `artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json` | Machine-readable batch summary | #2971 |
| `artifacts/calibration/2961/pilot_validation_calibration/replay-16a0a8f6d92f-0001/simulator_calibration_report.json` | Pilot calibration report | #2961 |
| `artifacts/calibration/2961/replay-577c2f83ac91-0001/simulator_calibration_report.json` | #3028 calibration report | #2961 |
| `artifacts/candles/3028_window/dataset_spec.json` | Dataset spec (venue_mismatch=true) | #3031 |
| `artifacts/replay_vs_paper_compare/replay-577c2f83ac91-0001/shadow_comparison.json` | #3028 shadow comparison | #3031 |
| `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md` | Pilot evidence (historic) | #1932 |

### Fingerprint Index

| Window | Comparison FP | Calibration FP |
|--------|--------------|----------------|
| Pilot (validation) | d71a4abdd5a89acbf1799cc4e837e845affc4c25b9eaf6c2460b81002b529e0f | 965fb48891129b8a1299804d679ba16b4e922242abb9601dfdca667e028c9da6 |
| #3028 | 8f74124bc362e09ad02ec4c11b2249d8e24fd0ac798d59467a3df552fb259405 | 795b5a58d50dba9b42d6a10c5a10233d888b92c875f1bc1541afdb09fc204001 |

---

## Per-Window Drift Matrix

| Field | Pilot Window | #3028 Window |
|-------|-------------|--------------|
| Window ID | paper_1909_1776991354682 | 0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab |
| Replay run ID | replay-16a0a8f6d92f-0001 | replay-577c2f83ac91-0001 |
| Strategy | primary_breakout_v1 | primary_breakout_v1 |
| Symbol | BTCUSDT | BTCUSDT |
| Paper time range | 2026-04-24T00:42:00Z - 00:43:00Z | 2026-06-06T00:28:12Z - 00:30:12Z |
| Source / Venue | MEXC (same-venue) | Binance (venue_mismatch=true) |
| same_venue | true | false |
| venue_mismatch | false | true |
| regime_confounded | false | true (regime_id=0 vs original 2) |
| Candle source | DB candles_1m (MEXC feed) | Binance public API (file dataset, 244 candles) |
| Comparison status | aligned | aligned |
| Deterministic replay | ok | ok |
| Signal count delta | 0 | -1 |
| Order count delta | -1 | -1 |
| Fill count delta | -1 | -1 |
| Inferred unfilled delta | 0 | 0 |
| **Drift classification** | **simulator_pessimistic** | **simulator_pessimistic** |
| Certainty | moderate | limited |
| Evidence level | proxy | proxy |
| Cross-run confirmation | confirmed (baseline + validation) | single run only |

### Classification Per Canon

Per #2973 drift classification canon (roadmap §6 A3, contract #1903):

| Window | Classification | Rationale |
|--------|---------------|-----------|
| Pilot | **simulator_pessimistic** | Replay produced 0 orders/0 fills vs paper 1 order/1 fill. Simulator missed real opportunity. Same-venue MEXC evidence. |
| #3028 | **simulator_pessimistic** | Replay produced 0 signals/0 orders/0 fills vs paper 1 signal/1 order/1 fill. However, signal delta of -1 is likely venue/regime-related, not pure simulator behavior. |

### Windows Excluded / Non-Comparable

None. Both windows in the bank are comparison-grade and were included.

---

## Aggregate Drift Classification

| Field | Value |
|-------|-------|
| aggregate_direction | **pessimistic** |
| aggregate_certainty | **limited** |
| window_count | 2 |
| same_venue_window_count | 1 (50%) |
| venue_mismatch_window_count | 1 (50%) |
| consistent_direction_across_windows | yes (both pessimistic) |
| signal_pattern | inconsistent (pilot: 0, #3028: -1) |
| order/fill_pattern | consistent (both: -1/-1) |

### Rationale

The aggregate direction is **pessimistic** because both windows independently
classify as simulator_pessimistic — replay produced fewer orders and fills than
paper in both cases.

The aggregate certainty is **limited** (not moderate) because:

1. **Window count:** Only 2 windows exist, not the 3+ target.
2. **Confounded window:** 1 of 2 windows (#3028) is confounded by venue
   mismatch and regime discrepancy. Its pessimistic classification reflects a
   mix of simulator behavior and venue/regime differences that cannot be
   separated.
3. **Same-venue evidence:** Only the pilot window provides pure same-venue
   MEXC evidence. The aggregate cannot claim multi-window same-venue truth.
4. **Consistency limits:** While order/fill deltas are consistent (-1/-1) across
   both windows, the signal delta differs (0 vs -1), suggesting the #3028 window
   has a different underlying cause for drift.

If the aggregate certainty were rated higher than limited, it would imply a
confidence that the available evidence does not support.

---

## Ranked Findings (ordered by material operational impact)

| Rank | Finding | Drift Class | Window | Certainty | Operational Impact |
|------|---------|-------------|--------|-----------|-------------------|
| 1 | Simulator consistently misses orders/fills in same-venue conditions | simulator_pessimistic | Pilot | moderate | High — if the simulator systematically misses orders that paper would execute, canary performance projections from replay-only evidence would be overconfident |
| 2 | Signal generation differs with venue/regime change | simulator_pessimistic (confounded) | #3028 | limited | Medium — signal gap of -1 may be venue or regime related, not simulator-only. Cannot quantify without same-venue MEXC data |
| 3 | Fill behaviour identical across windows (both -1) | simulator_pessimistic | Both | limited | Medium — consistent fill gap suggests systematic simulator limit, but n=2 is too small for confident pattern claim |
| 4 | No explicit reject data available in any window | execution_semantics_gap (proxy) | Both | high (on absence) | Low — proxy calibration is documented limitation; explicit reject handling is a known gap from #1903 contract |

---

## Candidate Execution-Realism Gap (from data, not theory)

**Gap: Fill model / order execution realism in replay**

Evidence: Across both windows (pilot moderate certainty + #3028 limited certainty),
the replay simulator consistently produces 0 fills where paper produced 1 fill.
The fill_count_delta pattern is -1/-1 across both windows.

This is not theoretical — it is directly observed from replay-vs-paper comparison
data in both windows. The candidate gap is in the replay fill model (or the
upstream order execution path that feeds fills).

**Blast radius:** The gap applies to the primary_breakout_v1 strategy on BTCUSDT.
Extrapolation to other symbols or strategies is unsupported.

**Note:** The #3028 signal delta (-1) likely involves venue/regime factors beyond
pure simulator behavior. The order/fill delta is the cleaner signal for simulator
realism assessment.

---

## Certainty Model

| Factor | Rating | Rationale |
|--------|--------|-----------|
| Window count adequacy | limited (2 of 3+ target) | Met minimum but below target |
| Same-venue coverage | limited (1 of 2 windows) | Half the bank is venue-mismatched |
| Cross-run consistency | moderate | Pilot confirmed across 2 runs; #3028 single run only |
| Regime data availability | unavailable | No regime scorecard for either window |
| Reject evidence availability | unavailable | Proxy-only calibration per contract #1903 |
| Classification canon match | moderate | Both windows cleanly map to simulator_pessimistic |

**Aggregate certainty: limited**

---

## Caveats / Limitations

### Honest Limitations

1. **2 windows only** — The 3+ comparison-grade window target remains unmet.
   The issue's #2971 dependency delivered the 2-window batch, but additional
   windows would diversify and potentially change the drift landscape.

2. **Venue mismatch (#3028)** — Binance ≠ MEXC. The #3028 drift classification
   is confounded by venue differences. It is a functional reference, not
   same-venue simulator truth.

3. **Regime discrepancy (#3028)** — The #3028 paper window used regime_id=2
   (HIGH_VOL_CHAOTIC). The Binance dataset defaults to regime_id=0 (TREND).
   Regime entry gates behaved differently in replay vs paper.

4. **Proxy-only calibration** — No explicit reject data is available for either
   window. All drift classifications are based on fill_count_delta proxy.

5. **Narrow windows** — Both windows are ~1-2 minutes. Longer windows would
   produce more robust drift signals and enable regime segmentation.

6. **Single symbol, single strategy** — BTCUSDT + primary_breakout_v1 only.
   No evidence about other symbols or strategy types.

7. **No regime scorecards** — Regime context for both windows is unavailable.
   #2975 remains open.

### Contextual Caveats

- The #3028 signal delta (-1) that differs from pilot (0) cannot be attributed
  to simulator behavior alone — it is likely venue/regime-related.
- The order/fill delta consistency (-1/-1 across both windows) is suggestive
  of a systematic simulator gap, but n=2 is not statistically significant.

---

## Impact on Downstream Issues

### #2975 — Regime Scorecards

The drift classification is now available as input for regime scorecard work.
Key constraints for #2975:
- Both windows have no regime_segments; scorecards will be `unavailable` for both.
- The #3028 regime discrepancy (regime_id=0 vs original 2) is the strongest
  signal that regime-aware window selection matters.
- If #2975 targets any window with regime segments, it likely needs longer
  reference windows than the current 1-2 minute bank.

### #2970 — Execution Realism Decision

The ranked findings and candidate gap identified in this report are now
available as the first data-driven input for the #1905 unpark decision.
However, #2970 should wait for regime scorecards (#2975) before unparking
#1905, because the #3028 regime confound makes it unclear whether the signal
gap is simulator or regime-related.

### #2974 — Product-Complete Review

The drift classification report satisfies Phase A3 (ARVP roadmap §6).
Product-complete criteria from the roadmap (§5.1) require:
- Window bank ≥2 windows (met: 2 windows) ✅
- Batch calibration per-window drift classification (met: both windows
  classified) ✅
- Ranked findings (met: 4 findings ranked) ✅
- Regime scorecards (unmet: #2975 still open) ❌
- Operator runbook (unmet: A6 not started) ❌
- Execution realism gap (met: 1 candidate gap identified) ✅

**#2974 remains open until all 6 product-complete criteria are met.**

---

## Safety Boundaries

- LR remains NO-GO
- No Live-Go / Echtgeld-Go
- No runtime execution beyond already-completed replay/compare/calibration
- No DB mutation
- No strategy code changes
- No Docker or workflow_dispatch actions
- No Risk/Execution/Allocation changes
- Binance candles are not MEXC same-venue evidence
- Drift classification is diagnosis, not trade authorization
- No batch conclusion without explicit limitations
- #3028 drift classification confounded by venue/regime differences
- ARVP, backtest, and replay evidence are validation artifacts, not live approval

---

## Input Checklist

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Each window classified to canon category | ✅ | Both: simulator_pessimistic |
| 2 | Batch-level drift summary exists | ✅ | This document + drift_classification_summary.json |
| 3 | Ranked findings exist (by material operational impact) | ✅ | 4 findings ranked in § Ranked Findings |
| 4 | At least one execution-realism candidate gap from data | ✅ | Fill model gap from both windows |
| 5 | Limitations clearly documented | ✅ | 7 honest limitations + contextual caveats |
| No Live-Go implication | ✅ | LR remains NO-GO |
| No runtime execution required | ✅ | All inputs from existing committed artifacts |

---

## Status

`#2973` multi-window drift classification for the 2-window bank is **delivered
and verified**. Per-window classification, aggregate summary, ranked findings,
certainty model, and candidate execution-realism gap are committed.

**Closure decision:** `HOLD_PARTIAL` — 2-window drift classification evidence
delivered. #2973 remains OPEN for the 3+ comparison-grade window target and
full multi-window certainty validation when the window bank expands.

AC criteria 1-5 are satisfied for the available 2-window bank. The issue
remains open per roadmap sequencing.

Next: A third comparison-grade window would diversify the drift landscape and
increase aggregate certainty. Same-venue MEXC data for the #3028 window would
resolve the primary confound.

---

## References

- Issue #2973: https://github.com/jannekbuengener/Claire_de_Binare/issues/2973
- Issue #2971: https://github.com/jannekbuengener/Claire_de_Binare/issues/2971
- Issue #2961: https://github.com/jannekbuengener/Claire_de_Binare/issues/2961
- Issue #3031: https://github.com/jannekbuengener/Claire_de_Binare/issues/3031
- PR #3053: https://github.com/jannekbuengener/Claire_de_Binare/pull/3053
- PR #3052: https://github.com/jannekbuengener/Claire_de_Binare/pull/3052
- PR #3051: https://github.com/jannekbuengener/Claire_de_Binare/pull/3051
- Roadmap: `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
