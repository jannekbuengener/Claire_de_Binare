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

## VectorGraph Minimal Schema (Issue #3422)

Seit Issue #3422 enthält das Schema die ersten VectorGraph-Elemente:

### Analyzer

```surql
DEFINE ANALYZER cdb_code_analyzer TOKENIZERS class, camel FILTERS lowercase, ascii;
```

- **TOKENIZERS**: `class` (Zeichenklassen-Wechsel: Buchstabe→Ziffer→Punctuation→Blank), `camel` (camelCase/PascalCase-Benennungen)
- **FILTERS**: `lowercase` (Normalisierung), `ascii` (ASCII-Faltung)
- Verwendet vom FULLTEXT-Index auf `doc_chunk.content`

### embedding-Feld

```surql
DEFINE FIELD embedding ON TABLE doc_chunk TYPE array;
```

- Typ: `array` (numerisches Array für Embedding-Vektoren)
- Keine Embedding-Generierung im Schema — reine Feld-/Index-Definition
- Embedding-Runtime wird in Issue #3424 (Hybrid Retrieval) adressiert

### HNSW Vector Index

```surql
DEFINE INDEX idx_doc_chunk_embedding_hnsw ON TABLE doc_chunk FIELDS embedding HNSW DIMENSION 1536 DIST COSINE;
```

- **Dimension**: 1536 (OpenAI `text-embedding-ada-002` / `text-embedding-3-small` Standard)
- **Distance**: COSINE (Standard für Text-Embeddings)
- **Default-Parameter**: EFC und M werden von SurrealDB automatisch bestimmt
- **Hinweis**: Dimension-Wechsel erfordert `DROP INDEX` + Recreate

### Full-text Search Index

```surql
DEFINE INDEX idx_doc_chunk_content_ft ON TABLE doc_chunk FIELDS content FULLTEXT ANALYZER cdb_code_analyzer BM25 HIGHLIGHTS;
```

- **ANALYZER**: `cdb_code_analyzer` (Code-fähig: camelCase, class-basiert, lowercase)
- **Ranking**: BM25 (Standard-Parameter k1=1.2, b=0.75)
- **Highlights**: Aktiviert `search::highlight()`-Unterstützung
- **Single-Field**: FULLTEXT-Indexes arbeiten nur auf genau einer Spalte (SurrealDB-Limit)

### Nächste Slices

- **#3423** — Graph Relations + Traversal Queries: RELATE-Traversals und Graph-Navigation
- **#3424** — Hybrid Retrieval Contract: Embedding-Runtime, Vector + Full-text + Graph Hybrid Query
- **#3421** — Readonly MCP Brain Evidence Contract: harter MCP-Vertrag für
  DB-backed Brain Evidence in read-only Tools

## SurrealQL Syntax Validation (Issue #3430)

Seit Issue #3430 ist eine SurrealQL-Syntax-Validation im Repo integriert:

### Korrektur: `surrealkit validate` existiert nicht

Die ursprüngliche Annahme aus #3420/#3430, dass `surrealkit validate` ein gültiger
Befehl sei, war **faktisch falsch**. Das offizielle SurrealKit CLI (`surrealkit`)
kennt keinen `validate`-Befehl. Die verfügbaren SurrealKit-Kommandos sind:
`init`, `sync`, `rollout` (plan/start/complete/rollback/repair/lint/status/baseline),
`seed`, `test`.

### Tatsächlicher Befehl: `surreal validate`

Der korrekte Befehl für reine Syntax-Validierung ohne Datenbank ist `surreal validate`
aus dem offiziellen SurrealDB CLI. Er prüft `.surql`-Dateien auf Parser-Ebene und
benötigt **keine laufende SurrealDB-Instanz**.

```bash
surreal validate infrastructure/surrealdb/context_intelligence_v0_deploy.surql
surreal validate infrastructure/surrealdb/context_intelligence_v0.surql
```

### CI-Integration

Ein separater CI-Job `surrealdb-validate` führt diese Prüfung bei Pull-Requests
aus, die `.surql`-Dateien ändern. Verwendet wird das offizielle SurrealDB Docker-
Image (`ghcr.io/surrealdb/surrealdb:v3.1.5`) mit fester Version.

### DB-gebundene SurrealKit-Tests (Zukunft)

SurrealKit's DB-gebundene Test-Suite (`surrealkit test`, deklarative Permission-
und Schema-Tests gegen eine laufende SurrealDB) bleibt **zukünftiger Scope**
und ist nicht Teil dieser Integration.

## Referenzen

- ADR-002: `knowledge/decisions/ADR-002-context-intelligence-canon.md`
- Issue #3420: GitHub issue (SLICE-02 — SurrealKit Schema Foundation)
- Issue #3430: GitHub issue (SurrealQL Syntax Validation)
- Issue #3418: Meta-Issue (Build SurrealDB-native ContextBrain / VectorGraph)
- Snapshot-Tool: `tools/surrealdb/schema_snapshot.py`
- Schema-Tests: `tests/surrealdb/`
