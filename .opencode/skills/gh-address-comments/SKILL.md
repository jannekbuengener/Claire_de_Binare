---
name: gh-address-comments
description: Address GitHub PR review comments in the current repo with `gh`. Use when the user wants comment triage, replies, or code changes for review feedback on the current-branch PR or a specified PR. Verify `gh` authentication first, rebuild context control-first, and do not assume an open PR exists. This skill does not handle generic issue-comment threads unless a separate workflow is added.
---

# GitHub Comment Handler

Run `gh` commands with escalated network access when needed.

## Workflow
1. Rebuild context control-first:
   - inspect GitHub control issue `#1445`
   - inspect the newest weekly comment on `#1445`
   - treat issue `#1492` only as current stage context
   - read `docs/runbooks/CONTROL_REGISTER.md`
   - read `CURRENT_STATUS.md`
   - read `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
2. Verify `gh` authentication with `gh auth status`.
3. Resolve the target PR:
   - prefer the current branch PR when one exists
   - otherwise use the explicit PR number or URL the user provided
   - if no PR is discoverable, stop and ask for it
4. Fetch comments and review threads with `gh` directly:
   - `gh pr view <PR> --json reviewThreads,comments,reviews`
   - `gh api /repos/{owner}/{repo}/pulls/<PR>/comments`
   - optional: use a repo-provided helper script only if it exists locally
5. Summarize actionable comments in numbered form.
6. If the user selected comments to address, implement the changes or draft the replies.

## Rules
- Do not assume there is an open PR for the current branch.
- Do not imply support for generic issue-comment threads; this pack is PR-focused.
- If auth or rate limits fail, ask the user to re-authenticate and retry.
- Keep code changes scoped to the selected comments.
- Do not read `#1492` as LR clearance.
