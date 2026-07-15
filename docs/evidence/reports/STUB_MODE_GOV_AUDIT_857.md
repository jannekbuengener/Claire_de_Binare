# STUB Mode Governance Audit (#857)

Scope: CI/workflow guards only. No Docker/Compose file changes and no trading-logic changes.

## Affected Workflows
- `.github/workflows/e2e.yml`
- `.github/workflows/e2e-tests.yml`
- `.github/workflows/e2e-happy-path.yaml`
- `.github/workflows/shadow-soak-evidence.yml`

## REQUIRED_SECRETS (REAL E2E)
- `SMTP_FROM`
- `SMTP_HOST`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `ALERT_EMAIL_TO`
- `MEXC_API_KEY`
- `MEXC_API_SECRET`

## Protected Context Definition
- `push` on `refs/heads/main`
- `workflow_dispatch` on `refs/heads/main`
- `schedule`

## Enforced Behavior
- Early preflight computes:
  - `e2e_mode` = `REAL` or `STUB`
  - `missing_secrets` = comma-separated missing secret names only
- Protected + STUB is fail-closed:
  - workflow exits with `Protected run cannot use STUB MODE. Missing secrets: ...`
- Non-protected STUB remains explicit and visible:
  - summary contains `NON-BLOCKING / STUB ONLY`

## PR/Fork Behavior
- `e2e-happy-path.yaml` now also runs on `pull_request`.
- For fork PRs, real E2E is not attempted; workflow exits cleanly with summary:
  - `NON-BLOCKING / STUB ONLY (fork)`
- For same-repo PRs, REAL runs when all required secrets are present; otherwise STUB is explicitly reported.

## Secret Mapping Fixes
- Added `SMTP_HOST` mapping in CI secret materialization for:
  - `.github/workflows/e2e.yml`
  - `.github/workflows/e2e-tests.yml`
  - `.github/workflows/shadow-soak-evidence.yml`
