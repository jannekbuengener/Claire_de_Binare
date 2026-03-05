# Runbook: CI Hygiene Drift Checks

## Purpose

Detect governance drift early without changing repository settings.

- Read-only only: detect, report, and review.
- No auto-apply to branch protection or required check contracts.
- Outputs are deterministic reports under `reports/`.

## What Is Checked

1. Branch protection drift on `main` against versioned baseline.
2. Required check contexts drift on `main` against versioned baseline.

Sources:

- `scripts/governance/check_branch_protection_drift.py`
- `scripts/governance/check_required_check_contexts.py`
- `reports/BRANCH_PROTECTION_BASELINE_main.json`
- `reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json`

## One-Command Execution

Preferred command:

```bash
python scripts/governance/run_ci_drift_checks.py --repo jannekbuengener/Claire_de_Binare --branch main
```

Offline/fallback mode (no live branch-protection API read):

```bash
python scripts/governance/run_ci_drift_checks.py --repo jannekbuengener/Claire_de_Binare --branch main --branch-protection-current-json reports/BRANCH_PROTECTION_BASELINE_main.json
```

Wrapper exit codes:

- `0`: no drift
- `2`: drift detected
- `1`: execution error

## Direct Script Execution

Branch protection drift:

```bash
python scripts/governance/check_branch_protection_drift.py --repo jannekbuengener/Claire_de_Binare --branch main
```

Required contexts drift:

```bash
python scripts/governance/check_required_check_contexts.py --baseline reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json --workflows-dir .github/workflows
```

## Report Outputs

- `reports/BRANCH_PROTECTION_DRIFT_REPORT_main.md`
- `reports/BRANCH_PROTECTION_APPLY_PAYLOAD_main.json`
- `reports/REQUIRED_CHECK_CONTEXTS_DRIFT_REPORT_main.md`

Hashes and normalized diffs are part of the reports for audit traceability.

## Interpretation

- `NO DRIFT`: baseline and current state are aligned.
- `DRIFT DETECTED`: contract mismatch exists and must be reviewed.
- `ERROR`: checker could not complete (auth, input, or runtime issue).

Required contexts drift meaning:

- A required context from baseline is no longer derivable from workflow job names.
- Typical cause: renamed `job.name` for a required check.

Branch protection drift meaning:

- At least one normalized branch-protection field differs from baseline.
- Use generated payload only as manual review input.

## Response on Drift (Manual Only)

1. Open both drift reports and identify exact changed fields/contexts.
2. Confirm if drift is intended and approved by maintainers.
3. If intended, update baseline through a reviewed PR.
4. If unintended, revert the source change.
5. For branch protection apply actions, use maintainer-run UI or `gh api` manually.

Do not run auto-apply from CI.

## GitHub Actions Path

- Workflow: `.github/workflows/governance-audit.yml`
- Trigger: `workflow_dispatch`
- Behavior: read-only audit run with artifacts; no settings mutation.

## Guardrails

- Do not change required contexts contract implicitly.
- Do not enable `pull_request_target` for governance drift checks.
- Keep automation read-only and deterministic.
