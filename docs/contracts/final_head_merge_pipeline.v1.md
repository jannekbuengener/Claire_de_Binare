# CDB Final-Head Merge Pipeline v1

Status: Canonical
Issue: `#4411`; merge-enforcement reconciliation: `#4602`
Related: `config/governance/pr-acceptance-policy.v1.yaml`, `docs/BRANCH_PROTECTION.md`, `docs/MERGE_REVIEW_FEEDBACK_GATE.md`, `docs/runbooks/merge_policy_ci_gate.md`.

## Purpose

Define one merge authority after `MERGE_CANDIDATE`, while letting GitHub's live `main-strict` ruleset enforce the same merge boundary used by Sample Brain.

## Stable roles

| Stable role id | Authority | Merge-required? |
|---|---|---|
| `cdb_final_head_pr_approval_gate` | Optional/advisory GitHub `APPROVE` helper | no |
| `cdb_final_head_merge_executor` | Regular merge only | yes |

Exactly one canonical final merge executor exists: `cdb_final_head_merge_executor`.
The repo-only merge path must not require local `cdb_context` or private operator state.

## Canonical flow

| Step | Role | Action | Merge authority |
|---|---|---|---|
| M1 | delivery | Issue slice delivered to routed PR | false |
| M2 | acceptance | Integration Wiring Audit | false |
| M3 | acceptance | Gap Classification | false |
| M4 | acceptance | Completeness -> `MERGE_CANDIDATE` | false |
| M5 | `cdb-batch-merge-conductor` | Freeze, integrate main, bind final head/base, Final Validation, verify hosted Required Checks -> `FINAL_HEAD_READY_FOR_APPROVAL` | false |
| M6 | process gate | Recheck all review feedback on the final head; require `unreviewed=0`, `unresolved_threads=0`, and no blocking review | false |
| M7 | `cdb_final_head_merge_executor` | Re-verify live `main-strict` ruleset, exact-head Required Checks, review-feedback gate, mergeability; regular merge | true |
| M8 | `cdb-session-close` | Verify MERGED, issue close eligibility, safe cleanup | false |

`FINAL_HEAD_READY_FOR_APPROVAL` is retained as a compatibility lifecycle token. It no longer means that a separate GitHub approval-provider mutation is required before merge.

## Hard rules

1. `MERGE_CANDIDATE` alone never authorizes merge.
2. Conductor must not merge or close issues.
3. Optional approval tooling may review/approve, but approval is not required for regular merge when the live ruleset requires zero approving reviews.
4. Merge Agent must not modify code while acting as merge executor.
5. HEAD or relevant Base drift invalidates final-head evidence and requires revalidation.
6. Required contexts are enforced by active GitHub ruleset `main-strict`: `ci (Unit/Integration + Lint gesammelt)` and `policy-gate`, both bound to GitHub Actions integration `15368`.
7. Review feedback is a mandatory process gate; see `docs/MERGE_REVIEW_FEEDBACK_GATE.md`.
8. Same-named Commit Status or Check Run from another integration is insufficient.
9. `--admin` is never a normal merge bypass.
10. Delivery/implementation sessions do not merge by default; merge authority remains explicit.
11. If the live ruleset later requires approving reviews, the merge path must fail closed until that live requirement is satisfied.

## Conductor success handoff

```text
decision: FINAL_HEAD_READY_FOR_APPROVAL
next_role: cdb_final_head_merge_executor
legacy_state_name: true
```

## Optional approval tooling

`cdb.pr_approval_context.v1`, `approval eligibility`, and `approve-body` remain deterministic advisory/reviewer helpers. If an APPROVE review is emitted, it must stay exact-head-bound, but absence of such a review is not a merge blocker while the live ruleset requires zero approving reviews.

## Merge Agent re-verify

Before `gh pr merge <PR> --squash --delete-branch`:

- current head/base match final validation evidence
- active `main-strict` ruleset applies to `refs/heads/main`
- live ruleset review requirement is satisfied (`required_approving_review_count = 0` currently)
- `ci (Unit/Integration + Lint gesammelt)` + `policy-gate` are successful on exact head from integration `15368`
- all review feedback is seen/dispositioned; `unreviewed=0`; `unresolved_threads=0`
- no blocking `CHANGES_REQUESTED` review
- PR is not draft and is mergeable
- no admin/force bypass
