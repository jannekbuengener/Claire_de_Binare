# CDB Profitability Candidate Contract v1

**Status:** Draft contract surface for #3034  
**Mode:** Docs / schema / example fixtures only  
**Parent:** #3032  
**Live-Readiness:** NO-GO  
**Runtime Impact:** none  

## Purpose

This document defines the first machine-readable contract surface for Profitability
Engine strategy candidates and their evidence packets.

It makes candidate comparison repeatable without changing the trading core:

- `profitability_candidate_contract.v1` defines what a strategy candidate is.
- `profitability_evidence_packet.v1` defines how validation evidence is reported.
- Example fixtures show valid shapes for documentation and later tooling.

## Contract Artifacts

| Artifact | Path | Role |
|---|---|---|
| Candidate schema | `docs/contracts/profitability_candidate_contract.v1.schema.json` | Candidate identity, scope, assumptions, lifecycle state, next gate |
| Evidence schema | `docs/contracts/profitability_evidence_packet.v1.schema.json` | Dataset fingerprint, gross/net metrics, friction costs, ARVP/Paper status, recommendation |
| Candidate example | `docs/contracts/examples/profitability_candidate_contract_valid.json` | Valid research-only candidate fixture |
| Evidence example | `docs/contracts/examples/profitability_evidence_packet_valid.json` | Valid research-only evidence fixture |

## Candidate Contract v1

The candidate contract captures the minimum comparable strategy definition:

- `candidate_id`
- `strategy_family`
- `symbol_universe`
- `timeframe`
- `direction`
- `regime_scope`
- `parameter_set`
- `hypothesis`
- `risk_assumptions`
- `execution_assumptions`
- `status`
- `allowed_next_gate`
- `reject_reason`
- `unsafe_zones`
- `limitations`

The canonical lifecycle statuses match the Profitability Engine Canon:

- `IDEA`
- `SPECIFIED`
- `BACKTESTED`
- `ARVP_VALIDATED`
- `STRESS_TESTED`
- `PAPER_CANDIDATE`
- `PAPER_VALIDATED`
- `MICRO_LIVE_CANDIDATE`
- `CAPITAL_SCALING_CANDIDATE`
- `REJECTED`
- `PARKED`
- `UNSAFE`
- `SUPERSEDED`
- `STALE`

## Evidence Packet v1

The evidence packet makes validation results comparable before ranking:

- dataset identity and fingerprint
- gross and net return
- fees, spread cost, and slippage cost
- profit factor, expectancy, win rate, average win/loss, drawdown, loss streak,
  and trade count
- regime scorecard status
- scenario results
- replay-vs-paper status
- simulator drift status
- risk block and kill-switch event counts
- recommendation and limitations

The `recommendation` field is advisory only. It cannot promote a candidate into
paper, live, micro-live, or capital scaling by itself.

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

- no productive candidate registry
- no DB migration
- no runtime implementation
- no dependency introduction
- no strategy logic change
- no live-readiness uplift

## Validation

For this docs-only slice, validation means:

1. JSON syntax for both schemas and both fixtures parses cleanly.
2. Each example fixture validates against its matching schema.
3. The contract surfaces include the #3034 required fields.
4. The safety boundaries remain explicit.

This validation does not prove strategy profitability, paper readiness, or live
readiness.
