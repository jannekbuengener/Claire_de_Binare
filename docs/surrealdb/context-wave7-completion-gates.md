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
- Wave-7 Completion Gates sind selbst reconciled und gelandet (Issue #2043)

### 3.4 Reconciliation-Stand

- Wave 7-A Docs-Reconciliation ist ueber PR #2224 gelandet.
- Wave 7-B Docs-Index-Update ist ueber PR #2225 gelandet.
- Wave 7-C ist erst abgeschlossen, wenn #2039, #2040, #2042 und #2043 gelandet sind.
- PR #2223 (#1986 ingestion scope rebuild) bleibt offen, eingefroren und **kein** Wave-7-Abschlusskriterium.
- PR #2216 (Wave 8 readiness/readiness) bleibt offen, eingefroren und **kein** Wave-7-Abschlusskriterium.

---

## 4. Praktische Verifikation (GitHub)

SSOT ist GitHub. Validierung erfolgt ueber PR-/Issue-Status.

Minimal:

- fuer jedes Dependency-Issue: Live-Issue-State ist geprueft
- gelandete Slices sind ueber gemergte PRs belegt (mindestens #2224 und #2225)
- offene W07-C-Restarbeit (#2039, #2040, #2042, #2043) ist als offen sichtbar
- Checks fuer den jeweils zu mergeenden W07-C-PR: keine failed/pending

Wave 7 ist **nicht** abgeschlossen, solange einer der offenen W07-C-Issues (#2039, #2040, #2042, #2043) nicht gelandet ist.

---

## 5. Output von Wave 7

Erwartetes Ergebnis:

- Repo hat eine vollstaendige docs-basierte Grundlage (Architektur, Roadmap, Ontology, Schema Draft, Validation, Handoff)
- spaetere Implementierungswellen koennen auf klaren Guardrails aufbauen
- Live-Readiness bleibt `NO-GO`; Wave 7 liefert nur die docs-basierte Grundlage und keine Betriebsfreigabe

---

## 6. Handover zu Wave 8

Wave 8 darf erst starten, wenn Gate-Checkliste in Abschnitt 3 erfuellt ist.

Wave 8 Fokus (nicht Teil von Wave 7):

- Indexer Scaffold
- Dry-run Export Pipeline

Wave 8 darf nicht ueber PR #2216 oder irgendeinen Board-Stage-Status als bereits freigegeben angenommen werden.
