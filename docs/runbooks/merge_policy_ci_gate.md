# Runbook: Merge Policy — CI Gate Configuration

## Overview

This runbook documents the GitHub settings that enforce the
"No Human Review" policy. CI is the sole merge gate.

See [no_human_review_policy.md](../governance/no_human_review_policy.md)
for the policy rationale.

Merge-method guidance for proof/slice PRs is documented in
[merge_strategy_squash_vs_merge.md](./merge_strategy_squash_vs_merge.md).

## Current State (as of 2026-03-05)

- Repo Actions workflow permissions: `Read and write`
- Canonical PR gate workflow: `.github/workflows/ci.yml` (`name: ci`)
- Canonical merge-relevant check names on PRs: `ci (Unit/Integration + Lint gesammelt)` and `policy-gate`
- Main/dispatch CI pipeline: `.github/workflows/ci.yaml` (`name: CI/CD Pipeline`)
- Sentinel source of truth: `.github/workflows/required-checks-audit.yml` is an on-demand `workflow_dispatch` audit that checks `policy-gate` + `ci (Unit/Integration + Lint gesammelt)` for the ref/SHA you run it on (use the relevant PR head ref for merge-contract audits)
- Governance decision: the PR gate wins, not the larger workflow. `ci.yaml` is not merge-relevant until explicitly consolidated into the PR contract.

## Canonical PR Gate Contract

The exact check-run names below are part of the merge contract on `main`:

| Contract scope | Canonical source | Merge-relevant | Contract name |
|-------|-------|-------|-------|
| Aggregate PR CI gate | `.github/workflows/ci.yml` | Yes | `ci (Unit/Integration + Lint gesammelt)` |
| Policy classification gate | `.github/workflows/policy-gate.yml` | Yes | `policy-gate` |
| Main/dispatch CI pipeline | `.github/workflows/ci.yaml` | No | None |

Implication: Sentinel, branch protection, and PR diagnostics must anchor on the PR-emitted check-run names above. A larger push-only workflow does not become canonical just because it contains more jobs.

## Contract Change Policy (API Stability)

The canonical check-run names above are a merge contract API and must be treated as
stable identifiers.

Any rename/split of canonical checks must ship in one migration change set that also updates:

