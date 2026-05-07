# CDB Context Intelligence — Core Schema Reference v1

**Status**: Draft (Wave 1 Reconcile)
**Authority**: Issue #1981 / Parent #1976
**Schema Implementation**: `infrastructure/surrealdb/context_intelligence_v0.surql`
**Dependencies**: #1977 (target vision), #1978 (ownership), #1979 (namespace layout), #1980 (ontology)
**Guardrail**: trade-capable is NOT a Live-Readiness-Go; Live-Readiness remains NO-GO.

---

## 1. Zweck

Dieses Dokument ist die **narrative Schema Reference** für die Core Collections des CDB Context
Intelligence Systems (CIS). Es beschreibt alle Collections, deren Felder, ID-Konvention,
Ownership-Annahmen und Guardrails in lesbarer Form.

Das eigentliche Schema-Draft-Artefakt ist das SurrealQL-Dokument unter
`infrastructure/surrealdb/context_intelligence_v0.surql`. Dieses Dokument ergänzt es mit
fachlichem Kontext und Ownership-Regeln, die bewusst nicht im `.surql`-Draft kodiert werden.

---

## 2. Scope und Nicht-Ziele

**Scope**:
- Narrative Referenz der 10 Core Collections aus #1981
- Feldbeschreibungen, ID-Konvention, Source-/Hash-/Time-/Confidence-Felder
- Ownership-/Permission-Annahmen dokumentiert

**Nicht-Ziele**:
- Kein produktives SurrealDB-Apply oder Schema-Migration
- Kein NS/DB-Bootstrap (CREATE/USE)
- Keine PERMISSIONS-Durchsetzung in SurrealDB (bewusst nicht im Draft)
- Keine Ingestion-Implementierung
- Keine Context-Indexer-Implementierung
- Keine MCP-Tool-Implementierung
- Kein Trading-State, keine Orders, keine Positions, keine Fills
- Keine Secrets, keine Broker-Credentials, keine API-Keys
- Keine Runtime-Änderung
- Kein Live-Readiness-Upgrade
- Kein Echtgeld-Go

---

## 3. Globale Konventionen

### 3.1 Record Identity

Jede Collection hat zwei komplementäre Identifier:

| Identifier | Typ | Zweck |
|---|---|---|
| SurrealDB Record ID (`repo_artifact:<id>`) | Interne Storage ID | Kanonisch auf Storage-Ebene |
| `*_id` Feld (z. B. `artifact_id: string`) | Stabile externe String-ID | Deterministische IDs, Cross-System-Referenzen |

Die `*_id` Felder ermöglichen reproduzierbare IDs außerhalb von SurrealDB (z. B. aus Git-Hashes
oder konventionierten Präfixen).

### 3.2 Zeitfelder

| Feld | Typ | Regel |
|---|---|---|
| `created_at` | `datetime` | **Pflichtfeld** für alle Collections (v0-Draft-Konvention) |
| `observed_at` | `datetime` | Domain-spezifisch: wann wurde das Objekt extern beobachtet |
| `collected_at` | `datetime` | Domain-spezifisch: wann wurde das Objekt ingestiert |
| `detected_at` | `datetime` | Domain-spezifisch: wann wurde ein Befund erkannt |
| `expires_at` | `datetime` | Domain-spezifisch: agent_memory TTL-Grenze |

### 3.3 Provenance- und Evidenzfelder

| Feld | Typ | Zweck |
|---|---|---|
| `source_path` | `string` | Relativer Pfad im Working Repo |
| `source_url` | `string` | URL (z. B. GitHub Raw, Blob) |
| `source_commit` | `string` | Git Commit SHA (kurz oder lang) |
| `source_hash` | `string` | Content Hash (SHA-256 oder SHA-1) |
| `integrity_algo` | `string` | Hash-Algorithmus (z. B. `sha256`) |
| `confidence` | `float` | Vertrauenswert [0.0–1.0] |
| `freshness` | `string` | Stale-Indikator (`fresh`, `stale`, `unknown`) |

### 3.4 Pflichtfeld-Semantik

Der Draft markiert Pflichtfelder als `-- REQUIRED(v0-draft)`. Diese Markierung ist
dokumentarisch — keine technische Enforcement via `ASSERT` oder `DEFAULT` im Draft.
Enforcement erfolgt in Producer-/Validator-Logik in späteren Wellen.

---

## 4. Collections (Core)

### 4.1 `repo_artifact`

**Zweck**: Versionierte Dateien oder Artefakte im Working Repo.

