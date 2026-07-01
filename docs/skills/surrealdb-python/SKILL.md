<!--
Canonical Skill Source: docs/skills/surrealdb-python/SKILL.md
Surface: docs (canonical)
Sync Status: mirrored
Last Verified: 2026-07-01
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: surrealdb-python
description: "CDB-curated, script-free activation of the official SurrealDB Python skill."
metadata:
  author: surrealdb
  source_commit: "95628976"
  cdb_curated: true
---

# SurrealDB Python SDK

## Zweck

Nutze diesen Skill fuer den SurrealDB-Python-SDK-Kontext: `Surreal`,
`AsyncSurreal`, Client/Server-Modus und Embedded-Varianten wie `mem://` oder
`file://`.

## Wann zuenden

- bei Python-Code mit dem Paket `surrealdb`
- bei Review von `Surreal(...)` oder `AsyncSurreal(...)`
- bei Embedded-Nutzung mit `mem://` oder `file://`
- bei SDK-Fragen zu CRUD, Query-Calls oder Session-Nutzung

## CDB-Kernpunkte

- Beispiele aus Upstream muessen auf CDB-Read-only- und Governance-Grenzen angepasst werden.
- Keine Zugangsdaten, Root-Defaults oder Startbefehle aus Upstream-Beispielen uebernehmen.
- Embedded- oder lokale Laufmodi sind kein Signal fuer produktive Freigabe.
- Dieser Skill bleibt script-frei und autorisiert keine Ausfuehrung.

## Governance Boundary

- CDB Governance gewinnt vor externer Doku.
- This skill is read-only guidance only; it does not authorize command execution.
- No DB-/MCP-writes are authorized by this skill.
- No Live-GO / Echtgeld-GO.

## Offizielle Quelle

- Docs: `https://surrealdb.com/docs/build/ai-agents/agent-skills`
- Repo: `https://github.com/surrealdb/agent-skills`
- Skill: `surrealdb-python`
- Inspected source commit: `95628976`

## Sichere Nutzung in CDB

- Nutze Upstream nur als API- und Pattern-Referenz.
- Fuer produktive oder DB-backed Behauptungen zaehlt CDB-Evidence vor Beispielcode.
- Wenn Embedded- oder WebSocket-Verhalten relevant ist, gleiche es mit dem Repo-Canon ab.
