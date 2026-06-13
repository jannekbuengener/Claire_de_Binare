# CDB Profitability -- Third Candidate Selection #3164

**Date:** 2026-06-13
**Parent:** #3164
**Predecessors:** #3156, #3157, #3162, PR #3163
**Refs:** #3032, #3156, #3157, #3162, #3163
**Status:** Complete -- third strategy candidate selected for league-table comparison

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `gh issue view 3156/3157/3162/3164`, `gh pr view 3163`, comprehensive repo inventory via grep/glob for strategy IDs, adapters, regime terms, candidate surfaces across `services/`, `core/`, `docs/`, `tests/`, `scripts/`, repo reads of 4 evidence artifacts, CDB_PROFITABILITY_ENGINE_CANON, CDB_PROFITABILITY_CANDIDATE_CONTRACT_V1, CDB_PROFITABILITY_LEAGUE_TABLE_V1, CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1, CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1, services/regime/service.py |
| `records_or_results` | #3164 OPEN, #3156 CLOSED (selected range_mean_reversion_v1), #3157 CLOSED (pipeline pass, R=-0.879), #3162 CLOSED (PARK entry), PR #3163 MERGED (dd3167ac). Two PARK candidates in league table: primary_breakout_v1 (TREND, R=-0.122) and range_mean_reversion_v1 (RANGE, R=-0.879). Both ranking_ready=false. Regime taxonomy: HIGH_VOL_CHAOTIC (ATR-based) -> TREND (ADX-based) -> RANGE (ADX-based) -> UNKNOWN (fallback). Both existing candidates BLOCK HIGH_VOL_CHAOTIC. MEXC calibrated data at ATR~77 contains ~10-27% HVC windows. liquidity_filtered_breakout_v1 and regime_switch_v1 have NO repo evidence backing. |
| `repo_crosscheck` | `docs/evidence/profitability_next_candidate_selection_3156.md`, `docs/evidence/profitability_range_mean_reversion_v1_pipeline_3157.md`, `docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md`, `docs/evidence/profitability_league_table_report_seed_3162.json`, `docs/evidence/profitability_calibrated_evidence_packet_v2_3032.md` (27.2% HVC), `docs/evidence/profitability_btcusdt_regime_calibration_3032.md` (ATR threshold variants), `services/regime/service.py:120-127` (regime derivation logic), `core/contracts/external_adapter_registry.py` (only momentum_builtin), `services/validation/strategy_replay_runner.py` (only primary_breakout_runner_v1) |
| `impact_on_plan` | HIGH_VOL_CHAOTIC is the only uncovered regime domain with repo-backed evidence. Previously rejected archetypes (volatility_breakout_v2, momentum_pullback_v1) remain TREND clones with insufficient differentiation. liquidity_filtered_breakout_v1 and regime_switch_v1 lack repo evidence for evaluation. A HIGH_VOL_CHAOTIC-specialized candidate provides maximum learning value for the league table. Implementation complexity is MEDIUM (new adapter, replay runner extension). |
| `limitations` | Candidate is a new repo-derived family, not an existing one. No replay runner support exists beyond primary_breakout_v1. PANIC regime is NOT implemented in the regime service. No SurrealDB/Context Brain/MCP evidence used. |

## Scope and Non-goals

### In scope
- Inventory existing strategy/candidate/regime surfaces in working repo.
- Compare candidate archetypes against available data and repo capabilities.
- Select exactly one third strategy candidate.
- Propose candidate contract draft path.
- Propose dataset/evidence path.
- Define measurable stop criteria for follow-up pipeline pass.
- No code, replay, DB, runtime, or Docker actions.

### Non-goals
- No strategy implementation.
- No pipeline execution.
- No scoring formula definition.
- No replay run.
- No threshold tuning.
- No DB or runtime access.
- No primary_breakout_v1 or range_mean_reversion_v1 modification.
- No candidate promotion or live-readiness claim.
- No invented numeric candidate scores.
- No contract JSON file written (path only proposed).
- No pipeline-pass follow-up issue created (selection happens first).

## Input Evidence

Committed repo evidence used for this selection:

1. **League table report #3162** (`docs/evidence/profitability_league_table_report_seed_3162.json`):
   - Two PARK candidates: primary_breakout_v1 (rank 1, R=-0.122) and range_mean_reversion_v1 (rank 2, R=-0.879).
   - Both `ranking_ready=false`.
   - Table status: PARTIAL. "A third candidate is recommended for meaningful multi-candidate comparison before a scoring formula can be developed."

