# Range Mean Reversion v1: HOLD/PARK Decision

**Issue:** #3162
**Candidate:** range_mean_reversion_v1 (long-only first pass)
**Decision:** PARK (with operational HOLD status)
**Date:** 2026-06-13

---

## Evidence Summary

| Metric | range_mean_reversion_v1 | primary_breakout_v1 (baseline) |
|---|---|---|
| Closed trades | 443 | 39 |
| Win rate | 14.67% | 15.38% |
| Gross return_r | -0.3474 | -0.0754 |
| Fee-adjusted return_r | -0.8788 | -0.1222 |
| Net PnL (quote) | -67,189.13 | -9,258.98 |
| Windows with trades | 20/20 | 17/20 |
| Evidence class | controlled_lab_evidence | controlled_lab_evidence |

**Source:** Committed execution economics and evidence packet JSON artifacts (see seed artifact for full refs).

---

## Why PARK (Not REJECT)

1. **useful as a second league-table entry** — a multi-candidate table is prerequisite for future honest ranking.
2. **no capital risk** — candidate is ring-fenced at controlled_lab_evidence only; LR remains NO-GO.
3. **short-side is blocked, not rejected** — if the simulator learns short execution, the full long_short hypothesis may produce different results.

---

## Operational HOLD Status

"PARK" is the allowed league-table recommendation enum. "HOLD" is an operational status describing the candidate's development state:

| Aspect | Status | Rationale |
|---|---|---|
| Direction | long-only first pass | Short-side blocked (HOLD_SHORT_BLOCKER) |
| Parameters | initial research estimate | Requires calibration from replay evidence |
| Symbol universe | BTCUSDT only | Single-symbol v1 |
| Regime risk | unmitigated | Mean reversion held during TREND/HIGH_VOL_CHAOTIC regime shifts may produce extended adverse moves |
| Scoring | not rankable | No repo-defined numeric scoring formula |

A HOLD means the candidate is not promoted, not rejected, not live — it is retained for structural comparison and deferred for future scope.

---

## Key Clarification

The issue #3162 body states: *"Primary breakout v1 achieved a 51.3% win rate."* This is incorrect. The committed evidence JSON (`profitability_execution_economics_primary_breakout_v1_mexc_multi_window_3032.json`) shows win_rate = 0.153846 (15.38%). The 51.3% value does not appear in any committed artifact and is not used in this decision.

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

**PARK** range_mean_reversion_v1 in the league table as a second PARK candidate. Create a follow-up issue to select or develop a third league-table candidate before defining a numeric scoring formula.

---

## Artifacts Created

- `docs/evidence/profitability_league_table_seed_range_mean_reversion_v1_3162.json` — seed entry
- `docs/evidence/profitability_league_table_report_seed_3162.json` — successor multi-candidate report
- This decision document
