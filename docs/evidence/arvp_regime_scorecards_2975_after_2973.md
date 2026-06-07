# ARVP Regime Scorecards — 2-Window Bank (2026-06-07)

Status: Regime scorecard availability report for #2975 across the available 2-window bank
Parent anchor: #1900 / #2961 / #2971 / #2973
Previous evidence: `docs/evidence/arvp_drift_classification_2973_after_2971.md`
Scorecard CLI: `services/validation/arvp_regime_scorecard_runner.py`
Core module: `core/replay/arvp_regime_scorecards.py`
Live-readiness implication: none
Live/Echtgeld implication: none

---

## Executive Summary

Regime scorecards were evaluated for both windows in the 2-window bank. Neither window
has `regime_segments` in its comparison input. Scorecard status is **unavailable** for both
windows — an honest reflection that the current window bank does not contain regime
segmentation data.

The #3028 window has a known regime discrepancy (`regime_id=0` TREND default vs original
`regime_id=2` HIGH_VOL_CHAOTIC) which is documented as a finding, not smoothed over.

**Key result:** Regime scorecards cannot be populated with `ok` status from the current
window bank. No forced inference or synthetic regime data was introduced.

---

## Inputs

### This Document

| Artifact | Type | Source |
|----------|------|--------|
| `docs/evidence/arvp_regime_scorecards_2975_after_2973.md` | Regime scorecard report | #2975 |
| `artifacts/regime_scorecards/2975/window_bank_2/regime_scorecard_summary.json` | Machine-readable summary | #2975 |
| `artifacts/regime_scorecards/2975/window_bank_2/replay-16a0a8f6d92f-0001/arvp_regime_scorecard.json` | Pilot scorecard (unavailable) | CLi runner |
| `artifacts/regime_scorecards/2975/window_bank_2/replay-16a0a8f6d92f-0001/arvp_regime_scorecard_summary.md` | Pilot scorecard summary | CLi runner |
| `artifacts/regime_scorecards/2975/window_bank_2/replay-577c2f83ac91-0001/arvp_regime_scorecard.json` | #3028 scorecard (unavailable) | CLi runner |
| `artifacts/regime_scorecards/2975/window_bank_2/replay-577c2f83ac91-0001/arvp_regime_scorecard_summary.md` | #3028 scorecard summary | CLi runner |

### Upstream Inputs

| Artifact | Type | Source |
|----------|------|--------|
| `docs/evidence/arvp_drift_classification_2973_after_2971.md` | Drift classification report | #2973 |
| `docs/evidence/arvp_batch_compare_2971_after_2961.md` | Batch compare summary | #2971 |
| `docs/evidence/arvp_calibration_batch_2961_after_3031.md` | Calibration batch summary | #2961 |
| `artifacts/drift_classification/2973/window_bank_2/drift_classification_summary.json` | Drift classification data | #2973 |
| `artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json` | Batch compare data | #2971 |
| `artifacts/candles/3028_window/dataset_spec.json` | #3028 dataset spec | #3031 |
| `artifacts/calibration/2961/pilot_validation_compare/replay-16a0a8f6d92f-0001/shadow_comparison.json` | Pilot shadow comparison | #2961 |
| `artifacts/replay_vs_paper_compare/replay-577c2f83ac91-0001/shadow_comparison.json` | #3028 shadow comparison | #3031 |

---

## Regime Context Availability

### Per-Window Check

| Criterion | Pilot Window | #3028 Window |
|-----------|-------------|--------------|
| shadow_comparison.json has `regime_segments` | ❌ No | ❌ No |
| Replay trace has `regime_id` per step | ❌ No (report.json lacks step-level regime) | ❌ No (no step-level trace available) |
| Calibration report has regime breakdown | ❌ No | ❌ No |
| `regime_fresh_ratio` available | ✅ 1.0 (but not segmented) | n/a (Binance dataset) |
| Expected/Original regime | unknown (pilot likely TREND) | HIGH_VOL_CHAOTIC (regime_id=2) |
| Replay/Default regime | none observed | TREND (regime_id=0) |
| regime_confounded | false | **true** |
| regime_discrepancy | none | **regime_id=0 vs 2 (HIGH_VOL_CHAOTIC)** |

### Scorecard CLI Output

Both windows were processed through `arvp_regime_scorecard_runner.py` using the
`--comparison` path against their respective `shadow_comparison.json` files:

