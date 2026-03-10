# Required Check Contexts Drift Report (main)

Timestamp (Europe/Berlin): `2026-02-19T20:47:51+01:00`  
Timestamp (UTC): `2026-02-19T19:47:51Z`  
State: **NO DRIFT**

## Hashes (SHA256)

- Baseline SHA256: `fc0113f49cbfbd3a13c820c8a924a9761c777998ffc1f75e14a46520a94a6df0`
- Current-derived SHA256: `7f7cd6f25a8daaeaf4aa5295dc41306ec366152565ce221a534dff8a61340a1d`

## Inputs

- Baseline file: `reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json`
- Workflows source: `.github/workflows/**` (read-only parse)

## Required Contexts (Baseline)

- `ci (Unit/Integration + Lint gesammelt)`

## Missing Required Contexts

- none

## Extra Derivable Contexts (Informational)

- `Build Summary`
- `Check Core Duplicates`
- `Check Delivery Gate`
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
- `Linting (Ruff)`
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
- `ai/review`
- `auto-label`
- `build`
- `bulk-label`
- `claude`
- `claude-review`
- `copilot-setup-steps`
- `e2e-paper-trading`
- `enforce-pr-template`
- `gitleaks (Secrets-Alarm)`
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
- `required-checks-audit (Sentinel)`
- `review`
- `shadow-soak-evidence`
- `smart-insights`
- `stale`
- `triage`
- `trivy (kritische CVEs/Supply-Chain)`
- `validate-branch-name`
- `validate-feature-workflow`
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

## Parse Errors

- none

## What To Do

- Required contexts are currently derivable from workflow job names. Keep job-name stability for required contexts.
