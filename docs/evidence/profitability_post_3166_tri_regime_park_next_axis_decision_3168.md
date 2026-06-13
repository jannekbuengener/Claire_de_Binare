# CDB Profitability -- Post-3166 Tri-Regime PARK Next Axis Decision #3168

**Date:** 2026-06-13
**Issue:** #3168
**Refs:** #3032, #3153, #3156, #3157, #3162, #3164, #3166, PR #3167
**Status:** Complete -- next research axis selected from tri-regime PARK evidence

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git status -sb`, `git rev-parse HEAD`, `git rev-parse origin/main`, `gh issue view 3168`, `gh issue view 3166`, `gh pr view 3167`, `gh pr list --state open`, duplicate search for profitability next-axis issues, repo reads of required profitability evidence and canon docs |
| `records_or_results` | `#3168` OPEN, `#3166` CLOSED, PR `#3167` MERGED, open PR list empty, duplicate search returned only `#3168`. Tri-regime PARK evidence now exists for TREND, RANGE, and HIGH_VOL_CHAOTIC. Gross and fee-adjusted returns are negative for all three candidates. |
| `repo_crosscheck` | `docs/evidence/profitability_league_table_report_seed_3166.json`, `docs/evidence/profitability_league_table_seed_momentum_capture_v1_3166.json`, `docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md`, `docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md`, `docs/evidence/profitability_league_table_report_seed_3162.json`, `docs/evidence/profitability_primary_breakout_v1_park_decision_3032.md`, `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_multi_window_3032.json`, `docs/evidence/profitability_execution_economics_range_mean_reversion_v1_mexc_multi_window_3157.json`, `docs/evidence/profitability_execution_economics_momentum_capture_v1_mexc_multi_window_3166.json`, `docs/evidence/profitability_mexc_multi_window_evidence_3032.md`, `docs/evidence/profitability_mexc_sample_size_expansion_3032.md`, `docs/evidence/profitability_btcusdt_regime_calibration_3032.md`, `docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`, `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`, `docs/strategy/CDB_PROFITABILITY_LEAGUE_TABLE_V1.md` |
| `impact_on_plan` | Tri-regime coverage is now complete on BTCUSDT/MEXC/1m long-only. Because all three candidates are negative on both gross and fee-adjusted return, the next highest-value axis is a boundary test on friction economics, not Candidate #4, not a scoring formula, and not another same-loop pipeline pass. |
| `limitations` | Repo-only analysis. No SurrealDB/Context Brain. No new pipeline execution. Current artifacts do not expose a per-trade slippage breakdown, so slippage can be tested only as a bounded sensitivity question, not as a fully decomposed historical fact. |

## Scope and Non-goals

### In scope
- Synthesize the three committed PARK results across TREND, RANGE, and HIGH_VOL_CHAOTIC.
- Select exactly one next research axis.
- Evaluate all six options from `#3168`.
- Produce a docs/evidence-only decision artifact.
- Recommend whether the BTCUSDT/MEXC/1m long-only candidate loop should continue or pause.

### Non-goals
- No Candidate #4.
- No new pipeline execution.
- No scoring formula definition.
- No paper, live, or Echtgeld implication.
- No runtime, DB, Docker, LR, or production-config work.
- No issue creation in this slice.

## Tri-Regime PARK Synthesis

The profitability league table now has three committed PARK candidates, one for each regime domain used in the current BTCUSDT/MEXC/1m controlled-lab loop.

| Candidate | Regime | Fee-adjusted return R | Gross return R | Closed trades | Decision |
|---|---|---:|---:|---:|---|
| `primary_breakout_v1` | TREND | -0.122 | -0.075 | 39 | PARK |
| `range_mean_reversion_v1` | RANGE | -0.879 | -0.347 | 443 | PARK |
| `momentum_capture_v1` | HIGH_VOL_CHAOTIC | -0.535 | -0.206 | 274 | PARK |

Evidence basis:

- `primary_breakout_v1`: `docs/evidence/profitability_primary_breakout_v1_park_decision_3032.md`
- `range_mean_reversion_v1`: `docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md`
- `momentum_capture_v1`: `docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md`
- merged three-candidate report: `docs/evidence/profitability_league_table_report_seed_3166.json`

