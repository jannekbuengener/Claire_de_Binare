# CI Guardrails Drift Report (main)

Timestamp (Europe/Berlin): `2026-03-10T14:09:00+01:00`  
Timestamp (UTC): `2026-03-10T13:09:00Z`  
State: **NO DRIFT**

## Scope

- Secret guardrail workflow: `.github/workflows/gitleaks.yml`
- Format guardrail workflow: `.github/workflows/ci.yml`
- Legacy restore-green guardrails:
  - `.github/workflows/ci.yaml`
  - `.github/workflows/required-checks-audit.yml`
- E2E protected-context guardrails:
  - `.github/workflows/e2e.yml`
  - `.github/workflows/e2e-tests.yml`
  - `.github/workflows/shadow-soak-evidence.yml`
- Mode: read-only contract validation

## Failed Rules

- none

## Findings

| component | rule | status | detail |
|---|---|---|---|
| `.github/workflows/gitleaks.yml` | `pull_request branch scope` | `PASS` | pull_request branches=['main'] |
| `.github/workflows/gitleaks.yml` | `push branch scope` | `PASS` | push branches=['main'] |
| `.github/workflows/gitleaks.yml` | `gitleaks job name` | `PASS` | name='gitleaks (Secrets-Alarm)' |
| `.github/workflows/gitleaks.yml` | `fail-closed job behavior` | `PASS` | continue-on-error=False |
| `.github/workflows/gitleaks.yml` | `full-history checkout` | `PASS` | fetch-depth=0 |
| `.github/workflows/gitleaks.yml` | `gitleaks action step` | `PASS` | gitleaks/gitleaks-action present |
| `.github/workflows/gitleaks.yml` | `repo gitleaks config` | `PASS` | GITLEAKS_CONFIG='gitleaks.toml' |
| `.github/workflows/ci.yml` | `Ruff step present` | `PASS` | step 'Ruff' present |
| `.github/workflows/ci.yml` | `Ruff command` | `PASS` | run snippet='ruff check .' |
| `.github/workflows/ci.yml` | `Black step present` | `PASS` | step 'Black' present |
| `.github/workflows/ci.yml` | `Black command` | `PASS` | run snippet='BASE="${{ github.event.pull_request.base.sha \|\| github.event.before }}"\nHEAD="${{ github.sha }}"\nFILES=$(git diff --name-only "$BASE" "$HEAD" -- \'*.py\' \| xargs)\n[ -z "$FILES" ] && echo "No python changes" && exit 0\nblack --config pyproject.toml --check $FILES\n' |
| `.github/workflows/ci.yaml` | `legacy push branch scope` | `PASS` | push branches=['main'] |
| `.github/workflows/ci.yaml` | `legacy Trivy reporting mode` | `PASS` | exit-code='0' |
| `.github/workflows/ci.yaml` | `legacy Trivy summary step` | `PASS` | step 'Trivy reporting mode summary' present |
| `.github/workflows/ci.yaml` | `legacy Trivy summary message` | `PASS` | run snippet='echo "### Trivy Scan" >> $GITHUB_STEP_SUMMARY\necho "- Non-blocking mode (reporting-only)." >> $GITHUB_STEP_SUMMARY\necho "- Full findings are available in this job log." >> $GITHUB_STEP_SUMMARY\n' |
| `.github/workflows/required-checks-audit.yml` | `sentinel manual-only trigger` | `PASS` | trigger keys=['workflow_dispatch'] |
| `.github/workflows/required-checks-audit.yml` | `sentinel job name` | `PASS` | name='required-checks-audit (Sentinel)' |
| `.github/workflows/required-checks-audit.yml` | `sentinel audit step present` | `PASS` | step 'Audit required check status' present |
| `.github/workflows/required-checks-audit.yml` | `sentinel audit-only mode marker` | `PASS` | audit-only marker and exit-0 summary must stay explicit |
| `.github/workflows/required-checks-audit.yml` | `sentinel canonical required context` | `PASS` | canonical required context must stay listed in required_checks |
| `.github/workflows/e2e.yml` | `preflight step present` | `PASS` | step 'Preflight required secrets (REAL vs STUB)' present |
| `.github/workflows/e2e.yml` | `preflight secret env mapping` | `PASS` | all required E2E secrets mapped in preflight env |
| `.github/workflows/e2e.yml` | `preflight required secret list` | `PASS` | preflight required list contains all expected secrets |
| `.github/workflows/e2e.yml` | `protected STUB hard fail step` | `PASS` | protected STUB hard fail step present |
| `.github/workflows/e2e.yml` | `protected STUB hard fail condition` | `PASS` | if="steps.preflight.outputs.protected_context == 'true' && steps.preflight.outputs.e2e_mode == 'STUB'" |
| `.github/workflows/e2e.yml` | `protected STUB hard fail message` | `PASS` | run snippet='echo "::error::Protected run cannot use STUB MODE. Missing secrets: ${{ steps.preflight.outputs.missing_secrets }}"\nexit 1\n' |
| `.github/workflows/e2e.yml` | `non-protected STUB visibility step` | `PASS` | step 'Mark non-protected STUB mode' present |
| `.github/workflows/e2e.yml` | `non-protected STUB visibility condition` | `PASS` | if="steps.preflight.outputs.protected_context != 'true' && steps.preflight.outputs.e2e_mode == 'STUB'" |
| `.github/workflows/e2e.yml` | `non-protected STUB summary message` | `PASS` | run snippet='echo "::warning::NON-BLOCKING / STUB ONLY. Missing secrets: ${{ steps.preflight.outputs.missing_secrets }}"\n{\n  echo ""\n  echo "### NON-BLOCKING / STUB ONLY"\n  echo "- Context is not protected."\n  echo "- Missing required secrets: ${{ steps.preflight.outputs.missing_secrets }}"\n} >> "$GITHUB_STEP_SUMMARY"\n' |
| `.github/workflows/e2e.yml` | `create secrets step present` | `PASS` | step 'Create CI secrets directory' present |
| `.github/workflows/e2e.yml` | `create secrets env mapping` | `PASS` | all required secret envs mapped for materialization |
| `.github/workflows/e2e.yml` | `forbidden inline secret fallbacks` | `PASS` | no inline secret fallback expressions found |
| `.github/workflows/e2e.yml` | `explicit STUB placeholder materialization` | `PASS` | STUB placeholders for stack secrets remain explicit and mode-bound |
| `.github/workflows/e2e.yml` | `REAL materialization guard` | `PASS` | REAL materialization guard present |
| `.github/workflows/e2e-tests.yml` | `preflight step present` | `PASS` | step 'Preflight required secrets (REAL vs STUB)' present |
| `.github/workflows/e2e-tests.yml` | `preflight secret env mapping` | `PASS` | all required E2E secrets mapped in preflight env |
| `.github/workflows/e2e-tests.yml` | `preflight required secret list` | `PASS` | preflight required list contains all expected secrets |
| `.github/workflows/e2e-tests.yml` | `protected STUB hard fail step` | `PASS` | protected STUB hard fail step present |
| `.github/workflows/e2e-tests.yml` | `protected STUB hard fail condition` | `PASS` | if="steps.preflight.outputs.protected_context == 'true' && steps.preflight.outputs.e2e_mode == 'STUB'" |
| `.github/workflows/e2e-tests.yml` | `protected STUB hard fail message` | `PASS` | run snippet='echo "::error::Protected run cannot use STUB MODE. Missing secrets: ${{ steps.preflight.outputs.missing_secrets }}"\nexit 1\n' |
| `.github/workflows/e2e-tests.yml` | `non-protected STUB visibility step` | `PASS` | step 'Mark non-protected STUB mode' present |
| `.github/workflows/e2e-tests.yml` | `non-protected STUB visibility condition` | `PASS` | if="steps.preflight.outputs.protected_context != 'true' && steps.preflight.outputs.e2e_mode == 'STUB'" |
| `.github/workflows/e2e-tests.yml` | `non-protected STUB summary message` | `PASS` | run snippet='echo "::warning::NON-BLOCKING / STUB ONLY. Missing secrets: ${{ steps.preflight.outputs.missing_secrets }}"\n{\n  echo ""\n  echo "### NON-BLOCKING / STUB ONLY"\n  echo "- Context is not protected."\n  echo "- Missing required secrets: ${{ steps.preflight.outputs.missing_secrets }}"\n} >> "$GITHUB_STEP_SUMMARY"\n' |
| `.github/workflows/e2e-tests.yml` | `create secrets step present` | `PASS` | step 'Create CI Secrets Directory' present |
| `.github/workflows/e2e-tests.yml` | `create secrets env mapping` | `PASS` | all required secret envs mapped for materialization |
| `.github/workflows/e2e-tests.yml` | `forbidden inline secret fallbacks` | `PASS` | no inline secret fallback expressions found |
| `.github/workflows/e2e-tests.yml` | `explicit STUB placeholder materialization` | `PASS` | STUB placeholders for stack secrets remain explicit and mode-bound |
| `.github/workflows/e2e-tests.yml` | `REAL materialization guard` | `PASS` | REAL materialization guard present |
| `.github/workflows/shadow-soak-evidence.yml` | `preflight step present` | `PASS` | step 'Preflight required secrets (REAL vs STUB)' present |
| `.github/workflows/shadow-soak-evidence.yml` | `preflight secret env mapping` | `PASS` | all required E2E secrets mapped in preflight env |
| `.github/workflows/shadow-soak-evidence.yml` | `preflight required secret list` | `PASS` | preflight required list contains all expected secrets |
| `.github/workflows/shadow-soak-evidence.yml` | `protected STUB hard fail step` | `PASS` | protected STUB hard fail step present |
| `.github/workflows/shadow-soak-evidence.yml` | `protected STUB hard fail condition` | `PASS` | if="steps.preflight.outputs.protected_context == 'true' && steps.preflight.outputs.e2e_mode == 'STUB'" |
| `.github/workflows/shadow-soak-evidence.yml` | `protected STUB hard fail message` | `PASS` | run snippet='echo "::error::Protected run cannot use STUB MODE. Missing secrets: ${{ steps.preflight.outputs.missing_secrets }}"\nexit 1\n' |
| `.github/workflows/shadow-soak-evidence.yml` | `non-protected STUB visibility step` | `PASS` | step 'Mark non-protected STUB mode' present |
| `.github/workflows/shadow-soak-evidence.yml` | `non-protected STUB visibility condition` | `PASS` | if="steps.preflight.outputs.protected_context != 'true' && steps.preflight.outputs.e2e_mode == 'STUB'" |
| `.github/workflows/shadow-soak-evidence.yml` | `non-protected STUB summary message` | `PASS` | run snippet='echo "::warning::NON-BLOCKING / STUB ONLY. Missing secrets: ${{ steps.preflight.outputs.missing_secrets }}"\n{\n  echo ""\n  echo "### NON-BLOCKING / STUB ONLY"\n  echo "- Context is not protected."\n  echo "- Missing required secrets: ${{ steps.preflight.outputs.missing_secrets }}"\n} >> "$GITHUB_STEP_SUMMARY"\n' |
| `.github/workflows/shadow-soak-evidence.yml` | `create secrets step present` | `PASS` | step 'Create CI secrets' present |
| `.github/workflows/shadow-soak-evidence.yml` | `create secrets env mapping` | `PASS` | all required secret envs mapped for materialization |
| `.github/workflows/shadow-soak-evidence.yml` | `forbidden inline secret fallbacks` | `PASS` | no inline secret fallback expressions found |
| `.github/workflows/shadow-soak-evidence.yml` | `explicit STUB placeholder materialization` | `PASS` | STUB placeholders for stack secrets remain explicit and mode-bound |
| `.github/workflows/shadow-soak-evidence.yml` | `REAL materialization guard` | `PASS` | REAL materialization guard present |

## What To Do

- If drift is unintended, restore the missing secret/format/restore-green/E2E guard in the workflow file.
- If drift is intended, update this checker in the same reviewed PR so the contract stays explicit.
