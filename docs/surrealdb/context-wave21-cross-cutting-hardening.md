# CDB Context Intelligence — Wave 21: Cross-cutting Hardening, Search, CI & Operations

**Status**: Draft / Planning
**Authority**: Issues #2199–#2204 / Epic #1976
**Context**: Final hardening and operationalization wave for Phase 5.

## 1. Übersicht
Dieses Dokument konsolidiert die Planungs- und Designentscheidungen für Wave 21. Ziel ist es, das Context Intelligence System (CIS) für den stabilen Betrieb vorzubereiten, ohne dabei in die Trading-Runtime einzugreifen.

---

## 2. #2198 — Vector Search & Embeddings Design

### Zweck
Ermöglichung semantischer Ähnlichkeitssuche ergänzend zu Graph- und Fulltext-Retrieval.

### Empfohlene Entscheidung
- **Modus**: **Optionaler** Hybrid-Ansatz.
- **Embeddings**: Lokale Generierung (z. B. via `sentence-transformers` / `FastEmbed`) bevorzugt, um Kosten zu kontrollieren und Secret-Abhängigkeiten (OpenAI/Cohere) zu vermeiden.
- **Speicherung**: SurrealDB native Vector-Indizierung (HNSW).
- **Hybrid-Ranking**: Kombiniertes Scoring aus Graph-Distance, BM25 (Fulltext) und Cosine Similarity (Vector).

### Risiken & Validierung
- **Risiko**: Hoher Speicherbedarf und CPU-Last bei Index-Rebuilds.
- **Validierung**: Benchmark der Vektorisierungszeit für das gesamte Repo.

### Drift- und Rebuild-Strategie

Embeddings sind driftanfällig: sowohl das Embedding-Modell als auch die Quelltexte
können sich ändern. Ohne explizite Drift-Strategie kollidieren Vektoren aus
verschiedenen Modellversionen im selben Index und verschlechtern die
Retrieval-Qualität.

**Modellversionierung:**
- Jedes Embedding-Modell erhält eine kanonische `model_id` und wird in der
  Embedding-Tabelle persistiert.
- Bei Modellwechsel: **Full-Rebuild** des Vector-Index, keine inkrementelle
  Mischmigration.
- Embeddings bleiben **optional** und sind keine Voraussetzung für das
  Kern-Retrieval (Graph + Fulltext).

**Rebuild-Auslöser:**
1. **Modellwechsel**: Neues Embedding-Modell als Standard gesetzt.
2. **Index-Parameter-Änderung**: HNSW-Parameter (`m`, `ef_construction`) geändert.
3. **Korpus-Änderung**: >20 % der Quelltexte via Hash-Vergleich geändert.

**Rebuild-Prozedur (offline / manuell):**
1. Neues Modell wird als `model_id` registriert.
2. Alte Embeddings behalten ihre `model_id` und bleiben zunächst referenzierbar.
3. Neuer HNSW-Index wird **parallel** neben dem alten Index aufgebaut
   (gestaffelt, um CPU-/Storage-Spitzen zu vermeiden).
4. Nach erfolgreichem Rebuild und Validierungs-Pass wird der alte Index
   deaktiviert, aber nicht gelöscht.
5. Nach einer Haltefrist von 30 Tagen wird der alte Index physisch gelöscht.

**Rollback:**
- Vollständiger Rollback durch Rücksetzen des aktiven `model_id`-Filters auf
  das vorherige Modell möglich, solange der alte Index nicht gelöscht wurde.
- Entscheidung zum Rollback ist manuell (Human Gate).
- **Kein automatisches produktives Enable.**

### Datenschutz- und Kosten-Leitplanken für optionalen externen Modus

Der externe Embedding-Modus ist **optional** und erfordert ein separates
Human-GO. Standardmäßig ist der lokale Modus aktiv.

**Datenverbleib:**
- Nur Chunk-Text (ohne Pfade, ohne Secrets, ohne PII) wird externalisiert.
- Chunk-Text muss vor Versand die No-Secrets-Guard-Pipeline (§5) durchlaufen.
- Keine Metadaten (Dateipfade, Issue-Nummern, Autor-Namen) verlassen den
  lokalen Kontext.
