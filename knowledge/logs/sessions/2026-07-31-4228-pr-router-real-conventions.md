# Session 2026-07-31 — Issue #4228 PR-Router Real Conventions

## Goal

Align `cdb-pr-router` with live CDB title/label conventions so real issues
resolve to a lane and safe route (`DONE_SLICE_ADDED_TO_BATCH_PR`).

## Brain Evidence

- `brain_source`: repo-only
- `brain_status`: not-used
- `context_tool_status`: absent (no Surreal/context MCP in this cloud run)
- `repo_fallback_reason`: unavailable
- Live GitHub + repo files used as authority

## Router

- Pre-fix: `CREATE_DEDICATED_PR` with deleted head
  `governance/pr-steward-batch-routing`
- Post-fix: `CREATE_DEDICATED_PR` → `dedicated/docs-governance-issue-4228`
- Work branch (cloud + anti-repush): `cloud-cursor/pr-router-real-conventions-5132`

## Delivered

- Policy title/label surface aligned to real prefixes and `scope:*`/`type:*`
- Token-based leftmost lane matcher + plural equivalence
- Missing metadata → `CREATE_NEW_BATCH_PR` + `repair_hints` (no unsafe reuse)
- Deleted branch override removed
- Contract tests for real issue matrix
- Runbook §4.1 + skill mirrors

## Validation

- `python -m tools.pr_routing validate-policy` PASS
- `pytest` PR-routing suites: 71 passed
- Live re-route #4204/#4174/#4226 → lane resolved + CREATE_NEW_BATCH_PR
- ruff/black/diff-check/secret-scan PASS on changed Python

## Boundaries

LR NO-GO; no merge; no issue close; no runtime/DB/MCP mutation.
