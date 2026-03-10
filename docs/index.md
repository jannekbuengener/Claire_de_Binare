# Start Here

Kurzer Navigationsindex fuer das Working Repo. Diese Seite ist kein Canon fuer Inhalte,
sondern ein Pointer auf die bestehenden Docs, Runbooks und Source Trees.

## Nach Aufgabe

| Wenn du ... | Geh hierhin | Warum |
|-------|-------|-------|
| Merge-Gates, Required Checks oder Actions-Fehler verstehen willst | [CI Index](ci/index.md) | Canon fuer PR-Gate, Trigger, Failure Modes und Workflow-Familien |
| Toggles, Secrets, Defaults oder operative Env-Variablen suchst | [Env Index](env/index.md) | Einstieg fuer Schalter, Secret Stores und Consumer |
| Schema, Migrations, Privileges, Fixtures oder DB-Validierung suchst | [DB Index](db/index.md) | Einstieg fuer Postgres-Canon und Surreal-Mirror |
| den Echtgeld-Go/No-Go-Stand brauchst | [docs/live-readiness/README.md](live-readiness/README.md) | Single Source of Truth fuer Live-Readiness |
| Board-, Milestone- oder Project-v2-Automation brauchst | [docs/runbooks/project_board_automation.md](runbooks/project_board_automation.md) | Operativer Leitfaden fuer Board-Automation |

## Kern-Pointer

- [docs/runbooks/merge_policy_ci_gate.md](runbooks/merge_policy_ci_gate.md)
  - Branch protection, merge-relevante Check-Namen, PR-Gate Contract.
- [docs/runbooks/project_board_automation.md](runbooks/project_board_automation.md)
  - Milestones, Labels, Project-v2-Flow, Token-Pfade und Troubleshooting.
- [docs/runbooks/control_board_board_as_code.md](runbooks/control_board_board_as_code.md)
  - Toggle, Dry-Run/Apply und Guardrails fuer Board-as-Code.
- [docs/operations/72H_SOAK_TEST_RUNBOOK.md](operations/72H_SOAK_TEST_RUNBOOK.md)
  - Operativer Einstieg fuer Shadow/Soak Evidence.
- [docs/governance/README.md](governance/README.md)
  - Governance-Dokumente und Audit-Artefakte.

## Wichtige Source Trees

- [`.github/workflows/`](../.github/workflows/)
  - Alle GitHub Actions Workflows.
- [`infrastructure/compose/README.md`](../infrastructure/compose/README.md)
  - Compose-Layer, Stack-Aufbau und Infra-Einstieg.
- [`infrastructure/database/`](../infrastructure/database/)
  - Postgres-Schema, Migrations und Privilege-Skripte.
- [`tests/fixtures/README.md`](../tests/fixtures/README.md)
  - Deterministische DB-Fixtures und Seed-Daten.
