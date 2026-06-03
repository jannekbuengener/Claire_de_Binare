# Session: Disable required_conversation_resolution on main (#2837)

**Date:** 2026-06-03  
**Issue:** [#2837](https://github.com/jannekbuengener/Claire_de_Binare/issues/2837)  
**Branch:** `governance/disable-required-conversation-resolution`  
**LR:** NO-GO (unchanged)

## Objective

Disable GitHub branch protection `required_conversation_resolution` on `main` and document that inline review threads are review signals, not merge blockers, while `ci` + `policy-gate` remain required.

## Before (GitHub API)

```json
{
  "required_conversation_resolution": {"enabled": true},
  "required_status_checks": ["ci (Unit/Integration + Lint gesammelt)", "policy-gate"],
  "required_approving_review_count": 0,
  "require_code_owner_reviews": false
}
```

## Action

```bash
gh api --method PUT repos/jannekbuengener/Claire_de_Binare/branches/main/protection \
  --input .tmp_bp_payload.json
```

Payload preserved all settings except `required_conversation_resolution: false`.

## After (GitHub API)

```json
{
  "required_conversation_resolution": {"enabled": false},
  "required_status_checks": ["ci (Unit/Integration + Lint gesammelt)", "policy-gate"],
  "required_approving_review_count": 0,
  "require_code_owner_reviews": false,
  "enforce_admins": {"enabled": true},
  "required_linear_history": {"enabled": true}
}
```

## Delivered (repo)

- `docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md` — § 1c branch protection table
- `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md` — merge blocker clarification
- `CURRENT_STATUS.md` — ledger entry

## Boundaries

- No code/runtime/DB/MCP changes
- Required status checks unchanged
- No LR/live/echtgeld scope

## Operator note

Blocking or security-relevant inline review feedback should still be handled before merge by discipline; only the GitHub enforcement gate was removed.
