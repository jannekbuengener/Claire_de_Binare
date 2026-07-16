# SYSTEM.CONTEXT

Status: canonical local entrypoint
Purpose: short system context for humans and agents starting in the Claire de Binare repository

## What This Repo Is

`Claire_de_Binare` is now both:

- the executable Claire de Binare repository for code, infrastructure, and tests
- the canonical home for active agent, governance, knowledge, and navigation docs

The old standalone documentation repository is retired as a productive source.
Historical individual artifacts may remain under `docs/archive/`; earlier
revisions are available through Git history.

## Runtime Surface

- `core/` shared domain code and utilities
- `services/` runnable service implementations
- `infrastructure/` compose, monitoring, database, and automation assets
- `tests/` unit, integration, smoke, and e2e coverage
- `tools/` and `scripts/` developer and governance tooling

## Canonical Entry Points

- `agents/AGENTS.md` local agent registry and read order
- `knowledge/CDB_KNOWLEDGE_HUB.md` knowledge hub and key operating links
- `CURRENT_STATUS.md` current Claire de Binare repository / engineering status
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` current operational live-readiness verdict
- `knowledge/CURRENT_STATUS.md` historical knowledge snapshot and older open-priority context
- `knowledge/ACTIVE_ROADMAP.md` consolidated roadmap entrypoint
- `docs/meta/REPOSITORY_CANON.md` canon decision and archive policy

## Working Rule

Do not resolve default documentation paths through an external docs repository.
Use local paths first. Historical investigation may use individual archive
artifacts or Git history, neither of which is a second canonical source.
