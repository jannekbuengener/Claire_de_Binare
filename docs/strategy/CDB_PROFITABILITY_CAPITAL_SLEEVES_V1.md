# CDB Profitability Capital Sleeves v1

**Status:** Draft contract surface for #3041  
**Mode:** Docs / schema / example fixtures only  
**Parent:** #3032  
**Live-Readiness:** NO-GO  
**Runtime Impact:** none  

## Purpose

This document defines the first Capital Sleeve Model and Paper Accounting v1
surface for the Profitability Engine.

The goal is not real capital allocation. The goal is a repeatable paper-only
governance and reporting model that groups candidates into sleeves and tracks
paper pnl, drawdown, and simulation state without touching risk or allocation
runtime code.

## Contract Artifacts

| Artifact | Path | Role |
|---|---|---|
| Capital sleeve model schema | `docs/contracts/profitability_capital_sleeve_model.v1.schema.json` | Sleeve definitions, paper context, and integration boundaries |
| Paper accounting report schema | `docs/contracts/profitability_paper_accounting_report.v1.schema.json` | Sleeve-level paper pnl and drawdown reporting |
| Model example | `docs/contracts/examples/profitability_capital_sleeve_model_valid.json` | Valid research-only sleeve model fixture |
| Report example | `docs/contracts/examples/profitability_paper_accounting_report_valid.json` | Valid research-only paper accounting report fixture |

## Relationship To Existing Repo Surfaces

Capital Sleeves v1 depends on already defined Profitability and paper surfaces:

- `#3040` defines how candidates are comparatively ranked before sleeve
  grouping.
- `#1784` remains the paper-betriebsfaden and operational context anchor.
- `#205` and `#211` remain future scaling anchors only.
- `#2985` remains the separate live roadmap and must not be collapsed into this
  slice.

This means Capital Sleeves v1 is a paper-governance contract over existing
evidence, not an allocation engine.

## Sleeve Design

The sleeve model records four paper-only sleeves:

- `CORE`
- `GROWTH`
- `OPPORTUNISTIC`
- `EXPERIMENTAL`

Each sleeve carries:

- purpose
- candidate profile
- admission basis
- explicit paper-only semantics

This keeps sleeve usage explicit instead of drifting into informal capital
language.

## Paper Accounting Design

The paper accounting report records:

- sleeve-level candidate counts
- sleeve-level paper pnl
- sleeve-level drawdown
- allocation simulation status
- notes and limitations

This provides visibility into paper behavior without creating real allocation
authority.

## Integration Boundaries

The integration boundaries are fail-closed:

- no risk-code changes
- no allocation-service changes
- no real capital authority
- future anchors `#205` and `#211` remain future-only
- live roadmap `#2985` remains separate

If later portfolio or allocation-runtime work is needed, that work stays out of
scope for this slice and belongs in a separate issue.

## Relationship To Neighbor Issues

- `#3041` must stay downstream of ranking and net economics.
- sleeve grouping is not a promotion engine
- paper accounting is not a live-go signal
- future risk/allocation integration remains a separate gate

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

- no risk-code change
- no allocation-service change
- no capital authorization
- no #205/#211 reactivation
- no runtime implementation
- no live-readiness uplift

## Validation

For this docs-only slice, validation means:

1. both JSON schemas parse and pass schema validation
2. both example fixtures validate against their matching schemas
3. sleeve governance remains paper-only and non-activating
4. future allocation and live-roadmap boundaries remain explicit

This does not prove a candidate is profitable, paper-ready, or live-ready.
