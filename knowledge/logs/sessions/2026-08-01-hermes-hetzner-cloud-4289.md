# Session — Hermes Hetzner residual gaps + live gate (#4289 / PR #4290)

Date: 2026-08-01  
Agent: Cursor Cloud  
LR: NO-GO  
Status: `HOLD_SCOPE_BLOCKER`

## Brain Evidence

- brain_source: unavailable
- brain_status: not-used
- context_tool_status: blocked (`cdb_context` MCP discovery error)
- context_trust_level: none
- records_found: 0
- repo_fallback_used: true
- repo_fallback_reason: tool_blocked

## Live bind

- Issue #4289 OPEN
- PR #4290 OPEN draft on `cloud-cursor/hermes-hetzner-bootstrap-49bf`
- Router advisory: `CREATE_NEW_BATCH_PR` / `LANE_MISMATCH` — prompt contract
  overrides; continued on existing #4290 (no new PR)
- Probe #4287/#4288 already CLOSED

## Delivered (repo)

- Hardened `update.sh` / `rollback.sh` to pin URL + required sha256 +
  `/opt/hermes/hermes-agent` path (no `main/scripts/install.sh`)
- `destroy.sh` label guard (`role=hermes`, `issue=4289`, `project=claire-de-binare`)
- `provision.sh` backups fail-closed; removed `--start-after-create` misuse
- Ops scripts executable; README/runbook/YAML intent notes
- Regression tests: `tests/unit/hermes_ops/test_ops_scripts_contract.py`

## Validation

- `pytest -q tests/unit/hermes_ops` → 28 passed
- hermes_ops validators + `pin-check --require-pinned` → ok
- `ruff check tools/hermes_ops tests/unit/hermes_ops` → ok

## Live blockers

1. `HCLOUD_TOKEN` / hcloud auth unset in this Cloud Agent
2. No dedicated Hermes GitHub App credentials (do not expand App 4410232)
3. No Windows host / UAC / Tailscale from this Linux Cloud environment

## Non-goals respected

- No merge of #4290, no `cdb-local-ci` publish, issue #4289 left OPEN
