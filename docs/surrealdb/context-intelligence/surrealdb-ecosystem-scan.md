# SurrealDB Ecosystem Scan for CDB Context Intelligence

## Kontext

Dieses Research-/Decision-Artefakt dokumentiert den engen SurrealDB-Ecosystem-Scan aus Issue #2252. Es ergaenzt #2251, ohne dessen Scope zu duplizieren, und dient als Entscheidungsinput fuer das CDB Context Intelligence System aus #1976.

Dieses Dokument ist keine Dependency-Freigabe, keine Runtime-Freigabe, keine DB-Write-Freigabe und keine Live-Readiness- oder Echtgeld-Ableitung.

## Scope-Abgrenzung

#2251 bewertet generische Referenzquellen. #2252 bewertet SurrealDB-native und SurrealDB-nahe Ecosystem-Quellen fuer Architektur-, SDK-, Retrieval-, MCP-, Migration-, Docs- und Control-Room-Patterns.

Nicht analysiert und nicht erneut bewertet wurden:

- `the-book-of-secret-knowledge`
- `awesome-python`
- generische Security-, Ops- oder Python-Kataloge ausserhalb des #2252-SurrealDB-Scope

## Gelesene Quellen

Primaere Quellen:

- `surrealdb/surrealdb`
- `surrealdb/surrealdb.py`
- `surrealdb/langchain-surrealdb`
- `surrealdb/kaig`

Sekundaere Quellen:

- `surrealdb/examples`
- `surrealdb/docs.surrealdb.com`
- `surrealdb/surrealist`
- `surrealdb/awesome-surreal`
- `smig`
- `surrealdb-migrations`
- `surreal-mcp`
- `surrealmcp`
- `surrealkit`

## Entscheidungsmatrix

