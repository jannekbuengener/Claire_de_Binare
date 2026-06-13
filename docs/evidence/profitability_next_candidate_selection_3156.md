# CDB Profitability -- Next Candidate Selection #3156

**Date:** 2026-06-13
**Parent:** #3156
**Predecessor:** #3032
**Refs:** #3153, #3155, #3154, #3151, #3149
**Status:** Complete -- next strategy candidate selected after primary_breakout_v1 PARK

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `git rev-parse`, `gh issue view 3156/3032`, `gh pr view 3154/3155`, comprehensive repo inventory via grep/glob for strategy IDs, adapters, regime terms, candidate surfaces across `services/`, `core/`, `docs/`, `tests/`, `scripts/` |
| `records_or_results` | #3156 OPEN, #3032 CLOSED, PRs #3154/#3155 MERGED. Repo contains exactly one live strategy (`primary_breakout_v1`). No `range_mean_reversion_v1`, `volatility_breakout_v2`, `momentum_pullback_v1`, or `high_vol_filter` exist. `momentum_builtin` adapter exists but is a threshold-only signal. MEXC multi-window evidence: 39 trades, net PnL -9258.98, fee-adjusted return R -0.122156, RANGE regime 36-47% per window. |
| `repo_crosscheck` | `docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`, `docs/strategy/CDB_PROFITABILITY_CANDIDATE_CONTRACT_V1.md`, `docs/contracts/profitability_candidate_contract.v1.schema.json`, `docs/evidence/profitability_primary_breakout_v1_park_decision_3032.md`, `docs/evidence/profitability_mexc_multi_window_evidence_3032.md`, `services/regime/service.py`, `core/contracts/external_adapter_registry.py`, `services/signal/service.py`, `services/validation/strategy_replay_runner.py` |
| `impact_on_plan` | RANGE regime is the dominant second regime (36-47%) in MEXC data and unsupported by primary_breakout_v1. Mean reversion candidate fills a clear gap. Multi-window calibrated dataset is immediately available for replay. |
| `limitations` | No SurrealDB/Context Brain used. No new replay or DB access in this slice. Candidate is research selection only, not implementation or promotion. |

## Scope and Non-goals

### In scope
- Inventory existing strategy/candidate/regime surfaces in working repo.
- Compare candidate archetypes against available data and repo capabilities.
- Select exactly one next strategy candidate.
- Draft candidate contract for the selected candidate.
- Propose dataset/evidence path.
- Define measurable stop criteria.
- Create follow-up issue for the pipeline pass.
- No code, replay, DB, runtime, or Docker actions.

### Non-goals
- No strategy implementation.
- No replay run.
- No threshold tuning.
- No DB or runtime access.
- No primary_breakout_v1 modification.
- No promotion or live-readiness claim.
- No invented numeric candidate scores.

## Input Evidence

Committed repo evidence used for this selection:

- `docs/evidence/profitability_primary_breakout_v1_park_decision_3032.md` -- PARK decision, full evidence chain closed.
- `docs/evidence/profitability_mexc_multi_window_evidence_3032.md` -- 20 windows, 39 trades, RANGE 36-47% per window, aggregate net PnL -9258.98.
- `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_multi_window_3032.json` -- Fee-adjusted return R -0.122156, fees 3489.37.
- `docs/evidence/profitability_league_table_seed_primary_breakout_v1_3032.json` -- PARK classification confirmed.
- Repo strategy inventory: only `primary_breakout_v1` exists as live strategy.
- Regime service taxonomy: `TREND` (ADX>=threshold), `RANGE` (ADX<=threshold), `HIGH_VOL_CHAOTIC` (ATR>=threshold).

## Why primary_breakout_v1 is excluded from tuning

primary_breakout_v1 is explicitly PARK after #3153/#3155. The decision is repo-backed:

- Sample-size PASS (39 closed trades) provides controlled-lab evidence.
- Economics are materially negative (net PnL -9258.98, fee-adjusted return R -0.122156).
- No tuning parameter improved aggregate economics in the evidence chain.
- The strategy is preserved as a baseline/regression control, not a promoted candidate.
- This slice does not modify, tune, or reopen primary_breakout_v1.

## Candidate Archetype Comparison

### range_mean_reversion_v1 (RECOMMENDED)

