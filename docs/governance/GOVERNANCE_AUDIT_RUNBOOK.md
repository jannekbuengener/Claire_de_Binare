# Governance Audit Runbook (Manual-Only)

## A) Purpose / Scope

- Manual-only governance audit; no auto-apply; no PR noise; read-only checks.
- Trigger model: `workflow_dispatch` only (no `push`, no `pull_request`, no `schedule`).
- This runbook is operational guidance only. It does not change workflows, scripts, or repository settings.

## B) How To Run (UI)

1. Open GitHub repository `jannekbuengener/Claire_de_Binare`.
2. Go to `Actions`.
3. Select workflow `Governance Audit`.
4. Click `Run workflow` and execute on the intended ref/branch.

Expected output:
- Step Summary shows status for both checks.
- Artifact `governance-audit-reports` is uploaded and contains generated baseline/report files.

## C) What Gets Checked (High Level)

- Branch Protection Drift Guard:
  - Script: `scripts/governance/check_branch_protection_drift.py`
  - Baseline: `docs/evidence/reports/BRANCH_PROTECTION_BASELINE_main.json`
  - Outputs: `artifacts/reports/governance/BRANCH_PROTECTION_*main.*`
- Required-Check Context Drift Guard:
  - Script: `scripts/governance/check_required_check_contexts.py`
  - Baseline: `docs/evidence/reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json`
  - Outputs: `artifacts/reports/governance/REQUIRED_CHECK_CONTEXTS_*main.*`

## D) Interpreting Results (Deterministic)

- `OK`:
  - Both checks report `OK`.
  - Workflow concludes `success`.
- `DRIFT`:
  - At least one guard reports drift (exit code `2`).
  - Workflow concludes `failure`.
  - Reports include missing/drift fields and diff details.

Branch protection mode note:
- Without optional admin token: `BASELINE FALLBACK (no admin token)` is expected and safe.
- With optional admin token: `LIVE (admin token)` is expected for branch-protection API read.

## E) What To Do On DRIFT (No Auto-Apply)

- Required context missing:
  - Do not rename required `job.name`.
  - Revert rename or update branch protection manually as maintainer action.
- Branch protection drift:
  - Use generated apply payload/commands as manual maintainer action only.
  - Never apply via CI workflow automation.
  - `main` must keep `allow_force_pushes=false`; Issue #4196 records the
    decision that force pushes are not an intentional operating mode.
  - Before applying this setting, derive a complete update payload from the
    current live protection response. Change only `allow_force_pushes` to
    `false`; preserve every other field.
  - Read the complete live protection again after apply and compare it with the
    pre-apply response. Any additional changed field is a failed apply and
    requires immediate investigation before delivery continues.
- Always capture evidence:
  - Actions run URL.
  - Artifact filename(s) and hash (for audit traceability).
  - Maintainer identity/time for any manual apply action.

## F) Optional Secret: `GOVERNANCE_AUDIT_ADMIN_TOKEN` (Document Only)

What it does:
- Enables LIVE read of the branch-protection endpoint during manual governance audit runs.

What it must be:
- Fine-grained PAT (or equivalent) with minimum required read access for repository administration/branch protection endpoint reads.
- Stored as repository secret named exactly `GOVERNANCE_AUDIT_ADMIN_TOKEN`.

What it must not do:
- Must never be printed or logged.
- Must never be used for write/apply operations in this workflow.
- Must not enable auto-apply behavior.

Rotation:
- Rotate on schedule and on staff/access changes.
- Update secret value only; keep secret name unchanged.

Explicit behavior without secret:
- If secret is absent, behavior remains unchanged and still safe (baseline fallback path).

## G) Guardrails

- No `pull_request_target` workaround.
- No workflow/job renames for required contexts.
- No Docker / Trading / Infrastructure scope.
- Manual-only governance audit, read-only checks, no settings apply.
