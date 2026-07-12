# Repository Hygiene Audit — Issue #4006

Status: execution evidence (2026-07-13)  
Issue: [#4006](https://github.com/jannekbuengener/Claire_de_Binare/issues/4006)  
LR: NO-GO (unchanged)

## Summary

Controlled, evidence-based cleanup of obsolete local worktrees, branches, remote
tracking refs, and duplicate stashes. All artefacts were classified before
deletion. Active delivery surfaces and protected runtime branches were preserved.

## Inventory (before → after)

| Metric | Before | After |
|--------|--------|-------|
| Worktrees | 10 | 1 (main only) |
| Local branches | 145 | 5 |
| `[gone]` upstream (local) | 119 | 1 |
| Stashes | 22 | 19 |
| `origin/*` remote-tracking refs | 48 | 38 |
| `origin/main` | `f13419a` | `5e4f889` |

## Worktrees removed (9)

All had merged PRs and no tracked changes. Untracked `.tmp_*` drafts were
classified `GENERATED_REDUNDANT`; one session log was archived locally under
`.local/repository_hygiene_4006/` (gitignored).

| ID | Branch | PR | Result |
|----|--------|-----|--------|
| WT-4005 | `docs/4005-community-health-reconcile` | #4024 | removed |
| WT-3912-T | `fix/arvp-3912-zero-event-telemetry` | #3956 | removed |
| WT-4004 | `ops/binance-reloc-4004-e-to-d` | #4007 | removed |
| WT-3995 | `main` (stale checkout) | #4018 | unregistered + dir removed |
| WT-3994 | `docs/3994-readme-navigation-reconcile` | #4011 | removed |
| WT-3912-C | `docs/arvp-3912-closeout-reconcile` | #3958 | removed |
| WT-DIAG | `docs/arvp-diag-telemetry-verification-preflight` | #3966 | removed |
| WT-P1 | `feat/arvp-p1-campaign-attribution-block-evidence` | #3961 | removed |
| WT-P15 | `feat/arvp-p15-campaign-id-compose-contract` | #3964 | removed |

## Local branches — final classification (5 remaining)

| Branch | Class | Reason |
|--------|-------|--------|
| `docs/4017-session-close` | KEEP_ACTIVE | Checked out in main worktree; PR #4027 merged; `[gone]` upstream — operator may switch to `main` |
| `main` | KEEP_PROTECTED | Synced to `origin/main` (`5e4f889`) |
| `docs/3467-no-trade-taxonomy` | KEEP_PROTECTED | Live remote; explicit plan hold |
| `runtime/3893-donchian-natural-paper-24h` | KEEP_PROTECTED | Live remote; runtime evidence hold |
| `opencode/pr-3265-fix` | KEEP_HISTORICAL | No merged PR; 2 unique commits; local-only |

~140 local branches deleted across two passes using `git cherry`, merged-PR
lookup (`gh pr list --head`), and squash-safe `-d`/`-D` with ledger evidence.

## Remote branches

| Class | Count |
|-------|-------|
| DELETE_COMPLETED (pushed delete) | 10 |
| KEEP_PROTECTED | 4 (`main`, grafana dependabot, `runtime/3893…`, `docs/3467…`) |
| HOLD_UNCLEAR (stale, no merged PR proof) | 24 |

Deleted remotes (merged-PR evidence): `chore/2799-session-log`,
`context/indexer-cli-contract-1989`, `epic-code`, `feat/2605-readonly-context-mcp-slice-4`,
`feat/arvp-1843-runner`, `feat/cdb-market-move-to-blue-1202`,
`feat/context-doc-chunking-1988`, `feat/market-prometheus-metrics-1148`,
`fix/1712-empty-gh-models-guard`, `real-task-proof-2821` (policy branch).

## Stashes

| Action | SHAs (prefix) | Reason |
|--------|---------------|--------|
| DROP | `675cef51`, `c9197e87` | Empty stash structure |
| DROP | `529da387` | Duplicate of merged PR #3981 work |
| KEEP | `03b091bf` (+ 18 others) | Unresolved or historical WIP |

## Protection preserved

- Main worktree not used for evidence commit
- Untracked `knowledge/logs/sessions/2026-07-13-4016-candidate-evidence.md` untouched
- Open Dependabot PR #3755 branch retained
- No `git clean`, `--force` worktree remove, `gc --prune`, or reflog expire

## Validation

```text
git worktree list --porcelain  → 1 worktree
git branch                     → 5 branches, all classified
git stash list                 → 19 entries
git remote prune --dry-run     → empty
git fsck --full                → 538 pre-existing "Could not read" missing objects;
                                 no broken refs on active branches; not introduced by this cleanup
```

## Safety boundaries

- No runtime/trading/DB/MCP mutations
- No credential values in this document
- Local backup ledger: `.local/repository_hygiene_4006/` (gitignored)

## Remaining HOLD (documented, not deleted)

- 24 stale `origin/*` branches without merged-PR proof
- 19 stashes (conservative keep)
- `opencode/pr-3265-fix` local branch
- Main WT stale checkout on `docs/4017-session-close` until operator switches

## Non-goals

- Repairing pre-existing missing git objects (`git fsck` read errors)
- Bulk deletion of undocumented stale remotes
- Changing main-worktree active branch during cleanup
