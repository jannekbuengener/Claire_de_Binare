<!--
Canonical Skill Source: docs/skills/surrealql/SKILL.md
Surface: opencode
Sync Status: mirrored-from-canon
Last Verified: 2026-07-01
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: surrealql
description: "CDB-curated, script-free activation of the official SurrealQL agent skill."
metadata:
  author: surrealdb
  source_commit: "95628976"
  cdb_curated: true
---

# SurrealQL

## Zweck

Nutze diesen Skill fuer SurrealQL-Queries, Schema-Definitionen,
Graph-Traversals und Syntax-Reviews rund um SurrealDB.

## Wann zuenden

- beim Schreiben oder Pruefen von `.surql`
- bei `DEFINE TABLE` / `DEFINE FIELD` / `DEFINE INDEX`
- bei Graph-Relationships und Record-IDs
- wenn SQL-Denkmuster auf SurrealQL uebersetzt werden muessen

## CDB-Kernpunkte

- SurrealQL ist nicht ANSI-SQL.
- Fuer aktuelle Syntax gilt die offizielle SurrealDB-Doku als SSOT.
- Repo-Kanon und CDB-Vertraege haben Vorrang, wenn CDB den Upstream enger fasst.
- Dieser Skill ist absichtlich script-frei und enthaelt keine Installations- oder
  Auto-Run-Anweisungen.

## Governance Boundary

- CDB Governance gewinnt vor externer Doku.
- This skill is read-only guidance only; it does not authorize command execution.
- No DB-/MCP-writes are authorized by this skill.
- No Live-GO / Echtgeld-GO.

## Offizielle Quelle

- Docs: `https://surrealdb.com/docs/build/ai-agents/agent-skills`
- Repo: `https://github.com/surrealdb/agent-skills`
- Skill: `surrealql`
- Inspected source commit: `95628976`

## Sichere Nutzung in CDB

- Nutze diesen Skill zusammen mit der offiziellen Doku, wenn Syntax oder
  Versionsverhalten unklar ist.
- Wenn CDB-Canon und Upstream-Beispiel kollidieren, stoppe und dokumentiere den
  Widerspruch statt still zu raten.
- Fuer Vector- oder Python-SDK-Themen lade den passenden Schwester-Skill.
