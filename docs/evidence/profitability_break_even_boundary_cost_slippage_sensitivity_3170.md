# CDB Profitability -- Break-Even Boundary and Cost/Slippage Sensitivity #3170

**Date:** 2026-06-13
**Issue:** #3170
**Refs:** #3032, #3157, #3162, #3166, #3168, PR #3169
**Status:** Complete -- docs-only boundary test for the tri-regime PARK loop

## Brain Evidence

| Field | Value |
|---|---|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `read AGENTS.md`, `read agents/AGENTS.md`, canonical read-order files, `git status -sb`, `git rev-parse HEAD`, `git rev-parse origin/main`, `git log --oneline origin/main..HEAD`, `git rev-parse --abbrev-ref HEAD`, `gh issue view 3170`, `gh issue view 3168`, `gh pr view 3169`, `gh pr list --state open`, `gh issue view 1445`, duplicate search for break-even/cost-slippage/friction/post-3168, repo reads of profitability evidence/contracts/scripts` |
| `records_or_results` | Branch `main` was current at entry and matched `origin/main` at `a82d34ae5468a0f1ebcf7e0084c3ad935aaaf864`. `#3170` is OPEN, `#3168` is CLOSED, PR `#3169` is MERGED, open PR list was empty, and duplicate search returned only the active issue plus its predecessor. The committed tri-regime artifacts show all three candidates negative on both gross and fee-adjusted return. |
| `repo_crosscheck` | `docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md`, `docs/evidence/profitability_league_table_report_seed_3166.json`, `docs/evidence/profitability_league_table_seed_primary_breakout_v1_3032.json`, `docs/evidence/profitability_league_table_seed_range_mean_reversion_v1_3162.json`, `docs/evidence/profitability_league_table_seed_momentum_capture_v1_3166.json`, `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_multi_window_3032.json`, `docs/evidence/profitability_execution_economics_range_mean_reversion_v1_mexc_multi_window_3157.json`, `docs/evidence/profitability_execution_economics_momentum_capture_v1_mexc_multi_window_3166.json`, `docs/evidence/profitability_evidence_packet_primary_breakout_v1_mexc_multi_window_3032.json`, `docs/evidence/profitability_evidence_packet_range_mean_reversion_v1_mexc_multi_window_3157.json`, `docs/evidence/profitability_evidence_packet_momentum_capture_v1_mexc_multi_window_3166.json`, `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`, `docs/contracts/profitability_evidence_packet.v1.schema.json`, `docs/contracts/profitability_execution_economics_assessment.v1.schema.json` |
| `impact_on_plan` | Existing committed artifacts are sufficient for a bounded docs-only break-even test. Fee sensitivity can be derived directly from the committed gross/net deltas. Spread/slippage cannot be claimed as measured rescue drivers because the current artifacts do not expose decomposed historical spread/slippage costs. |
| `limitations` | Repo-only. No SurrealDB/context-brain evidence. No replay or pipeline rerun. Current tri-regime packets carry `spread_cost=0.0` and `slippage_cost=0.0`, while the primary multi-window economics summary says slippage is reflected in fill prices but not exposed per trade. That supports only bounded friction sensitivity, not historical slippage decomposition. |

## Scope

### In scope

- Docs-only boundary test using already committed tri-regime profitability artifacts.
- Fee reduction scenarios derived from committed gross and fee-adjusted returns.
- Bounded statement of spread/slippage uncertainty.
- Explicit recommendation on whether the BTCUSDT/MEXC/1m long-only loop remains parked.

### Out of scope

- No helper script.
- No JSON companion artifact.
- No replay or pipeline execution.
- No Candidate #4.
- No scoring formula.
- No venue, runtime, DB, Docker, LR, or production-config work.
- No Live-Go, no Echtgeld-Go, no Paper-Go.
- No issue creation.

## Tri-Regime PARK Context

The current BTCUSDT/MEXC/1m long-only loop has three committed PARK candidates,
one for each regime domain used by the current loop.