- Bei Provider-Ausfall greift ausschließlich Graph + Fulltext; kein
  Degraded-Mode mit unvollständigen Vektoren.

**Provider-Grenzen:**
- Erlaubt nur mit separater Provider-Entscheidung und dokumentierter
  Datenschutz-/Retention-Regelung.
- **Nicht erlaubt:** Provider ohne explizite Zero-Retention-Garantie; Provider,
  die Embeddings für Modell-Training wiederverwenden.
- **Kein Provider-Zwang.**

**Kostenkontrolle:**
- Festes monatliches Kostenlimit (Policy-Platzhalter; konkrete Werte per
  separater Entscheidung).
- Bei Überschreitung: Stop + Alert, kein automatisches Budget-Upgrade.
- Kosten-Monitoring via Provider-Dashboard; kein CDB-internes Billing-System.

---

## 3. #2199 — SurrealDB Fulltext Search Tuning

### Zweck
Optimierung der textbasierten Suche innerhalb der Dokumentations-Chunks und Code-Kommentare.

### Design
- **Indexer**: `FULLTEXT` Index auf `content` Feldern in der `doc_chunk` Tabelle.
- **Tokenization**: Standardmäßig `class::token::tokenizer::en` (Englisch), da Code und Doku primär Englisch sind.
- **Scoring**: Nutzung von BM25 für Relevanz-Ranking.
- **Fuzzy Search**: Deaktiviert für Code-Präzision, optional für Doku-Suche.

### Chunk-Scoring-Komponenten

Jeder Search-Hit wird durch ein gewichtetes Scoring aus mehreren Komponenten bewertet:

| Komponente | Gewichtung | Bemerkung |
|---|---|---|
| **BM25 / lexical relevance** | Primär | Standard-Relevanz über Termfrequenz. |
| **Exact identifier match** | Boost | Exakter Treffer auf Symbol-, Issue- oder Dateinamen bekommt Vorrang. |
| **Document freshness / staleness penalty** | Dämpfung | Dokumente > 180 Tage ohne Update erhalten leichten Penalty; kein kategorischer Ausschluss. |
| **Graph proximity** | Boost | Höhere Relevanz für Chunks, die im Knowledge-Graph nahe am Triggerpunkt liegen (linked decisions, related docs). |
| **Fuzzy expansion** (nur Doku-Kontext) | Optional | Nur für Docs-only Search aktivierbar; erweitert die Treffermenge bei Tippfehlern/stilistischen Variationen. |

### Klarstellungen

- **Code-Präzision bevorzugt exact mode**: Fuzzy Expansion ist für Code-Suche deaktiviert, um falsche Symbol-Zuordnungen zu vermeiden.
- **Fuzzy nur für Doku-Kontext**: Aktivierung ausschließlich über separaten Query-Flag für Docs-only Retrieval.
- **Performance-Tests gehören zu #2200**: Die Latenz- und Durchsatzmessung von Search-Queries wird in §4 (#2200) geplant und validiert.

### Validierung
- Test-Queries gegen bekannte Fachbegriffe (z. B. "Risk Service", "Kill-Switch") und Prüfung der Ranking-Qualität.

---

## 4. #2200 — Performance & Scale Validation Plan

### Zweck
Sicherstellung der Reaktionsfähigkeit bei wachsendem Repository-Umfang.

### Benchmarks
- **Ingestion Performance**: Ziel < 5 Minuten für kompletten Repo-Reindex (ca. 2000 Dateien).
- **Query Latency**: Ziel < 200ms für Standard-Context-Retrieval via MCP.
- **Memory Footprint**: Überwachung der SurrealDB-Auslastung bei großen Graph-Joins.

### Strategie
- **Incremental Indexing**: Nur geänderte Dateien (via Hash-Vergleich) neu prozessieren.
- **Tombstone Cleanup**: Regelmäßige Bereinigung gelöschter Artefakte aus dem Graph.

### Cache-Strategie (Plan)

Zusätzlich zu Incremental Indexing wird eine Caching-Schicht vorgesehen:

