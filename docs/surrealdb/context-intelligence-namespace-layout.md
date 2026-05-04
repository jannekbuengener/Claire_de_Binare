# CDB Context Intelligence — Namespace/Database Layout (Target Contract)

**Status**: Canonical (Issue #1979)
**Authority**: Issue #1979 / Parent #1976
**Scope**: Target layout definition — not an applied bootstrap
**Guardrail**: trade-capable is NOT a Live-Readiness-Go; Live-Readiness remains NO-GO.

---

## 1. Zweck

Dieses Dokument definiert das verbindliche Namespace-/Database-Layout fuer das
CDB Context Intelligence System (CIS) in SurrealDB. Es ist ein Target Layout Contract —
**kein** produktives Bootstrap, **kein** produktives Apply, **kein** Runtime-Enable.

---

## 2. Nicht-Ziele

- Kein produktives SurrealDB-Bootstrap oder Apply.
- Keine CREATE/USE-Statements in `.surql`-Schema-Drafts.
- Keine Runtime-/Compose-/Service-Aenderung.
- Keine DB- oder Migration-Aenderung.
- Keine Aenderung an `infrastructure/surrealdb/setup.surql`.
- Kein Trading-State, keine Secrets, kein Live-/Echtgeld-Go.

---

## 3. Entscheidung: Ziel-Layout

| Element | Wert | Status |
|---------|------|--------|
| **Namespace** | `cdb` | Target layout (not applied) |
| **Database** | `context_intelligence` | Target layout (not applied) |

### 3.1 Alternative Evaluation

| Option | Namespace | Database | Bewertung |
|--------|-----------|----------|-----------|
| **A (selected)** | `cdb` | `context_intelligence` | **STARK**: Projektname + Domaenenname; erweiterbar fuer weitere DBs unter `cdb/*`; aligniert mit SurrealDB Multi-Tenancy-Idiom; trennt sauber von `governance` |
| B (rejected) | `cdb_context` | `main` | **SCHWACH**: `main` ist generisch und nicht-deskriptiv; `cdb_context` als Namespace ist zu eng fuer zukuenftige CIS-Subdomains; widerspricht SurrealDB NS-Design |

### 3.2 Begruendung fuer Option A

1. **SurrealDB Best Practice**: Namespace = organisatorische Gruppe, Database =
   fachlicher Scope. `cdb` als Projekt-Namespace kann beliebig viele
   Fachdatenbanken aufnehmen (`context_intelligence`, `evidence_fabric`,
   `agent_memory`, etc.).
2. **Erweiterbarkeit**: Zukuenftige CIS-Subdomains (z. B. die `primary_scoped`
   SurrealDB-Domaenen `evidence_fabric` und `agent_memory` aus
   `ownership.yaml`) koennen als eigene Databases unter `cdb/*` angelegt
   werden, ohne top-level Namespace-Sprawl.
3. **Historie**: Der Namespace `cdb` ist bereits historisch belegt (Legacy
   `cdb`/`cdb` in `rollback-cutover-plan.md:42`). Die explizite Wiederaufnahme
   als definierter Target Namespace bereinigt diese Ambiguitaet.
4. **Trennung**: Vollstaendige Namespace-Trennung zum bestehenden
   `governance`/`governance_mirror`. Keine Kollision, keine implizite Reuse,
   keine Cross-NS Queries als Default.

---

## 4. Trennung zum Governance Mirror

| Dimension | Governance Mirror | Context Intelligence |
|-----------|-------------------|---------------------|
| **Namespace** | `governance` | `cdb` |
| **Database** | `governance_mirror` | `context_intelligence` |
| **SurrealDB Role** (ownership.yaml) | `mirror_read_only`, `append_only_mirror` | `mirror_read_only` |
| **Canonical Source** | Git (docs, ledger) | Git (Working Repo Canon) |
| **Writers** | Docs owners, agents via ledger | Context indexer |
| **Readers** | Governance queries, audit analytics | Agents, CDB-MCP |
| **Setup Artefakt** | `infrastructure/surrealdb/setup.surql` | `infrastructure/surrealdb/context_intelligence_v0.surql` (read-only draft) |

### Regeln

- **Kein Namespace-/Database-Reuse**: CIS verwendet ausschliesslich
  `cdb`/`context_intelligence`; der Namespace `governance` und die Database
  `governance_mirror` bleiben dem Governance Mirror vorbehalten.
- **Keine Cross-NS Queries als Default**: Default-Queries operieren innerhalb
  eines Namespaces. Cross-NS-Zugriffe sind nicht vorgesehen und beduerfen
  einer separaten Design-Entscheidung.
- **Keine Migration**: Es werden keine Daten zwischen `governance`/
  `governance_mirror` und `cdb`/`context_intelligence` migriert. Jeder
  Namespace ist ein eigenstaendiger Datenraum.
- **Getrennte Sessions**: Zukuenftig sind getrennte SurrealDB-Sessions oder
  Credentials pro Namespace denkbar, werden aber nicht in diesem Slice
  implementiert.

---

## 5. Naming-Konventionen

Die folgenden Konventionen gelten fuer alle Tabellen, Felder und Records
innerhalb von `cdb`/`context_intelligence`. Sie sind aus dem bestehenden
Schema-Draft `infrastructure/surrealdb/context_intelligence_v0.surql`
abgeleitet und werden hiermit formalisiert.

### 5.1 Table Naming

- **Format**: `snake_case`, semantisch beschreibend
- **Beispiele**: `repo_artifact`, `code_symbol`, `doc_page`, `doc_chunk`,
  `concept`, `dependency_edge`, `evidence_ref`, `claim`, `decision_event`,
  `agent_memory`
- **Regel**: Keine Praefixe, kein Namespacing in Tabellennamen (die NS/DB-
  Hierarchie traegt die organisatorische Trennung)

### 5.2 Relation Naming

- **Deferred to #1982** (Relationship Vocabulary).
- Bestehende Konvention aus dem Schema-Draft: Edge-Tabellen tragen Namen wie
  `dependency_edge`. Dies bleibt kompatibel mit der erwarteten #1982-
  Spezifikation.
- Container-Tabellen (statt expliziter SurrealDB RELATE/GRAPH Edges) sind
  das aktuelle v0-Modell und werden in #1982 bewertet.

### 5.3 Stable IDs (Record Identity)

Jede Tabelle fuehrt zwei Identitaetsebenen:

| Ebene | Format | Beispiel |
|-------|--------|----------|
| SurrealDB Record ID | `<table>:<id>` | `repo_artifact:abc123` |
| Stable ID Field | `*_id` (string, Pflichtfeld) | `artifact_id: "abc123"` |

- Der SurrealDB Record ID ist der kanonische Storage-Level Identifier.
- Das `*_id` String-Feld dient als stabiler, deterministischer Identifier
  fuer Cross-Referenzen und systemuebergreifende Lookups.
- Pflichtfelder sind im Schema-Draft als `REQUIRED(v0-draft)` markiert.

**Stable ID Felder pro Tabelle:**

| Tabelle | Stable ID Feld |
|---------|---------------|
| `repo_artifact` | `artifact_id` |
| `code_symbol` | `symbol_id` |
| `doc_page` | `page_id` |
| `doc_section` | `section_id` |
| `doc_chunk` | `chunk_id` |
| `concept` | `concept_id` |
| `dependency_edge` | `edge_id` |
| `evidence_ref` | `evidence_id` |
| `claim` | `claim_id` |
| `decision_event` | `decision_id` |
| `agent_memory` | `memory_id` |
| `audit_observation` | `observation_id` |
| `contradiction` | `contradiction_id` |
| `stale_context` | `stale_id` |
| `scope_drift_event` | `drift_id` |
| `knowledge_quality_score` | `score_id` |

### 5.4 Hash-Feld Konventionen

| Feld | Verwendung | Beispiel-Tabellen |
|------|-----------|-------------------|
| `source_hash` | Hash des Quellartefakts (Git File/Blob) | `repo_artifact`, `doc_page`, `doc_section`, `doc_chunk`, `code_symbol`, `evidence_ref` |
| `content_hash` | Hash des ingestierten Chunk-Inhalts | `doc_chunk` |
| `integrity_hash` | Governance-/Audit-Integritaets-Hash | (Governance Mirror Tabellen; in CIS nur bei Bedarf) |

Regel: Jedes CIS-Record MUSS mindestens `source_hash` fuehren, wenn es aus
einem Git-Artefakt stammt. Records ohne `source_hash` sind Drift (vgl.
`ownership.yaml` Drift Rule `missing_source_hash`).

### 5.5 Source-Feld Konventionen

| Feld | Typ | Semantik |
|------|-----|---------|
| `source_path` | `string` | Pfad im Git Working Repo |
| `source_commit` | `string` | Git Commit SHA |
| `source_url` | `string` | Optional: GitHub URL zum Artefakt |

### 5.6 Zeitfeld Konventionen

| Feld | Typ | Semantik |
|------|-----|---------|
| `created_at` | `datetime` | **Pflichtfeld** nach v0 Producer-/Validator-Contract; der aktuelle Schema-Draft deklariert `VALUE $value OR time::now()`, ohne produktives Apply durch diesen Slice. |
| `observed_at` | `datetime` | Letzte Beobachtung des Quellartefakts |
| `collected_at` | `datetime` | Zeitpunkt der Evidence-Erhebung |
| `detected_at` | `datetime` | Zeitpunkt der Anomalie-/Drift-/Contradiction-Erkennung |
| `computed_at` | `datetime` | Zeitpunkt der Berechnung (z. B. `knowledge_quality_score`) |

Regel: `created_at` ist in jeder CIS-Tabelle ein Pflichtfeld des
Producer-/Validator-Contracts. #1979 aendert keine Enforcement-, ASSERT-,
DEFAULT- oder Runtime-Semantik.

---

## 6. Bootstrap-/Rollback-/Rebuild-Konzept

**Status**: Konzeptionell, **nicht** von diesem Slice angewandt.

Die folgenden Statements sind illustrative Beispiele fuer einen zukuenftigen
Bootstrap. Sie werden **nicht** in `.surql`-Dateien geschrieben und **nicht**
gegen eine produktive SurrealDB-Instanz ausgefuehrt.

### 6.1 Illustrative Bootstrap (future, not applied)

```surql
-- Target namespace + database for CDB Context Intelligence
-- (illustrative; not executed by this PR)
CREATE NS cdb;
USE NS cdb;
CREATE DATABASE context_intelligence;
USE DATABASE context_intelligence;

-- Schema aus context_intelligence_v0.surql laden
-- (DEFINE TABLE statements apply after USE DATABASE)
```

### 6.2 Rollback (conceptual)

```surql
-- CIS komplett entfernen, keine Auswirkung auf governance/governance_mirror
USE NS cdb;
REMOVE DATABASE context_intelligence;
```

- `surrealdb_enabled: false` in `feature-flags.yaml` deaktiviert alle
  CIS-Reads (Feature-Flag umfasst die gesamte SurrealDB-Instanz).
- Gleiche Logik wie bestehender Rollback-Plan
  (`rollback-cutover-plan.md:14-17`).

### 6.3 Rebuild (conceptual)

```surql
REMOVE DATABASE context_intelligence;
CREATE DATABASE context_intelligence;
-- Re-Apply context_intelligence_v0.surql
-- Re-Ingestion aus Git (deterministisch via source-hash)
```

### 6.4 Prinzipien

- **Zero Data Loss**: CIS ist ein mirror; alle Primaerdaten liegen in Git.
- **Deterministisch**: Re-Ingestion via `source_hash` reproduziert
  identischen Zustand (CDB_CONSTITUTION §2).
- **Kein Impact auf Trading-Runtime**: CIS laeuft parallel; SurrealDB ist
  Sidecar.
- **Kein Impact auf Governance Mirror**: `REMOVE DATABASE context_intelligence`
  tangiert `governance`/`governance_mirror` nicht.

---

## 7. Verhaeltnis zu anderen Artefakten

| Artefakt | Beziehung |
|----------|-----------|
| `infrastructure/config/surrealdb/ownership.yaml` | Definiert die Domain-Ownership; CIS ist `context_intelligence`-Domain |
| `docs/surrealdb/data-ownership-matrix.md` | Matrix bestaetigt `mirror_read_only` Rolle |
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Schema-Draft; bewusst NS/DB-frei laut Header-Guardrails |
| `infrastructure/surrealdb/setup.surql` | Governance Mirror Bootstrap (`governance`/`governance_mirror`); unveraendert |
| `docs/surrealdb/context-intelligence-system.md` | Architekturdokument (verweist auf dieses Layout) |
| `docs/surrealdb/rollback-cutover-plan.md` | Ergaenzt um CIS-Target-Layout Abschnitt |

---

## 8. Guardrails

- **Kein produktives Apply**: Dieses Dokument ist ein Target Contract, keine
  Migration.
- **Kein SurrealDB-Bootstrap**: NS/DB werden nicht erstellt.
- **Keine `.surql`-Aenderung**: `context_intelligence_v0.surql` behaelt
  explizit "no bootstrap (NS/DB)".
- **Kein Eingriff in Governance Mirror**: `governance`/`governance_mirror`
  bleiben unveraendert.
- **Kein Live-/Echtgeld-Go**: Stage `trade-capable` ist kein LR-Go.
- **Keine Runtime-/Compose-/Service-Aenderung**.

---

## Provenance / Quellen

- **Issue**: #1979
- **Parent**: #1976
- **Dependencies**: #1977 (Vision), #1978 (Ownership Boundaries)
- **Referenz-Dokumente**:
  - `infrastructure/config/surrealdb/ownership.yaml`
  - `docs/surrealdb/data-ownership-matrix.md`
  - `infrastructure/surrealdb/context_intelligence_v0.surql`
  - `infrastructure/surrealdb/setup.surql`
  - `docs/surrealdb/context-intelligence-system.md`
  - `docs/surrealdb/rollback-cutover-plan.md`