**Schlüsselfelder**:

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `artifact_id` | `string` | ✅ | Stabile externe ID (z. B. `repo:<commit>:<path>`) |
| `artifact_type` | `string` | | Typ (z. B. `markdown`, `python`, `yaml`, `surql`) |
| `source_path` | `string` | | Repo-relativer Pfad |
| `source_url` | `string` | | GitHub Blob URL |
| `source_commit` | `string` | | Git Commit SHA |
| `source_hash` | `string` | | Content Hash |
| `integrity_algo` | `string` | | Hash-Algorithmus |
| `size_bytes` | `int` | | Dateigrößen in Bytes |
| `mime_type` | `string` | | MIME Type |
| `observed_at` | `datetime` | | Beobachtungszeitpunkt |
| `freshness` | `string` | | Frische-Indikator |
| `confidence` | `float` | | Vertrauenswert |
| `created_at` | `datetime` | ✅ | Indexierungszeitpunkt |
| `comment` | `string` | | Freitext |

**Indexes**: `artifact_id` (UNIQUE), `source_path`, `source_hash`, `created_at`

---

### 4.2 `code_symbol`

**Zweck**: Statisch extrahierte Code-Symbole (Klassen, Funktionen, Typen, Konstanten).

**Schlüsselfelder**:

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `symbol_id` | `string` | ✅ | Stabile externe ID |
| `language` | `string` | | Programmiersprache (z. B. `python`) |
| `symbol_kind` | `string` | | Art (z. B. `class`, `function`, `constant`) |
| `qualified_name` | `string` | | Vollqualifizierter Name (z. B. `core.risk.RiskManager`) |
| `name` | `string` | | Kurzname |
| `file_path` | `string` | | Quelldatei-Pfad |
| `span_start_line` | `int` | | Startzeile |
| `span_end_line` | `int` | | Endzeile |
| `source_hash` | `string` | | Datei-Content-Hash |
| `source_commit` | `string` | | Git Commit SHA |
| `confidence` | `float` | | Vertrauenswert |
| `created_at` | `datetime` | ✅ | Indexierungszeitpunkt |
| `comment` | `string` | | Freitext |

**Indexes**: `symbol_id` (UNIQUE), `qualified_name`, `file_path`, `created_at`

---

### 4.3 `doc_page`

**Zweck**: Eine vollständige Markdown-Dokumentationsseite.

**Schlüsselfelder**:

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `page_id` | `string` | ✅ | Stabile externe ID |
| `source_path` | `string` | | Repo-relativer Pfad |
| `source_url` | `string` | | GitHub Blob URL |
| `source_commit` | `string` | | Git Commit SHA |
| `source_hash` | `string` | | Content Hash |
| `title` | `string` | | Dokumententitel |
| `doc_format` | `string` | | Format (z. B. `markdown`) |
| `observed_at` | `datetime` | | Beobachtungszeitpunkt |
| `freshness` | `string` | | Frische-Indikator |
| `confidence` | `float` | | Vertrauenswert |
| `created_at` | `datetime` | ✅ | Indexierungszeitpunkt |
| `comment` | `string` | | Freitext |

**Indexes**: `page_id` (UNIQUE), `source_path`, `source_hash`, `created_at`

---

### 4.4 `doc_section`

**Zweck**: Ein Heading-gebundener Abschnitt innerhalb einer `doc_page`.

**Schlüsselfelder**:

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `section_id` | `string` | ✅ | Stabile externe ID |
| `page_ref` | `record` | | Referenz auf übergeordnete `doc_page` |
| `heading` | `string` | | Überschrift des Abschnitts |
| `heading_path` | `array` | | Hierarchiepfad (z. B. `["3. Arch", "3.1 SurrealDB"]`) |
| `section_index` | `int` | | Position im Dokument |
| `span_start_line` | `int` | | Startzeile |
| `span_end_line` | `int` | | Endzeile |
| `source_hash` | `string` | | Abschnitts-Content-Hash |
| `confidence` | `float` | | Vertrauenswert |
| `created_at` | `datetime` | ✅ | Indexierungszeitpunkt |
| `comment` | `string` | | Freitext |

**Indexes**: `section_id` (UNIQUE), `page_ref`, `created_at`

---

### 4.5 `doc_chunk`

**Zweck**: Token-dimensionierter Content-Chunk für Retrieval, abgeleitet aus `doc_page`/`doc_section`.

