# ADR-002: Context Intelligence Canon — ADOPT_AFTER_FOUNDATION_REPAIR

| Field | Value |
| --- | --- |
| Status | **accepted** |
| Date | 2026-06-24 |
| Issue | GitHub issue #3419 (SLICE-01) |
| Parent | GitHub issue #3418 |
| Architecture Decision | `ADOPT_AFTER_FOUNDATION_REPAIR` |

## Kontext

Das CDB Context Intelligence System (CIS) besitzt eine starke, fail-closed
read-only Foundation, bestehend aus:

- Context MCP Bridge mit 27+ read-only Tools (`Readiness`, `Briefing`,
  `Package`, `Impact`, `QualityScore`, `ArchitectSignals`, `ScopeDrift`,
  `Stale`, `Contradictions`, `ClaimResolve`, `EvidenceResolve`,
  `DecisionHistory`, `DecisionReplay`, `MemoryGet`, `TrustSummary`,
  `ControlRoomView`, `AgentOSReadiness`, u.a.)
- Registry + Permission Guard mit `PERSIST_ALLOWED=false`,
  `MUTATION_ALLOWED=false` als Default auf `main`
- DB-Record-Evidence-Contract mit guarded Adapter-Schicht
- Hybrid-Ranking-Architektur und 30+ SurrealDB-Dokumente
- Context-Package-Modell, Agent-Handoff-Contracts, Briefing-Enrichment
- Wave-10 bis Wave-21 Completion Gates

Diese Foundation ist robust und produktionstauglich für den read-only Betrieb.
Sie ist jedoch **kein SurrealDB-native VectorGraph/EvidenceGraph**.

Die aktuelle Foundation verwendet In-Memory- und Repo-File-Queries über die
Bridge. Ein SurrealDB-native VectorGraph mit DB-eigenen Records,
RELATE-Traversals, Embeddings, Vector-Indizes, Full-text-Indizes und
DB-backed Brain Evidence existiert noch nicht.

## Entscheidung

**`ADOPT_AFTER_FOUNDATION_REPAIR`**

Das CDB-Projekt adoptiert die SurrealDB-native Context Intelligence Architektur
mit VectorGraph, EvidenceGraph und DB-gestütztem ContextBrain — aber **erst nach
erfolgreicher Foundation-Reparatur**.

Die "Foundation Repair" umfasst:

1. **#3420 — SurrealKit Schema Foundation** — kanonische Schema-Basis (Tables,
   Indexes, Permission-Template, Migrations-Setup)
2. **#3421 — Readonly MCP Brain Evidence Contract** — harter MCP-Vertrag für
   DB-backed Brain Evidence in read-only Tools
3. **#3422 — VectorGraph Minimal Schema** — `repo_artifact`, `decision`,
   `evidence_record`, `dependency_edge` als DB-native Records mit
   RELATE-Traversals
4. **#3423 — Graph Relations + Traversal Queries** — RELATE-Traversals,
   Graph-Navigation, Decision-Chain-Auflösung
5. **#3424 — Full-text + Vector + Hybrid Retrieval Contract** — Vector-Indizes,
   Full-text-Indizes, Hybrid-Ranking in SurrealDB
6. **#3425 — Agent Skills / Rules Integration** — Skill-Surface-Verkabelung mit
   Context Brain
7. **#3426 — Permission Matrix + Readonly Agent User** — granulare Permissions,
   SCOPE-User, fail-closed Defaults
8. **#3427 — ContextBrain Report / Gist Ledger Integration** — Report-Generator,
   Ledger-Integration, Evidence-Packs

Diese Foundation-Reparatur ist eine Voraussetzung, kein optionaler Schritt.
Ohne diese Slices ist kein SurrealDB-native Betrieb mit DB-backed Evidence,
Vector-Suche oder Permission-Sicherheit möglich.

## Begründung

### Strategic Context

1. **Aktuelle Foundation ist stark aber In-Memory/Repo-bound.** Die Bridge und
   Registry erlauben reibungslosen read-only Betrieb, aber jede Query geht
   durch In-Memory- oder Repo-File-Layer statt durch SurrealDB-native
   Records und Indizes.
2. **Vector/Full-text-Suche erfordert SurrealDB-native Schema.** Ohne
   `DEFINE INDEX ... FT` und Vector-Indizes auf SurrealDB-Tabelle ist
   kein hybrides Retrieval möglich, das über In-Memory-Ranking hinausgeht.
3. **Evidence-Kette braucht DB-backed Records.** Der aktuelle
   DB-Record-Evidence-Contract definiert das *Was* und *Wie* für
   Evidence-Prüfung, aber die Records selbst sind noch nicht in SurrealDB
   als `evidence_record`- oder `decision`-Records materialisiert.
4. **Permission-Sicherheit erfordert SCOPE-User + Schema-basierte Rechte.**
   Der aktuelle Permission Guard ist eine Application-Layer-Sperre.
   SurrealDB-native SCOPE-User und `DEFINE PERMISSIONS` sind nötig für
   fail-closed Agent-Zugriff auf den VectorGraph.

### Gap Matrix

Die detaillierte Gap-Analyse zwischen aktueller Foundation und Zielarchitektur
steht im externen Research-Report:

- **Datei (extern):** `CDB_SURREALDB_CONTEXT_INTELLIGENCE_GAP_MATRIX.md`
- **Pfad (lokal):** `D:\Dev\Office\CDB\CDB_SurrealDB_Context_Intelligence_System\NEU\`
- **Status:** Nicht im Repo gespiegelt (externe Evidence)

Kernaussage der Gap Matrix: Die Foundation deckt ca. 70 % der benötigten
CIS-Architektur ab (read-only, Contracts, Bridge-Tools, Registry,
Permission Guard). Die fehlenden 30 % sind SurrealDB-native Records,
Indizes und Permissions, die durch #3420–#3427 adressiert werden.

### Deep Research Report

Der Architecture Decision liegt folgender externer Research-Report zugrunde:

- **Datei (extern):** `CDB_SURREALDB_CONTEXT_INTELLIGENCE_DEEP_RESEARCH_REPORT.md`
- **Pfad (lokal):** `D:\Dev\Office\CDB\CDB_SurrealDB_Context_Intelligence_System\NEU\`
- **Status:** Nicht im Repo gespiegelt (externe Evidence)

Der Report analysiert die SurrealDB-Ecosystem-Reife, Schema-Design-Ansätze
und Integrationstiefe für CDB. Er empfiehlt den gewählten
"Foundation-first, VectorGraph-second"-Ansatz.

### Bestehende Posture

Die aktive Context-Brain-Posture ist in
[`CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md)
(#2775) dokumentiert:

- `read_only_context_brain = conditional`
- Default: `brain_source=repo-only`, `brain_status=not-used`
- DB-backed Claims nur mit guarded Adapter + Record-Evidence
- `PERSIST_ALLOWED=false`, `MUTATION_ALLOWED=false` auf `main`

Dieser ADR-002 ändert die bestehende Posture nicht. Er dokumentiert den
Entscheid, nach Foundation-Reparatur auf eine SurrealDB-native Architektur
umzustellen, ohne die aktuellen Guardrails aufzuweichen.

## Scope

### In Scope

- Architecture Decision Record für `ADOPT_AFTER_FOUNDATION_REPAIR`
- Referenz auf Gap Matrix (extern)
- Referenz auf Deep Research Report (extern)
- CONTROL_REGISTER-Eintrag
- Abgrenzung zu bestehenden Decisions (#2775)

### Nicht-Ziele (explizit)

- **Keine** Implementierung von VectorGraph/EvidenceGraph-Code
- **Keine** Schema-Änderungen an SurrealDB
- **Keine** DB-Writes, Migrationen oder Data-Ingestion
- **Kein** Live-Go / Echtgeld-Go
- **Keine** Docker- oder Runtime-Änderungen (BLUE/RED)
- **Keine** MCP-Mutationen
- **Keine** Trading-State- oder Secrets-Aufnahme
- **Kein** Scope-Wachstum auf #3420–#3427 (separate Issues)
- **Kein** automatischer Persist- oder Mutations-Modus

## Abhängigkeiten

| Slice | Issue | Kritisch für |
|---|---|---|
| SLICE-02 | #3420 | Schema Foundation, ohne die keine Schema-Änderungen möglich |
| SLICE-03 | #3421 | MCP Evidence Contract für DB-backed Brain |
| SLICE-04 | #3422 | VectorGraph Minimal Schema |
| SLICE-05 | #3423 | Graph Relations + Traversal Queries |
| SLICE-06 | #3424 | Hybrid Retrieval (Vector + Full-text) |
| SLICE-07 | #3425 | Agent Skills Integration |
| SLICE-08 | #3426 | Permission Matrix + Readonly Agent User |
| SLICE-09 | #3427 | ContextBrain Report / Ledger |

## Konsequenzen

### Positive

1. Klare Architektur-Entscheidung für das gesamte CIS-Programm
2. Foundation bleibt unverändert produktiv; keine Regression durch übereilte
   VectorGraph-Einführung
3. Alle Folgeslices (#3420–#3427) haben einen referenzierbaren Decision Anchor
4. Gap Matrix und Research Report sind als externe Evidence dokumentiert
   und nachvollziehbar

### Negative

1. VectorGraph/EvidenceGraph-Value ist erst nach Abschluss aller 8 Slices
   lieferbar
2. Research Reports sind nicht im Repo gespiegelt — externe Abhängigkeit
3. Agenten müssen bis zur Fertigstellung weiterhin mit repo-only/In-Memory
   Context Brain arbeiten (Status quo)
4. Kein DB-backed Evidence-Chain-Betrieb vor #3427

## Safety Boundaries

| Boundary | Value |
|---|---|
| LR Status | **NO-GO** (unverändert) |
| Board Stage `trade-capable` | **Orthogonal** — kein Live-Go |
| Real Money Go | **false** |
| Productive DB Writes | **false** |
| `PERSIST_ALLOWED` | **false** |
| `MUTATION_ALLOWED` | **false** |
| Runtime BLUE/RED Changes | **false** |
| MCP Mutations | **false** |
| Secrets in Outputs | **false** |

Board-Stage `trade-capable` autorisiert weder Live-Kapital noch
Strategie-Freigabe. LR-Verdikt bleibt ausschliesslich in
`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.

## Referenzen

- [`CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md) — Issue #2775
- [`agents/AGENTS.md`](../../agents/AGENTS.md) — Brain Evidence Gate
- [`docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md)
- Extern: `CDB_SURREALDB_CONTEXT_INTELLIGENCE_DEEP_RESEARCH_REPORT.md`
  (`D:\Dev\Office\CDB\CDB_SurrealDB_Context_Intelligence_System\NEU\`)
- Extern: `CDB_SURREALDB_CONTEXT_INTELLIGENCE_GAP_MATRIX.md`
  (`D:\Dev\Office\CDB\CDB_SurrealDB_Context_Intelligence_System\NEU\`)
- #3418 — Meta-Issue: Build SurrealDB-native ContextBrain / VectorGraph Foundation
- #3420–#3427 — Folgeslices (Foundation Repair)