| Criterion | Assessment |
|-----------|------------|
| Hypothesis | Clear: prices revert to mean in RANGE regime; enter at z-score extremes, exit at mean |
| Distinct from primary_breakout_v1 | Fully: primary_breakout requires TREND + breakout; mean reversion requires RANGE + reversion. Opposite regime and signal logic. |
| Regime fit | Strong: MEXC multi-window data shows 36-47% RANGE per window. primary_breakout blocks RANGE. |
| Data availability | Immediate: existing MEXC multi-window calibrated files under artifacts/candles/mexc_multi_window_3032/ |
| Implementation complexity | Medium: requires new signal logic (z-score bands), but existing replay runner can consume new adapter. Adapter registration is low-effort. |
| Validation path | Full pipeline: calibrate parameters via replay against multi-window dataset, compute execution economics, produce evidence packet. No live go required. |
| Risk | Low: no runtime change, no production config, no DB, no live. Short-side execution realism needs validation. |

### volatility_breakout_v2

| Criterion | Assessment |
|-----------|------------|
| Hypothesis | Different volatility regime detection for breakout entries |
| Distinct from primary_breakout_v1 | Weak: still a breakout/trend strategy. Risk of threshold-tuned clone. |
| Regime fit | Overlaps primary_breakout (both target TREND/HIGH_VOL). |
| Data availability | Same MEXC data, but no clear differentiation benefit. |
| Implementation complexity | Low (could reuse runner), but differentiation unclear. |
| Validation path | Would repeat primary_breakout evidence path without clear added hypothesis. |
| Risk | Medium: could be seen as thinly disguised primary_breakout tuning. |

**Decision: NOT SELECTED.** Insufficient differentiation from PARK candidate. Risk of being a threshold-tuned clone.

### momentum_pullback_v1

| Criterion | Assessment |
|-----------|------------|
| Hypothesis | Enter on pullbacks within established momentum (trend retracement entries) |
| Distinct from primary_breakout_v1 | Partial: different entry logic but same regime requirement (TREND). Both are trend-following. |
| Regime fit | Requires TREND regime. primary_breakout already covered this regime domain. |
| Data availability | Same MEXC data. |
| Implementation complexity | Medium (requires trend detection + retracement filter). |
| Validation path | Would need TREND-dominant dataset, which the MEXC fragments lack (only 0.5-32% TREND). |
| Risk | Medium: regime overlap with PARK candidate could duplicate negative economics. |

**Decision: NOT SELECTED.** Same regime dependency as PARK candidate. Insufficient differentiation.

### high_vol_filter_or_avoidance_candidate

| Criterion | Assessment |
|-----------|------------|
| Hypothesis | Avoid or filter HIGH_VOL_CHAOTIC regimes instead of trading them |
| Distinct from primary_breakout_v1 | Weak: primary_breakout already blocks HIGH_VOL_CHAOTIC per contract |
| Regime fit | HIGH_VOL_CHAOTIC is already blocked by existing strategy contracts |
| Data availability | Not needed; the behavior is already contract-enforced |
| Implementation complexity | Very low, but also produces no trading signal |
| Validation path | No clear evidence gap: existing contracts already filter HVC |
| Risk | Low, but produces no new actionable candidate |

**Decision: NOT SELECTED.** No new research value. Existing contracts already handle HVC avoidance.

### Comparative Ranking (Qualitative, Not Numeric)

| Candidate | Differentiation | Regime Fit | Data Ready | Implementation Path | Verdict |
|-----------|----------------|------------|------------|-------------------|---------|
| range_mean_reversion_v1 | HIGH | STRONG | YES | CLEAR | **SELECT** |
| volatility_breakout_v2 | LOW | OVERLAP | YES | MUDDY | Reject |
| momentum_pullback_v1 | MEDIUM | OVERLAP | PARTIAL | MUDDY | Reject |
| high_vol_filter | LOW | N/A | YES | NONE | Reject |

## Selected Candidate

**range_mean_reversion_v1**

Candidate ID: `cand-range-mean-reversion-v1-btcusdt-mexc`

### Reason for Selection

1. **Regime gap filled**: primary_breakout_v1 blocks RANGE regime. MEXC multi-window data shows RANGE is the dominant or second regime in every window (36-47%). A RANGE-specialized candidate covers a regime that the PARK candidate explicitly excludes.

2. **Clear hypothesis**: Mean reversion in low-ADX environments is a well-studied, testable hypothesis with clear entry (z-score extreme) and exit (reversion to mean) rules.

3. **Data ready**: The existing MEXC multi-window calibrated dataset (20 windows, 66358 rows) is immediately available for file-backed replay. No new data capture or DB access needed.

4. **Testable without Live-Go**: Full pipeline (calibrate -> replay -> economics -> evidence packet) runs entirely offline with existing infrastructure.