| Candidate | Regime | Gross R | Net R | Closed trades | Fees quote |
|---|---|---:|---:|---:|---:|
| `primary_breakout_v1` | TREND | -0.075 | -0.122 | 39 | 3489.37 |
| `range_mean_reversion_v1` | RANGE | -0.347 | -0.879 | 443 | 40543.12 |
| `momentum_capture_v1` | HIGH_VOL_CHAOTIC | -0.206 | -0.535 | 274 | 24920.45 |

Source refs:

- `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_multi_window_3032.json`
- `docs/evidence/profitability_execution_economics_range_mean_reversion_v1_mexc_multi_window_3157.json`
- `docs/evidence/profitability_execution_economics_momentum_capture_v1_mexc_multi_window_3166.json`
- `docs/evidence/profitability_league_table_report_seed_3166.json`

## Method

This slice uses the following fail-closed method:

1. Treat the execution-economics summaries as the numeric SSOT for gross return,
   fee-adjusted return, gross PnL, net PnL, fee totals, and trade counts.
2. Use the evidence packets only as cross-checks for `fees`, `trade_count`,
   `spread_cost`, and `slippage_cost`.
3. Define fee drag as:

   `fee drag = gross_return_r - fee_adjusted_return_r`

4. Define the fee-free proxy as the committed gross result, not as a claim that
   all historical friction has been fully decomposed.
5. Treat spread/slippage only as a bounded uncertainty surface, not as a measured
   rescue driver, because current tri-regime artifacts do not expose decomposed
   historical spread/slippage costs.

### Friction interpretation boundary

- The current evidence packets for all three candidates carry
  `spread_cost = 0.0` and `slippage_cost = 0.0`.
- The profitability scripts that produced the range and momentum packets also
  write `spread_cost = 0.0` and `slippage_cost = 0.0` directly.
- The primary multi-window economics summary states that execution-simulator
  slippage is reflected in fill prices but is not exposed per trade.

Therefore:

- fee sensitivity is directly derivable from current artifacts
- spread/slippage decomposition is not directly derivable from current artifacts
- any spread/slippage discussion must stay bounded and hypothetical

## Boundary Scenarios

### Scenario definitions

- `observed_current`: committed fee-adjusted result as recorded today.
- `fee_reduction_50pct`: gross result minus 50% of the observed fee drag.
- `fee_reduction_75pct`: gross result minus 25% of the observed fee drag.
- `fee_free_proxy`: committed gross result.
- `required uplift to break-even at current fee`: absolute improvement needed to
  move the current fee-adjusted result to `0.0R`.
- `required uplift to break-even at fee-free proxy`: absolute improvement needed
  to move the gross result to `0.0R`.

### Return-r scenario table

| Candidate | observed_current | fee_reduction_50pct | fee_reduction_75pct | fee_free_proxy | uplift_to_break_even_current | uplift_to_break_even_fee_free |
|---|---:|---:|---:|---:|---:|---:|
| `primary_breakout_v1` | -0.122 | -0.099 | -0.087 | -0.075 | 0.122 | 0.075 |
| `range_mean_reversion_v1` | -0.879 | -0.613 | -0.480 | -0.347 | 0.879 | 0.347 |
| `momentum_capture_v1` | -0.535 | -0.371 | -0.288 | -0.206 | 0.535 | 0.206 |

### Supporting quote table

| Candidate | gross_pnl_quote | net_pnl_quote | fees_quote | fee_reduction_50pct_quote | fee_reduction_75pct_quote |
|---|---:|---:|---:|---:|---:|
| `primary_breakout_v1` | -5769.61 | -9258.98 | 3489.37 | -7514.29 | -6641.95 |
| `range_mean_reversion_v1` | -26646.02 | -67189.13 | 40543.12 | -46917.58 | -36781.80 |
| `momentum_capture_v1` | -15523.11 | -40443.55 | 24920.45 | -27983.33 | -21753.22 |

## Scenario Reading

### observed_current

All three candidates are materially negative on the committed fee-adjusted
surface.

### fee_reduction_50pct

Even after removing half of the currently observed fee drag, all three candidates
remain negative.

