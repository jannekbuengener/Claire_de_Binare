<!--
Canonical Skill Source: docs/skills/ctb-docker-stack/SKILL.md
Surface: docs (canonical)
Sync Status: mirrored
Last Verified: 2026-07-01
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: ctb-ops-stack-skillpack
description: Ops skillpack for the current CDB stack. Use when Codex needs command-first PowerShell guidance for Docker, compose, DR, rollback, incident response, or stack inspection in the working repo. Use canonical BLUE+RED runtime paths, respect `SECRETS_PATH`, and require explicit user approval before any mutating Docker or compose action.
disable-model-invocation: true
---

# CDB Ops Stack Skillpack

## Discovery mapping
- Folder: ctb-docker-stack
- Skill name: ctb-ops-stack-skillpack
- Treat these as the same OpenCode skill surface; do not rename the folder or the skill in this patch.

## Canon first
- Working repo only.
- Start control-first:
  1. GitHub control issue `#1445`
  2. newest weekly comment on `#1445`
  3. ratified stage issue `#1492` as Board context only
  4. `docs/runbooks/CONTROL_REGISTER.md`
  5. `CURRENT_STATUS.md`
  6. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
  7. only then repo-level commands, issues, or PR actions
- Use `knowledge/CDB_DOCKER_STACK_INVENTORY.md` only after the control-first chain above.
- Treat Board stage and LR verdict separately. `trade-capable` does not authorize live operations.
- `#1492` is ratified stage context, not LR-GO.

## Approval gate
For any command that mutates Docker Desktop, compose state, containers, networks, volumes, images, or configuration:

> STOP -> present the exact command -> wait for explicit user approval -> then act

This replaces older gate names. The required approver is the explicit user in the current thread.

## Hard rules
- No guessing. Missing runtime facts or target paths require a short clarifying question.
- No secrets: never print secret values or secret file contents.
- Use canonical compose files explicitly: `infrastructure/compose/compose.blue.yml` and `infrastructure/compose/compose.red.yml`.
- Do not give single-compose shortcuts as default guidance; prefer `make docker-up` and explicitly reference `infrastructure/compose/compose.blue.yml` + `infrastructure/compose/compose.red.yml`.
- Treat `SECRETS_PATH` as canonical for local secrets.
- Never use `docker compose down -v` unless the user explicitly approves a destructive action.

## External Documentation Lookup

This skill references Docker, Compose, and container runtime documentation:
- Load `cdb-external-docs` before composing Docker commands or debugging stack issues.
- Look up `docs/external-docs/index.md` → Runtime / Infrastruktur section.
- Relevant: Docker Docs, Docker Compose, Dev Containers.
- Verify compose syntax and behavior against official docs before mutating stack state.

## Default output format
1. Context snapshot
2. Proposed commands, clearly marked as not executed until approved
3. Mini-runbook
4. Approval status: pending or approved
