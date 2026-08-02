# Session Log — #4151 Request-/Content-Fingerprint trennen

**Date:** 2026-07-31  
**Agent:** cloud-session  

**Issue:** #4151  

**Wave:** parallel-wave-2026-07-31-c  
**Target status:** `DONE_SLICE_ADDED_TO_BATCH_PR`

## Brain Evidence

- `brain_source`: repo-only
- `brain_status`: not-used
- `context_tool_status`: absent
- `repo_fallback_reason`: unavailable
- Context-Brain-/SurrealDB-MCP not in active MCP surface

## Prerequisites

- Issue #4151 OPEN (live `gh issue view`)
- Parameter-Control #4148 CLOSED; PR #4154 merged on main
- PR-Router: `CREATE_NEW_BATCH_PR` → `batch/validation-research-issue-4151`
  - lane `validation-research`, lock `UNLOCKED`, merge_mode `batch`
  - reason: `CREATE_NEW_BATCH_WITH_DEFAULT_METADATA` (missing objective/contract/risk labels)

## Scope delivered

- `core/replay/dataset_identity.py` — request vs content identity helpers
- `DatasetSpec.request_fingerprint()` alias (compat)
- `DatasetResult.request_fingerprint` + `content_fingerprint`
- File-/DB-Provider set both fingerprints on load
- Unit tests: `tests/unit/replay/test_dataset_identity.py` (+ provider assertions)

## Deferred (explicit)

- Full Effective-Config-Snapshot
- DQ-/Rankability-/Window-parity hardening beyond content hash
- Merge / Issue close / `cdb-local-ci` publish

## Safety

- LR NO-GO unchanged
- No productive DB writes, no live/echtgeld, no secrets in hash inputs