| Window | Run ID | Status | Fingerprint |
|--------|--------|--------|-------------|
| Pilot | replay-16a0a8f6d92f-0001 | unavailable | `43e57fb78982c091dde9a147a71a69ee06676991cbe37cf719d0d8e4e5f61a15` |
| #3028 | replay-577c2f83ac91-0001 | unavailable | `e49de1d8524c3ca66c40db8f8001ecead5b31867883032af93984110612bf0a9` |

Both scorecards have:
- `status: unavailable`
- `notes: ["unavailable: comparison input has no regime_segments"]`
- `segments: []` (empty)
- `source: comparison`

---

## Per-Window Regime Scorecard Matrix

| Field | Pilot Window | #3028 Window |
|-------|-------------|--------------|
| Window ID | `paper_1909_1776991354682` | `0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab` |
| Replay run ID | `replay-16a0a8f6d92f-0001` | `replay-577c2f83ac91-0001` |
| Strategy | `primary_breakout_v1` | `primary_breakout_v1` |
| Symbol | BTCUSDT | BTCUSDT |
| Venue | MEXC (same-venue) | Binance (venue_mismatch=true) |
| same_venue | true | false |
| venue_mismatch | false | true |
| regime_context_available | false | false |
| regime_confounded | false | true |
| expected/original regime | likely consistent (regime_id unknown) | HIGH_VOL_CHAOTIC (regime_id=2) |
| replay/default regime | none (no regime_id in steps) | TREND (regime_id=0, defaulted) |
| regime_discrepancy | none | **regime_id=0 vs 2** |
| scorecard_status | **unavailable** | **unavailable** |
| scorecard_source | comparison | comparison |
| scorecard_fingerprint | 43e57fb7... | e49de1d8... |
| drift_classification | simulator_pessimistic | simulator_pessimistic (confounded) |
| drift_certainty | moderate | limited |

---

## #3028 Regime Discrepancy

The #3028 window (Binance candle dataset) has a known regime discrepancy that must not
be smoothed over or dismissed:

| Aspect | Paper Trade (original) | Replay Dataset (Binance) |
|--------|----------------------|------------------------|
| Venue | MEXC | Binance |
| Candles source | MEXC feed via cdb_candles | Binance klines API |
| regime_id | **2 (HIGH_VOL_CHAOTIC)** | **0 (TREND) — default** |
| Regime data available | Yes (paper had regime context) | No (Binance has no regime data) |
| Regime entry gate behavior | Blocked entry (HIGH_VOL_CHAOTIC blocks) | Allowed entry (TREND allowed) |

The dataset spec explicitly notes: *"All regime_id defaulted to 0 (TREND) because Binance
klines lack regime data. Original MEXC paper trade used regime_id=2 (HIGH_VOL_CHAOTIC)."*

**Impact on scorecard interpretation:** Even if regime_segments existed in the comparison
input, the #3028 window would need a separate `venue_mismatch` flag and `regime_discrepancy`
note because the Binance-based regime data is not comparable with the original MEXC paper
trade's regime context.