## Decision

**Selected next research axis:**

`Break-even boundary + cost/slippage sensitivity analysis`

## Why This Axis Is Selected

This axis has the highest economic learning value because it improves economic truth before adding complexity.

The decision is deliberately conservative:

1. This is **not** a rescue thesis.
2. This is a **boundary test**.
3. The core question is whether the negative net result is explained by friction, or whether the loop is economically negative even at the zero-fee boundary.

The evidence already supports three strong facts:

1. Tri-regime coverage is complete for the current loop: TREND, RANGE, and HIGH_VOL_CHAOTIC are all represented.
2. All three candidates are negative on `fee_adjusted_return_r`.
3. All three candidates are also negative on `gross_return_r`, which is the current closest repo-backed zero-fee boundary.

That means:

- zero-fee / low-fee analysis is a **boundary check**, not an optimization path
- friction improvement matters only if the friction component explains the negative net finding
- if even the gross or zero-fee boundary stays negative, the BTCUSDT/MEXC/1m long-only candidate loop should be economically parked

## Boundary Interpretation

Using the existing execution economics artifacts:

| Candidate | Gross return R | Fee-adjusted return R | Boundary reading |
|---|---:|---:|---|
| `primary_breakout_v1` | -0.075 | -0.122 | Negative even before fees are subtracted |
| `range_mean_reversion_v1` | -0.347 | -0.879 | Deeply negative before fees; fees worsen an already losing loop |
| `momentum_capture_v1` | -0.206 | -0.535 | Materially negative before fees; fees worsen an already losing loop |

Current repo evidence therefore does **not** support the claim that a lower-fee venue or a minor friction improvement would by itself make these candidates profitable.

The correct next step is to quantify that boundary explicitly and fail closed:

- If the zero-fee boundary is still negative for all three, the current BTCUSDT/MEXC/1m long-only candidate loop should pause.
- If plausible friction reductions cannot close the remaining gap, the loop should stay paused.
- If the current artifacts cannot isolate slippage honestly, that limitation must be recorded instead of inventing a rescue story.

## Evaluation of the Six Options from #3168

| Option | Verdict | Assessment |
|---|---|---|
| 1. Short-side / long-short expansion | Reject for next slice | Premature. Existing evidence marks short-side as blocked by current replay/simulator constraints. Adds implementation complexity before proving the current loop can survive even the zero-fee boundary. |
| 2. Different symbol or multi-symbol scan | Reject for next slice | Adds a second major variable before the current loop's failure mode is quantified. Symbol expansion should come only after the friction boundary is understood. |
| 3. Different venue / better fee-liquidity venue | Reject for next slice | Premature as a first move. Venue change is only economically relevant if friction can plausibly rescue the loop. Current gross-return evidence does not support that assumption. |
| 4. Longer dataset / more market regimes | Not selected now | Valuable as a later data-axis step, but not the highest-value first move. The current loop already spans 20 windows, 1105.97 hours, and all three regime domains. More same-axis data is lower-value than first quantifying whether the economics are structurally unrecoverable. |
| 5. Break-even boundary + cost/slippage sensitivity analysis | **SELECT** | Highest-value truth surface. Uses current evidence, adds no false complexity, and directly answers whether friction explains the losses or whether the loop is negative even at the zero-fee boundary. |
| 6. Stop BTCUSDT/MEXC long-only candidate loop until data axis improves | Operational recommendation, not the selected research axis | This is the recommended operating posture, but it is a governance/action recommendation rather than the research axis itself. The selected axis provides the evidence basis for making that pause explicit and durable. |

## Rejected Alternatives

At least two alternatives are explicitly rejected as the next slice:

### Rejected: Short-side / long-short expansion

- Short-side remains blocked in current candidate evidence.
- This would expand scope into implementation realism before the current loop has passed a basic economic boundary test.
- It risks adding complexity where the present evidence already suggests the long-only loop is negative even before fee subtraction.

### Rejected: Different venue / better fee-liquidity venue

