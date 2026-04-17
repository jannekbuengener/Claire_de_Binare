# Session Log: #1645 Wave-2 Branch Cleanup (8 Branches)

**Date:** 2026-04-17
**Issue:** #1645 — [HARDENING][GIT] Carefully disentangle local Git/worktree state and reduce branch sprawl
**Scope:** Wave-2 Micro-Batch — 8 `tracking-gone` Branches, behind 34–46 vs main

---

## Branches Deleted

All 8 branches were individually verified: commit content present on main, upstream PR confirmed MERGED.

| Branch | Commit(s) | PR | Content Verified |
|---|---|---|---|
| `docs/status-ledger-kw16-1689-1690` | `ad56ec0d` | #1689+#1690 MERGED | CURRENT_STATUS.md:65 ✅ |
| `docs/1688-session-skill-routing` | `419d357f` | #1690 MERGED | CLAUDE.md:23-25 ✅ |
| `docs/1667-commands-coupling-doc` | `9032bb97` | #1689 MERGED | GITHUB_WORKFLOW_REGISTER.md:200-212 ✅ |
| `docs/current-status-ledger-2026-04-13` | `823ed87a` | #1686 MERGED | CURRENT_STATUS.md:65 ✅ |
| `1666-actions-workflow-drift-doc` | `727ad946` | #1686 MERGED | CONTROL_REGISTER.md:56 ✅ |
| `1663-session-start-skill` | `b8930256` | #1684 MERGED | `.codex/cdb_skills/cdb-session-start/SKILL.md` ✅ |
| `1664-session-close-skill` | `85f41b9b` | #1685 MERGED | `.codex/cdb_skills/cdb-session-close/SKILL.md` ✅ |
| `codex/1659-rest-slice-20260412` | `79b38199` + `d98b5c9c` | #1660 MERGED | Control-plane docs on main ✅ |

## Verification

- `git branch | Measure-Object`: 237 → **229**
- All 8 branches confirmed absent from `git branch`
- All upstream PRs live-verified MERGED on GitHub
- All commit content confirmed present on main at file/line level

## Root Cause

Squash-merge sprawl pattern: all 8 were source branches of squash-merged PRs. Remote branches auto-deleted by `gh pr merge --squash --delete-branch`; local tracking branches remained as `[gone]` entries.

## Wave Progress

- Wave 1 (2026-04-17): 4/4 branches deleted (`docs/status-mark-*`, `fix/security-*`)
- Wave 2 (2026-04-17): 8/8 branches deleted
- **Total: 12 branches deleted, 241 → 229 local branches**
- Remaining: 228 non-main branches (out of scope for this session)

## Issue Comment

https://github.com/jannekbuengener/Claire_de_Binare/issues/1645#issuecomment-4268547886