2. **Candidate #2 selection #3156** (`docs/evidence/profitability_next_candidate_selection_3156.md`):
   - Full archetype comparison for second candidate.
   - volatility_breakout_v2 rejected (TREND clone risk).
   - momentum_pullback_v1 rejected (same TREND regime dependency).
   - high_vol_filter rejected (no research value).

3. **Range mean reversion pipeline #3157** (`docs/evidence/profitability_range_mean_reversion_v1_pipeline_3157.md`):
   - 20 windows, 443 trades, fee-adjusted return R=-0.879.
   - All 20 windows negative. Held as PARK.

4. **HOLD/PARK decision #3162** (`docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md`):
   - Recommends third candidate before scoring formula.
   - Confirms short-side blocked, parameters are initial estimates.

5. **Regime service** (`services/regime/service.py:112-127`):
   - Regime derivation: HIGH_VOL_CHAOTIC -> TREND -> RANGE -> UNKNOWN.
   - HIGH_VOL_CHAOTIC wins all tiebreakers (checked first).

6. **Regime calibration #3032** (`docs/evidence/profitability_calibrated_evidence_packet_v2_3032.md`):
   - Calibrated ATR ~77 produces ~27% HVC, 24% TREND, 49% RANGE.
   - Sufficient HVC windows exist for meaningful testing.

7. **Adapter and runner constraints** (`core/contracts/external_adapter_registry.py`, `services/validation/strategy_replay_runner.py`):
   - Only `momentum_builtin` registered as strategy adapter.
   - Replay runner supports only `primary_breakout_runner_v1`.
   - Signal service hardcoded to primary_breakout_v1.

## League Table State

| Candidate | Candidate ID | Regime | Status | Fee-adj Return R | ranking_ready |
|---|---|---|---|---|---|
| primary_breakout_v1 | cand-primary-breakout-v1-btcusdt-mexc-3032 | TREND | PARK | -0.122 | false |
| range_mean_reversion_v1 | cand-range-mean-reversion-v1-btcusdt-mexc | RANGE | PARK (HOLD) | -0.879 | false |

Both candidates are controlled_lab_evidence only. League table is PARTIAL with no numeric scoring formula defined.

## Regime Taxonomy (from Regime Service)

The regime service uses a deterministic cascade:

```
if ATR >= atr_high_vol_threshold          -> HIGH_VOL_CHAOTIC
elif ADX >= adx_trend_threshold           -> TREND
elif ADX <= adx_range_threshold           -> RANGE
else keep current regime (or UNKNOWN)
```

HIGH_VOL_CHAOTIC wins all tiebreakers (checked first). There is no PANIC regime implemented; UNKNOWN is the fallback.

## Why primary_breakout_v1 and range_mean_reversion_v1 Are Excluded from Tuning

- **primary_breakout_v1**: Explicitly PARK after #3153/#3155. Economics materially negative (R=-0.122). No tuning parameter improved aggregate economics in the evidence chain. Preserved as baseline/regression control.

- **range_mean_reversion_v1**: Explicitly PARK after #3162. Economics severely negative (R=-0.879, 14.67% win rate). Short-side blocked. Parameters are initial research estimates; no calibration pass was performed because aggregate economics were definitive.

Neither candidate is reopened, tuned, or modified in this slice.

## Candidate Archetype Comparison

### momentum_capture_v1 (RECOMMENDED)

A repo-derived candidate family based on the uncovered HIGH_VOL_CHAOTIC regime domain. This is a new candidate family proposed from the regime gap identified in the league table analysis. It does not currently exist in the repo as code, contract, or adapter.

