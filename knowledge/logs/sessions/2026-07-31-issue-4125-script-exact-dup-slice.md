# Session 2026-07-31 — Issue #4125 exact script duplicate consolidation slice

## Gate
- Bootloader / Read Order: repo-fallback (`context_tool_status=absent`)
- Git: `origin/main` @ `53b8741a`
- Issue #4125: OPEN
- PR-Router: `CREATE_NEW_BATCH_PR` (lane `ci-tooling`, lock UNLOCKED)
- Branch (cloud agent policy): `cloud-cursor/scripts-exact-dup-consolidate-4125-0f03`
  (router suggested `batch/ci-tooling-issue-4125`)
- LR: NO-GO; no script execution against real systems

## Delivered
- Removed exact twins under `infrastructure/scripts/` for owner-kept helpers
- Quarantined `smart_startup.py` to `infrastructure/scripts/legacy/` (fail-closed main)
- Removed tracked `.timetrack.json` twins (runtime state)
- Extended `scripts/check_core_duplicates.py` Rule 3 (git-tracked identical clones)
- README owner/legacy notes; unit tests for script-surface guard

## Deferred (later slice)
- manage_secrets.ps1, activate_live_data.ps1, setup_testnet.ps1, security_audit.sh,
  stack_up.ps1, stack_verify.ps1

## Validation
- pytest tests/unit/scripts/test_check_core_duplicates.py — PASS
- python scripts/check_core_duplicates.py — PASS
- python -m tools.validate_root_layout — PASS
- python -m tools.validate_readme_links — PASS
- ruff/black on changed Python — PASS
- git diff --check — PASS
- gitleaks protect --staged — (run at commit)

## Status
`DONE_SLICE_ADDED_TO_BATCH_PR` (target after PR handoff; issue stays open)
