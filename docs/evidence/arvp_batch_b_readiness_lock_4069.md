# ARVP Batch-B Readiness Lock (#4069)

**Parent:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)  
**Predecessor:** [#4029](https://github.com/jannekbuengener/Claire_de_Binare/issues/4029) — terminal no-survivors funnel  
**Technical correction:** [#4065](https://github.com/jannekbuengener/Claire_de_Binare/issues/4065) / PR #4068  
**Decision:** `BATCH_B_LOCKED` — candidate identity, hypothesis boundaries, and dedupe boundaries only  
**Execution:** **not authorized**  
**LR:** **NO-GO** · `ranking_ready=false`

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none
```

The Context Brain briefing returned no DB-backed evidence records. All decisions below are therefore traceable to live GitHub state and versioned repository evidence only.

## Input truth

- Batch-A recompute after #4065: 726/780 rankable records, **0 survivors**.
- Batch-A result is terminal for its ten candidates; no unchanged repeat is allowed.
- The #3990 three-strategy campaign is also excluded unchanged.
- Readiness source: `docs/evidence/arvp_batch_b_readiness_4065.md`.
- Longlist source: `docs/evidence/arvp_strategy_longlist_deep_research_3746.md`.
- Development selection is reused by reference: 39 non-overlapping Binance BTCUSDT 1m monthly windows, SHA-256 `3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52`.

## Dedupe resolution

| Candidate | Compared with | Decision | Material boundary |
|---|---|---|---|
| `bollinger_mean_reversion_v1` | Batch-A `range_mean_reversion_v1` | **EXCLUDED_NEAR_DUPLICATE** | Bollinger distance is rolling mean/std-dev normalization and does not add a sufficiently distinct hypothesis |
| `range_bound_reversion_v1` | Batch-A `range_mean_reversion_v1` | **LOCKED** | Confirmed structural support/resistance edges; no z-score or Bollinger trigger |
| `mtf_1m_entry_5m_trend_v1` | `htf_bias_ltf_trigger_v1` | **LOCKED** | One completed-5m bias layer plus separate 1m trigger |
| `htf_bias_ltf_trigger_v1` | `mtf_1m_entry_5m_trend_v1` | **DEFERRED_OVERLAPPING_MTF** | Additional 15m hierarchy is complexity without proven incremental information |

## Final locked Batch B

| # | strategy_id | Rank | Family | Frozen distinction |
|---:|---|---:|---|---|
| 1 | `hh_hl_continuation_v1` | 7 | Trend | Confirmed swing structure; neither MA nor channel breakout |
| 2 | `rsi_momentum_v1` | 26 | Momentum | RSI continuation/burst, never oversold mean reversion |
| 3 | `high_vol_avoidance_v1` | 10 | Volatility filter | Filter-only; blocks chaotic-vol entries and makes no alpha claim |
| 4 | `range_bound_reversion_v1` | 19 | Mean reversion | Structural range-edge fade; no normalized-distance trigger |
| 5 | `mtf_1m_entry_5m_trend_v1` | 5 | Multi-timeframe | Last completed 5m bar gates a separately specified 1m entry |

The count is evidence-driven rather than forced to 6–8. It preserves five distinct hypothesis lanes after removing tested and overlapping candidates.

## Stage-A planning arithmetic

| Dimension | Count |
|---|---:|
| Locked candidates | 5 |
| Development windows | 39 |
| Scenarios | 2 (`baseline`, `pessimistic_execution`) |
| Planned scenario runs | **390** |

This is a planning count only. No runner, queue, replay, or campaign is created or started by this lock.

## Excluded and deferred

- Hard excluded: all ten Batch-A candidates and the three #3990 candidates.
- Near-duplicate excluded: `bollinger_mean_reversion_v1`.
- MTF deferred: `htf_bias_ltf_trigger_v1`.
- Domain deferred: multi-symbol, spread/liquidity filter, regime-switch, and Strategy Gearbox (#205).

## Lock semantics

`BATCH_B_LOCKED` means:

1. Candidate identities cannot change silently.
2. Hypothesis and dedupe boundaries are normative for the next spec slice.
3. Numeric parameters, runners, adapters, and campaign artifacts remain absent.
4. Any candidate substitution requires reopening #4069 or a superseding decision with evidence.
5. Implementation and execution require a separate explicit Dual-GO.

## Acceptance readback

- [x] Dedupe matrix with evidence
- [x] Excluded/deferred list
- [x] Versioned Batch-B lock manifest
- [x] Five-candidate count justified without size forcing
- [x] LR NO-GO and no-promotion boundary explicit
- [x] No runner implementation or campaign start

**Exit gate:** `BATCH_B_LOCKED`  
**Next gate:** `BATCH_B_IMPLEMENTATION_DUAL_GO`