| Quelle | Klasse | CDB-Welle/Issues | Konkreter Nutzen | Uebernehmbares Pattern | Nicht uebernehmen | Risiko | Empfehlung |
|---|---|---|---|---|---|---|---|
| `surrealdb/surrealdb` | Engine-/SurrealQL-Wahrheit | #1976, #2079-#2090, #2103-#2128, #2197-#2205 | Belegt native Faehigkeiten fuer HNSW, MTREE, vector KNN, BM25 Analyzer, RELATE und Graph-Verhalten. | Engine-Testmuster als Referenz fuer read-only Query- und Retrieval-Tests nutzen. | Keine Engine-Internals vendoren oder Runtime-Semantik aus Tests direkt uebernehmen. | Version-/Semantikdrift zwischen lokalem Stand und spaeterer Runtime moeglich. | P1: als kanonische Referenz- und Testkorpusquelle nutzen. |
| `surrealdb/surrealdb.py` | Python-SDK / lokale Tooling-Anbindung | #2079-#2090, #2091-#2102 | Bietet Query-, Select-, Create-, Update-, Delete-, Insert-, Relation- und Live-Query-Oberflaechen fuer Python-Anbindung. | CDB-eigener Wrapper mit allowlisted SELECT/read-only metadata queries, Statement Classification und deny-by-default Mutationsblock. | SDK nicht roh an Agenten oder MCP durchreichen; keine raw Mutation Statements ohne Human-GO. | Vollstaendige CRUD-/raw-query Surface; ohne Wrapper zu breit fuer CDB Context Layer. | P0: nur ueber CDB-read-only Wrapper nutzen. |
| `surrealdb/langchain-surrealdb` | Retrieval / Vector Store | #2103-#2128, #2079-#2090 | Zeigt MTREE-Index mit COSINE und F32, `vector::distance::knn()`, Score Thresholds und Metadata Filters. | Query-Shape fuer vector retrieval, Score-Filtering und Metadata-Filter als Pattern. | `add_documents` und `delete` nicht uebernehmen; keine direkte Dependency-Freigabe. | Write/Delete-Surface im VectorStore; LangChain-Abhaengigkeits- und Scope-Risiko. | P1: Retrieval-Pattern nutzen, nicht als Dependency adoptieren. |
| `surrealdb/kaig` | Knowledge-AI / Graph-RAG / Agent Memory | #2103-#2128, #2091-#2102 | Zeigt `embed_and_insert`, vector search, graph relation insertion und recursive graph querying. | Graph-RAG- und Memory-Patterns fuer Hybrid Retrieval und Traversal. | Write-heavy Ingestion, Relation-Inserts und experimentelle Runtime nicht uebernehmen. | Breite write surface, experimenteller Charakter, unklarer Maintenance-Fit. | P1: als Pattern-Katalog nutzen, nicht als Dependency. |
| `surrealdb/examples` | Beispiele / Testkorpus | #2079-#2090, #2103-#2128, #2197-#2205 | `examples/vector-search` zeigt BM25 + MTREE + vector similarity praktisch. | Kleine fixture-nahe Query-Slices fuer Hybrid BM25 + Vector Tests. | Keine grossen Datenbestaende ungeprueft kopieren; keine externen Embedding-Calls in CDB-Tests. | Beispiel-Daten koennen zu gross oder write-lastig sein. | P1: als selektiver Testkorpus und Query-Referenz nutzen. |
| `surrealdb/docs.surrealdb.com` | Docs-/Evidence-/Chunking-Quelle | #1976, #2103-#2128 | Dokumentiert RELATE-Semantik inklusive Caveat: RELATE kann Edges zu nicht existierenden Records erzeugen, wenn nicht per Schema Constraints gegated. | Docs-Chunks als Evidence- und Retrieval-Korpus; RELATE-Caveat als Guardrail fuer Graph-Kontext. | Keine Docs ungeprueft als Runtime-Wahrheit fuer andere Versionen behandeln. | Versionierung und Doc-Stand muessen spaeter explizit festgehalten werden. | P1: fuer Evidence-Chunks und Guardrail-Wording nutzen. |
| `surrealdb/surrealist` | UI / Control Room | #2145-#2205, #2197-#2205 | Referenz fuer Schema Visibility, Query Formatting/Validation, Dataset Apply und Schema Refresh. | UI-Workflow-Patterns: Schema-Zugriffsanzeige, Table Names, Value Formatter/Validator, Schema Refresh nach Apply. | Dataset Apply nicht als CDB-Abhaengigkeit oder Write-Pfad uebernehmen. | Dataset Apply ist write-faehig; UI-Code ist nicht automatisch passend fuer CDB. | P2: als Control-Room-Inspiration nutzen, nicht als Dependency. |
| `surrealdb/awesome-surreal` | Ecosystem Discovery | #2252, #1976 | Zeigt relevante Ecosystem-Kategorien fuer Surrealist, LangChain, MCP, Migration und AI Docs Retrieval. | Discovery-Index fuer spaetere gezielte Quellenpruefung. | Keine ungepruefte Uebernahme gelisteter Projekte. | Katalog kann veraltet sein; Eintraege sind keine Qualitaetsfreigabe. | P2: als Beobachtungs-/Discovery-Surface nutzen. |
| `surreal-mcp` | External MCP / Agent Tooling | #2091-#2102 | Community-MCP mit Tool-Surface fuer `query`, `create`, `update`, `delete`, `merge`, `patch`, `upsert`, `insert`, `relate`. | MCP-Tool-Katalog als Negativ-/Guardrail-Referenz fuer CDB-read-only Contracts. | Write-faehige Tools und raw SurrealQL nicht uebernehmen. | Hohe Write-/Delete-Surface; keine CDB-Governance-Gates. | P0: Architekturreferenz, keine direkte Dependency. |
| `surrealmcp` | External MCP / offizielle MCP-Referenz | #2091-#2102 | Enthalten sind raw SurrealQL, `insert`, `create`, `upsert`, `update`, `delete`, `relate`, Cloud-/Endpoint-Mutationen und Metrics. | Statement Classification, deny-by-default Write Gates, Human-GO und read-only Tool-Allowlist als CDB-Anforderung ableiten. | Raw SurrealQL, Cloud-/Endpoint-Mutationen, delete/update/create/upsert/relate nicht uebernehmen. | Sehr breite Agent- und Cloud-Mutationssurface; ohne CDB-Gates ungeeignet. | P0: Risiko-/Pattern-Katalog, keine direkte Dependency. |
| `surrealkit` | Migration / Schema Governance | #2197-#2205, #2067-#2078 | Zeigt dry-run sync, prune guardrails, rollout locks, status, start/complete/rollback phases und schema hash checks. | Dry-run, active rollout lock, schema hash/status, shared-db prune refusal und explizite Rollout-Phasen. | Keine direkte Tool-Adoption ohne separate Lizenz-/Maintenance-/Fit-Entscheidung. | Migrations-/Schema-Tool kann destruktiv sein; separate Governance noetig. | P1: Rollout-Konzepte uebernehmen, nicht direkt freigeben. |
| `smig` | Migration / Schema Diffing | #2197-#2205, #2067-#2078 | Zeigt schema diffing, `_migrations` tracking, checksum/down-checksum und rollback integrity checks. | Integrity-Checks fuer Up/Down-Migrationen, Status-Tracking, Rollback-Verifikation. | Auto-generierte migrations nicht ungeprueft in CDB uebernehmen. | Owner-/Maintenance-Fit unklar; Generation kann semantisch riskant sein. | P1: Konzepte fuer Checksums und Rollback-Integrity adaptieren. |
| `surrealdb-migrations` | Migration / historisches Tool | #2197-#2205, #2067-#2078 | Zeigt dry-run via transaction rollback, checksum validation und version-order validation. | Dry-run als transaction rollback, checksum/version-order gates. | Nicht als neue Dependency empfehlen; Projekt ist archived/abgeloest zugunsten Surrealkit. | Archived/Maintenance-Risiko; Tooling kann DB-mutierend sein. | P2: historische Referenz, keine Dependency. |