### fee_reduction_75pct

Even after removing 75% of the currently observed fee drag, all three candidates
remain negative.

### fee_free_proxy

All three candidates remain negative at the committed gross-result boundary:

- `primary_breakout_v1`: `R=-0.075`
- `range_mean_reversion_v1`: `R=-0.347`
- `momentum_capture_v1`: `R=-0.206`

This is the decisive result of the slice.

### required uplift to break-even at current fee

The current loop would need the following additional performance uplift to reach
break-even without changing anything else:

- `primary_breakout_v1`: `+0.122R`
- `range_mean_reversion_v1`: `+0.879R`
- `momentum_capture_v1`: `+0.535R`

### required uplift to break-even at fee-free proxy

Even after removing the currently observed fee drag entirely, the loop would still
need the following gross-performance uplift to reach break-even:

- `primary_breakout_v1`: `+0.075R`
- `range_mean_reversion_v1`: `+0.347R`
- `momentum_capture_v1`: `+0.206R`

## Explicit Rule

If all three candidates remain negative at the fee-free proxy, the
BTCUSDT/MEXC/1m long-only loop stays **PARKED**.

That rule is triggered here.

## Aggregate Tri-Regime Conclusion

**Selected conclusion:** `FULL_STOP_ON_THIS_LOOP`

Interpretation:

1. The current tri-regime loop is not merely fee-damaged; it remains negative at
   the committed fee-free proxy for every candidate.
2. Fee reduction improves the loss profile but does not plausibly rescue any of
   the three candidates into non-negative territory.
3. Because the loop is already gross-negative in TREND, RANGE, and
   HIGH_VOL_CHAOTIC, the present slice does not support a same-loop continuation
   thesis.
4. Spread/slippage cannot be honestly claimed as the hidden rescue factor because
   current artifacts do not expose decomposed measured spread/slippage costs.

Therefore the current BTCUSDT/MEXC/1m long-only candidate loop should remain
parked.

## Recommendation

### Current recommendation

- Keep the BTCUSDT/MEXC/1m long-only loop parked.
- Do not recommend Candidate #4.
- Do not recommend a scoring formula.
- Do not recommend venue-axis expansion from this slice, because no candidate
  becomes plausibly non-negative even at the fee-free proxy.

### Follow-up recommendation only

If future research is resumed, it should begin only after an explicit maintainer
decision outside this slice and only on a different research axis than the
current parked loop.

This artifact does **not** recommend immediate venue-axis work, because the
fee-free proxy remains negative for all three candidates.

## Safety

- LR remains `NO-GO`.
- No Live-Go.
- No Echtgeld-Go.
- No Paper-Go.
- Board stage `trade-capable` is not Live-Go.
- League table and profitability outputs remain advisory and evidence-only.
- No runtime, DB, Docker, venue, replay, or production-config action is
  authorized by this artifact.

## Sources

- `docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md`
- `docs/evidence/profitability_league_table_report_seed_3166.json`
- `docs/evidence/profitability_league_table_seed_primary_breakout_v1_3032.json`
- `docs/evidence/profitability_league_table_seed_range_mean_reversion_v1_3162.json`
- `docs/evidence/profitability_league_table_seed_momentum_capture_v1_3166.json`
- `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_multi_window_3032.json`
- `docs/evidence/profitability_execution_economics_range_mean_reversion_v1_mexc_multi_window_3157.json`
- `docs/evidence/profitability_execution_economics_momentum_capture_v1_mexc_multi_window_3166.json`
- `docs/evidence/profitability_evidence_packet_primary_breakout_v1_mexc_multi_window_3032.json`
- `docs/evidence/profitability_evidence_packet_range_mean_reversion_v1_mexc_multi_window_3157.json`
- `docs/evidence/profitability_evidence_packet_momentum_capture_v1_mexc_multi_window_3166.json`
- `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`
- `docs/contracts/profitability_evidence_packet.v1.schema.json`
- `docs/contracts/profitability_execution_economics_assessment.v1.schema.json`
