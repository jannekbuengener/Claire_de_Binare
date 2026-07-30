<!--
Canonical Skill Source: docs/skills/cdb-pr-router/SKILL.md
Surface: claude
Sync Status: mirrored-from-canon
Last Verified: 2026-07-30
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-pr-router
description: Read-only CDB PR inventory, compatibility routing, lock and merge-trigger evaluation before any work surface is created.
---

# CDB PR Router

## Purpose

Route an open Issue to exactly one safe existing PR or recommend a new
Batch-/Dedicated-PR. The skill is read-only and never creates branches,
worktrees, PRs, comments, statuses or merges.

## Mandatory timing

Run this skill before:

- Session-Plan-Finalisierung,
- Branch-Erstellung,
- Worktree-Erstellung,
- PR-Erstellung.

## Preconditions

1. Context Brain Preflight and Brain Evidence.
2. Canonical read order.
3. Fresh `origin/main` and live GitHub inventory.
4. Issue is live and open.
5. Current agent identity is known.

## Command

```powershell
python -m tools.pr_routing route --issue <ISSUE> --agent <AGENT>
```

Supporting validators:

```powershell
python -m tools.pr_routing validate-policy
python -m tools.pr_routing validate-pr-body --body-file <BODY_FILE>
python -m tools.pr_routing evaluate-trigger --snapshot <JSON> --observed-at <UTC>
python -m tools.pr_routing merge-readiness --body-file <BODY_FILE>
```

## Required output

- `issue_number`
- `routing_decision`
- `target_pr`
- `target_branch`
- `batch_key`
- `lane`
- `compatibility_reasons`
- `incompatibility_reasons`
- `lock_state`
- `validation_profile`
- `merge_mode`
- `merge_trigger_state`
- `policy_id`
- `observed_at`
- `evidence_sources`
- `collection_errors`
- `candidate_prs_considered`
- `reason_codes`

## Decisions

- `ROUTE_TO_EXISTING_BATCH_PR`
- `ROUTE_TO_EXISTING_DEDICATED_PR`
- `CREATE_NEW_BATCH_PR`
- `CREATE_DEDICATED_PR`
- `HOLD_PR_LOCK_CONFLICT`
- `HOLD_NO_SAFE_ROUTE`

## Fail-closed rules

- Never choose between multiple compatible PRs.
- Never route paused, parked or blocked work.
- Never infer an unknown lane or validation profile.
- Never accept malformed markers, ledgers or locks.
- Never auto-take over a stale lock.
- Never route new slices to `merge_candidate` or `frozen`.
- An inventory that reaches the configured PR limit is incomplete and HOLD.

## Authority

The output is a recommendation for Session Lead and Human Authority. The router
does not own the PR and cannot authorize a merge. LR remains `NO-GO`.

## References

- Runbook: `docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md`
- Machine Policy: `config/governance/pr-routing-policy.v1.yaml`
