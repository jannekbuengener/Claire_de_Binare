# Required Check Contexts Drift Report (main)

Timestamp (Europe/Berlin): `2026-03-15T22:16:47+01:00`  
Timestamp (UTC): `2026-03-15T21:16:47Z`  
State: **NO DRIFT**

## Hashes (SHA256)

- Baseline SHA256: `2b4034e1465a850f3e2a21cb3899cb76d23858adead3f2b8ab77db9647295dae`
- Current-derived SHA256: `defd4111d7b2093b9fd0b06cf236bc556e8221b0d6e4fcc4c8683066d95179dc`

## Inputs

- Baseline file: `reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json`
- Workflows source: `.github/workflows/**` (read-only parse)

## Required Contexts (Baseline)

- `ci (Unit/Integration + Lint gesammelt)`
- `policy-gate`

## Missing Required Contexts

- none

## Extra Derivable Contexts (Informational)

- `Build Summary`
- `Check Core Duplicates`
- `Check Delivery Gate`
- `Check Docs For Merge Conflict Markers`
- `Container Scan (Trivy)`
- `Contract Drift Guard`
- `Contract Tests`
- `Core Duplicates Guard`
- `Correlation Event Coverage Guard`
- `Dependency Audit (pip-audit)`
- `Documentation Checks`
- `E2E Happy Path`
- `E2E Smoke Test (market_data → signal)`
- `Format Check (Black)`
- `Full Repository Scan`
- `LR-004: Completion State Validation`
- `LR-021 Replay Smoke (fixture → hashes)`
- `Linting (Ruff)`
- `MCP Runtime Smoke`
- `Python compatibility matrix (informational)`
- `Scan Base Images (Redis, Postgres)`
- `Scan Custom Python Services`
- `Secret Scanning (Gitleaks)`
- `Security Audit (Bandit)`
- `Security Scan Summary`
- `Sync Labels from labels.json`
- `Tests (Python ${{ matrix.python-version }})`
- `Trivy - Base Images`
- `Trivy - Custom Services`
- `Type Checking (mypy)`
- `Validate Message Contracts`
- `add-to-project`
- `ai/review`
- `apply-pr-milestone`
- `assign-single`
- `auto-label`
- `backfill`
- `build`
- `bulk-label`
- `capture-intent`
- `claude`
- `claude-review`
- `copilot-setup-steps`
- `dispatch-control-board-routing`
- `dispatch-milestone-label`
- `e2e-paper-trading`
- `enforce-pr-template`
- `gitleaks (Secrets-Alarm)`
- `governance-audit`
- `guard`
- `housekeeping`
- `invoke`
- `label`
- `labels`
- `milestone-assignment`
- `milestone-autofix`
- `noop`
- `opencode`
- `performance-check`
- `reconcile-project-board`
- `required-checks-audit (Sentinel)`
- `review`
- `route-control-board`
- `shadow-soak-evidence`
- `smart-insights`
- `stale`
- `sync-project-status`
- `sync-project-status-label-map`
- `sync-stage-labels`
- `triage`
- `triage-guard`
- `trivy (kritische CVEs/Supply-Chain)`
- `upsert-control-board`
- `validate-branch-name`
- `validate-feature-workflow`
- `weekly-digest`
- `weekly-digest-failure-alert`
- `❓ Bot Help`
- `💬 PR Comment`
- `📢 Notifications`
- `🔍 Emoji Detection`
- `🚫 Block PR Merge`
- `🛡️ Security & Quality Check`
- `🤖 Emoji Bot Handler`

## Mapping (required context -> workflow file / job id)

| context | status | workflow_file | job_id | job_name | workflow_name |
|---|---|---|---|---|---|
| `ci (Unit/Integration + Lint gesammelt)` | present | `.github/workflows/ci.yml` | `ci` | `ci (Unit/Integration + Lint gesammelt)` | `ci` |
| `policy-gate` | present | `.github/workflows/policy-gate.yml` | `policy-gate` | `policy-gate` | `Policy Gate` |

## Parse Errors

- none

## What To Do

- Required contexts are currently derivable from workflow job names. Keep job-name stability for required contexts.
