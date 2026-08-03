# Session 2026-08-03 — #4258 Cursor dual-run root-cause debug

## Scope
Plan-GO dual-run root-cause for existing Cursor ERROR runs only.
No third agent/run. No merge. No `cdb-local-ci`. Issue stays OPEN.

## Brain Evidence
- brain_source: repo-only
- brain_status: not-used
- context_tool_status: available
- context_trust_level: none
- repo_fallback_reason: insufficient_evidence

## Live facts
- Issue #4258 OPEN
- PR #4302 MERGED @ e899ed41
- Both ERROR runs still readable via Cursor v1 GETs
- Claimed branches both GitHub 404
- Usage (documented agent-scoped path): run1=1041 tokens, run2=1596 tokens
- Artifacts empty; stream status/result/done; no structured error
- Primary classification: UNKNOWN_OBSERVABILITY_GAP (MEDIUM)
- Router: CREATE_NEW_BATCH_PR → batch/agent-skills-issue-4258

## Delivered
- cursor-support-bundle CLI + module
- recorded fixtures for both ERROR runs
- provider live usage/artifacts on documented paths
- tracked evidence + ready-to-send support draft (not sent)
- regression tests (9 targeted passed)

## Boundaries
LR NO-GO; cursor_http_posts=0; no third run; no merge.
