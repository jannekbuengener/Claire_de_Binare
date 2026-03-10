# Runbook: MCP Worktree Hygiene

## Purpose

Keep operator workflows predictable and reduce local MCP/repo drift before PR work.

## Principle

- Default mode is read-only until intent and target branch are clear.
- Validate repository state first, then edit.
- Do not treat local machine state as source of truth; `origin/main` is the baseline.

## Common Drift Pitfalls

- Local branch is behind `main`, but files are inspected as if current.
- Worktree points to an older commit while another worktree was already merged.
- Unrelated local edits leak into a task because work happens in a dirty tree.
- Temporary local artifacts are created in tracked paths.

## Safe Pre-PR Checklist

Run these checks before preparing a PR:

```bash
git status -sb
git fetch origin
git log --oneline --decorate -n 5 origin/main
```

For content sanity checks, run explicit `rg` commands:

```bash
rg -n "workflow_run" .github/workflows
rg -n "workflows:\\s*\\[" .github/workflows
rg -n "required-checks-enforcer|required-checks-audit" docs .github/workflows
```

Interpretation:

- If local `HEAD` is behind `origin/main`, rebase/refresh before changing files.
- If `git status -sb` is not clean and edits are unrelated, switch to a clean worktree.
- If old workflow names still appear, update references in the same change set.

## Worktree Handling

- Prefer one dedicated worktree per issue/PR branch.
- Name worktrees by issue id to avoid accidental overlap.
- Remove stale worktrees after merge.
- Never rely on a local branch pointer as merge evidence; verify with GitHub PR state.

## Local Artifacts

- Local helper scripts and machine-specific outputs belong in `.local/` or outside repo.
- For known local-only script policy, see [local_ops_artifacts.md](./local_ops_artifacts.md).

## Scope Guard

- This runbook is read/validate guidance only.
- It does not introduce write automation, secret handling changes, or workflow behavior changes.