This is consistent with all upstream evidence documents (#2961, #2971, #2973) which
document this discrepancy as a confound, not an ignorable edge case.

---

## Scorecard Status / Limitations

### Honest Limitations

1. **No regime_segments in any window** — Neither the pilot shadow comparison nor the
   #3028 shadow comparison contains `regime_segments`. The scorecard runner correctly
   produces `unavailable`.

2. **No step-level replay traces** — The replay report.json files do not contain
   `steps[{ts_ms, regime_id, signals_emitted}]` or `trades[{exit_ts_ms, exit_regime_id}]`
   structures. The replay_trace path of the scorecard runner cannot be used.

3. **#3028 regime discrepancy is a real confound** — The Binance dataset defaults all
   regime_ids to 0 (TREND). The original paper trade used regime_id=2 (HIGH_VOL_CHAOTIC).
   This is a structural data gap, not a recoverable one.

4. **Narrow windows — 1-2 minutes** — Both windows are too short to contain meaningful
   regime transitions. Longer windows (5+ minutes, 1h+) would be more likely to contain
   `regime_segments` in their comparison outputs.

5. **Single symbol, single strategy** — Only BTCUSDT + primary_breakout_v1. No regime
   evidence for other symbols or strategy types.

6. **Proxy-only calibration** — No explicit reject data in any window. Regime scorecards
   would need regime-labeled reject data for completeness.

---

## Impact on Downstream Issues

### #2970 — Execution Realism Decision

The regime scorecard report shows that neither window has usable regime context.
The #1905 unpark decision (#2970) must either:
- Wait for windows that contain `regime_segments` in their comparison outputs, OR
- Proceed without regime-level insight, using only the aggregate drift classification
  from #2973 (pessimistic, limited certainty)

**Recommendation for #2970:** The regime scorecards are `unavailable` — not blocking
but not providing additional insight. The execution-realism candidate gap from #2973
(fill model gap, both windows: -1 fill delta) is the strongest signal available.
The #3028 regime confound reduces certainty but does not invalidate the finding.

### #2974 — Product-Complete Review

Per #2973 § Impact on Downstream Issues, product-complete criteria require:

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Window bank >=2 windows | ✅ | 2 windows |
| Batch calibration per-window drift classification | ✅ | Both windows classified |
| Ranked findings | ✅ | 4 findings ranked |
| Regime scorecards | **unavailable** | This report — scorecard status unavailable for both windows |
| Operator runbook | ❌ | A6 not started |
| Execution realism gap | ✅ | 1 candidate gap identified |

**#2974 remains open.** Regime scorecards are `unavailable` but documented. Product-complete
review must account for the absence of regime-level insight as a known limitation.

---

## Safety Boundaries

- LR remains NO-GO
- No Live-Go / Echtgeld-Go
- No runtime execution beyond committed replay/compare/calibration artifacts
- No DB mutation
- No strategy code changes
- No Risk/Execution/Allocation changes
- Binance candles are not MEXC same-venue evidence
- Regime scorecards are diagnosis, not trade authorization
- `unavailable` status does not imply regime absence — only that the current
  window bank lacks regime segmentation data
- #3028 regime discrepancy is a structural confound, not a recoverable gap
- No scorecard without explicit limitations
- No inference of regime behavior from full-window aggregate metrics

---

## Acceptance Criteria Assessment

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `regime_segments` checked per window | ✅ | Both shadow_comparison files inspected — no regime_segments found |
| 2 | Scorecard generated for each window where data exists | ✅ | Both windows: scorecard CLI produced `unavailable` artifacts |
| 3 | `unavailable` used honestly when data missing — no forced inference | ✅ | Both scorecards: status=unavailable, notes explain why |
| 4 | Relation to calibration findings documented | ✅ | Drift classification (#2973) cross-referenced per window |
| 5 | No regime-inference claims without data support | ✅ | No inference made; unavailable explicitly declared |
| No Live-Go implication | ✅ | LR remains NO-GO |
| No runtime execution required | ✅ | All inputs from existing committed artifacts |
| Deterministic/reproducible | ✅ | Same CLI + same shadow_comparison.json → same fingerprints |

---

## Status

`#2975` regime scorecard evaluation for the 2-window bank is **delivered and verified**.

Both windows produce `status=unavailable` scorecards because neither contains
`regime_segments` in their comparison inputs. The #3028 regime discrepancy
(`regime_id=0` vs original `regime_id=2`) is documented as a finding.

**Closure decision:** `DONE` — #2975 Acceptance Criteria are satisfied. AC #3
explicitly accepts `unavailable` status when regime data is missing. The scorecard
artifacts are deterministic, committed, and reproducible.

A third window with longer duration and same-venue MEXC regime data would be needed
to produce `ok`-status regime scorecards.

---

## References

- Issue #2975: https://github.com/jannekbuengener/Claire_de_Binare/issues/2975
- Issue #2973: https://github.com/jannekbuengener/Claire_de_Binare/issues/2973
- Issue #2971: https://github.com/jannekbuengener/Claire_de_Binare/issues/2971
- Issue #2961: https://github.com/jannekbuengener/Claire_de_Binare/issues/2961
- Issue #3031: https://github.com/jannekbuengener/Claire_de_Binare/issues/3031
- Issue #2970: https://github.com/jannekbuengener/Claire_de_Binare/issues/2970
- Issue #2974: https://github.com/jannekbuengener/Claire_de_Binare/issues/2974
- PR #3054: https://github.com/jannekbuengener/Claire_de_Binare/pull/3054
- PR #3053: https://github.com/jannekbuengener/Claire_de_Binare/pull/3053
- PR #3052: https://github.com/jannekbuengener/Claire_de_Binare/pull/3052
- PR #3051: https://github.com/jannekbuengener/Claire_de_Binare/pull/3051
- Roadmap: `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
