# CDB Profitability League Table v1

**Status:** Draft contract surface for #3040  
**Mode:** Docs / schema / example fixtures only  
**Parent:** #3032  
**Live-Readiness:** NO-GO  
**Runtime Impact:** none  

## Purpose

This document defines the first Strategy League Table v1 surface for the
Profitability Engine.

The goal is not automatic promotion. The goal is a repeatable, evidence-backed
ranking view that compares candidates on net economics, robustness, evidence
completeness, and safety status before any next research gate is considered.

## Contract Artifacts

| Artifact | Path | Role |
|---|---|---|
| League table model schema | `docs/contracts/profitability_league_table_model.v1.schema.json` | Ranking dimensions, rules, recommendation semantics |
| League table report schema | `docs/contracts/profitability_league_table_report.v1.schema.json` | Candidate ranking output and report shape |
| Model example | `docs/contracts/examples/profitability_league_table_model_valid.json` | Valid research-only ranking model fixture |
| Report example | `docs/contracts/examples/profitability_league_table_report_valid.json` | Valid research-only ranking report fixture |

## Relationship To Existing Repo Surfaces

League Table v1 depends on already defined Profitability contracts:

- `#3034` defines the candidate and evidence packet surfaces.
- `#3035` defines dataset-quality preconditions.
- `#3037` defines multi-candidate batch evidence grouping.
- `#3038` defines stress signals used for robustness and stress resilience.
- `#3039` defines the execution-economics surface and `ranking_ready`.

This means League Table v1 is a ranking contract over existing evidence, not a
new runtime evaluator.

## Scoring Design

League Table v1 records weighted scoring dimensions such as:

- net return
- robustness
- evidence completeness
- safety status
- stress resilience

Weights are explicit, and gross-only ranking is forbidden. A candidate without
net-economics readiness may still appear in the report, but it must not be
treated as fully rankable.

## Ranking Rules

The ranking rules are fail-closed:

- no gross-only ranking
- `ranking_ready=true` is required for honest full ranking
- blocked conditions remain explicit
- tie-breakers must prefer safer and better evidenced candidates, not just
  raw returns

This keeps the table from hiding weak assumptions behind a single score.

## Recommendation Semantics

League Table recommendations remain advisory only:

- `REJECT`
- `PARK`
- `PROMOTE_TO_NEXT_RESEARCH_GATE`
- `UNSAFE`
- `NO_RECOMMENDATION`

These are not executable actions. They do not authorize paper, micro-live,
capital allocation, or reactivation of `#205` / `#211`.

## Report Design

The report output records:

- table status
- candidate rank
- total score
- ranking readiness
- net return
- dimension scores
- recommendation
- limitations summary

This allows partial tables where some candidates are present for visibility but
still clearly marked as not rank-ready.

## Relationship To Neighbor Issues

- `#3040` must stay downstream of `#3039`; ranking without net economics is
  incomplete.
- `#205` and `#211` remain future scaling anchors only and are not reactivated
  here.
- If later portfolio allocation or capital-sleeve logic is needed, that work
  stays out of scope for this slice and belongs in a separate issue.

## Safety Boundaries

- LR remains NO-GO.
- `trade-capable` is not Live-Go.
- No Echtgeld-Go.
- No runtime change.
- No productive DB write.
- No MCP mutation.
- No Risk, Execution, Allocation, kill-switch, or LR gate change.
- ARVP, backtest, and paper are evidence, not approval.
- AI, dashboard, and docs are not authority.
- No automatic promotion.
- No capital scaling without separate gates.

## Non-Goals

- no automatic promotion
- no capital allocation
- no #205/#211 reactivation
- no runtime implementation
- no DB migration
- no live-readiness uplift

## Validation

For this docs-only slice, validation means:

1. both JSON schemas parse and pass schema validation
2. both example fixtures validate against their matching schemas
3. ranking remains net-first and fail-closed
4. recommendation semantics remain advisory and non-executing

This does not prove a candidate is profitable, paper-ready, or live-ready.
