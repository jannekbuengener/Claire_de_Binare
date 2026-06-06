# CDB Profitability Execution Economics v1

**Status:** Draft contract surface for #3039  
**Mode:** Docs / schema / example fixtures only  
**Parent:** #3032  
**Live-Readiness:** NO-GO  
**Runtime Impact:** none  

## Purpose

This document defines the first Execution Economics v1 surface for the
Profitability Engine.

The goal is not to change the execution service. The goal is to make candidate
economics auditable before any ranking step by forcing gross return, cost
attribution, and net return into one repeatable research contract.

## Contract Artifacts

| Artifact | Path | Role |
|---|---|---|
| Economics model schema | `docs/contracts/profitability_execution_economics_model.v1.schema.json` | Research fee/spread/slippage model and fail-closed assumption policy |
| Economics assessment schema | `docs/contracts/profitability_execution_economics_assessment.v1.schema.json` | Candidate-level gross-to-net assessment output |
| Model example | `docs/contracts/examples/profitability_execution_economics_model_valid.json` | Valid research-only economics model fixture |
| Assessment example | `docs/contracts/examples/profitability_execution_economics_assessment_valid.json` | Valid research-only assessment fixture |

## Relationship To Existing Repo Surfaces

Execution Economics v1 does not replace execution runtime code:

- `profitability_evidence_packet.v1` already contains `gross_return`,
  `net_return`, `fees`, `spread_cost`, and `slippage_cost`.
- `#3037` defines how batch evidence is grouped across candidates.
- `#3038` defines the stress scenarios that inform slippage and friction
  understanding.

This slice adds the missing contract layer that says when those fields are good
enough to support a comparison and when they remain too weak for ranking.

## Model Design

Execution Economics Model v1 records:

- fee model basis and bounded assumptions
- spread model basis and measurement unit
- slippage model basis and input sources
- explicit cost-attribution requirements
- evidence integration references
- explicit warning/fail/blocked rules when assumptions are incomplete

The model is fail-closed:

- missing gross return is `BLOCKED`
- missing slippage assumptions for candidate comparison is `FAIL`
- weak or estimated fee assumptions may downgrade to `WARNING`

This keeps net performance honest instead of pretending gross return is enough.

## Assessment Design

Execution Economics Assessment v1 records:

- candidate and model identity
- gross return
- net return
- cost breakdown
- assessment status
- ranking readiness
- assumption findings

`ranking_ready=false` is meaningful. A candidate may have positive gross return
and still remain not rankable because cost assumptions are incomplete or stress
signals show fragile economics.

## Relationship To Neighbor Issues

- `#3034` defines the candidate and evidence packet surfaces consumed here.
- `#3035` defines dataset quality prerequisites before economics should be
  trusted.
- `#3037` defines the multi-candidate batch evidence hook.
- `#3038` defines profitability scenario stress packs that inform economics
  assumptions.
- `#3040` remains separate and may only rank candidates after this net
  economics surface exists.
- If later runtime integration or live fee sourcing is required, that work
  stays out of scope for this slice and belongs in a separate issue.

## Ranking Dependency

Strategy League Table work must treat Execution Economics as a hard dependency:

- no gross-only ranking
- no candidate promotion based on raw replay return alone
- no hidden fee, spread, or slippage assumptions

Without Execution Economics v1, any league table is incomplete.

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

- no execution-service change
- no live fee or exchange integration
- no risk-code change
- no DB migration
- no league table implementation
- no live-readiness uplift

## Validation

For this docs-only slice, validation means:

1. both JSON schemas parse and pass schema validation
2. both example fixtures validate against their matching schemas
3. fee, spread, slippage, and cost attribution are explicit
4. ranking dependency on net economics remains explicit and fail-closed

This does not prove a candidate is profitable, paper-ready, or live-ready.