- **Read-through Cache**: Für häufige Context Queries (z. B. wiederkehrende MCP-Tool-Abfragen nach "Risk Service", "Kill-Switch"). Bei Miss: Query gegen SurrealDB, Ergebnis in Cache schreiben, dann zurückgeben.
- **Invalidierung via Content Hash / Doc Chunk Hash**: Cache-Eintrag wird verworfen, sobald sich der Hash des zugrunde liegenden Chunks ändert.
- **Kein Cache für permission-sensitive scoped memory**: Agent-spezifische Kontexte (Scoped Memory) werden nie gecached, da der Zugriff permission-geprüft ist und Caching die Isolation verletzen würde.
- **Cache miss muss korrekt sein**: Bei einem Miss wird das exakte Query-Ergebnis aus SurrealDB zurückgegeben — kein "optimistisches" oder partielles Resultat.

### Cross-Link zu #2203

- **Snapshot-Retention / Backup gehört zu #2203**: Tägliche Snapshots, monatliche Archive und Tombstone-Retention werden in §7 (#2203) definiert.
- **Performance-Cache ist kein Backup**: Der Read-through Cache ist ein flüchtiges Performance-Instrument und ersetzt keine persistente Backup-Strategie.

### Benchmark-Runner

- **Benchmark-Runner nur als separater Follow-up**: Die tatsächliche Benchmark-Implementierung (Skript, reproduzierbarer Datensatz, CI-Integration mit Schwellwerten) wird als eigener Slice ausserhalb von Wave 21 geplant — dies ist reines Design.
- Keine Implementierung in diesem Scope.

---

## 5. #2201 — Protective Hardening Plan

### Zweck
Absicherung des CIS gegen Datenlecks (Secrets) und unautorisierte Zugriffe.

### Maßnahmen
- **No-Secrets Guard**: Integration eines Secret-Scanners in die Ingestion-Pipeline (Fail-closed bei Treffern).
- **Permission Model**: Strikte Trennung von Read-only MCP Tools und Admin-Import CLI.
- **Redaction Policy**: Automatisierte Maskierung potenzieller PII oder sensibler Pfade im Context-Output.
- **Multi-Agent Isolation**: Sicherstellung, dass Agent A nicht den Scoped Memory von Agent B ausliest, sofern nicht explizit für Handoff freigegeben.

### PII-Scanner (optionaler Zusatz-Guard)

- **Optional, nicht Pflicht für Kernfunktion**: Der PII-Scanner ist ein zusätzlicher Schutzmechanismus oberhalb der No-Secrets-Guard- und Redaction-Policy-Ebene.
- Aktivierung erfordert separates Human-GO und eine dokumentierte PII-Klassifikation.
- Kein produktives Enable ohne diesen Guard, wenn aktiviert.

### MCP Permission Audit Prozedur (Plan)

Eine periodische Audit-Prozedur sichert die Integrität des Permission-Modells:

1. **Read-only Tool Audit**: Alle als read-only deklarierten MCP-Tools werden gegen ihre tatsächliche Capability geprüft. Jedes Tool, das schreibende SurrealDB-Operationen ausführt, wird markiert.
2. **Admin/Import-Tools getrennt**: Admin-CLI- und Import-Tools werden in einer separaten Audit-Kategorie geführt; keine Vermischung mit read-only Query-Tools.
3. **Deny-by-default für write-capable actions**: Tools mit Schreibzugriff benötigen eine explizite Allowlist-Eintragung; Standard ist Verweigerung.

### Local/Dev/Prod Separation Policy

- **Lokale/dev Experimente**: Dürfen keine produktiven Secrets (`SECRETS_PATH`) oder eine produktive DB-Instanz verwenden. Lokale SurrealDB-Instanzen sind isoliert.
- **Prod-like Modus**: Nur mit separatem Human-GO und dokumentierter Umgebungskonfiguration. Kein automatischer Übergang von dev zu prod.
- Trennung gilt auf Namespace-/Database-Ebene in SurrealDB sowie für alle Secrets-Referenzen.

### Access-Matrix für mehrere Agenten

| Agent | Scoped Memory | Handoff | Shared Context (read-only) |
|---|---|---|---|
| **Agent A** | Eigenes Memory (privat) | Nur explizit via Handoff-Token | Gemeinsame Doc-Chunks, Graph-Knoten |
| **Agent B** | Eigenes Memory (privat) | Nur explizit via Handoff-Token | Gemeinsame Doc-Chunks, Graph-Knoten |
| **Admin-Tool** | Kein Scoped Memory | N/A | Alle read-only Surfaces |

