---
name: onboarding
description: >
  Canonical CDB onboarding entrypoint for Codex. Route slash and natural-language
  onboarding intent to the single smart read-only status-card path. Read-only by
  default. No Live-Go, no Echtgeld-Go, no runtime/Docker/DB/MCP mutation.
---

# CDB onboarding

If the user says `/onboarding`, `onboarding`, `onboarding durchführen`, `mach onboarding`,
`fresh agent onboarding`, or equivalent, run: `python -m tools.onboarding_orchestrator`

Do not start `cdb-session-start` or `onboarding_doctor` as the primary path for onboarding intent.

Default output is the CDB Onboarding status card.

Do not create `.env`, initialize secrets, initialize context, write reports, create issues, or run Docker unless the user explicitly selects a next option after the status card.

## Run

```bash
python -m tools.onboarding_orchestrator
python -m tools.onboarding_orchestrator --format json
python -m tools.onboarding_orchestrator --mode check-only
```

## Guardrails

- Read-only by default.
- LR remains NO-GO.
- Board stage `trade-capable` is not Live-Go.
- No Echtgeld-Go.
- No file writes, no GitHub writes, no branch creation, no PR creation, no runtime/Docker/DB/MCP mutation, no secrets.
- Report only the orchestrator `Status`, `State`, warnings, and `allowed_next_actions`.
- Do not invent extra onboarding options or reintroduce the removed legacy setup branch.
- `--mode check-only` is dry-run only and must not imply setup execution.
- The `1. Ja / 2. Abbruch` prompt is only valid when the orchestrator reports `State: SETUP_CONFIRMATION_PENDING`.