**Schlüsselfelder**:

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `chunk_id` | `string` | ✅ | Stabile externe ID |
| `page_ref` | `record` | | Referenz auf übergeordnete `doc_page` |
| `section_ref` | `record` | | Referenz auf übergeordnete `doc_section` |
| `chunk_index` | `int` | | Position innerhalb der Seite/Section |
| `content` | `string` | | Text-Content des Chunks |
| `content_hash` | `string` | | SHA-Hash des Content-Strings |
| `tokens_estimate` | `int` | | Geschätzte Token-Anzahl |
| `source_hash` | `string` | | Quelldatei-Hash |
| `confidence` | `float` | | Vertrauenswert |
| `created_at` | `datetime` | ✅ | Indexierungszeitpunkt |
| `comment` | `string` | | Freitext |

**Indexes**: `chunk_id` (UNIQUE), `page_ref`, `section_ref`, `content_hash`, `created_at`

---

### 4.6 `concept`

**Zweck**: Ein abstraktes Domänen-Konzept aus der CDB-Ontologie.

**Schlüsselfelder**:

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `concept_id` | `string` | ✅ | Stabile externe ID |
| `name` | `string` | | Kanonischer Name |
| `description` | `string` | | Definition/Beschreibung |
| `tags` | `array` | | Tags |
| `source_refs` | `array` | | Quellreferenzen |
| `evidence_refs` | `array` | | Evidenzreferenzen |
| `freshness` | `string` | | Frische-Indikator |
| `confidence` | `float` | | Vertrauenswert |
| `created_at` | `datetime` | ✅ | Indexierungszeitpunkt |
| `comment` | `string` | | Freitext |

**Indexes**: `concept_id` (UNIQUE), `name`, `created_at`

---

### 4.7 `decision_event`

**Zweck**: Eine aufgezeichnete Architektur- oder Governance-Entscheidung mit Begründung.

**Schlüsselfelder**:

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `decision_id` | `string` | ✅ | Stabile externe ID |
| `ledger_source` | `string` | ✅ | Ledger-Quellpfad (Git-Pfad + Commit-SHA). Pflicht per `ownership.yaml` Drift-Regel `ledger_link_missing`. |
| `event_id` | `string` | ✅ | Eindeutige Ledger-Event-ID. Pflicht per `ownership.yaml` Drift-Regel `ledger_link_missing`. |
| `title` | `string` | | Entscheidungstitel |
| `question` | `string` | | Entscheidungsfrage |
| `answer` | `string` | | Entscheidung |
| `decision_type` | `string` | | Typ (z. B. `architecture`, `governance`, `policy`) |
| `status` | `string` | | Status (z. B. `active`, `superseded`, `invalidated`) |
| `scope` | `string` | | Geltungsbereich |
| `evidence_refs` | `array` | ✅ | Evidenzreferenzen mit Ledger-Provenance. Pflicht per `ownership.yaml` Drift-Regel `missing_evidence_ref`. |
| `claim_refs` | `array` | | Verknüpfte Claims |
| `affected_artifacts` | `array` | | Betroffene Artefakte |
| `agent` | `string` | | Erstellender Agent |
| `human_go` | `bool` | | Wurde Human-GO erteilt? |
| `confidence` | `float` | | Vertrauenswert |
| `superseded_by` | `string` | | ID der nachfolgenden Entscheidung |
| `invalidated_by` | `string` | | ID der invalidierenden Entscheidung |
| `uncertainty` | `string` | | Dokumentierte Restunsicherheit |
| `created_at` | `datetime` | ✅ | Aufzeichnungszeitpunkt |
| `comment` | `string` | | Freitext |

**Indexes**: `decision_id` (UNIQUE), `status`, `created_at`

---

### 4.8 `evidence_ref`

**Zweck**: Referenz auf ein Evidenz-Artefakt (CI-Run, Commit, Log, Report).

**Schlüsselfelder**:

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `evidence_id` | `string` | ✅ | Stabile externe ID |
| `evidence_type` | `string` | | Typ (z. B. `ci_run`, `commit`, `log`, `report`) |
| `source_path` | `string` | | Repo-relativer Pfad |
| `source_url` | `string` | | URL des Evidenz-Artefakts |
| `source_hash` | `string` | | Content Hash |
| `source_commit` | `string` | | Git Commit SHA |
| `collected_at` | `datetime` | | Sammelzeitpunkt |
| `observed_by` | `string` | | Erfassender Agent/Service |
| `freshness` | `string` | | Frische-Indikator |
| `confidence` | `float` | | Vertrauenswert |
| `validates` | `array` | | IDs der durch diese Evidenz validierten Objekte |
| `invalidates` | `array` | | IDs der durch diese Evidenz invalidierten Objekte |
| `related_artifacts` | `array` | | Verknüpfte Artefakt-IDs |
| `related_decisions` | `array` | | Verknüpfte Entscheidungs-IDs |
| `created_at` | `datetime` | ✅ | Indexierungszeitpunkt |
| `comment` | `string` | | Freitext |

