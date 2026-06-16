# Onboarding Examples

Status: Orientation
Issue: #3238

These examples show the smallest useful CDB developer workflows. They are
written for docs/onboarding and do not authorize runtime, Docker, trading,
productive DB, memory-write, or LR changes.

Docs/UI sind Orientierung, keine Autoritaet. LR bleibt NO-GO. No Live-Go. No
Echtgeld-Go.

## Available Examples

| Example | Use it when | File |
|---|---|---|
| First issue flow | You need to read one scoped issue, verify live state, set LOCK/START, branch, and make a bounded change | [`first_issue_to_pr_flow.md`](first_issue_to_pr_flow.md) |
| First PR flow | You need to validate, commit, push, open a PR, wait for checks, merge, and comment the issue | [`first_issue_to_pr_flow.md`](first_issue_to_pr_flow.md) |
| Repo Brain first use | You need to use Context Intelligence or Repo Brain as read-only orientation without DB-backed claims | [`repo_brain_first_use.md`](repo_brain_first_use.md) |

## Which Example Should I Use?

Use the first issue-to-PR flow when the task is already approved, bounded, and
issue-driven.

Use the Repo Brain first-use example when the task mentions Context,
SurrealDB, MCP, evidence, memory, or agent onboarding and you must decide
whether verified records exist or whether to fall back to repo-only evidence.

## What Is Deliberately Not Included?

- No real GUI or web app buildout.
- No screenshots or visual asset generation.
- No Docker or runtime startup path.
- No service, trading, risk, execution, strategy, or LR implementation path.
- No productive DB or memory-write path.
- No credential values or environment-specific private material.
- No replacement for governance, bootloader, or GitHub live truth.