| Criterion | Assessment |
|-----------|------------|
| Hypothesis | In HIGH_VOL_CHAOTIC regimes (high ATR, elevated volatility), directional candle expansions capture momentum. A strategy that enters on significant directional candles during HVC and exits on volatility contraction or reversal can produce net positive returns before regime transition. |
| Distinct from primary_breakout_v1 | Fully. primary_breakout requires TREND (high ADX) + breakout; momentum_capture requires HIGH_VOL_CHAOTIC (high ATR) + directional momentum. Opposite regime requirement (HVC is blocked by primary_breakout). Different signal logic (directional candle vs breakout threshold). |
| Distinct from range_mean_reversion_v1 | Fully. range_mean_reversion requires RANGE (low ADX) + mean reversion; momentum_capture requires HIGH_VOL_CHAOTIC (high ATR) + momentum continuation. Opposite regime requirement (HVC is blocked by range_mean_reversion). Opposite signal logic (momentum vs reversion). |
| Regime fit | HIGH_VOL_CHAOTIC is the only uncovered regime in the existing league table. Both PARK candidates block HVC. At calibrated ATR ~77, MEXC windows contain ~10-27% HVC. Uncalibrated ATR=2.0 produces 99.5% HVC (blocked for existing candidates but relevant for this candidate). |
| Data availability | Same MEXC multi-window calibrated dataset (20 windows, 66358 rows, 1105.97 total hours). Multiple ATR threshold variants available from #3032 calibration series for windows with meaningful HVC splits. |
| Implementation complexity | Medium. Requires new signal logic (directional candle detection, momentum continuation or volatility contraction exit). New adapter class registration in adapter registry. Replay runner extension (currently only supports primary_breakout_runner_v1). StrategyAdapterId Literal type expansion. |
| Validation path | Full pipeline: calibrate directional candle threshold -> replay against HVC-dominant windows -> compute execution economics -> produce evidence packet. No live go required. |
| Execution economics risk | Elevated. HVC by definition has wide spreads and potential slippage. Choppy HVC markets may produce frequent entries and exits with fee drag (similar to the fee dominance issue in range_mean_reversion_v1). Short-side execution unvalidated. |
| Learning value for league table | HIGH. If momentum_capture_v1 produces positive economics, it proves HVC is a viable regime and the league table gains a meaningful third strategy. If it produces negative economics, the league table gains strong evidence that BTCUSDT MEXC offers no profitable edge regardless of regime -- a powerful finding for future research scope. |

### volatility_breakout_v2 (NOT SELECTED)

Evaluated and rejected in #3156. The rejection rationale is preserved:

| Criterion | Assessment |
|-----------|------------|
| Hypothesis | Different volatility regime detection for breakout entries |
| Distinct from primary_breakout_v1 | Weak: still a breakout/trend strategy. Risk of threshold-tuned clone. |
| Regime fit | Overlaps primary_breakout (both target TREND). |
| Data availability | Same MEXC data, but no clear differentiation benefit. |
| Implementation complexity | Low (could reuse runner), but differentiation unclear. |
| Validation path | Would repeat primary_breakout evidence path without clear added hypothesis. |
| Risk | Medium: could be seen as thinly disguised primary_breakout tuning. |

**Decision: NOT SELECTED.** Insufficient differentiation from PARK candidate. Risk of being a threshold-tuned clone. No new evidence since #3156 changes this assessment.

### momentum_pullback_v1 (NOT SELECTED)

Evaluated and rejected in #3156. The rejection rationale is preserved:

| Criterion | Assessment |
|-----------|------------|
| Hypothesis | Enter on pullbacks within established momentum (trend retracement entries) |
| Distinct from primary_breakout_v1 | Partial: different entry logic but same regime requirement (TREND). Both are trend-following. |
| Regime fit | Requires TREND regime. primary_breakout already covers this regime domain. |
| Data availability | Same MEXC data. |
| Implementation complexity | Medium (requires trend detection + retracement filter). |
| Validation path | Would need TREND-dominant dataset, which the MEXC fragments lack (only 0.5-32% TREND). |
| Risk | Medium: regime overlap with PARK candidate could duplicate negative economics. |

**Decision: NOT SELECTED.** Same regime dependency as PARK candidate. Insufficient differentiation. No new evidence since #3156 changes this assessment.

### high_vol_filter (NOT SELECTED)

Evaluated and rejected in #3156. The rejection rationale is preserved:

| Criterion | Assessment |
|-----------|------------|
| Hypothesis | Avoid or filter HIGH_VOL_CHAOTIC regimes instead of trading them |
| Distinct from primary_breakout_v1 | Weak: primary_breakout already blocks HIGH_VOL_CHAOTIC per contract |
| Regime fit | HIGH_VOL_CHAOTIC is already blocked by existing strategy contracts |
| Data availability | Not needed; the behavior is already contract-enforced |
| Validation path | No clear evidence gap: existing contracts already filter HVC |

**Decision: NOT SELECTED.** No new research value. Existing contracts already handle HVC avoidance.

### liquidity_filtered_breakout_v1 (NOT EVALUATED)

This archetype was listed for consideration in #3164 but has no repo-backed evidence. No contracts, docs, or evidence entries exist for this candidate family in the working repo. Cannot be evaluated as a candidate for this selection without evidence foundation.

### regime_switch_v1 (NOT EVALUATED)

This archetype was listed for consideration in #3164 but has no repo-backed evidence. No contracts, docs, or evidence entries exist for this candidate family in the working repo. Cannot be evaluated as a candidate for this selection without evidence foundation.

### Comparative Ranking (Qualitative, Not Numeric)

