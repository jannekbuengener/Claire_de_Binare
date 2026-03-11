# CI Index

Kurzer Einstieg fuer Workflows, Trigger, Failure Modes und den merge-relevanten
CI-Contract.

## Canonical PR Gate

- Workflow: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
- Merge-relevante Check-Namen auf PRs:
  - `ci (Unit/Integration + Lint gesammelt)`
  - `policy-gate`
- Canon-Runbook: [docs/runbooks/merge_policy_ci_gate.md](../runbooks/merge_policy_ci_gate.md)

Wichtig: `ci.yml` ist der PR-Gate-Workflow. Die groessere Push-/Dispatch-Pipeline
[`ci.yaml`](../../.github/workflows/ci.yaml) ist nicht merge-relevant, solange der
Contract nicht explizit geaendert wird.

## Workflow-Familien

| Bereich | Primaere Dateien | Trigger | Einstieg |
|-------|-------|-------|-------|
| PR Gate | [ci.yml](../../.github/workflows/ci.yml), [policy-gate.yml](../../.github/workflows/policy-gate.yml) | `pull_request`, `push` | [merge_policy_ci_gate.md](../runbooks/merge_policy_ci_gate.md) |
| Main / Dispatch Pipeline | [ci.yaml](../../.github/workflows/ci.yaml) | `push`, `workflow_dispatch` | [merge_policy_ci_gate.md](../runbooks/merge_policy_ci_gate.md) |
| Board / Milestone Automation | [add_to_project.yml](../../.github/workflows/add_to_project.yml), [project_status_sync.yml](../../.github/workflows/project_status_sync.yml), [auto-milestone.yml](../../.github/workflows/auto-milestone.yml) | `issues`, `pull_request`, `repository_dispatch` | [project_board_automation.md](../runbooks/project_board_automation.md) |
| Board-as-Code | [control_board_upsert.yml](../../.github/workflows/control_board_upsert.yml), [control_board_auto_routing.yml](../../.github/workflows/control_board_auto_routing.yml) | `workflow_dispatch`, `issues`, `pull_request`, `schedule` | [control_board_board_as_code.md](../runbooks/control_board_board_as_code.md) |
| Soak / Heavy Evidence | [shadow-soak-evidence.yml](../../.github/workflows/shadow-soak-evidence.yml) | `schedule`, `workflow_dispatch` | [SHADOW_SOAK_RUN_INDEX.md](../evidence/SHADOW_SOAK_RUN_INDEX.md) |
| Audit / Exception Semantics | [required-checks-audit.yml](../../.github/workflows/required-checks-audit.yml) | `workflow_dispatch` | [README.md](README.md), [ACTION_REQUIRED_RUNBOOK.md](ACTION_REQUIRED_RUNBOOK.md) |

## workflow_run Kanten

- `Auto Milestone PR Intent` -> `Auto Milestone PR Apply`
- `Weekly Project Digest` -> `Weekly Digest Failure Alert`

Die aktuelle Dependency-Map und die Rename-Regel stehen in
[docs/ci/README.md](README.md).

## Haeufige Failure Modes

- Required Check rot oder Branch Protection blockiert:
  - [docs/runbooks/merge_policy_ci_gate.md](../runbooks/merge_policy_ci_gate.md)
- Project-v2 / Token / Scope Fehler:
  - [docs/runbooks/project_board_automation.md](../runbooks/project_board_automation.md)
- `workflow_run`-Rename-Drift:
  - [docs/ci/README.md](README.md)
- MCP/Worktree Usability Drift:
  - [docs/runbooks/mcp_worktree_hygiene.md](../runbooks/mcp_worktree_hygiene.md)
- CI/Governance Drift (read-only):
  - [docs/runbooks/ci_hygiene_drift_checks.md](../runbooks/ci_hygiene_drift_checks.md)
- Gruen mit Ausnahmepfad statt echtem E2E-Pass:
  - [docs/ci/README.md](README.md)
