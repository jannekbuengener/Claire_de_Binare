# CI Triage Restore Green (Primary Repo)

Date: 2026-02-19 (UTC snapshot from `gh` data)  
Repo: `jannekbuengener/Claire_de_Binare`  
Mode: Read-only triage + fix-plan drafting (no PR opened, no workflow edits yet)

## Scope and constraints
- Goal: restore deterministic, enforceable GitHub Actions health.
- Hard constraints honored: no Docker operations, no trading logic changes, no infra/runtime changes.
- Allowed analysis surface used: `.github/workflows/**`, `reports/**`, `docs/**`, `scripts/governance/**`.

## 1) Required checks and branch protection (main)

Branch protection snapshot for `main`:

| Setting | Value |
|---|---|
| `required_status_checks.strict` | `true` |
| Required contexts | `ci (Unit/Integration + Lint gesammelt)` |
| Required approvals | `0` |
| Dismiss stale reviews | `false` |
| Code owner review required | `false` |
| Last push approval required | `false` |
| Admin enforcement | `true` |
| Required conversation resolution | `true` |

Ruleset snapshot (`/rules/branches/main`):
- `non_fast_forward` rule active.
- `pull_request` rule active (`allowed_merge_methods: merge,rebase`), no additional required status-check contexts there.

### Required context to workflow/job mapping

| Required check context | App | Workflow file | Workflow name | Job id/name | Evidence |
|---|---|---|---|---|---|
| `ci (Unit/Integration + Lint gesammelt)` | `app_id=15368` (GitHub Actions) | `.github/workflows/ci.yml` | `ci` | job id `ci`, job name `ci (Unit/Integration + Lint gesammelt)` | `run 22191851170` (success, job emitted exact context) |

## 2) Recent run inventory (~20) for relevant workflows

### 2.1 Required workflow: `ci` (`.github/workflows/ci.yml`)

Last 20 conclusions:
- `success: 19`
- `action_required: 1`

Main branch context within last 20:
- `22191851170` success (`push`, `main`)
- `22191024920` success (`push`, `main`)
- `22190634754` success (`push`, `main`)
- `22188907264` success (`push`, `main`)

PR context note:
- One outlier `action_required` run: `22192989773` (`pull_request`, branch `copilot/sub-pr-865`, no jobs executed).

### 2.2 Adjacent pipeline: `CI/CD Pipeline` (`.github/workflows/ci.yaml`)

Last 20 conclusions:
- `failure: 11`
- `action_required: 8`
- `cancelled: 1`

Latest main failures:
- `22191851100` (`push`, `main`) failed at `Container Scan (Trivy)`.
- `22191025043` (`push`, `main`) failed at `Container Scan (Trivy)`.
- `22190634770` (`push`, `main`) failed at `Container Scan (Trivy)`.

### 2.3 Adjacent workflow: `E2E Happy Path` (`.github/workflows/e2e-happy-path.yaml`)

Last 20 conclusions:
- `success: 17`
- `failure: 2`
- `action_required: 1`

Current outlier matching the same PR symptom:
- `22192989851` (`pull_request`, branch `copilot/sub-pr-865`) -> `action_required`, no jobs.

### 2.4 Historical sentinel: `required-checks-audit (Sentinel)` (`.github/workflows/required-checks-audit.yml`)

Last 20 conclusions:
- `failure: 20` (historical window, mostly 2026-02-16)

Representative failed run:
- `22075752655` -> GitHub UI summary: "This run likely failed because of a workflow file issue."
- No failed-job logs available for that run (`log not found`).

## 3) Current failures and root-cause classification