| Candidate | Differentiation | Regime Fit | Data Ready | Implementation Path | Learning Value | Verdict |
|-----------|----------------|------------|------------|-------------------|----------------|---------|
| momentum_capture_v1 | HIGH | STRONG (HVC) | YES | CLEAR (medium effort) | HIGH | **SELECT** |
| volatility_breakout_v2 | LOW | OVERLAP (TREND) | YES | MUDDY | LOW | Reject |
| momentum_pullback_v1 | MEDIUM | OVERLAP (TREND) | PARTIAL | MUDDY | LOW | Reject |
| high_vol_filter | LOW | N/A | YES | NONE | NONE | Reject |

## Selected Candidate

**momentum_capture_v1**

Candidate ID: `cand-momentum-capture-v1-btcusdt-mexc`

### Reason for Selection

1. **Regime gap filled**: Both existing PARK candidates explicitly BLOCK HIGH_VOL_CHAOTIC. The league table has coverage for TREND (primary_breakout_v1) and RANGE (range_mean_reversion_v1) but zero coverage for HIGH_VOL_CHAOTIC -- the regime that wins all tiebreakers in the regime service cascade and is the most common regime in uncalibrated data. A HIGH_VOL_CHAOTIC-specialized candidate covers the only remaining regime domain with existing data support.

2. **Maximum differentiation**: momentum_capture_v1 requires HIGH_VOL_CHAOTIC (high ATR) and prohibits trading in TREND and RANGE. This is the orthogonal opposite of both PARK candidates. The league table would contain three regime-specialized strategies, each operating in a mutually exclusive regime domain.

3. **Maximum learning value for the league table**: This is the decisive criterion. The existing league table contains two candidates with negative economics in two different regimes. A third result in the remaining regime will determine whether any regime on BTCUSDT MEXC supports profitable trading:
   - If momentum_capture_v1 produces positive economics: the league table becomes actionable (HVC has edge, TREND/RANGE do not).
   - If momentum_capture_v1 produces negative economics: strong evidence that BTCUSDT MEXC offers no profitable edge in any regime, which would inform future research direction (different symbol, different market, different data source).
   - Either outcome adds more learning value than any TREND-clone candidate.

4. **Data ready**: The existing MEXC multi-window calibrated dataset provides windows with meaningful HVC splits (10-27% at calibrated ATR ~77, up to 99.5% at ATR=2.0). Multiple ATR threshold variants are available from the #3032 calibration series.

5. **Testable without Live-Go**: Full pipeline (calibrate -> replay -> economics -> evidence packet) runs entirely offline with existing infrastructure. Adapter registration and replay runner extension are clearly scoped work items.

### Non-selection reasons for alternatives

- **volatility_breakout_v2**: Insufficiently differentiated from primary_breakout_v1. Risk of threshold-tuned TREND clone. Rejected. Rationale preserved from #3156.
- **momentum_pullback_v1**: Same TREND regime dependency as primary_breakout_v1. Insufficient differentiation. Rejected. Rationale preserved from #3156.
- **high_vol_filter**: No research value; existing contracts already enforce HVC avoidance. Rejected. Rationale preserved from #3156.
- **liquidity_filtered_breakout_v1**: No repo evidence exists. Cannot be responsibly evaluated. Not selected.
- **regime_switch_v1**: No repo evidence exists. Cannot be responsibly evaluated. Not selected.

**This selects a candidate for research; it does not implement or promote it.**

## Candidate Contract Draft Path

A machine-readable candidate contract draft should be written to:

`docs/evidence/profitability_candidate_selection_3164_contract_draft.json`

Proposed fields:

| Field | Proposed Value |
|-------|----------------|
| candidate_id | `cand-momentum-capture-v1-btcusdt-mexc` |
| strategy_family | `momentum_capture` |
| symbol_universe | `BTCUSDT` |
| timeframe | `1m` |
| direction | `long_only_first_pass` (proposed; short-side realism to be evaluated) |
| regime_scope | allowed: `HIGH_VOL_CHAOTIC`, blocked: `TREND, RANGE, UNKNOWN` |
| parameter_set | directional_candle_threshold (to be calibrated), momentum_exit_threshold, atr_contraction_exit, position_sizing |
| status | `SPECIFIED` (proposed) |
| allowed_next_gate | `BACKTESTED` |

The contract is draft/proposed with research-only status. It does not claim implementation, promotion, or live readiness.

## Dataset / Evidence Path Proposal

### Dataset

**Primary**: MEXC multi-window calibrated dataset (20 windows, 66358 rows, 1105.97 total hours).

Path: `artifacts/candles/mexc_multi_window_3032/window_###/regime_calibrated/`