5. **Distinct signal logic**: Z-score-based mean reversion is fundamentally different from breakout-based trend following. No risk of duplicating primary_breakout_v1 results.

### Non-selection reasons for alternatives

- **volatility_breakout_v2**: Insufficiently differentiated from the PARK candidate. Risk of threshold-tuned clone. Rejected.
- **momentum_pullback_v1**: Same regime dependency as PARK candidate (TREND). Insufficient differentiation. Rejected.
- **high_vol_filter**: No research value; existing contracts already enforce HVC avoidance. Rejected.

**This selects a candidate for research; it does not implement or promote it.**

## Candidate Contract Draft

A machine-readable candidate contract draft has been written to:

`docs/evidence/profitability_candidate_selection_3156_contract_draft.json`

Key fields:

| Field | Value |
|-------|-------|
| candidate_id | `cand-range-mean-reversion-v1-btcusdt-mexc` |
| strategy_family | `range_mean_reversion` |
| symbol_universe | `BTCUSDT` |
| timeframe | `1m` |
| direction | `long_short` |
| regime_scope | allowed: `RANGE`, blocked: `HIGH_VOL_CHAOTIC, PANIC, UNKNOWN` |
| parameter_set | zscore_lookback=20, entry_zscore=2.0, exit_zscore=0.0, position_sizing=0.01, atr_stop=2.0 |
| status | `SPECIFIED` |
| allowed_next_gate | `BACKTESTED` |

The contract is draft/proposed with research-only status. It does not claim implementation, promotion, or live readiness.

## Dataset / Evidence Path Proposal

### Dataset

**Primary**: MEXC multi-window calibrated dataset (20 windows, 66358 rows, 1105.97 total hours).

Path: `artifacts/candles/mexc_multi_window_3032/window_###/regime_calibrated/`

This dataset is repo-live, committed under #3152/#3154, and ready for file-backed replay consumption.

### Evidence Path

1. **Calibration**: Determine z-score thresholds for entry (potentially using distribution-based calibration similar to the ATR p75 rule from #3145).
2. **Replay**: Run file-backed replay for each window with the `range_mean_reversion_v1` adapter.
3. **Economics**: Capture execution economics using the #3149 extension (14 economics fields already available in report.json).
4. **Evidence Packet**: Produce a machine-readable evidence packet following `profitability_evidence_packet.v1` schema.
5. **Data Quality Gate**: Run existing dataset quality checks from #3035 schema.

### No new data capture required

This candidate does not require DB access or new data capture. The existing MEXC multi-window dataset is sufficient for the initial backtest pass.

## Stop Criteria

The candidate pipeline pass for `range_mean_reversion_v1` should stop if:

1. **Sample-size PASS fails**: Fewer than 20 total closed trades across all windows (same threshold as #3152).
2. **Economics are materially negative**: Aggregate net PnL quote or fee-adjusted return R is similar to or worse than primary_breakout_v1 benchmark (-0.122156).
3. **Short-side execution invalid**: Replay shows zero valid short fills or systematic short-side failure in the simulator.
4. **RANGE regime not confirmed**: Replay results show the strategy primarily triggers outside RANGE regime (contradicting the hypothesis).
5. **Implementation blocker**: The existing replay runner cannot consume the new signal logic without core infrastructure changes (would escalate scope).
6. **Promotion implied**: Any result that would imply paper readiness or live readiness without explicit gates.

At any stop condition, the candidate receives a PARK or REJECT classification and is not promoted.

## Follow-up Issue

A follow-up issue has been created for the full pipeline pass:

See issue link in #3156 comment.

## Safety Boundaries

- Candidate selection is research-only, not implementation or promotion.
- No Live-Go, no Echtgeld-Go, LR remains NO-GO.
- No runtime actions, no Docker actions, no DB access.
- No production config or code changes.
- No primary_breakout_v1 tuning in this slice.
- No automatic promotion from this selection.
- Contract draft is proposed research metadata, not a runtime configuration.

## Limitations

1. This selection uses committed repo evidence only; no new replay or DB query was executed.
2. Parameter set (zscore_lookback=20, entry_threshold=2.0) is an initial research estimate, not calibrated.
3. Controlled_lab_evidence only; no natural-paper or live evidence exists for any candidate in this repo.
4. Short-side execution in the replay simulator is unvalidated for this strategy type.
5. The existing candidate contract uses draft/proposed status; the next pipeline pass must validate against the schema.
6. No SurrealDB/Context Brain/MCP evidence was used.
