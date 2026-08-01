# Session — Hermes Hetzner live ops attempt (#4289 / PR #4290)

Date: 2026-08-01  
Agent: Cursor (Windows local)  
LR: NO-GO  
Status: `HOLD_SCOPE_BLOCKER`

## Brain Evidence

- brain_source: repo-only
- brain_status: not-used
- context_tool_status: available (prior turn LOW / no records)
- context_trust_level: none
- records_found: 0
- repo_fallback_reason: insufficient_evidence

## Delivered (repo)

- Confirmed and fixed mandatory preflight gaps on branch
  `cloud-cursor/hermes-hetzner-bootstrap-49bf`.
- Pinned Hermes `v2026.7.30` / commit `cc4cab2f…` with install.sh sha256.
- Replaced `hermes-serve@` with `hermes-dashboard@` (ports 9119/9120, `--isolated`).
- Added `provision.sh`, backup/restore/update/rollback scripts.
- Token broker: `--token-file` 0600 only; App `4410232` fail-closed for write.
- Closed probe issues #4287 / #4288.

## Validation

- `pytest -q tests/unit/hermes_ops` → 22 passed
- hermes_ops validators + `pin-check --require-pinned` → ok
- `ruff check tools/hermes_ops tests/unit/hermes_ops` → ok

## Live blockers

1. `hcloud` context unauthorized / no HCLOUD token in env or secrets.
2. No compatible GitHub App for Hermes write (cdb-local-ci App is checks-only).
3. Session not elevated → Windows user/workspace creation not executed.

## Non-goals respected

- No merge of #4290, no `cdb-local-ci` publish, issue #4289 left OPEN.
