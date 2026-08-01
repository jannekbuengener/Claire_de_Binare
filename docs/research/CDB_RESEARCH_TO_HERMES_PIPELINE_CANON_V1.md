# Research-to-Hermes Pipeline Canon v1

**Status:** Canon draft for Wave 1 (#4264)  
**Parent:** #4263  
**Mode:** Docs / architecture only — no runtime, no plugins, no cloud provisioning  
**Live-Readiness:** NO-GO  
**Board stage:** `trade-capable` ≠ Live-Go  

## Purpose

Define the end-to-end Research → Candidate → Validation → Decision pipeline before
compilers or runners exist. This canon separates roles, trust boundaries, and
handoff surfaces so free-form agent text cannot silently become a strategy
promotion path.

## Textual flow diagram

```text
[Research Request]
        |
        v
[Claire Context Gate] ---- read-only context / stop signals
        |                   (no promotion authority)
        v
[Parallel Research Sources] ---- external apps / docs / evidence refs
        |                        (no validation authority)
        v
[Candidate Compiler] ---- ResearchBrief + StrategyCandidate contracts
        |
        v
[GitHub Candidate Registry] ---- issue/PR ledger only (not productive DB)
        |
        v
[Hermes Validation Chief] ---- ValidationManifest orchestration
        |                      (no live / risk / promotion authority)
        v
[Cloud Runner / CDB ARVP] ---- offline validation jobs + evidence artifacts
        |
        v
[Candidate Evidence + Decision Record]
        |
        +--> REJECT | REVISE | PARK | PAPER_CANDIDATE
             (PAPER_CANDIDATE ≠ Live-Go; no automatic promotion)
```

## Role matrix (installed apps / surfaces)

| Surface / App | Allowed role (exactly one) | Explicitly excluded |
|---|---|---|
| Claire Context Gate | Read-only context briefing, stop/required-reads | Writes, live GO, strategy promotion |
| Research sources (docs / OSINT / installed research apps) | Evidence / hypothesis input only | Validation verdict authority |
| Candidate Compiler | Emit `cdb.research_brief.v1` + `cdb.strategy_candidate.v1` | Runtime trading, DB registry |
| GitHub Candidate Registry | Issue/PR ledger + review surface | Productive strategy registry |
| Hermes Validation Chief | Orchestrate validation gates via manifest | Live, Risk, Promotion authority |
| Cloud Runner | Execute offline validation jobs | Capital allocation, live credentials |
| CDB ARVP | Offline replay / scorecard evidence | Live readiness or promotion |
| TickerSage | Visualization only | Research, validation, decision authority |
| Gmail / Calendar | Optional operations surfaces | Pipeline authority |
| Tarot | **Excluded** — not part of pipeline v1 | All research/validation/decision roles |

## Trust and authority boundaries

| Actor | May do | Must not do |
|---|---|---|
| Research apps | Propose hypotheses and source refs | Issue PASS/FAIL or promote |
| Hermes | Schedule gates, collect evidence refs | Live trades, risk overrides, capital GO |
| CDB Risk / Execution | Remain authoritative for any order path | Be bypassed by research artifacts |
| DecisionRecord | Recommend REJECT/REVISE/PARK/PAPER_CANDIDATE | Authorize Live-Go or automatic promotion |
| Human Gate / LR SSOT | Sole live/echtgeld authority | Be inferred from PAPER_CANDIDATE |

Hard invariants for pipeline v1:

- `hermes_live_authority: false`
- `research_apps_validation_authority: false`
- `automatic_strategy_promotion: false`
- `real_money_go: false`
- `productive_db_writes: false`
- `plugin_installation: false` (this slice)

## Status model overview

| Stage | Meaning | Gate artifact |
|---|---|---|
| `RESEARCH_REQUESTED` | Briefing intent captured | `cdb.research_brief.v1` |
| `CANDIDATE_DRAFTED` | Structured candidate exists | `cdb.strategy_candidate.v1` |
| `READY_FOR_VALIDATION` | Completeness gate passed | Candidate completeness rules |
| `VALIDATION_RUNNING` | Manifest + runner active | `cdb.validation_manifest.v1` |
| `EVIDENCE_COMPLETE` | Hashes + metrics present | `cdb.candidate_evidence.v1` |
| `DECIDED` | Explicit next actions | `cdb.decision_record.v1` |

Research, Orchestration, Validation, and Decision remain distinct stages. A stage
may only advance when the corresponding machine-readable contract validates.

## Separation of concerns

| Concern | Owner | Contract surface |
|---|---|---|
| Research intent | Research / Compiler | `cdb.research_brief.v1` |
| Falsifiable candidate | Compiler | `cdb.strategy_candidate.v1` |
| Validation plan / gates | Hermes orchestration | `cdb.validation_manifest.v1` |
| Measured outcomes | Runner / ARVP | `cdb.candidate_evidence.v1` |
| Next-action decision | Decision steward (human-gated) | `cdb.decision_record.v1` |

## Lineage (do not replace)

Closed profitability / evidence lineage remains authoritative for its own
surfaces and must not be rewritten by this canon:

- Profitability candidate / evidence: #3034 / #3043 — `profitability_candidate_contract.v1`, `profitability_evidence_packet.v1`
- Evidence assembly / ARVP packet lineage: #4022

Wave-1 contracts are **adjacent orchestration contracts**. They may reference
profitability artifacts by ID/hash; they do not supersede them.

## Non-goals

- No runtime implementation
- No plugin installation
- No cloud provisioning
- No productive DB registry
- No ML/RL model training
- No Live / Paper / Echtgeld GO

## Safety boundaries

- LR-Status: **NO-GO**
- Board `trade-capable` ≠ Live-Go
- `PAPER_CANDIDATE` is a research decision class only
- Missing evidence never yields PASS
- Free-form agent text is never a valid handoff

## Related artifacts

| Artifact | Path |
|---|---|
| Contract overview | [`docs/contracts/CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md`](../contracts/CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md) |
| Profitability candidate (lineage) | [`docs/strategy/CDB_PROFITABILITY_CANDIDATE_CONTRACT_V1.md`](../strategy/CDB_PROFITABILITY_CANDIDATE_CONTRACT_V1.md) |
