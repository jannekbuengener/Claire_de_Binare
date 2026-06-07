# ARVP Batch Compare — 2-Window Bank (2026-06-07)

Status: Replay-vs-paper batch compare summary for #2971 across the available 2-window bank
Parent anchor: #1900 / #2961 / #3031
Previous evidence: `docs/evidence/arvp_calibration_batch_2961_after_3031.md`
Live-readiness implication: none
Live/Echtgeld implication: none

## Context

#2971 demands a replay-vs-paper batch compare across all comparison-grade windows in the
window bank. After #2961 (calibration batch, closed via PR #3052) and #3031 (Binance candle
backfill, closed via PR #3051), the 2-window bank is fully calibrated:

1. **Pilot Window** (paper_1909_1776991354682): same-venue MEXC, calibration complete
2. **#3028 Window** (0c39ac88-...): Binance file dataset, venue_mismatch=true, calibration complete

This document aggregates the per-window compare results into a batch summary.

## Batch Decision

- `batch_ready`: true
- `window_count`: 2
- `same_venue_windows`: 1
- `venue_mismatch_windows`: 1
- `multi_window_coverage`: HOLD_MISSING_COMPARISON_GRADE_WINDOWS
- `target_3_plus_windows`: not met
- `batch_status`: PARTIALLY_UNBLOCKED

