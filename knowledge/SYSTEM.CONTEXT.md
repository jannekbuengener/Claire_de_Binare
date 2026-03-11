# SYSTEM.CONTEXT

Status: canonical local entrypoint
Purpose: short system context for humans and agents starting in the working repo

## What This Repo Is

`Claire_de_Binare` is now both:

- the executable working repository for code, infrastructure, and tests
- the canonical home for active agent, governance, knowledge, and navigation docs

The old standalone docs repository is retired as a productive source. If
historical material is needed, use the local archive snapshot under
`docs/archive/docs_hub_snapshot/`.

## Runtime Surface

- `core/` shared domain code and utilities
- `services/` runnable service implementations
- `infrastructure/` compose, monitoring, database, and automation assets
- `tests/` unit, integration, smoke, and e2e coverage
- `tools/` and `scripts/` developer and governance tooling

## Canonical Entry Points

- `agents/AGENTS.md` local agent registry and read order
- `knowledge/CDB_KNOWLEDGE_HUB.md` knowledge hub and key operating links
- `knowledge/CURRENT_STATUS.md` current system state and open priorities
- `knowledge/ACTIVE_ROADMAP.md` consolidated roadmap entrypoint
- `docs/meta/WORKING_REPO_CANON.md` canon decision and archive policy

## Working Rule

Do not resolve default documentation paths through an external docs repository.
Use local paths first. Only historical investigation should touch the archive
snapshot.
