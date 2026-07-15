# CI PR Decoupling Note

Date: 2026-02-19
Branch: `ci/decouple-noncritical-from-pr`

## Scope
- Workflow-only changes under `.github/workflows/`
- No Docker/Compose/Dockerfile changes
- No trading logic changes

## Decoupled From PR Load

| Workflow | File | Before | After |
|---|---|---|---|
| E2E Happy Path | `.github/workflows/e2e-happy-path.yaml` | `pull_request (main)`, `push (main)`, `workflow_dispatch`, `schedule` | `push (main)`, `workflow_dispatch`, `schedule` |

## Additional PR Noise Reduction

| Workflow | File | Before | After |
|---|---|---|---|
| ci | `.github/workflows/ci.yml` | `pull_request (main)`, `push (all branches, path-filtered)` | `pull_request (main)`, `push (main only, path-filtered)` |

## Manual Start
- E2E Happy Path: `gh workflow run "E2E Happy Path"`

## Scheduled Runs
- E2E Happy Path: Sundays at `05:30 UTC` (`30 5 * * 0`)

## Safety Notes
- No workflow names were changed.
- No `pull_request_target` usage detected.
- Required branch-protection check observed on `main`: `ci (Unit/Integration + Lint gesammelt)`.
