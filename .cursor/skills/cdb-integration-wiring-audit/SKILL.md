<!--
Canonical Skill Source: docs/skills/cdb-integration-wiring-audit/SKILL.md
Surface: cursor
Sync Status: mirrored-from-canon
Last Verified: 2026-07-30
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-integration-wiring-audit
description: 'Read-only audit that proves whether an implementation is reachable through entry points, registration, configuration, dataflow, persistence, runtime, failure paths, observability, documentation, and legacy/bypass surfaces. Use for PR-acceptance wiring evidence. Do not use for implementation, routing, CI decisions, or issue creation.'
disable-model-invocation: true
---

# CDB Integration Wiring Audit

## Purpose

Read-only leaf skill of the PR-Acceptance Skill Family v1. Prove whether a
claimed implementation is actually wired and reachable across ten axes.

Policy: `config/governance/pr-acceptance-policy.v1.yaml` (`cdb-pr-acceptance-v1`)  
Schema: `docs/contracts/pr_acceptance_skill_family.v1.schema.json`  
Evidence marker: `<!-- cdb-pr-acceptance:v1 -->`

## Use this skill when

- a PR claims a feature, skill, contract, or path is integrated
- Completeness Review needs wiring evidence
- UNKNOWN or unreachable integration must be distinguished from follow-up hardening

## Do NOT use this skill when

- the task is implementation, refactoring, or CI repair
- a second PR-routing engine is requested
- GitHub issues must be created
- a Completeness or Conductor orchestration decision is needed (Batch 2 skills)

## Ten wiring axes

Exactly these ten dimensions, in order:

1. Entry Point
2. Registration / Discovery
3. Configuration
4. Dataflow
5. Persistence
6. Runtime
7. Failure Path
8. Observability
9. Documentation
10. Legacy / Bypass Risk

## Row contract

Every axis row MUST include:

- `dimension`
- `applicability` (`REQUIRED` | `OPTIONAL` | `NOT_APPLICABLE`)
- `state` (`PASS` | `FAIL` | `NOT_APPLICABLE` | `UNKNOWN`)
- `evidence_ids`
- `gap_ids`
- `affected_claim`
- `current_pr_fix_required`
- `reason`

Hard rules:

- `NOT_APPLICABLE` requires a non-empty `reason`.
- `UNKNOWN` on a required surface blocks `MERGE_CANDIDATE`.
- Head/base SHA drift invalidates evidence (`INVALIDATED_BY_DRIFT`).

## Verdict precedence

Apply the first matching verdict:

1. `UNREACHABLE_IMPLEMENTATION` — missing real entry, registration, or runtime path
2. `BLOCKED_UNCLEAR_INTEGRATION` — required surface is `UNKNOWN`
3. `WIRING_REQUIRED_IN_CURRENT_PR` — current PR claim needs a fix now
4. `WIRING_FOLLOWUP_ALLOWED` — claim remains true; optional hardening remains
5. `WIRED_AND_REACHABLE` — otherwise

## Boundaries

- No writes.
- No second routing engine.
- No CI decision logic.
- No issue creation.
- No implementation work.

## Required envelope fields

Producer: `cdb-integration-wiring-audit`

Common envelope:

- `schema_version`: `cdb-pr-acceptance-skill-family/v1`
- `policy_id`: `cdb-pr-acceptance-v1`
- `subject.repository`, `subject.pr_number`
- `subject.head_sha` / `subject.base_sha` — 40 lowercase hex
- `observed_at` — RFC3339
- `run_status` — `COMPLETE` | `BLOCKED` | `INVALIDATED_BY_DRIFT`
- `lifecycle`, `decision`, `findings`, `evidence`, `limitations`, `handoff`
- `result.axes` (exactly ten rows) and `result.verdict`

## Handoff

Hand classified wiring gaps to `cdb-pr-gap-classifier`. Do not invent gap
classes here.
