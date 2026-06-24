# Context Intelligence v0 — SurrealKit Compatibility Layer

**Issue:** #3420 (SLICE-02)
**Parent Meta:** #3418
**Architecture Decision:** ADR-002 (`ADOPT_AFTER_FOUNDATION_REPAIR`)

## Überblick

Dieses Dokument beschreibt die SurrealKit-Kompatibilitätsschicht der
`context_intelligence_v0`-Schemafläche.  Die Schicht ist eine **reine
Schema- und Tooling-Foundation** — sie autorisiert keine produktive Migration,
keinen Live-Sync und keine Daten-Bootstrapping.

## Dateistruktur

| Datei | Zweck |
|-------|-------|
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Kanonischer Schema-Draft (18 Tabellen) — bewusst ohne NS/DB-Kontext |
| `infrastructure/surrealdb/context_intelligence_v0_deploy.surql` | SurrealKit-kompatibles Deploy-Wrapper mit NS/DB + `IF NOT EXISTS` + Permissions |
| `tools/surrealdb/schema_snapshot.py` | Deterministisches Schema-Snapshot-Tool (repo-backed) |
| `infrastructure/surrealdb/schema_baseline.json` | Committes Schema-Hash-Baseline |
| `tests/surrealdb/test_context_intelligence_v0_surql.py` | Schema-Contract-Tests |
| `tests/surrealdb/test_schema_snapshot.py` | Snapshot-Tests |

## Was die Kompatibilitätsschicht leistet

1. **Idempotentes Schema-Loading** — alle `DEFINE TABLE`-Statements im Deploy-Wrapper
   nutzen `IF NOT EXISTS`, sodass das Schema mehrfach geladen werden kann, ohne
   Fehler zu produzieren.
2. **NS/DB-Isolation** — das Deploy-Wrapper definiert `NS cdb` / `DB context_intel`
   und stellt sicher, dass alle Tabellen im korrekten Namespace/Database-Kontext
   angelegt werden.
3. **Fail-closed Permissions** — jede Tabelle hat `FOR select NONE, FOR create NONE,
   FOR update NONE, FOR delete NONE`.  Produktive Berechtigungen werden durch
   Issue #3426 (Permission Matrix + Readonly Agent User) definiert.
4. **Schema-Integritätsprüfung** — das Snapshot-Tool erlaubt die Prüfung, ob
   das aktuelle Schema mit einem Baseline-Hash übereinstimmt (CI-fähig).

## Sync-Workflow (vorbereitet, nicht aktiviert)

Der Sync-Workflow (`surrealkit sync`) ist **vorbereitet, aber nicht aktiviert**.
Der deploybare Schema-Wrapper ist SurrealKit-kompatibel formuliert, sodass
ein späterer Sync-Schritt die `.surql`-Dateien in eine SurrealDB-Instanz laden
kann.  Der tatsächliche Sync und die zugehörigen Credentials/Authorisierung
werden im nächsten Slice (#3421 — Readonly MCP Brain Evidence Contract) adressiert.

## Nicht-Ziele (explizit)

- **Keine** produktive Datenmigration
- **Kein** Live-Sync gegen echte SurrealDB-Instanzen
- **Kein** Bootstrapping von Daten
- **Keine** Änderung an `PERSIST_ALLOWED` / `MUTATION_ALLOWED`
- **Kein** Runtime-/Docker-/MCP-Scope
- **Keine** Trading-State-Objekte (Orders/Fills/Positions/Risk-State)

## Nächster Slice

- **#3421** — Readonly MCP Brain Evidence Contract: harter MCP-Vertrag für
  DB-backed Brain Evidence in read-only Tools

## Referenzen

- ADR-002: `knowledge/decisions/ADR-002-context-intelligence-canon.md`
- Issue #3420: GitHub issue (SLICE-02 — SurrealKit Schema Foundation)
- Issue #3418: Meta-Issue (Build SurrealDB-native ContextBrain / VectorGraph)
- Snapshot-Tool: `tools/surrealdb/schema_snapshot.py`
- Schema-Tests: `tests/surrealdb/`