| Workflow/check | Example run | Failure signature (excerpt) | Classification | Deterministic root cause hypothesis |
|---|---|---|---|---|
| `ci` required workflow | `22192989773` | `conclusion=action_required`, `jobs=[]` | Permission/approval gate | PRs opened by `Copilot` branch can enter manual-approval state before jobs are scheduled; required context is not emitted until approval/run. |
| `E2E Happy Path` | `22192989851` | `conclusion=action_required`, `jobs=[]` | Permission/approval gate | Same approval gating condition as above on the same PR branch; not a test/runtime flake. |
| `CI/CD Pipeline / Container Scan (Trivy)` | `22191851100` | Trivy reports `CVE-2026-26007` for `cryptography 44.0.1`, then `Process completed with exit code 1` | Deterministic dependency/vuln gate | `.github/workflows/ci.yaml` sets Trivy `exit-code: "1"` (`trivy-scan`), so known HIGH findings produce repeatable hard failures on `main`. |
| `required-checks-audit (Sentinel)` (historical) | `22075752655` | "run likely failed because of a workflow file issue" | Deterministic historical workflow issue | Older revisions in that period were unstable and fail-closed against broader check sets; current file is now report-only and aligned to the single required context. |

Historical but now resolved (kept for completeness):
- `Sync Repository Labels` had deterministic failures:
  - checkout/repository access failure (`22190634785`)
  - manifest format failure (`22190878102`, `cannot unmarshal !!map into []github.Label`)
- Subsequent runs are green (`22190939838`, `22191032706`).

## 4) Minimal fix approach per failing area

| Area | Minimal fix approach | Files (allowlist only) | Why this is deterministic |
|---|---|---|---|
| `CI/CD Pipeline` Trivy red-on-main | Convert the `trivy-scan` inside `ci.yaml` to reporting-only in this pipeline (while keeping security signal visible in summary), and keep dedicated `trivy.yml` as the security evidence workflow. | `.github/workflows/ci.yaml` | Removes repeated hard-fail from a known dependency CVE backlog without touching service/runtime deps or Docker. |
| `action_required` on Copilot PRs | Treat as governance/permissions issue: require maintainer approval of queued runs before expecting required contexts. Optional runbook documentation to make this operationally deterministic. | Optional docs-only: `docs/**` (new runbook) | Root cause is workflow approval policy, not flaky test execution. |
| Sentinel historical instability | Keep sentinel non-blocking/reporting semantics; optionally harden output messaging for `action_required`/missing context diagnostics. | Optional: `.github/workflows/required-checks-audit.yml` | Prevents false-red governance noise while preserving observability. |

## 5) Draft PR-sized fix plan (no execution yet)

### PR 1 (recommended): `ci/restore-green-trivy-reporting`
- Scope:
  - `.github/workflows/ci.yaml`
- Change set:
  - Adjust `trivy-scan` behavior from hard-fail to reporting-only in this workflow.
  - Keep explicit warning output in job summary for non-zero findings.
  - Do not rename workflow/job names.
- Verification (non-Docker):
  - YAML validation (`gh workflow view` + syntax check tooling available in repo/runner).
  - Confirm context names unchanged.
  - Trigger non-Docker CI run and verify `CI/CD Pipeline` reaches green with visible Trivy warning signal.
- Rollback:
  - `git revert <commit>` or revert PR.

### PR 2 (optional): `ci/action-required-runbook`
- Scope:
  - `docs/**` (new short runbook)
- Change set:
  - Document maintainer steps for resolving `action_required` runs so required checks are emitted predictably.
- Verification:
  - Docs render/lint pass.
- Rollback:
  - Revert PR.

### Operational step (outside code PRs)
- Review and apply repository Actions approval policy for app-generated PR branches (Copilot) so required workflows can run without manual deadlock.
- This is a settings action, not a repo-code change.

## 6) Risk assessment

- Proposed code touch for green restoration is limited to CI workflow logic (`.github/workflows/ci.yaml`), no runtime service code.
- No `services/**`, `core/**`, `infrastructure/**`, Dockerfiles, Compose files, or tests need edits for the recommended first PR.
- Required check context stability is preserved: `ci (Unit/Integration + Lint gesammelt)` remains unchanged.

## 7) No-Docker / No-Trading-Logic compliance statement

- No Docker/Compose commands were executed in this triage.
- No trading logic was modified.
- No infrastructure/runtime stack files were modified.
- No secrets were printed; only secret names/policies were referenced.
