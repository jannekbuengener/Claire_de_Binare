<!--
Canonical Skill Source: docs/skills/cdb-pr-completeness-review/SKILL.md
Surface: opencode
Sync Status: mirrored-from-canon
Last Verified: 2026-07-30
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-pr-completeness-review
description: 'Read-only aggregator that produces exactly one PR completeness verdict across eight fixed dimensions before acceptance state MERGE_CANDIDATE. Aggregates existing evidence; does not discover implementation or write to GitHub.'
disable-model-invocation: true
---

# CDB PR Completeness Review

## Purpose

Read-only aggregator of the PR-Acceptance Skill Family v1. Produce exactly one
final completeness verdict across eight fixed dimensions. This is the only
fachliche Einstufung before acceptance-state `MERGE_CANDIDATE`.

Policy: `config/governance/pr-acceptance-policy.v1.yaml` (`cdb-pr-acceptance-v1`)
Schema: `docs/contracts/pr_acceptance_skill_family.v1.schema.json`
Evidence marker: `<!-- cdb-pr-acceptance:v1 -->`

## Use this skill when

- a batch or dedicated PR must be promoted toward `MERGE_CANDIDATE`
- wiring, gap, gatekeeper, CI, and test evidence already exist or must be delegated
- acceptance lifecycle is at `COMPLETENESS_REVIEW`

## Do NOT use this skill when

- implementation or GitHub writes are requested
- merge execution is requested (use `cdb-batch-merge-conductor`)
- findings still need leaf discovery without aggregation

## Exactly eight dimensions (fixed order)

1. `Funktionalität`
2. `Wiring / Integration`
3. `Konfiguration`
4. `Persistenz / Zustand`
5. `Runtime / Deployment`
6. `Tests / Validierung`
7. `Dokumentation / Runbooks / Contracts`
8. `Operative Readiness / Observability`

Every row MUST include: `dimension`, `state`, `reason`, and `evidence_ids`.
Allowed `state` values: `PASS`, `FAIL`, `NOT_APPLICABLE`, `UNKNOWN`.

Hard dimension rules:

- `UNKNOWN` prevents `MERGE_CANDIDATE`.
- `NOT_APPLICABLE` requires a concrete non-empty `reason`.
- Head or base drift invalidates prior evidence (`INVALIDATED_BY_DRIFT`).
- Issue closure alone is not evidence.

## Workflow

1. Read live PR and linked issues.
2. Resolve acceptance criteria completely.
3. Inspect batch ledger and slice commits.
4. Capture reviews, head, base, and combined diff.
5. Call `cdb-integration-wiring-audit`.
6. Reference `cdb-contract-evidence-gatekeeper`.
7. Reference `cdb-test-first` and `cdb-shadow-validation`.
8. Reference `cdb-ci-cd-guard` and `cdb-drift-reconcile`.
9. Hand all evidenced findings to `cdb-pr-gap-classifier`.
10. Emit exactly one final verdict.

## Verdict precedence (highest blocking first)

1. missing, stale, or contradictory evidence → matching `BLOCKED_*`
2. scope no longer coherently reviewable → `PR_SPLIT_REQUIRED`
3. at least one `MUST_FIX_IN_CURRENT_PR` → `CURRENT_PR_EXTENSION_REQUIRED`
4. real residuals not yet deduplicated or routed → `FOLLOWUP_SLICES_REQUIRED`
5. all dimensions `PASS` or justified `NOT_APPLICABLE` → `MERGE_CANDIDATE`

Allowed verdicts:

- `MERGE_CANDIDATE`
- `CURRENT_PR_EXTENSION_REQUIRED`
- `PR_SPLIT_REQUIRED`
- `FOLLOWUP_SLICES_REQUIRED`
- `BLOCKED_MISSING_EVIDENCE`
- `BLOCKED_SCOPE_AMBIGUITY`
- `BLOCKED_VALIDATION_GAP`
- `BLOCKED_UNCLEAR_CLOSURE`

## Hard rules

- `UNKNOWN` blocks `MERGE_CANDIDATE`.
- `NOT_APPLICABLE` without reason is invalid and blocks.
- `FOLLOWUP_SLICES_REQUIRED` is not mergeable.
- `MUST_FIX_IN_CURRENT_PR` must not be deferred into a follow-up.
- `PR_SPLIT_REQUIRED` precedes any merge path.
- No GitHub writes.
- No implementation.
- No own routing or CI logic.
- Persist evidence with marker `<!-- cdb-pr-acceptance:v1 -->` only when the
  calling session is authorized to write PR comments; this skill itself remains
  read-only and returns the envelope to the caller.

## Required envelope fields

Producer: `cdb-pr-completeness-review`

Common envelope:

- `schema_version`: `cdb-pr-acceptance-skill-family/v1`
- `policy_id`: `cdb-pr-acceptance-v1`
- `subject.repository`, `subject.pr_number`
- `subject.head_sha` / `subject.base_sha` — 40 lowercase hex
- `observed_at` — RFC3339
- `run_status` — `COMPLETE` | `BLOCKED` | `INVALIDATED_BY_DRIFT`
- `lifecycle`, `decision`, `findings`, `evidence`, `limitations`, `handoff`
- `result.dimensions` (exactly eight rows in fixed order)
- `result.verdict`

## Handoff

On `MERGE_CANDIDATE`, hand the schema-valid bundle to
`cdb-batch-merge-conductor`. Otherwise return the blocking verdict and classified
residuals; do not merge.
