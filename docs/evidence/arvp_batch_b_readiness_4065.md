# ARVP Batch-B Readiness Map (#4065 P5 — zero survivors path)

**Parent:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)  
**Trigger:** Recomputed survivors = 0 after #4065 fix  
**Terminal status:** `VERDICT_CONFIRMED_ZERO_SURVIVORS_BATCH_B_PLAN_READY`  
**LR:** NO-GO · No Batch-B implementation or campaign in this delivery

---

## Exclusions (hard)

### Batch A (tested — exclude all 10)

`breakout_volatility_filter_v1`, `volatility_breakout_v1`, `ema_trend_follow_v1`, `ma_crossover_v1`, `range_mean_reversion_v1`, `bollinger_squeeze_breakout_v1`, `roc_breakout_confirm_v1`, `opening_range_breakout_v1`, `atr_expansion_v1`, `momentum_capture_v1`

### #3990 (tested — exclude all 3)

`donchian_breakout_v1`, `breakout_trend_filter_v1`, `primary_breakout_v1` (PARKED)

---

## Dedupe matrix (A5)

| Longlist candidate | Compare against | Result | Evidence |
|---|---|---|---|
| Z-Score Range Mean Reversion (rank 9) | `range_mean_reversion_v1` | **EXCLUDED_NEAR_DUPLICATE** | Same mean-reversion family; Batch A tested RMR |
| Breakout after Compression (rank 17) | `bollinger_squeeze_breakout_v1` | **EXCLUDED_NEAR_DUPLICATE** | Vol-compression → breakout hypothesis overlap |
| Breakout + Momentum (rank 14) | `roc_breakout_confirm_v1`, `momentum_capture_v1` | **EXCLUDED_NEAR_DUPLICATE** | Batch A tested both ROC and momentum |
| Breakout + Trend Filter (rank 3) | `breakout_trend_filter_v1` | **EXCLUDED_ALREADY_TESTED** | #3990 campaign |
| `bollinger_mean_reversion_v1` (proposed) | `range_mean_reversion_v1` | **CONDITIONAL_NEEDS_DEDUPE** | Requires documented material hypothesis/entry/exit delta |
| `range_bound_reversion_v1` (proposed) | `range_mean_reversion_v1` | **CONDITIONAL_NEEDS_DEDUPE** | Range-edge fade vs z-score RMR — needs spec delta |
| `mtf_1m_entry_5m_trend_v1` (proposed) | `htf_bias_ltf_trigger_v1` | **CONDITIONAL_NEEDS_DEDUPE** | Both MTF; must prove non-overlapping trigger rules |

---

## PROPOSED_BATCH_B (conditional — not size-forced)

| strategy_id | Family | Longlist rank | Status | Data need |
|---|---|---:|---|---|
| `hh_hl_continuation_v1` | Trend | 7 | **READY_FOR_SPEC** | 1m OHLCV |
| `rsi_momentum_v1` | Momentum | 26 | **READY_FOR_SPEC** | 1m OHLCV |
| `high_vol_avoidance_v1` | Vol filter | 10 | **READY_FOR_SPEC** | 1m OHLCV |
| `bollinger_mean_reversion_v1` | Mean reversion | 18 | **CONDITIONAL_NEEDS_DEDUPE** | 1m OHLCV |
| `range_bound_reversion_v1` | Mean reversion | 19 | **CONDITIONAL_NEEDS_DEDUPE** | 1m OHLCV |
| `mtf_1m_entry_5m_trend_v1` | Multi-TF | 5 | **CONDITIONAL_NEEDS_DEDUPE** | 1m + 5m derived |
| `htf_bias_ltf_trigger_v1` | Multi-TF | 12 | **CONDITIONAL_NEEDS_DEDUPE** | 1m + 5m/15m derived |

**Deferred:** Multi-symbol (#28–29), spread/liquidity filter (#24), regime-switch (#32), Gearbox (#205)

**Estimated jobs if 5 candidates locked:** 5 × 39 × 2 = **390 scenario runs** (same structure as Batch A)

---

## Issue structure (dedupe before create)

1. Meta under #1900: `[ARVP][FUNNEL] Batch B readiness lock` (WP1 analog)
2. Implementation slices only after explicit Batch-B Dual-GO
3. No runner/campaign in current #4065 scope

Exit gate: `BATCH_B_PLAN_READY`
