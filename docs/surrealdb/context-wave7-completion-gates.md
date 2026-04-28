# Context Intelligence — Wave 7 Completion Gates

**Status**: Draft
**Authority**: Issue #2043 / Parent #2034 / Epic #1976
**Scope**: Docs-only (keine Runtime-Aenderung)

---

## 1. Zweck

Dieses Dokument definiert **Abschlusskriterien fuer Wave 7** (Context Intelligence Landing).
Es soll spaeteren Agenten ermoeglichen, den Stand **ohne Chatverlauf** zu pruefen.

Wichtig:

- Wave-7-Abschluss ist **kein** Live-Readiness-Go.
- Wave-7-Abschluss ist **keine** produktive SurrealDB-Aktivierung.

---

## 2. Guardrails (Anti-Kriterien)

Wave 7 DARF NICHT enthalten:

- Runtime-Aenderungen
- produktives SurrealDB-Enable
- Ingestion-Implementierung
- MCP-Bridge-Implementierung
- Trading-State-Beruehrung
- Live-Readiness-Upgrade
- Echtgeld-Go

Wenn eines davon passiert: **STOPP** und PR/Issue splitten.

---

## 3. Gate-Checkliste (MUSS)

Wave 7 gilt als abgeschlossen, wenn alle Punkte erfuellt sind.

### 3.1 Architektur und Roadmap

- Architektur-Zielbild ist im Repo gelandet: `docs/surrealdb/context-intelligence-system.md` (Issue #2035)
- Roadmap / Issue-Map ist im Repo gelandet: `docs/surrealdb/context-intelligence-roadmap.md` (Issue #2036)

### 3.2 Schema und Ontology (Draft)

- SurrealQL Schema-Draft existiert im Repo (Issue #2037)
- Ontology Seed existiert im Repo: `docs/surrealdb/context-ontology-v0.yaml` (Issue #2038)

### 3.3 Operational Docs

- Static Validation Checklist existiert im Repo (Issue #2039)
- Agent Handoff Doku existiert im Repo (Issue #2040)
- SurrealDB Docs Index ist aktualisiert (Issue #2041)
- PR Slicing Plan existiert im Repo (Issue #2042)

---

## 4. Praktische Verifikation (GitHub)

SSOT ist GitHub. Validierung erfolgt ueber PR-/Issue-Status.

Minimal:

- fuer jedes Dependency-Issue: zugehoerigen PR-Link vorhanden
- PR Checks: keine failed/pending
- PR Merge-Gate: `mergeStateStatus=CLEAN` oder explizit dokumentiert, warum blockiert

Wenn PRs durch Branch Protection blockiert sind (`mergeStateStatus=BLOCKED`):

- Wave 7 ist **nicht** abgeschlossen, bis die required reviews erfuellt sind und der Merge erfolgt.

---

## 5. Output von Wave 7

Erwartetes Ergebnis:

- Repo hat eine vollstaendige docs-basierte Grundlage (Architektur, Roadmap, Ontology, Schema Draft, Validation, Handoff)
- spaetere Implementierungswellen koennen auf klaren Guardrails aufbauen

---

## 6. Handover zu Wave 8

Wave 8 darf erst starten, wenn Gate-Checkliste in Abschnitt 3 erfuellt ist.

Wave 8 Fokus (nicht Teil von Wave 7):

- Indexer Scaffold
- Dry-run Export Pipeline
