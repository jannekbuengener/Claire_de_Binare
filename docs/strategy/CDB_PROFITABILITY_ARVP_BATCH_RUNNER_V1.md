# CDB Profitability ARVP Batch Runner v1

**Status:** Draft contract surface for #3037  
**Mode:** Docs / schema / example fixtures only  
**Parent:** #3032  
**Live-Readiness:** NO-GO  
**Runtime Impact:** none  

## Purpose

This document defines the first design contract for a multi-candidate ARVP batch
runner inside the Profitability Engine program.

The goal is not a new runtime. The goal is a repeatable batch shape that can:

- take multiple candidate contracts as input
- bind them to one explicit dataset selection
- route them through existing replay and ARVP evidence surfaces
- emit a comparable batch summary with explicit `COMPLETED`, `PARKED`,
  `BLOCKED`, or `FAILED` outcomes

## Contract Artifacts

| Artifact | Path | Role |
|---|---|---|
| Batch manifest schema | `docs/contracts/profitability_arvp_batch_manifest.v1.schema.json` | Input contract for candidates, dataset selection, evidence hooks, and failure policy |
| Batch summary schema | `docs/contracts/profitability_arvp_batch_summary.v1.schema.json` | Output contract for per-candidate outcomes and batch-level status |
| Manifest example | `docs/contracts/examples/profitability_arvp_batch_manifest_valid.json` | Valid research-only manifest fixture |
| Summary example | `docs/contracts/examples/profitability_arvp_batch_summary_valid.json` | Valid research-only batch summary fixture |

## Relationship To Existing ARVP Surfaces

Batch Runner v1 is deliberately a thin orchestration layer over existing repo
surfaces. It does not replace them:

- `core.replay.scenario_harness.run_scenario_group` remains the scenario group
  orchestration anchor and emits `ScenarioGroupManifest`.
- `core.replay.run_registry.ReplayRunRecord` remains the run identity and
  lifecycle anchor.
- `core.replay.arvp_gate.ARVPEvidenceBundle` and `ARVPGateVerdict` remain the
  gate/evidence verdict anchor.
- `core.replay.replay_vs_paper_compare` remains the replay-vs-paper comparison
  anchor.
- `core.replay.scenario_packs` is a current technical scenario source, but the
  profitability-specific Scenario Pack Library remains separate work in `#3038`.

This means Batch Runner v1 defines how existing evidence is grouped, not how the
underlying ARVP components behave internally.

## Manifest Design

The manifest is the controlled batch input. It requires:

- one explicit dataset selection with fingerprint and quality verdict
- one or more candidate inputs with contract references and adapter IDs
- a clear adapter boundary that stays research-only
- explicit runner surface references
- explicit evidence hooks into the Profitability Evidence Packet and batch
  summary
- a failure policy that distinguishes `BLOCKED` from `PARKED`

The manifest is fail-closed:

- missing candidate contracts are not silently tolerated
- missing dataset quality reports are not silently tolerated
- adapter boundary ambiguity is a `BLOCKED` condition
- scenario pack usage is by reference only in this issue; pack definitions are
  not duplicated here

## Output Bundle Design

The summary is the controlled batch output. It records:

- batch-level status
- counts for completed, parked, blocked, and failed candidates
- per-candidate dataset quality verdict
- per-candidate `ScenarioGroupManifest` reference and fingerprint
- one or more run record references
- gate verdict reference
- optional replay-vs-paper compare reference
- evidence packet reference
- blocking reasons, advisory findings, and next action

This design keeps a candidate comparable even when the batch is only partial.
One weak candidate must not erase the evidence of the others.

## Failure Semantics

Batch Runner v1 separates outcomes deliberately:

- `COMPLETED`: evidence bundle is complete enough to move into the next
  profitability step
- `PARKED`: evidence exists, but scenario or comparison quality still requires
  review
- `BLOCKED`: a prerequisite such as dataset quality or adapter boundary is
  missing, so honest execution is not possible
- `FAILED`: execution attempt or evidence generation failed in a way that still
  needs explicit triage

`PARKED` is not a soft success, and `BLOCKED` is not a cosmetic label. Both
must remain explicit in the batch summary.

## Relationship To Neighbor Issues

- `#3034` defines the candidate and evidence packet contracts consumed here.
- `#3035` defines the dataset quality report referenced by the batch manifest.
- `#3038` stays separate and will define profitability-specific scenario pack
  contents; this slice only defines the consumption hook.
- `#3039` stays separate and will define net-economics interpretation after
  batch evidence exists.
- `#3031` remains the active data blocker for replayable 1m candles and can
  still block honest batch execution.

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

- no new batch runtime implementation
- no core rewrite
- no DB migration
- no scenario pack catalog definition
- no execution economics model
- no strategy ranking
- no live-readiness uplift

## Validation

For this docs-only slice, validation means:

1. both JSON schemas parse and pass schema validation
2. both example fixtures validate against their matching schemas
3. the batch contracts reference the existing ARVP surfaces instead of replacing
   them
4. `BLOCKED` and `PARKED` remain explicit and fail-closed

This does not prove batch profitability, paper readiness, live readiness, or
capital readiness.