**Decision:** The 2-window bank supports a functional batch compare. The 3+ comparison-grade
window target (#2971 original aspiration) remains unmet. #2971 stays OPEN for the 3+ target.

## Window Bank Matrix

| Property | Pilot Window | #3028 Window |
|----------|-------------|--------------|
| Window ID | paper_1909_1776991354682 | 0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab |
| Replay run ID | replay-16a0a8f6d92f-0001 | replay-577c2f83ac91-0001 |
| Strategy | primary_breakout_v1 | primary_breakout_v1 |
| Symbol | BTCUSDT | BTCUSDT |
| Paper Time | 2026-04-24 00:42–00:43 UTC | 2026-06-06 00:28–00:30 UTC |
| Venue | MEXC (same-venue) | Binance (venue_mismatch=true) |
| Candle source | DB candles_1m (MEXC feed) | Binance public API (file dataset) |
| Replayable | yes | yes |
| Deterministic replay | ok | ok |
| Comparison FP | d71a4abdd5a89acbf…529e0f | 8f74124bc362e09ad…59405 |
| Calibration FP | 965fb48891129b8a…28c9da6 | 795b5a58d50dba9b…04001 |
| Status | aligned | aligned |
| Drift | pessimistic | pessimistic |
| Certainty | moderate | limited |
| Venue match | ✅ same-venue MEXC | ❌ Binance != MEXC |
| Regime | likely consistent | regime_id=0 vs original 2 |

## Per-Window Compare Results

### Pilot Window — `paper_1909_1776991354682` (MEXC)

| Metric | Paper | Replay | Delta |
|--------|-------|--------|-------|
| Signals | 1 | 1 | 0 |
| Orders | 1 | 0 | -1 |
| Fills | 1 | 0 | -1 |
| Unfilled (inferred) | 0 | 0 | 0 |

- **Drift:** pessimistic (simulator missed 1 order + 1 fill)
- **Certainty:** moderate — same-venue, consistent across baseline + validation
- **Limitations:** proxy-only calibration; no explicit reject data
- **Fingerprints comparison:** `d71a4abdd5a89acbf1799cc4e837e845affc4c25b9eaf6c2460b81002b529e0f`
- **Fingerprints calibration:** `965fb48891129b8a1299804d679ba16b4e922242abb9601dfdca667e028c9da6`

### #3028 Window — `0c39ac88-...` (Binance)

| Metric | Paper | Replay | Delta |
|--------|-------|--------|-------|
| Signals | 1 | 0 | -1 |
| Orders | 1 | 0 | -1 |
| Fills | 1 | 0 | -1 |
| Unfilled (inferred) | 0 | 0 | 0 |

- **Drift:** pessimistic (simulator missed 1 signal + 1 order + 1 fill)
- **Certainty:** limited — venue/regime confounded
- **Key caveat:** signal delta of -1 is new vs pilot (where signals matched). Likely
  venue/regime-related (regime_id=0 vs original 2, price differences Binance vs MEXC).
- **Limitations:** venue_mismatch, regime_discrepancy, proxy-only calibration
- **Fingerprints comparison:** `8f74124bc362e09ad02ec4c11b2249d8e24fd0ac798d59467a3df552fb259405`
- **Fingerprints calibration:** `795b5a58d50dba9b42d6a10c5a10233d888b92c875f1bc1541afdb09fc204001`

## Cross-Window Delta Analysis

| Aspect | Pilot | #3028 | Interpretation |
|--------|-------|-------|----------------|
| Drift classification | pessimistic | pessimistic | Both windows show replay underperforms paper |
| Signal delta | 0 | -1 | New signal gap in #3028 is venue/regime-related |
| Order delta | -1 | -1 | Consistent across windows |
| Fill delta | -1 | -1 | Consistent across windows |
| Evidence certainty | moderate | limited | #3028 confounded by venue/regime |

Both windows classify as pessimistic, but the causes differ: the pilot reflects pure
simulator behavior (same-venue), while #3028 reflects a mix of simulator behavior and
venue/regime differences that cannot be separated.

## Venue / Regime Caveats

- **venue_mismatch=true**: Binance != MEXC (#3028 dataset_spec.json)
- **Regime discrepancy**: #3028 uses default regime_id=0 (TREND), but the original
  paper trade used regime_id=2 (HIGH_VOL_CHAOTIC)
- **Price differences**: real price differences between Binance and MEXC affect
  breakout detection
- **Same-venue evidence**: only the pilot window provides pure same-venue MEXC evidence
- **Confounded classification**: #3028 drift classification cannot be read as pure
  MEXC simulator truth

## Batch Aggregation

### Artifact Paths

```
docs/evidence/arvp_batch_compare_2971_after_2961.md     — this document
artifacts/batch_compare/2971/window_bank_2/              — machine-readable batch summary
  batch_compare_summary.json

Per-window artifacts (committed):
artifacts/calibration/2961/pilot_baseline/               — pilot baseline
artifacts/calibration/2961/pilot_validation/             — pilot validation replay
artifacts/calibration/2961/pilot_validation_compare/     — pilot shadow comparison
artifacts/calibration/2961/pilot_validation_calibration/ — pilot calibration report
artifacts/calibration/2961/replay-577c2f83ac91-0001/     — #3028 calibration report
artifacts/replay_reports/replay-577c2f83ac91-0001/       — #3028 replay report
artifacts/replay_vs_paper_compare/replay-577c2f83ac91-0001/ — #3028 shadow comparison
artifacts/candles/3028_window/                           — Binance candle dataset
```

### Fingerprint Index

| Window | Comparison FP | Calibration FP |
|--------|--------------|----------------|
| Pilot (validation) | d71a4abdd5a89acbf1799cc4e837e845affc4c25b9eaf6c2460b81002b529e0f | 965fb48891129b8a1299804d679ba16b4e922242abb9601dfdca667e028c9da6 |
| #3028 | 8f74124bc362e09ad02ec4c11b2249d8e24fd0ac798d59467a3df552fb259405 | 795b5a58d50dba9b42d6a10c5a10233d888b92c875f1bc1541afdb09fc204001 |

### Classification by Non-Comparable Reason

All windows in the bank are comparison-grade and comparable. No windows were
silently skipped or excluded.

| Window | Comparable | Reason if not |
|--------|-----------|---------------|
| Pilot | ✅ | — |
| #3028 | ✅ | — |

## Acceptance Criteria Assessment

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Batch compare runs for all window-bank entries | ✅ | Both windows have shadow_comparison.json |
| 2 | Per-window `shadow_comparison` output exists | ✅ | Pilot: d71a4... ; #3028: 8f74124... |
| 3 | Per-window deltas and fingerprints documented | ✅ | Documented in after_3031.md + this document |
| 4 | Batch aggregation created | ✅ | This document + batch_compare_summary.json |
| 5 | Non-comparable windows classified with explicit reason | ✅ | 0 non-comparable windows; all bank entries included |
| 6 | No Live-Go implication introduced | ✅ | LR remains NO-GO |
| 7 | Reproducible: same windows → same output | ✅ | Deterministic artifacts; fingerprints match |

**All acceptance criteria met for the 2-window bank.**

The aspirational 3+ target (#1488 in comments, #1900 roadmap) is not part of the
issue AC but is the reason this issue remains open.

## Impact on Downstream Issues

| Issue | Impact |
|-------|--------|
| #2973 (drift classification) | Can proceed on 2-window basis with explicit caveats |
| #2975 (regime scorecards) | Unchanged — no regime data in either window |
| #2970 (realism gap decision) | Unchanged — requires regime scorecards first |
| #2985 (full ARVP roadmap) | Cross-reference: 2-window bank available, 3+ target open |

## Remaining Gaps

1. **3+ comparison-grade windows** — target not met. Requires fresh runtime paper
   execution or discovering new repo-backed evidence.
2. **Same-venue MEXC data for #3028 window** — the #3028 calibration is confounded
   by venue mismatch. A MEXC candle backfill would be needed for pure simulator
   evidence.
3. **Regime scorecards** — no regime data available for either window.
4. **Explicit reject data** — calibration is proxy-only; no fill_rate_delta
   available.

## Safety Boundaries

- LR remains NO-GO
- No Live-Go / Echtgeld-Go
- No runtime execution beyond already-completed replay/compare/calibration
- No DB mutation
- No strategy code changes
- Binance candles are not MEXC evidence
- Batch evidence is offline comparison, not runtime authorization
- No trading decisions derived from this batch
- #3028 drift classification confounded by venue/regime differences

## Status

`#2971` batch compare for the 2-window bank is **delivered and verified**.
Per-window compare outputs, fingerprints, batch aggregation, and cross-window
analysis are committed.

**Closure decision:** `HOLD_PARTIAL` — 2-window batch evidence delivered. #2971
remains OPEN for the 3+ comparison-grade window target. AC for the 2-window
scope are fully met, but the issue's broader 3+ aspiration keeps it open.

Next: 3rd comparison-grade window requires fresh runtime paper execution or
discovery of new repo-backed evidence.
