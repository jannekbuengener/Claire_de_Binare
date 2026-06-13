# CDB Profitability -- primary_breakout_v1 PARK Decision #3032

**Date:** 2026-06-13T13:35:00Z
**Parent:** #3032
**Issue:** #3153
**Refs:** #3152, #3154, #3151, #3149
**Status:** Complete -- PARK seed league-table decision recorded from merged multi-window evidence

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `gh issue view`, `gh pr view`, repo reads for league-table contracts/examples/docs and merged #3152 evidence artifacts | 
| `records_or_results` | #3153 OPEN at start, #3032 OPEN, PR #3154 merged. Input evidence: total_windows=20, windows_with_trades=17, closed_trades_total=39, wins=6, losses=33, gross_pnl_quote=-5769.61, net_pnl_quote=-9258.98, fees_total_quote=3489.37, fee_adjusted_return_r=-0.122156, sample_size_verdict=PASS, evidence_class=controlled_lab_evidence. |
| `repo_crosscheck` | `docs/contracts/profitability_league_table_model.v1.schema.json`, `docs/contracts/profitability_league_table_report.v1.schema.json`, `docs/strategy/CDB_PROFITABILITY_LEAGUE_TABLE_V1.md`, `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`, `docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`, merged #3152 evidence files |
| `impact_on_plan` | The contract can represent `PARK` honestly. The report schema still requires numeric score fields without a repo-backed numeric scoring method, so this slice emits a conservative seed report with `ranking_ready=false` and a documented zero-score sentinel. |
| `limitations` | No DB, runtime, replay, or tuning work used here. The decision is based only on committed evidence and contract docs. |

## Scope and Non-goals

### In scope
- Read committed #3152/#3154 evidence only.
- Read league-table contracts and docs.
- Emit a first league-table seed artifact and a ranking report seed.
- Classify `primary_breakout_v1` explicitly as `PARK` or `REJECT`.

### Non-goals
- No new replay run.
- No DB/runtime/Docker action.
- No strategy optimization.
- No threshold tuning.
- No production config change.
- No strategy behavior change.
- No promotion.

## Input Evidence

Primary merged evidence inputs:

- `docs/evidence/profitability_mexc_multi_window_evidence_3032.md`
- `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_multi_window_3032.json`
- `docs/evidence/profitability_evidence_packet_primary_breakout_v1_mexc_multi_window_3032.json`

Key committed facts used in this slice:

| Metric | Value |
|--------|-------|
| Selected windows | 20 |
| Successful replays | 20 |
| Windows with trades | 17 |
| Closed trades | 39 |
| Wins / losses | 6 / 33 |
| Gross PnL quote | -5769.61 |
| Net PnL quote | -9258.98 |
| Fees total quote | 3489.37 |
| Aggregate fee-adjusted return R | -0.122156 |
| Sample-size verdict | PASS |
| Evidence class | controlled_lab_evidence |

## League Table Contract

The existing League Table v1 contract allows an honest `PARK` outcome:

- `docs/contracts/profitability_league_table_model.v1.schema.json`
  - allowed recommendations explicitly include `PARK` and `REJECT`
  - `gross_only_ranking_allowed=false`
  - `ranking_ready_required=true`
- `docs/contracts/profitability_league_table_report.v1.schema.json`
  - candidate rows require `total_score`, `ranking_ready`, `net_return`, `recommendation`
- `docs/strategy/CDB_PROFITABILITY_LEAGUE_TABLE_V1.md`
  - league table is advisory only
  - no automatic promotion
  - `ranking_ready=true` is required for honest full ranking
- `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`
  - `ranking_ready=false` is meaningful when economics or comparison quality remain too weak for ranking use

Contract limitation found in this slice:

- The report schema requires numeric score fields.
- The repo does not define a numeric scoring formula for converting evidence into those values.
- To avoid invented metrics, this slice uses a fail-closed zero-score sentinel and marks `ranking_ready=false`.

## Ranking / Classification

### Decision

**`PARK`**

### Why not `PROMOTE_TO_NEXT_RESEARCH_GATE`

- aggregate economics are materially negative
- evidence is still controlled_lab_evidence only
- no natural-paper evidence exists
- this slice must not imply promotion, paper readiness, or live readiness

### Why not `REJECT`

- `CDB_PROFITABILITY_ENGINE_CANON.md` defines `PARKED` as: candidate remains possible, but without an active delivery step
- the same canon reserves `REJECTED` for candidates that are fachlich oder evidenzseitig verworfen
- current evidence is strongly negative, but still useful as a baseline/regression control
- no new comparison against alternative candidates was run in this slice

### Ranking status

| Field | Value |
|------|-------|
| Recommendation | `PARK` |
| ranking_ready | `false` |
| table_status | `PARTIAL` |
| total_score | `0.0` |

The `0.0` score is **not** a comparative metric. It is a fail-closed sentinel because the schema requires a numeric field while the repo does not define a numeric scoring method for honest full ranking.

## Economic Findings

The decisive economic facts are negative even after sample-size PASS:

- `net_pnl_quote = -9258.98`
- `fees_total_quote = 3489.37`
- `fee_adjusted_return_r = -0.122156`
- `win_rate = 15.38%`

This is exactly the kind of case the Profitability Engine is supposed to stop cleanly:

- sample quantity improved enough to assess the controlled-lab evidence
- economics did not support progression
- therefore the candidate must not move forward as an active promoted research winner

## Decision

`primary_breakout_v1` receives a **PARK** seed league-table entry.

Implications:

1. The strategy is visible in the ranking surface.
2. It is explicitly non-promoted.
3. It may remain as a baseline/regression candidate.
4. No paper or live implication is created.

## Implications for #3032

- #3032 now has a concrete example that the profitability pipeline can stop a weak candidate without inventing optimism.
- The next profitability step should not be tuning this candidate in-place.
- If `primary_breakout_v1` is used further, it should be as a parked baseline/reference candidate, not as a promoted winner.

## Follow-ups

- This slice creates the seed report and decision only.
- Natural-paper evidence for future candidates remains a separate path.
- No threshold-tuning issue is created here.

## Safety Boundaries

- Classification is `PARK`, not promotion.
- Controlled-lab evidence only.
- No strategy optimization in this slice.
- No Live-Go, no Echtgeld-Go, LR remains NO-GO.
- `primary_breakout_v1` may remain as baseline/regression candidate if PARK.
- No DB/runtime/Docker action.

## Limitations

1. The decision uses committed evidence only; no new replay or comparison run was allowed.
2. The report schema requires numeric scores, but the repo does not define a numeric scoring formula.
3. The zero-score sentinel is therefore a contract-shaped placeholder, not a comparative ranking metric.
4. `public.candles_1m` has no per-row venue/source column; the MEXC attribution in upstream evidence is inherited from prior same-venue evidence.