- **Scoped Memory**: Jeder Agent hat isolierte, nur für ihn sichtbare Daten.
- **Handoff**: Nur explizit durch einen Agenten freigegebene Kontexte werden übertragen.
- **Shared Context**: Nur über erlaubte read-only Surfaces (Doc-Chunks, Graph-Abfragen) zugänglich.

---

## 6. #2202 — CI Integration Plan

### Zweck
Automatisierte Sicherstellung der Datenqualität und Schema-Konformität.

### CI-Checks
- **Dry-run Indexer**: Läuft bei PRs gegen Doku/Code, um Parsing-Fehler frühzeitig zu erkennen.
- **JSONL / Schema Validation**: Validierung der exportierten JSONL-Artefakte (Chunks, Edges, Nodes) gegen die SurrealQL-Ontologie-Definition. Prüfung auf Schema-Konformität, Feld-Vollständigkeit und Typ-Korrektheit.
- **Link Integrity**: Prüfung auf Broken Links zwischen Doku-Chunks und Code-Symbolen im Graph.
- **Query Contract Tests**: Validierung, ob definierte MCP-Query-Templates (z. B. "get context for symbol", "find related decisions") deterministisch und ohne Fehler ausführbar sind.
- **MCP Registry Tests**: Prüfung der MCP-Tool-Registry auf Vollständigkeit und Konsistenz: jedes gelistete Tool muss vorhanden, jedes vorhandene Tool muss gelistet sein.
- **Guardrail Tests**: Automatisierte Prüfung der Guardrails (No-Secrets-Guard, Redaction) gegen vordefinierte Testdaten mit bekannten Triggers.

### CI-Wiring

- **Keine `.github/workflows/`-Datei erstellen**: Die konkrete GitHub Actions-Verdrahtung bleibt ein separater Implementierungs-Slice ausserhalb von Wave 21.
- **CI-Wiring als Folgearbeit**: Die obigen Checks sind hier nur als Plan-Kategorien definiert. Tatsächliche Workflow-Erstellung, Runner-Selektion und Fail-Verhalten sind getrennt zu designen und zu implementieren.

---

## 7. #2203 — Backup, Restore, Retention & Archive Strategy

### Zweck
Sicherstellung der Disaster Recovery Fähigkeit des Knowledge-Kerns.

### Strategie
- **Backup**: Täglicher Export via `surreal export` in verschlüsselte Archive (gitignored, lokal/S3-kompatibel).
- **Restore**: Dokumentiertes Verfahren zur Wiederherstellung des Graphen aus dem letzten Export.
- **Retention**: 30 Tage Vorhaltung für tägliche Snapshots; 12 Monate für monatliche Archive.
- **Tombstones**: Verbleib gelöschter Artefakte für 90 Tage im Graph (markiert als `deleted`), danach physische Löschung.

### Backup Scope (explizit)

| Einschluss | Ausschluss |
|---|---|
| SurrealDB namespace/database exports | Secrets (`.env`, `SECRETS_PATH`-Inhalte) |
| Ontology/Schema-Artefakte (SurrealQL-Definitionen) | Raw external repos (nicht-importierte Fremd-Repos) |
| Import-Manifeste (was wurde wann aus welcher Quelle importiert) | Generated caches (flüchtig, aus Performance-Cache rekonstruierbar) |
| Audit-/Evidence-Reports | Logs mit potenziellen Secrets (vorher gefiltert) |

### Audit Report Retention

- **Short-term**: Operative Audit-Reports werden 30 Tage vorgehalten (im täglichen Snapshot enthalten).
- **Longer-term**: Monatlich aggregierte Audit-Reports werden in den monatlichen Archiven für 12 Monate vorgehalten.

### Lokale/Dev vs. spätere produktive Trennung

- **Lokale/dev-Phase**: Backup erfolgt lokal (Dateisystem); kein S3-kompatibler Storage erforderlich. Restore-Prozedur wird ausschließlich lokal getestet.
- **Spätere produktive Phase**: Erfordert separates Human-GO und dokumentierte Speicherort-Entscheidung (S3-kompatibel oder äquivalent). Kein automatischer Übergang.