**Preferred ATR variant**: The ATR threshold variant from the #3032 calibration series that produces the most meaningful HIGH_VOL_CHAOTIC split without sacrificing TREND/RANGE diversity for comparison. The p75 variant (ATR ~77 USD) produces ~10-27% HVC and is recommended for the initial pass. The uncalibrated ATR=2.0 variant may also be tested as a HVC-maximizing boundary condition.

### Evidence Path

1. **Calibration**: Determine directional candle threshold for entry (possibly using the ATR multiplier approach similar to primary_breakout_v1's breakout threshold from #3145).
2. **Replay**: Run file-backed replay for each window with the `momentum_capture_v1` adapter.
3. **Economics**: Capture execution economics using the existing #3149 field set.
4. **Evidence Packet**: Produce evidence packet following `profitability_evidence_packet.v1` schema.
5. **Data Quality Gate**: Run existing dataset quality checks from #3035 schema.

### No new data capture required

This candidate does not require DB access or new data capture. The existing MEXC multi-window dataset is sufficient for the initial backtest pass.

## Stop Criteria for Follow-up Pipeline Pass

The candidate pipeline pass for `momentum_capture_v1` should stop and produce a PARK or REJECT classification if:

1. **Sample-size PASS fails**: Fewer than 10 total closed trades across all windows (lower threshold than #3152 due to smaller expected HVC window share).

2. **Economics are materially negative relative to benchmarks**:
   - **Fail/park** if fee-adjusted return R is worse than the primary_breakout_v1 benchmark (-0.122). This means the candidate adds no improvement over the existing worst-performing PARK candidate.
   - **Hard negative evidence (PARK strongly recommended)** if fee-adjusted return R < -0.5, or if churn/fee drag dominates economics (similar to range_mean_reversion_v1's fee dominance of 40,543 vs gross PnL of -26,646).
   - **Also fail** if the result is worse than both existing PARK candidates or adds no league-table learning value (e.g., same magnitude of loss as existing candidates without explaining why).

3. **HVC regime not dominant**: Replay results show the strategy primarily triggers outside HIGH_VOL_CHAOTIC regime, contradicting the hypothesis.

4. **Implementation blocker**: The existing replay runner cannot consume the new signal logic without core infrastructure changes beyond adapter registration and runner extension (would escalate scope).

5. **Short-side execution invalid** (if long_short is attempted): Replay shows zero valid short fills or systematic short-side failure in the simulator.

6. **Promotion implied**: Any result that would imply paper readiness or live readiness without explicit gates.

At any stop condition, the candidate receives a PARK or REJECT classification and is not promoted.

## Follow-up Recommendation

A separate follow-up issue should be created to run the `momentum_capture_v1` controlled-lab pipeline pass. The follow-up issue must:

- Reference this selection document (#3164) as the selection authority.
- Define the specific adapter registration and replay runner extension work items.
- Define the ATR threshold variant selection for the initial pass.
- Define the calibration methodology for directional candle thresholds.
- Include the stop criteria defined above.
- Explicitly state no Live-Go, no Echtgeld-Go, no promotion.

The follow-up issue is NOT created by this selection. Candidate selection must be merged before the pipeline issue is created.

## Safety Boundaries

- Candidate selection is research-only, not implementation or promotion.
- No Live-Go, no Echtgeld-Go, LR remains NO-GO.
- Board-stage trade-capable is not Live-Go.
- No runtime actions, no Docker actions, no DB access.
- No production config or code changes.
- No primary_breakout_v1 or range_mean_reversion_v1 tuning in this slice.
- No automatic promotion from this selection.
- Contract draft path is proposed research metadata, not a runtime configuration.
- League table remains advisory only.
- AI, dashboard, and docs do not authorize trading.

## Limitations

1. This selection uses committed repo evidence only; no new replay, DB query, or SurrealDB context was accessed.
2. `momentum_capture_v1` is a new repo-derived candidate family. It has no adapter code, no contract, and no prior evidence.
3. No replay runner support exists for any candidate beyond `primary_breakout_v1`. The pipeline pass requires runner extension.
4. HIGH_VOL_CHAOTIC window share is small (10-27%) in calibrated datasets; the candidate may produce insufficient sample size even with 20 windows.
5. Controlled_lab_evidence only; no natural-paper or live evidence exists for any candidate in this repo.
6. Short-side execution in the replay simulator is unvalidated for this strategy type.
7. PANIC regime is not implemented in the regime service; UNKNOWN is the only fallback.
8. `liquidity_filtered_breakout_v1` and `regime_switch_v1` were not evaluated due to absence of repo evidence.
9. No SurrealDB/Context Brain/MCP evidence was used.
