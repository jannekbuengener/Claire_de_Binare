# CDB Profitability Control Room v1

**Status:** Draft contract surface for #3042  
**Mode:** Docs / schema / example fixtures only  
**Parent:** #3032  
**Live-Readiness:** NO-GO  
**Runtime Impact:** none  

## Purpose

This document defines the first Profitability Control Room v1 requirements for
operator and management visibility.

The goal is not a gate or approval engine. The goal is a read-only visibility
surface that makes candidate status, ranking, economics, evidence completeness,
and sleeve paper behavior visible without claiming operational authority.

## Contract Artifacts

| Artifact | Path | Role |
|---|---|---|
| Control room requirements schema | `docs/contracts/profitability_control_room_requirements.v1.schema.json` | Required panels, questions, and authority boundaries |
| Control room snapshot schema | `docs/contracts/profitability_control_room_snapshot.v1.schema.json` | Read-only snapshot shape for visibility outputs |
| Requirements example | `docs/contracts/examples/profitability_control_room_requirements_valid.json` | Valid research-only requirements fixture |
| Snapshot example | `docs/contracts/examples/profitability_control_room_snapshot_valid.json` | Valid research-only snapshot fixture |

## Relationship To Existing Repo Surfaces

Control Room v1 depends on already defined Profitability and cockpit surfaces:

- `#1445` remains the existing operative cockpit anchor.
- `#3034` and `#3035` define candidate and dataset evidence foundations.
- `#3040` defines the league table view consumed here.
- `#3041` defines sleeve paper-pnl visibility consumed here.

This means Control Room v1 is a visibility contract over existing evidence, not
an approval path.

## Panel Design

Control Room v1 requires at least these panels:

- Candidate Status
- Strategy League Table
- Cost / Risk / Regime
- Evidence Completeness
- Sleeve PnL

Each panel must declare its required inputs and whether it is intended for
operator view, management view, or both.

## Operator And Management Questions

The requirements layer must make concrete questions answerable, such as:

- which candidates are blocked or parked and why
- where evidence is incomplete
- where sleeve-level paper pnl or drawdown needs attention
- which candidates are net-credible but still not rank-ready

This keeps the control room anchored in decision support rather than pretty
status surfaces.

## Authority Boundaries

The authority boundaries are fail-closed:

- dashboard is not approval
- AI is not authority
- docs are not authority
- no Grafana-gate semantics

The control room may summarize evidence, but it cannot authorize promotion,
paper go, live go, capital allocation, or risk overrides.

## Relationship To Neighbor Issues

- `#3042` stays downstream of candidate, economics, ranking, and sleeve
  contracts.
- `#1445` remains the operational cockpit anchor and is not mutated here.
- If later dashboard or implementation work is needed beyond this requirements
  surface, that work stays out of scope for this slice and belongs in a
  separate issue.

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

- no dashboard implementation
- no Grafana-gate semantics
- no runtime implementation
- no DB migration
- no automatic promotion
- no live-readiness uplift

## Validation

For this docs-only slice, validation means:

1. both JSON schemas parse and pass schema validation
2. both example fixtures validate against their matching schemas
3. candidate, ranking, economics, evidence, and sleeve visibility stay explicit
4. dashboard / AI / docs remain non-authoritative

This does not prove a candidate is profitable, paper-ready, or live-ready.
