<!--
Canonical Skill Source: docs/skills/surrealdb-vector/SKILL.md
Surface: docs (canonical)
Sync Status: canonical
Last Verified: 2026-07-01
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: surrealdb-vector
description: "CDB-curated, script-free activation of the official SurrealDB vector skill."
metadata:
  author: surrealdb
  source_commit: "95628976"
  cdb_curated: true
---

# SurrealDB Vector Search

## Zweck

Nutze diesen Skill fuer HNSW-Indexe, KNN-Abfragen, Similarity-Scoring und
vektorbasierte Retrieval-Muster in SurrealDB.

## Wann zuenden

- bei `DEFINE INDEX ... HNSW`
- bei KNN-Queries mit `<|K, EF|>`
- bei Score-/Threshold-Logik fuer RAG oder semantische Suche
- bei Review von Vector-Schema- oder Embedding-Feldern

## CDB-Kernpunkte

- Dimension, Distanzfunktion und Typ muessen zum Embedding-Vertrag passen.
- Scoring-Logik gehoert nachvollziehbar dokumentiert und testbar gemacht.
- Dieser Skill bleibt script-frei und gibt keine Laufzeit- oder Installationsbefehle vor.

## Governance Boundary

- CDB Governance gewinnt vor externer Doku.
- This skill is read-only guidance only; it does not authorize command execution.
- No DB-/MCP-writes are authorized by this skill.
- No Live-GO / Echtgeld-GO.

## Offizielle Quelle

- Docs: `https://surrealdb.com/docs/build/ai-agents/agent-skills`
- Repo: `https://github.com/surrealdb/agent-skills`
- Skill: `surrealdb-vector`
- Inspected source commit: `95628976`

## Sichere Nutzung in CDB

- Halte Vector-Suche strikt getrennt von Runtime- oder Live-Freigaben.
- Nutze diesen Skill fuer Query- und Schema-Verstaendnis, nicht als Schreibfreigabe.
- Wenn HNSW-Details von CDB-Vertraegen abweichen, gilt der engere CDB-Vertrag.