### Mini-Restore-Runbook (Plan)

1. **Snapshot auswählen**: Täglichen oder monatlichen Snapshot aus dem Backup-Verzeichnis selektieren.
2. **Checksum/Hash verifizieren**: Integrität des Archivs vor dem Restore prüfen.
3. **In isolierten Namespace wiederherstellen**: Restore in einen separaten SurrealDB-Namespace (z. B. `restore_tmp`), nicht direkt in den produktiven Namespace.
4. **Validierungs-Queries ausführen**: Schema-Integrität, Chunk-Count, Graph-Konnektivität im isolierten Namespace prüfen.
5. **Promotion nur mit Human-GO**: Nach erfolgreicher Validierung wird der wiederhergestellte Namespace manuell auf den produktiven Namespace umgeschaltet.

**Keine DB-Commands ausführen**: Dieses Runbook ist reiner Plan. Keine `surreal`-, `curl`- oder direkten DB-Befehle werden in diesem Scope ausgeführt.

---

## 8. #2204 — Documentation & Decision Governance Cadence

### Zweck
Verhinderung von "Knowledge Rot" und veralteten Architekturentscheidungen.

### Cadence
- **Monthly Stale Review**: Automatisierter Bericht über Dokumente, die > 90 Tage nicht aktualisiert wurden.
- **Decision Debt Audit**: Vierteljährliche Prüfung offener oder widersprüchlicher Decisions im Graph.
- **Evidence Review**: Validierung, ob Claims noch durch aktuelle Logs/Hashes gedeckt sind.

### Owner-Matrix

| Artefakt | Owner | Verantwortlichkeit |
|---|---|---|
| Ontology/Schema (SurrealQL-Definitionen) | Ontology-Owner | Schema-Konsistenz, Migrationen, Feld-Semantik |
| Ingestion Pipeline (Import, Parsing, Chunking) | Ingestion-Owner | Korrektheit der Datenaufnahme, Parser-Updates |
| MCP/Tool Contracts (Query-Schnittstellen) | MCP Contract Owner | Tool-Signaturen, Registry-Pflege, Contract-Tests |
| Docs/Runbooks (SurrealDB-Betrieb) | Docs/Runbook Owner | Aktualität der Betriebsdokumentation, Runbook-Cadence |
| Audit/Evidence (Reports, Hashes, Logs) | Audit/Evidence Owner | Nachvollziehbarkeit, Hash-Ketten, Evidence-Review |

### Runbook Review Cadence

- **Monthly Lightweight Review**: Jedes Runbook wird monatlich auf offensichtliche Veraltung geprüft (veraltete Pfade, falsche Kommandos, inkonsistente Referenzen). Ergebnis: kurzer Vermerk im jeweiligen Runbook ("reviewed YYYY-MM-DD").
- **Quarterly Decision Debt Review**: Gemeinsam mit dem Decision Debt Audit werden Runbooks auf strukturelle Lücken und widersprüchliche Verfahren geprüft.

### Issue-to-Doc Synchronization Policy

- **Merged PR**: Muss entweder die kanonischen Docs aktualisieren oder explizit dokumentieren, warum kein Doc-Update erforderlich ist (z. B. reiner Refactor ohne Interface-Änderung).
- **Closed Issue**: Soll auf ein Repo-gestütztes Artefakt verweisen (Doc, Runbook, Decision Record), nicht nur auf einen PR.
- **Stale Issue Comments**: Sind Hinweise, keine Wahrheit. Verbindlich ist nur der aktuelle Repo-Stand (Git + Docs).

### Bericht-Automatisierung

- **Bleibt separater Future-Slice**: Die Automatisierung der Stale-Review- und Decision-Debt-Berichte (z. B. als GitHub Actions Job) wird ausserhalb von Wave 21 geplant und implementiert.
- Keine Implementierung in diesem Scope.

---

## 9. Abschluss-Gatter (Wave 21 Completion)
Siehe separates Dokument: `docs/surrealdb/context-wave21-completion-gates.md`.

---

## Provenance
- **Epic**: #1976
- **Phase**: Phase 5 (Governance Intelligence Runtime)
- **Provenance**: operator-assisted draft; authority remains Git repo, linked issues, and reviewed PR state.
