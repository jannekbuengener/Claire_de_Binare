---
name: gh-fix-ci
description: Inspect failing GitHub PR checks in the current repo with `gh`, pull actionable GitHub Actions logs, summarize the failure context, then propose a fix plan and implement after explicit user approval. Use for GitHub Actions-based PR CI failures; for external checks, report the URL and keep them out of scope.
disable-model-invocation: true
---

# GitHub CI Fix

## Overview
Use `gh` to locate failing PR checks, fetch GitHub Actions logs for actionable failures, summarize the failure snippet, then draft a concise plan in the current thread and implement after explicit approval.

## Inputs
- `repo`: path inside the repo, default `.`
- `pr`: PR number or URL, optional
- authenticated `gh`

## Workflow
1. Rebuild context control-first:
   - inspect GitHub control issue `#1445`
   - inspect the newest weekly comment on `#1445`
   - treat issue `#1492` only as current stage context
   - read `docs/runbooks/CONTROL_REGISTER.md`
   - read `CURRENT_STATUS.md`
   - read `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
2. Verify `gh` authentication with `gh auth status`.
3. Resolve the PR:
   - prefer the current branch PR if present
   - otherwise use the PR the user specified
4. Inspect failing GitHub Actions checks:
   - prefer `docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py`
   - fall back to `gh pr checks`, `gh run view`, and log fetches if needed
5. Separate GitHub Actions failures from external checks and mark external systems as out of scope.
6. Summarize the failure with the check name, URL, and short log snippet.
7. Draft a short fix plan in the current thread and wait for explicit user approval before implementation.
8. After explicit approval, implement the fix, run relevant verification, and suggest rechecking PR status.

## Rules
- Do not depend on a separate `plan` skill.
- Do not assume a fixed required-check count; use the current repo and GitHub state.
- If logs are missing or the run is still active, say so explicitly.
- Do not read `#1492` as LR clearance.

## Bundled resource
`docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py` fetches failing PR checks, extracts log snippets, and can emit JSON for summarization.
