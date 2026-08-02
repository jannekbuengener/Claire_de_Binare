# Session — Hermes Hetzner #4289 / PR #4290

Date: 2026-08-02
Branch: `cloud-cursor/hermes-hetzner-bootstrap-49bf`
Start head: `00db85d22e05075da2f07ccca4246fd51c7f860f`
Final head: `aee96e1bc2b04e214d795b7d12ab6c7c19ced562`
Status: `HOLD_SCOPE_BLOCKER`
LR: NO-GO

## Brain Evidence

brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none

## Delivered

- CI lint fix (Black) + git-mode executable contract
- Runbook + evidence: Object Storage ≠ HCLOUD
- Credential/SSH preflight redacted; live provision blocked

## Validation

- pytest hermes_ops: 28 passed
- ruff / secret-scan / pin-check / validate-profiles: PASS

## Boundaries

- No merge, no cdb-local-ci, no secrets in outputs
- No Agent Control Plane / #4286 touch
