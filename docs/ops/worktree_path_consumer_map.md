# Worktree Path Consumer Map

Status: Audit artifact for GitHub Issues #4386 / #4388  
Date: 2026-08-07  
Scope: Inventory only — no migration in this document.

## Canonical target (post-contract)

- Root: `Y:\Worktrees` (`CDB_WORKTREE_ROOT`)
- Pattern: `Y:\Worktrees\<repository>\<worktree-name>`
- Governed entry: `python -m tools.worktrees create ...`
- Main checkout on `D:` remains allowed

## Create / recommend (docs)

| Path | Current pattern | Role |
|---|---|---|
| `docs/onboarding/first_issue_sandbox.md` | was `../cdb-sandbox-<issue>` | onboarding create guidance (updated to Y: CLI) |
| `docs/surrealdb/context-agent-handoff.md` | was `.worktrees/feat-…` | SurrealDB slice gate (updated to Y: CLI) |
| `docs/runbooks/windows_worktree_y_root.md` | Y: contract | new SSOT runbook |

## Cleanup / inventory tooling

| Path | Role |
|---|---|
| `tools/cleanup/worktree_obsolescence_cleanup.ps1` | classify + optional remove (dry-run default) |
| `tools/cleanup/local_dev_workspace_inventory.ps1` | discover worktrees |
| `tools/cleanup/local_dev_hygiene_classify.py` | mark discovered WTs PROTECTED |
| `tools/worktrees/` | new resolver / policy / create / reconcile |

## Skills / guards

| Path | Role |
|---|---|
| `docs/skills/cdb-session-start/SKILL.md` (+ mirrors) | dirty/stale WT STOP |
| `docs/skills/cdb-session-close/SKILL.md` (+ mirrors) | evidence-based remove |
| `docs/skills/cdb-drift-reconcile/SKILL.md` (+ mirrors) | post-merge WT drift classify |

## Ignore / scan excludes

| Path | Pattern |
|---|---|
| `.gitignore` | `.worktrees/`, `.worktrees_backup/` |
| `.github/scripts/backlog_curation.py` | skip `.worktrees` |
| Dockerfile discovery tests | exclude nested `.worktrees` |

## Live practice (operator host, pre-migration)

Observed patterns (not canon create paths):

- `D:\Dev\Workspaces\Repos\cdb-wt-*`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\.worktrees\*`
- Rare `C:\Users\…\Temp\…` prunable worktrees

## Non-goals of this map

- No automatic migration
- No deletion list authorization
- No Linux/CI Y: binding
