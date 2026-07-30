<!--
Canonical Skill Source: docs/skills/cdb-batch-merge-conductor/SKILL.md
Surface: docs (canonical)
Sync Status: canonical
Last Verified: 2026-07-30
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-batch-merge-conductor
description: 'Orchestration skill that freezes a MERGE_CANDIDATE PR, integrates main, delegates final validation, publishes cdb-local-ci, and performs capability-based regular squash-merge. No separate human merge GO field; never --admin.'
disable-model-invocation: true
---

# CDB Batch Merge Conductor

## Purpose

Orchestration skill of the PR-Acceptance Skill Family v1. Own freeze, main
integration, final head/base capture, delegation of final checks, required-status
verification, regular squash-merge, and handoff to `cdb-session-close`.

Policy: `config/governance/pr-acceptance-policy.v1.yaml` (`cdb-pr-acceptance-v1`)
Schema: `docs/contracts/pr_acceptance_skill_family.v1.schema.json`
Evidence marker: `<!-- cdb-pr-acceptance:v1 -->`

## Ownership

- Reihenfolge
- Freeze
- Main-Integration
- Final-Head- und Base-Erfassung
- Delegation der finalen Prüfungen
- Required-Status-Verifikation
- regulärer Squash-Merge
- Übergabe an `cdb-session-close`

## Does not own

- eigene CI-Implementierung
- eigene Review-Taxonomie
- eigene Routing-Engine
- eigene Gap-Klassifikation
- eigene Evidence-Taxonomie
- eigene Issue-Closeout-Logik

## Authorization contract

- No separate Human-/Merge-GO micro-approval after an authorized Conductor phase.
- No field `human_merge_authorization`.
- No status `BLOCKED_HUMAN_AUTHORITY`.
- Merge remains capability-based: every gate in
  `docs/runbooks/merge_policy_ci_gate.md` must be proven on the exact final head.
- Missing technical capability → `DONE_PR_OPEN_MERGE_HANDOFF`, never `--admin`.

## Phases

1. `FREEZE` — set acceptance lifecycle `FROZEN`; no further slices
2. `MAIN_INTEGRATION` — integrate current `origin/main`; rebind head/base
3. `FINAL_VALIDATION` — delegate Full Fast-CI, policy-gate mirror, `cdb-local-ci`
4. `MERGE` — regular `gh pr merge <PR> --squash --delete-branch` only
5. `HANDOFF_SESSION_CLOSE` — pass only `SLICE_DELIVERED` ledger rows to close

Any conflict resolution, new commit, or semantic change after Completeness
invalidates the old Completeness bundle and forces a fresh
`cdb-pr-completeness-review` before continuing.

## Workflow

1. Read current `MERGE_CANDIDATE` acceptance bundle.
2. Verify live PR, reviews, locks, head, and base.
3. Verify task scope and merge capability.
4. Set acceptance state to `FROZEN`; reject new slices.
5. Integrate current main.
6. Recapture final head and base SHAs.
7. On drift/semantic change: re-run Completeness Review.
8. Re-check combined diff and closure claims.
9. Delegate final validation path to existing skills (`cdb-ci-cd-guard`, etc.).
10. Run Full Fast-CI once on the exact final head.
11. Run local policy-gate mirror.
12. Publish `cdb-local-ci` as Commit Status on exactly that head.
13. Re-check head, base, reviews, mergeability immediately before merge.
14. Execute regular squash-merge only.
15. Verify merge SHA, PR state, and main live.
16. Hand only ledger rows with `SLICE_DELIVERED` to `cdb-session-close`.

## Block codes

- `BLOCKED_SCOPE_OR_REVIEW` → session status `HOLD_SCOPE_OR_REVIEW`
- `BLOCKED_HEAD_BASE_DRIFT` → session status `HOLD_MAIN_OR_HEAD_DRIFT`
- `BLOCKED_LOCAL_VALIDATION`
- `BLOCKED_REQUIRED_STATUS`
- `BLOCKED_AUTH_PUBLISHER`
- `BLOCKED_MERGE_METHOD`
- `BLOCKED_ISSUE_CLOSEOUT`

Missing technical capability maps to `DONE_PR_OPEN_MERGE_HANDOFF`.

## Forbidden

- `--admin`
- Fake-Green
- stale slice evidence as final evidence
- merge retry without a new hypothesis
- closing undelivered issues
- reviving a remote branch after merge
- inventing `human_merge_authorization` or `BLOCKED_HUMAN_AUTHORITY`
- opening a post-merge `CURRENT_STATUS-only` / `ledger-only` Nachlauf-PR
  after squash-merge (Issue `#4218`); ledger/status lines belong
  **vor dem Freeze** in this PR or later in a `docs-governance` batch

## Required envelope fields

Producer: `cdb-batch-merge-conductor`

Common envelope:

- `schema_version`: `cdb-pr-acceptance-skill-family/v1`
- `policy_id`: `cdb-pr-acceptance-v1`
- `subject.repository`, `subject.pr_number`
- `subject.head_sha` / `subject.base_sha` — 40 lowercase hex
- `observed_at` — RFC3339
- `run_status` — `COMPLETE` | `BLOCKED` | `INVALIDATED_BY_DRIFT`
- `lifecycle`, `decision`, `findings`, `evidence`, `limitations`, `handoff`
- `result.phase`
- `result.block_codes`
- `result.merge_executed` (optional boolean)
- `result.closure_eligible_issues` (optional issue numbers)

## Handoff

After live-verified merge, hand `SLICE_DELIVERED` closure-eligible issues to
`cdb-session-close`. Do not close undelivered ledger rows.