**Indexes**: `evidence_id` (UNIQUE), `source_path`, `source_hash`, `collected_at`, `created_at`

---

### 4.9 `agent_memory`

**Zweck**: Scoped Memory-Eintrag eines Agenten. Schema-only — aktiviert keine Memory-Writes.

**Schlüsselfelder**:

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `memory_id` | `string` | ✅ | Stabile externe ID |
| `scope` | `string` | ✅ | Agent-Scope-Identifier (z. B. `agent:OPENCODE/copilot`) |
| `namespace` | `string` | ✅ | Namespace (z. B. `session`, `project`, `governance`) |
| `memory_type` | `string` | | Typ (siehe scoped-agent-memory-model-v1.md) |
| `content` | `string` | | Memory-Inhalt |
| `source_refs` | `array` | | Quellreferenzen |
| `evidence_refs` | `array` | | Evidenzreferenzen |
| `confidence` | `float` | | Vertrauenswert [0.0–1.0] |
| `ttl` | `int` | | Time-to-Live in Sekunden |
| `expires_at` | `datetime` | | Ablaufzeitpunkt |
| `stale_after` | `int` | | Stale-Schwelle in Sekunden |
| `superseded_by` | `string` | | ID des ersetzenden Memory-Eintrags |
| `created_by` | `string` | ✅ | Agent ID des Erstellers |
| `created_at` | `datetime` | ✅ | Erstellungszeitpunkt |
| `comment` | `string` | | Freitext |

**Indexes**: `memory_id` (UNIQUE), `scope`, `namespace`, `created_at`

Für vollständige Memory-Typen, Write-/TTL-/Supersede-/Stale-Regeln und Abgrenzung zu
`shared_memory` siehe [`docs/surrealdb/scoped-agent-memory-model-v1.md`](scoped-agent-memory-model-v1.md).

---

### 4.10 `context_query`

**Zweck**: Aufgezeichnete Context-Query eines Agenten (Audit-Trail, Retrieval-Log).

**Schlüsselfelder**:

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `query_id` | `string` | ✅ | Stabile externe ID |
| `query_type` | `string` | | Typ (z. B. `symbol_lookup`, `doc_search`, `evidence_resolve`) |
| `query_text` | `string` | | Query-String oder -Beschreibung |
| `context_refs` | `array` | | Referenzierte Context-Objekte |
| `confidence` | `float` | | Vertrauenswert des Ergebnisses |
| `created_at` | `datetime` | ✅ | Abfragezeitpunkt |
| `comment` | `string` | | Freitext |

**Indexes**: `query_id` (UNIQUE), `query_type`, `created_at`

