# CDB Profitability Scenario Pack Library v1

**Status:** Draft contract surface for #3038  
**Mode:** Docs / schema / example fixtures only  
**Parent:** #3032  
**Live-Readiness:** NO-GO  
**Runtime Impact:** none  

## Purpose

This document defines the first profitability-specific Scenario Pack Library for
stress-testing strategy candidates before they move toward ranking or paper
candidate status.

The goal is not a new simulator. The goal is a controlled, versioned catalog of
stress scenarios that can be consumed by the ARVP Batch Runner and reported
through existing Profitability evidence surfaces.

## Contract Artifacts

| Artifact | Path | Role |
|---|---|---|
| Scenario pack catalog schema | `docs/contracts/profitability_scenario_pack_catalog.v1.schema.json` | Versioned catalog of profitability stress scenarios |
| Stress summary schema | `docs/contracts/profitability_scenario_stress_summary.v1.schema.json` | Candidate-level stress outcome summary |
| Catalog example | `docs/contracts/examples/profitability_scenario_pack_catalog_valid.json` | Valid research-only catalog fixture |
| Stress summary example | `docs/contracts/examples/profitability_scenario_stress_summary_valid.json` | Valid research-only stress summary fixture |

## Relationship To Existing Repo Surfaces

Profitability Scenario Pack Library v1 does not replace the existing technical
scenario surfaces:

- `core.replay.scenario_packs.py` remains the current technical built-in pack
  surface and already defines deterministic packs such as `baseline`,
  `pessimistic_execution`, `delayed_execution`, `low_liquidity`, and
  `feed_gap`.
- `#3037` defines how a batch runner consumes scenario references and groups
  them into comparable evidence.
- `profitability_evidence_packet.v1` already contains `scenario_results` and is
  the downstream evidence hook for this slice.

This means `#3038` defines the profitability research catalog and stress
semantics, not a new runtime runner.

## Scenario Domains

Scenario Pack Library v1 must cover at least these domains:

- slippage shock
- spread expansion
- partial fills
- rejections
- latency
- feed gaps
- volatility stress
- liquidity stress

Each scenario in the catalog carries:

- a stable `scenario_id`
- a domain
- a severity
- deterministic config overrides
- an expected research use

The deterministic requirement is deliberate. Random stress without reproducible
shape would weaken candidate comparison and break auditability.

## Catalog Design

The catalog is the reusable scenario definition layer. It records:

- catalog identity and pack version
- covered stress domains
- one or more scenario packs with deterministic overrides
- explicit evidence integration references
- limitations

Versioning matters because later scenario additions must not silently rewrite
the meaning of older stress evidence.

## Stress Summary Design

The stress summary is the candidate-level outcome layer. It records:

- overall stress outcome
- per-scenario status
- per-scenario net return delta
- per-scenario drawdown delta
- impact summary
- recommendation impact without authority

Stress evidence remains advisory only:

- `PASS` does not authorize paper, micro-live, live, or capital scaling
- `WARNING` means the candidate may need to be parked or reviewed
- `FAIL` means the candidate is stress-fragile for the scoped research purpose
- `BLOCKED` means the stress result cannot be assessed honestly

## Relationship To Neighbor Issues

- `#3034` defines the evidence packet surface that receives scenario results.
- `#3035` defines dataset quality prerequisites before stress evidence is
  trusted.
- `#3037` defines the batch-runner consumption hook for scenario references.
- `#3039` remains separate and will convert gross results plus friction into
  net-economics interpretation.
- If later runtime or simulation work is needed beyond this contract surface,
  that implementation stays out of scope for this slice and belongs in a
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

- no scenario runner implementation
- no execution-service rewrite
- no new execution simulation in core
- no DB migration
- no ranking logic
- no live-readiness uplift

## Validation

For this docs-only slice, validation means:

1. both JSON schemas parse and pass schema validation
2. both example fixtures validate against their matching schemas
3. the catalog covers the required `#3038` stress domains
4. the evidence path from scenario catalog to batch runner to evidence packet
   stays explicit

This does not prove a candidate is profitable, paper-ready, or live-ready.
