# Required Check Contexts Drift Report (main)

Timestamp (Europe/Berlin): `2026-07-27T22:36:01+02:00`  
Timestamp (UTC): `2026-07-27T20:36:01Z`  
State: **NO DRIFT**

## Hashes (SHA256)

- Baseline SHA256: `cb3d540d7c614797bf17ea0a5af536c484e260649b0279d6788a6963d9057453`
- Current-derived SHA256: `76106943c0d48a1baf6481137d69719dec9ae5d4e1ad23b0216774db54bdde5b`

## Inputs

- Baseline file: `docs/evidence/reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json`
- Workflows source: `.github/workflows/**` (read-only parse)

## Required Contexts (Baseline)

- `cdb-local-ci`

## Commit Status / External Contexts (not workflow jobs)

- `cdb-local-ci`

## Missing Required Contexts

- none

## Extra Derivable Contexts (Informational)

- `Analyze Python`
- `Check Core Duplicates`
- `Check Delivery Gate`
- `Check Docs For Merge Conflict Markers`
- `Dependabot report-only broker`
- `E2E Happy Path`
- `E2E Smoke Test (market_data → signal)`
- `Full Repository Scan`
- `LR-021 Replay Smoke (offline shadow bundle)`
- `MCP Runtime Smoke (optional, manual-only)`
- `Optional SurrealDB Memory Proof`
- `Python compatibility matrix (informational)`
- `Scan Base Images (Redis, Postgres)`
- `Scan Custom Python Services`
- `Security Scan Summary`
- `Sync Labels from labels.json`
- `Trivy - Base Images`
- `Trivy - Custom Services`
- `Validate Message Contracts`
- `add-to-project`
- `ai/review`
- `apply-pr-milestone`
- `assign-single`
- `backfill`
- `build`
- `capture-intent`
- `ci (Unit/Integration + Lint gesammelt)`
- `classify`
- `comment-epic`
- `context-refresh`
- `copilot-setup-steps`
- `curate`
- `daily-delta`
- `dispatch-milestone-label`
- `e2e-paper-trading`
- `enforce-pr-template`
- `escalate`
- `gitleaks (Secrets-Alarm)`
- `governance-audit`
- `guard`
- `housekeeping`
- `issue-automation`
- `labels`
- `opencode`
- `performance-check`
- `persist-via-pr`
- `policy-gate`
- `reconcile-project-board`
- `required-checks-audit (Sentinel)`
- `root-session-hygiene-warning`
- `scan`
- `security-readout`
- `shadow-soak-evidence`
- `smart-insights`
- `stale`
- `surrealdb-validate`
- `sync-project-status`
- `sync-project-status-label-map`
- `sync-stage-labels`
- `triage-guard`
- `trivy (kritische CVEs/Supply-Chain)`
- `upsert-control-board`
- `validate-branch-name`
- `validate-feature-workflow`
- `weekly-digest`
- `weekly-digest-failure-alert`
- `weekly-hygiene`
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
| `cdb-local-ci` | external/commit-status | n/a | n/a | n/a | n/a |

## Parse Errors

- none

## What To Do

- Required contexts are covered by Commit Status / external contexts and/or workflow job names. Keep publisher and branch-protection names aligned for commit-status contexts.