> **Hinweis**: `context_query` ist im Schema-Draft `context_intelligence_v0.surql` vorhanden.
> Ein früherer Issue-Comment (#1981) hatte es als fehlend markiert — das war eine Fehleinschätzung
> auf Basis einer unvollständigen Sichtprüfung.

---

## 5. Ownership-Annahmen

Diese Ownership-Regeln ergänzen das Schema-Draft und werden **nicht** im `.surql`-Draft als
PERMISSIONS kodiert. Enforcement erfolgt durch Producer-/Validator-Logik und die kanonische
`infrastructure/config/surrealdb/ownership.yaml`.

| Collection | Canonical Source | SurrealDB Role | Writer | Reader |
|---|---|---|---|---|
| `repo_artifact` | Git (Working Repo) | `mirror_read_only` | Context Indexer | Agents, CDB-MCP |
| `code_symbol` | Git (Working Repo) | `mirror_read_only` | Context Indexer | Agents, CDB-MCP |
| `doc_page` | Git (Working Repo) | `mirror_read_only` | Context Indexer | Agents, CDB-MCP |
| `doc_section` | Git (Working Repo) | `mirror_read_only` | Context Indexer | Agents, CDB-MCP |
| `doc_chunk` | Git (Working Repo) | `mirror_read_only` | Context Indexer | Agents, CDB-MCP |
| `concept` | Git (Working Repo) | `mirror_read_only` | Context Indexer | Agents, CDB-MCP |
| `decision_event` | Git (Ledger) | `append_only_mirror` | Agents via Ledger | Agents, Audit |
| `evidence_ref` | Git (Ledger) + Indexer | `primary_scoped` | Context Indexer | Agents, CDB-MCP, Audit |
| `agent_memory` | SurrealDB | `primary_scoped` | Agent (scoped) | Agent (scoped) |
| `context_query` | SurrealDB | `primary_scoped` | Agents | Agents, Audit |

**Ownership-Regeln (unbedingt)**:
- Kein direkter Agent-Write auf `mirror_read_only` Collections.
- `agent_memory` writes nur scoped: `agent_id` + `namespace` — kein unscoped global write.
- Kein Cross-Agent-Write ohne explizites Human-GO.
- Git/Repo bleibt einzige SSoT für alle Mirror-Collections.

---

## 6. Verbotene Felder und Klassen

Folgende Felder und Datenklassen sind in **allen** Collections verboten:

| Kategorie | Beispiele |
|---|---|
| **Trading-State** | `order_id`, `position_id`, `fill_id`, `balance`, `risk_exposure` |
| **Secrets** | `api_key`, `password`, `private_key`, `broker_token`, `credential` |
| **Live Risk State** | `drawdown_live`, `pnl_live`, `margin_used_live` |
| **PII** | Private Daten jenseits öffentlicher Repo-Metadaten |

Jedes Schema-Artefakt, das eines dieser Felder enthält, ist ungültig und muss vor
dem Import abgelehnt werden.

---

## 7. Namespace/Database Target

Alle Collections operieren im Target-Namespace/-Database:

- **Namespace**: `cdb`
- **Database**: `context_intelligence`

Dies ist ein Target-Layout-Contract — kein produktiver Bootstrap. Vollständige
Spezifikation in [`docs/surrealdb/context-intelligence-namespace-layout.md`](context-intelligence-namespace-layout.md).

---

## 8. Beziehungen zwischen Collections

Komplexe Relationen werden in Welle 3+ über die `dependency_edge`-Collection und das
Relationship Vocabulary ([`docs/surrealdb/context-relationship-vocabulary-v0.md`](context-relationship-vocabulary-v0.md))
ausgedrückt. Dieser Schema-v1-Draft erzwingt **keine** komplexen Relationen.

Interne Referenzen verwenden `record`-Typ-Felder (z. B. `page_ref ON doc_section`).

---

## 9. Implementierungshinweis

Das Schema-Draft-Artefakt (`context_intelligence_v0.surql`) vermeidet bewusst:
- `USE NS` / `USE DB` Statements (kein produktives Bootstrap)
- `PERMISSIONS` Definitionen (Enforcement via Logik, nicht DB-Layer in v0)
- `ASSERT` / `DEFAULT` Enforcement-Constraints (Pflichtfelder via Producer-Logik)

Diese Entscheidungen gelten für v0. Spätere Wellen können Enforcement-Constraints ergänzen,
wenn die Producer-/Validator-Logik klar definiert und testbar ist.

---

## 10. Guardrails (Zusammenfassung)

| # | Guardrail | Status |
|---|---|---|
| G1 | Kein Trading-State in Collections | ✅ |
| G2 | Keine Secrets in Collections | ✅ |
| G3 | Kein Live-Readiness-Go | ✅ |
| G4 | Kein Echtgeld-Go | ✅ |
| G5 | Keine Runtime-Änderung | ✅ |
| G6 | Keine autonome Freigabe ohne Human-GO | ✅ |
| G7 | Board-Stage ≠ LR-Go | ✅ |
| G8 | Kein produktives Schema-Apply | ✅ |
| G9 | Git/Repo ist SSoT für Mirror-Collections | ✅ |
| G10 | Source-Hash-Pflicht für alle Mirror-Records | ✅ |

---

## Quellen / Provenance

| Quelle | Typ | Status |
|---|---|---|
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Schema Draft | PRESENT |
| `infrastructure/config/surrealdb/ownership.yaml` | Ownership YAML | PRESENT |
| `docs/surrealdb/context-intelligence-system.md` | Architektur | PRESENT |
| `docs/surrealdb/context-intelligence-namespace-layout.md` | Namespace Layout | PRESENT |
| `docs/surrealdb/scoped-agent-memory-model-v1.md` | Memory Model | PRESENT |
| `docs/surrealdb/data-ownership-matrix.md` | Ownership Narrative | PRESENT |
| Issue #1981 | Authority | OPEN |
| Epic #1976 | Parent | OPEN |
