# Session 2026-07-31 — #4224 backlog curation non-canon tree exclusion

## Scope

Issue #4224: Exclude nested `.worktrees` and nested git roots from
`backlog_curation` source ranking so historical-only curation stays
`fail_closed` independent of local worktree pollution.

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none
```

## Delivery

- Branch: `batch/ci-tooling-issue-4224`
- Commit: `d70f44b2027db98add0af35273439361a025ba1b`
- PR: #4225 (draft batch)
- Router: `CREATE_NEW_BATCH_PR` → later `ROUTE_TO_EXISTING_BATCH_PR` expected

## Validation

- 34 unit tests PASS (`tests/unit/scripts/test_backlog_curation.py`)
- historical-only PASS on polluted primary and clean detached worktree
- ruff/black/`git diff --check` PASS

## Boundaries

- No merge, no issue close, no Full Fast-CI, no `cdb-local-ci`
- LR NO-GO unchanged