## Priorisierte Empfehlungen

### P0

- Fuer #2091-#2102 MCP Bridge: CDB-native read-only MCP Tool Contracts zuerst definieren; externe MCP-Server nicht direkt adoptieren.
- Fuer #2079-#2090 Context Query CLI: `surrealdb.py` nur ueber CDB Wrapper nutzen; Default nur SELECT/read-only metadata; raw Mutation Statements blocken.

### P1

- Fuer #2197-#2205 Hardening: Surrealkit-Rollout-Konzepte uebernehmen: dry-run, active rollout lock, schema hash/status, shared-db prune refusal.
- Fuer #2103-#2128 Retrieval: Hybrid BM25 + Vector + Graph traversal prototypisieren; Ingestion/Write-Pfade strikt getrennt halten.

### P2

- Surrealist als UI-/Control-Room-Inspiration nutzen, nicht als Dependency.
- External MCPs weiter als Risiko-/Pattern-Katalog beobachten.

## Guardrails

- Keine Dependency-Freigabe.
- Keine DB-Write-Freigabe.
- Keine Live-/LR-/Echtgeld-Ableitung.
- Human-GO bleibt fuer Writes zwingend.
- Context Layer bleibt getrennt von Trading Runtime State, Orders, Positions, Fills, Risk State und Secrets.

## Restunsicherheiten

- Externe Repos koennen sich aendern; konkrete SHAs wurden im Dry-Run nicht belastbar als Artefakt-Evidence festgehalten.
- Lizenz-/Maintenance-Bewertung bleibt Decision-Input und ist keine Freigabe.
- `surrealmcp` wurde lokal eindeutig gelesen; es bleibt trotzdem nur Referenz und keine CDB-Dependency-Empfehlung.
- Fuer spaetere Umsetzung sollten Quelle, Commit-SHA, Lizenz und Maintenance-Zustand je uebernommenes Pattern separat festgehalten werden.
