# Session Log: #1645 Wave-3 Branch Cleanup (tracking-origin-main)

**Date:** 2026-04-17
**Issue:** #1645 — [HARDENING][GIT] Carefully disentangle local Git/worktree state and reduce branch sprawl
**Scope:** Wave-3 — 10 `tracking-origin-main` branches (upstream misconfigured to `origin/main`)

---

## Assessment Method

These branches have `upstream = origin/main` (misconfiguration). This is a different class from
`tracking-gone`. The upstream misconfiguration can mask the real state. Each branch was evaluated on:
1. Commit content vs main (three-dot diff)
2. Whether specific change is already on main (direct content check)
3. Live PR/issue status on GitHub

---

## Branches Deleted (8/10)

| Branch | Ahead/Behind | Evidence | PR/Issue |
|---|---|---|---|
| `ci/extend-soak-window` | 1/283 | `FULL_SOAK_MINUTES: 30` on main ✅ | Content superseded |
| `docs/fix-stale-1603-ledger` | 1/21 | `Active GitHub focus: keine` on main ✅ | Content superseded |
| `docs/issue-1412-lr-ssot-separation-clean` | 1/170 | P-phase table removed on main ✅ | PR #1414 MERGED, #1412 closed |
| `docs/reconcile-1646-signal-risk-market` | 1/18 | 3-file reconcile | PR #1705 MERGED 2026-04-16, #1646 closed |
| `fix/1376-hitl-solo-maintainer` | 1/171 | HITL_RUNBOOK.md update | PR #1392 MERGED 2026-04-06, #1376 closed |
| `fix/1380-entrypoint-milestone-framing` | 2/171 | ACTIVE_ROADMAP+KNOWLEDGE_HUB | PR #1393 MERGED 2026-04-06, #1380 closed |
| `issue-1577-primary-breakout-config-canon` | 1/73 | All 5 files on main ✅ | PR #1600 MERGED 2026-04-10 |
| `smart-insights-fix` | 1/35 | `permissions: {}` on main ✅ | Content superseded via PR #1694 |

---

## Branches Retained (2/10)

### `ci/pr-noise-kill-clean` — NOT cleanup-ready

- Ahead=2, Behind=536
- Two commits: "Remove Discussion Pipeline (unused)" + "decouple non-critical PR workflows"
- `discussion_pipeline/` already absent from main → that part superseded
- **BUT**: ci.yml diff vs main shows real content differences:
  - Different `actions/checkout` SHA pins vs main's current pins
  - Different `actions/setup-python` SHA pins
  - Removes `pytest -q -k "not test_mcp_time_server_runtime"` → just `pytest -q`
    (main deliberately excludes the MCP runtime test)
  - Removes `--diff-filter=d` from Black check
  - Removes header comments
- These ci.yml changes are NOT on main and include potentially harmful content (removing MCP test exclusion)
- **Decision**: fail-closed — retain; needs explicit review before any deletion

### `issue-1564-canon-drift-cleanup` — NOT cleanup-ready

- Ahead=1, Behind=72
- Fixes `post_merge_followup_scanner.py`: renames `"BLACK terminology"` → `"Risk Service legacy terminology"`,
  splits regex strings to avoid self-triggering false positives
- **Content NOT on main**: `post_merge_followup_scanner.py` still has `("BLACK terminology", ...)` on main
- Issue #1564 closed as `COMPLETED` 2026-04-10 — but no PR was merged
- Ambiguous: was deliberately not merged (issue closed without fix), or oversight?
- **Decision**: fail-closed — retain; verify intent before deletion

---

## Verification

- `git branch | Measure-Object`: 229 → **221**
- All 8 deleted branches confirmed absent
- `ci/pr-noise-kill-clean` and `issue-1564-canon-drift-cleanup` both still present ✅

## Root Cause

`tracking-origin-main` branches have upstream misconfigured to `origin/main` instead of their own remote
branch. This is often caused by: (a) running `git checkout -b <branch>` from a `main`-tracking state
without setting the upstream explicitly, or (b) using `--track origin/main` accidentally.
Most of these branches were source branches of squash-merged PRs — the squash-merge on GitHub
auto-deleted the remote, and the local branch was left with `origin/main` as upstream because that
was configured at branch creation time.

## Issue Comment

https://github.com/jannekbuengener/Claire_de_Binare/issues/1645 (to be posted)
