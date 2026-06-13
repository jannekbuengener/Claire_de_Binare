# Momentum Capture v1: HOLD/PARK Decision

**Issue:** #3166
**Candidate:** momentum_capture_v1 (long-only first pass)
**Decision:** PARK (with operational HOLD status)
**Date:** 2026-06-13

---

## Evidence Summary

| Metric | momentum_capture_v1 | range_mean_reversion_v1 | primary_breakout_v1 (baseline) |
|---|---|---|---|
| Closed trades | 274 | 443 | 39 |
| Win rate | 5.84% | 14.67% | 15.38% |
| Gross return_r | -0.2063 | -0.3474 | -0.0754 |
| Fee-adjusted return_r | **-0.5350** | -0.8788 | -0.1222 |
| Net PnL (quote) | -40,443.55 | -67,189.13 | -9,258.98 |
| Profit factor | 0.188 | 0.085 | 0.230 |
| Windows with trades | 20/20 | 20/20 | 17/20 |
| Evidence class | controlled_lab_evidence | controlled_lab_evidence | controlled_lab_evidence |

**Source:** `docs/evidence/profitability_execution_economics_momentum_capture_v1_mexc_multi_window_3166.json`, `docs/evidence/profitability_evidence_packet_momentum_capture_v1_mexc_multi_window_3166.json`

---

## Why PARK (Not REJECT)

1. **useful as a third league-table entry** — the league table now has coverage across all three regime domains (TREND, RANGE, HIGH_VOL_CHAOTIC), which was the explicit goal of #3164. A three-candidate table is materially more informative than a two-candidate one, even with negative economics across all three.
2. **no capital risk** — candidate ring-fenced at controlled_lab_evidence only; LR remains NO-GO.
3. **strong negative evidence for league-table learning value** — the #3164 selection explicitly states: *"If momentum_capture_v1 produces negative economics, the league table gains strong evidence that BTCUSDT MEXC offers no profitable edge regardless of regime"* (point 3, page 3). This outcome has research value.
4. **short-side is blocked, not rejected** — long-only first pass only.

---

## Operational HOLD Status

| Aspect | Status | Rationale |
|---|---|---|
| Direction | long-only first pass | Short-side blocked (HOLD_SHORT_BLOCKER) |
| Parameters | initial research estimate | ATR p75 (61.82 USD) directional threshold; p90 and p50 variants not tested |
| Symbol universe | BTCUSDT only | Single-symbol v1 |
| Regime risk | unmitigated | High fee drag (91.2% of gross loss) suggests high-frequency false signals |
| Scoring | not rankable | No repo-defined numeric scoring formula |

A HOLD means the candidate is not promoted, not rejected, not live — it is retained for structural comparison and deferred for future scope.

---

## Stop Condition Assessment

Per #3164 selection doc stop criteria:

| Criterion | Finding | Verdict |
|---|---|---|
| Sample-size PASS | 274 closed trades across 20 windows | PASS |
| Fee-adjusted return R < -0.5 | R = -0.5350 | **HARD NEGATIVE (PARK strongly recommended)** |
| Fee drag dominates economics | Fees = 24,920.45 vs gross PnL = -15,523.11 (91.2% of gross loss) | Confirmed — fee drag is extreme |
| Worse than both existing PARK candidates | R = -0.535 is worse than primary_breakout (-0.122) but better than range_mean_reversion (-0.879). Rank: 2nd of 3. | Between benchmarks |
| HVC regime not dominant | Not applicable; pipeline only triggers in HVC per contract | OK |
| Promotion implied | No | PASS |

---

## Regulatory Notes

| Gate | Status |
|---|---|
| Live-Go | NO-GO |
| Echtgeld-Go | NO-GO |
| Promotion allowed | No |
| Paper deployment | Not recommended |
| New replay run | Not required for this decision |

---

## Recommendation

**PARK** momentum_capture_v1 in the league table as a third PARK candidate. The league table now has regime coverage across all three domains (TREND, RANGE, HIGH_VOL_CHAOTIC) with uniformly negative economics — strong evidence that no regime on BTCUSDT MEXC 1m offers a profitable edge under current signal logic and fee assumptions.

A numeric scoring formula should not be defined until a candidate with materially positive economics exists, as the current set of three PARK candidates provides only negative baselines.

---

## Artifacts Created

- `docs/evidence/profitability_league_table_seed_momentum_capture_v1_3166.json` — seed entry
- `docs/evidence/profitability_league_table_report_seed_3166.json` — successor multi-candidate report (3 candidates)
- This decision document
- `docs/evidence/profitability_execution_economics_momentum_capture_v1_mexc_multi_window_3166.json` — execution economics
- `docs/evidence/profitability_evidence_packet_momentum_capture_v1_mexc_multi_window_3166.json` — evidence packet
- `docs/evidence/profitability_candidate_momentum_capture_v1_3166.json` — candidate contract