1. Sentinel mapping in `.github/workflows/required-checks-audit.yml` (#1065)
2. Branch protection required contexts on `main`
3. `workflow_run` dependency map and downstream mappings in `docs/ci/README.md` (#1068 / #1071)

Contract change PRs must include verification evidence that branch protection and
Sentinel still point to the canonical names after the change.

## Ownership and Review Routing

- Route CI contract changes with labels `governance` and `scope:ci`.
- Reference this contract issue in change PRs: #1073.
- Default code owner remains `.github/CODEOWNERS` (`* @jannekbuengener`); governance/ops reviewers should be requested for CI-contract-impacting changes.

## Delta: `ci.yaml` vs. Canonical PR Gate

`ci.yaml` currently contains checks that are not part of the merge contract because the workflow is `push`/`workflow_dispatch` only:

- `Core Duplicates Guard`
- `Type Checking (mypy)` (currently advisory via `continue-on-error`)
- `Contract Tests`
- `Contract Drift Guard`
- `LR-004: Completion State Validation`
- `Correlation Event Coverage Guard`
- `Secret Scanning (Gitleaks)`
- `Container Scan (Trivy)`
- `Security Audit (Bandit)` (currently advisory via `continue-on-error`)
- `Dependency Audit (pip-audit)` (currently advisory via `continue-on-error`)
- `Documentation Checks`
- `Build Summary`

`Linting (Ruff)`, `Format Check (Black)`, and `Tests` also exist in `ci.yaml`, but the canonical PR contract intentionally remains the single aggregate check-run emitted by `.github/workflows/ci.yml`.

## Policy Gate Categories

`policy-gate` classifies pull requests deterministically from labels, title prefixes,
and changed files:

| Category | Label | Title prefix | Allowed files |
|-------|-------|-------|-------|
| `docs-only` | `docs-only` | `[docs-only]` or `docs-only:` | `docs/**` and `*.md` |
| `workflows-only` | `workflows-only` | `[workflows-only]` or `workflows-only:` | `.github/workflows/**` |
| `infra-only` | `infra-only` | `[infra-only]` or `infra-only:` | `infrastructure/**` and `.github/workflows/**` |
| `core/service` | none | none | Any other diff; requires `manual-approval` or `allow-core-change` |

Hard-fails for workflow changes in `.github/workflows/**`:

- Any workflow containing `pull_request_target`
- Any workflow missing an explicit `permissions:` section
- Any workflow containing `write-all`

`manual-approval` and `allow-core-change` are explicit override labels for
`core/service` PRs. They do not bypass the workflow safety checks above.

The gate reevaluates on `opened`, `synchronize`, `reopened`, `labeled`,
`unlabeled`, and `edited` so label removals cannot leave a stale PASS behind.

## Workflow Permissions

Auto-milestone writes on `pull_request` runs require the repo-level GitHub Actions
workflow permission to be `Read and write`. This repo is set to that value.

Clickpath:

```text
Settings -> Actions -> General -> Workflow permissions -> Read and write
```

CLI verification:

```bash
gh api repos/jannekbuengener/Claire_de_Binare/actions/permissions/workflow
```

Expected output:

```json
{"default_workflow_permissions":"write","can_approve_pull_request_reviews":true}
```

## Required GitHub Settings

### Branch Protection (main)

Apply via GitHub UI (Settings > Branches > main) or CLI:

```bash
# Set required status checks (strict: branch must be up to date)
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["ci (Unit/Integration + Lint gesammelt)","policy-gate"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews=null \
  --field restrictions=null \
  --field required_conversation_resolution=true \
  --field allow_force_pushes=false \
  --field allow_deletions=false
```

### Verify Settings

```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection \
  | python -m json.tool
```

Expected output (key fields):

| Field | Expected |
|-------|----------|
| `required_status_checks.strict` | `true` |
| `required_status_checks.contexts` | `["ci (Unit/Integration + Lint gesammelt)", "policy-gate"]` |
| `required_approving_review_count` | `0` |
| `enforce_admins.enabled` | `true` |
| `required_conversation_resolution.enabled` | `true` |
| `allow_force_pushes.enabled` | `false` |
| `allow_deletions.enabled` | `false` |

### Disable Human Reviews (if re-enabled accidentally)

```bash
# Remove required_pull_request_reviews entirely:
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_pull_request_reviews \
  --method DELETE

# Or set to 0 approvals:
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_pull_request_reviews \
  --method PATCH \
  --field required_approving_review_count=0
```

### Enable Auto-merge (optional)

```bash
# Enable auto-merge at repo level (PRs merge when checks pass):
gh api repos/jannekbuengener/Claire_de_Binare \
  --method PATCH \
  --field allow_auto_merge=true
```

Then per PR:

```bash
gh pr merge <number> --auto --squash
```

### Adding Required Checks

When a quarantined test is fixed and added to CI:

1. Add the job to `.github/workflows/ci.yml`
2. Update branch protection to include the new check context:

```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_status_checks \
  --method PATCH \
  --field strict=true \
  --field contexts='["ci (Unit/Integration + Lint gesammelt)", "policy-gate", "<new-check-name>"]'
```

3. Remove the test from the quarantine table in `no_human_review_policy.md`

## References

- #1065 Sentinel Phase A contract behavior
- #1067 Canonical PR gate decision (`ci.yml` as merge contract)
- #1068 workflow_run dependency robustness
- #1071 workflow_run governance follow-up
- #1073 CI Contract — Canonical Check-Run Names

## Rollback: Re-enable Human Reviews

If the policy is reverted:

```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_pull_request_reviews \
  --method PATCH \
  --field required_approving_review_count=1
```

Document the change in [BRANCH_PROTECTION_LOG.md](../governance/BRANCH_PROTECTION_LOG.md).
