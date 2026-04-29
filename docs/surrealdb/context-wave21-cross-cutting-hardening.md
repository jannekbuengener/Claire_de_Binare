# CDB Context Intelligence — Wave 21: Cross-cutting Hardening, Search, CI & Operations

**Status**: Draft / Planning
**Authority**: Issues #2198–#2204 / Epic #1976
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

---

## 3. #2199 — SurrealDB Fulltext Search Tuning

### Zweck
Optimierung der textbasierten Suche innerhalb der Dokumentations-Chunks und Code-Kommentare.

### Design
- **Indexer**: `FULLTEXT` Index auf `content` Feldern in der `doc_chunk` Tabelle.
- **Tokenization**: Standardmäßig `class::token::tokenizer::en` (Englisch), da Code und Doku primär Englisch sind.
- **Scoring**: Nutzung von BM25 für Relevanz-Ranking.
- **Fuzzy Search**: Deaktiviert für Code-Präzision, optional für Doku-Suche.

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

---

## 5. #2201 — Protective Hardening Plan

### Zweck
Absicherung des CIS gegen Datenlecks (Secrets) und unautorisierte Zugriffe.

### Maßnahmen
- **No-Secrets Guard**: Integration eines Secret-Scanners in die Ingestion-Pipeline (Fail-closed bei Treffern).
- **Permission Model**: Strikte Trennung von Read-only MCP Tools und Admin-Import CLI.
- **Redaction Policy**: Automatisierte Maskierung potenzieller PII oder sensibler Pfade im Context-Output.
- **Multi-Agent Isolation**: Sicherstellung, dass Agent A nicht den Scoped Memory von Agent B ausliest, sofern nicht explizit für Handoff freigegeben.

---

## 6. #2202 — CI Integration Plan

### Zweck
Automatisierte Sicherstellung der Datenqualität und Schema-Konformität.

### CI-Checks
- **Dry-run Indexer**: Läuft bei PRs gegen Doku/Code, um Parsing-Fehler frühzeitig zu erkennen.
- **Schema Validation**: Validierung der exportierten JSONL-Artefakte gegen die SurrealQL-Ontologie.
- **Link Integrity**: Prüfung auf Broken Links zwischen Doku-Chunks und Code-Symbolen im Graph.

---

## 7. #2203 — Backup, Restore, Retention & Archive Strategy

### Zweck
Sicherstellung der Disaster Recovery Fähigkeit des Knowledge-Kerns.

### Strategie
- **Backup**: Täglicher Export via `surreal export` in verschlüsselte Archive (gitignored, lokal/S3-kompatibel).
- **Restore**: Dokumentiertes Verfahren zur Wiederherstellung des Graphen aus dem letzten Export.
- **Retention**: 30 Tage Vorhaltung für tägliche Snapshots; 12 Monate für monatliche Archive.
- **Tombstones**: Verbleib gelöschter Artefakte für 90 Tage im Graph (markiert als `deleted`), danach physische Löschung.

---

## 8. #2204 — Documentation & Decision Governance Cadence

### Zweck
Verhinderung von "Knowledge Rot" und veralteten Architekturentscheidungen.

### Cadence
- **Monthly Stale Review**: Automatisierter Bericht über Dokumente, die > 90 Tage nicht aktualisiert wurden.
- **Decision Debt Audit**: Vierteljährliche Prüfung offener oder widersprüchlicher Decisions im Graph.
- **Evidence Review**: Validierung, ob Claims noch durch aktuelle Logs/Hashes gedeckt sind.

---

## 9. Abschluss-Gatter (Wave 21 Completion)
Siehe separates Dokument: `docs/surrealdb/context-wave21-completion-gates.md`.

---

## Provenance
- **Epic**: #1976
- **Phase**: Phase 5 (Governance Intelligence Runtime)
- **Provenance**: operator-assisted draft; authority remains Git repo, linked issues, and reviewed PR state.