- A venue switch is only justified once friction has been shown to be the decisive explanatory variable.
- The current evidence does not show that. All three candidates remain negative on the current zero-fee proxy (`gross_return_r`).
- Changing venue first would mix friction effects with venue/data/market-structure changes and reduce clarity.

### Rejected: Different symbol or multi-symbol scan

- This broadens the search space before the current loop is economically falsified or bounded.
- The current question is not yet "which symbol works" but "is the current loop structurally broken even without fees?"

## Explicit Recommendation on the Current Candidate Loop

**Recommendation:** pause the BTCUSDT/MEXC/1m long-only candidate loop until the break-even/friction boundary is explicitly resolved.

This pause recommendation is already directionally supported by the existing evidence because:

- regime coverage is complete
- no candidate is economically positive
- no candidate is even gross-positive in aggregate
- the league table remains `ranking_ready=false`

No Candidate #4 should be created inside the same BTCUSDT/MEXC/1m long-only loop until this boundary question is resolved.

## Why Candidate #4 Is Premature

Candidate #4 is premature for four reasons:

1. The original regime-coverage reason for adding new candidates is exhausted. TREND, RANGE, and HIGH_VOL_CHAOTIC are already covered.
2. The current three-candidate set is uniformly negative, so another same-loop candidate is more likely to add code than economic truth.
3. The more important unresolved question is economic boundary, not missing regime coverage.
4. A fourth candidate before resolving the boundary would risk false progress: more artifacts, no new truth.

## Why a Scoring Formula Is Premature

A scoring formula is premature because the repo evidence already says the table is not honestly rank-ready:

- `ranking_ready=false` is explicit in the seed artifacts
- the current report is intentionally `PARTIAL`
- the existing docs say a numeric scoring formula should not be defined while the table contains only negative PARK baselines

Creating a scoring formula here would manufacture false precision from three negative single-symbol, single-venue, long-only candidates.

## Follow-up Issue Recommendation Only

Recommended follow-up issue title:

`[PROFITABILITY][ECONOMICS] Quantify zero-fee boundary and cost/slippage sensitivity after tri-regime PARK`

Recommended scope for that follow-up:

- docs/evidence only
- derive explicit zero-fee boundary from current committed execution economics artifacts
- quantify fee drag from current gross-to-net deltas
- define bounded slippage/spread sensitivity scenarios without inventing unavailable history
- state whether any plausible friction improvement could move a candidate to break-even
- produce an explicit pause/continue recommendation for the BTCUSDT/MEXC/1m long-only loop

Not in scope for that follow-up:

- no new replay run
- no new candidate
- no venue integration
- no symbol expansion
- no runtime/DB/Docker/LR work

## Stop Criteria for the Follow-up

The recommended follow-up should stop and report HOLD if any of the following occurs:

1. The current artifacts cannot support an honest zero-fee boundary calculation.
2. Slippage cannot be bounded honestly from repo evidence and would require invented assumptions.
3. Scope drifts into Candidate #4, pipeline execution, venue integration, symbol expansion, runtime work, DB work, Docker work, LR work, paper work, or live work.
4. The analysis shows the zero-fee boundary remains negative for all three candidates and no plausible friction reduction closes the gap.
5. A scoring formula is proposed before a positive-economics candidate exists.

If stop criterion 4 is reached, the follow-up should explicitly confirm:

- pause BTCUSDT/MEXC/1m long-only candidate creation
- do not create Candidate #4
- do not define a scoring formula
- move the next research discussion to a different data axis only after the pause is recorded

## Safety Boundaries

- LR remains `NO-GO`.
- No Live-Go.
- No Echtgeld-Go.
- No Paper-Go.
- Board stage `trade-capable` is not Live-Go.
- League-table and profitability evidence remain advisory only.
- No runtime, DB, Docker, or production-config change.
- No new pipeline pass.
- No Candidate #4.
- No scoring formula.

## Final Recommendation

Select **`Break-even boundary + cost/slippage sensitivity analysis`** as the one next research axis.

Treat it as a conservative economic boundary test, not as a rescue narrative.

Until that boundary is resolved, the BTCUSDT/MEXC/1m long-only candidate loop should be treated as **paused by default**.
