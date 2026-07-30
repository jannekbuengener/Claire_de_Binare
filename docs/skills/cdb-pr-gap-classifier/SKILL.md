<!--
Canonical Skill Source: docs/skills/cdb-pr-gap-classifier/SKILL.md
Surface: docs (canonical)
Sync Status: canonical
Last Verified: 2026-07-30
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-pr-gap-classifier
description: 'Read-only classifier that assigns already discovered, evidenced PR findings to exactly one residual-work class. Use after wiring audit or other leaf evidence. Do not discover new findings or create issues.'
disable-model-invocation: true
---

# CDB PR Gap Classifier

## Purpose

Read-only leaf skill of the PR-Acceptance Skill Family v1. Assign each already
discovered and evidenced PR finding to exactly one residual-work class.

Policy: `config/governance/pr-acceptance-policy.v1.yaml` (`cdb-pr-acceptance-v1`)
Schema: `docs/contracts/pr_acceptance_skill_family.v1.schema.json`
Evidence marker: `<!-- cdb-pr-acceptance:v1 -->`

## Use this skill when

- wiring audit, gatekeeper, CI guard, or review findings already exist
- Completeness Review needs residual-work classification
- a finding must be separated into current-PR fix vs follow-up vs dedicated PR

## Do NOT use this skill when

- findings still need to be discovered
- issues must be created or closed
- implementation or merge orchestration is requested

## Exactly five gap classes

1. `MUST_FIX_IN_CURRENT_PR`
2. `FOLLOWUP_AFTER_MERGE`
3. `SEPARATE_DEDICATED_PR`
4. `PARKED_NOT_ACTIVE`
5. `NOT_A_REAL_GAP`

No other class names are allowed.

## Required output fields

Every gap row MUST include:

- `gap_id`
- `classification` (or null when blocked)
- `classification_status`
- `summary`
- `affected_claim`
- `current_pr_fix_required`
- `separate_issue_required`
- `suggested_issue_target`
- `why_not_now`
- `evidence_ids`
- `dedupe_result`

## Hard rules

- False current claim, safety/contract breach, or incomplete delivery →
  `MUST_FIX_IN_CURRENT_PR`.
- Security, migration, risk/LR, or large independent scope with a still-true
  current claim → `SEPARATE_DEDICATED_PR`.
- Independent hardening → `FOLLOWUP_AFTER_MERGE`.
- Inactive future work → `PARKED_NOT_ACTIVE`.
- Proven false positive or already fully covered observation → `NOT_A_REAL_GAP`.
- Insufficient evidence → `classification_status=BLOCKED_INSUFFICIENT_EVIDENCE`
  and **no** class (`classification=null`).
- Dedupe against an existing issue does **not** change the fachliche class.
- This skill does not discover findings.
- This skill does not create issues.

## Required envelope fields

Producer: `cdb-pr-gap-classifier`

Common envelope:

- `schema_version`: `cdb-pr-acceptance-skill-family/v1`
- `policy_id`: `cdb-pr-acceptance-v1`
- `subject.repository`, `subject.pr_number`
- `subject.head_sha` / `subject.base_sha` — 40 lowercase hex
- `observed_at` — RFC3339
- `run_status` — `COMPLETE` | `BLOCKED` | `INVALIDATED_BY_DRIFT`
- `lifecycle`, `decision`, `findings`, `evidence`, `limitations`, `handoff`
- `result.gaps`

## Handoff

Return classified gaps to Completeness Review (Batch 2). Do not execute merge
or issue-close actions.
