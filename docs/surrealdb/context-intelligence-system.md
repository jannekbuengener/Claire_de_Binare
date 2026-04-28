# CDB Context Intelligence System — Architecture Document (Canonical)

**Status**: Draft (Wave 7)
**Authority**: Issue #2035 / Epic #1976
**Guardrail**: trade-capable is NOT a Live-Readiness-Go.

## 1. Zweck
Das CDB Context Intelligence System (CIS) dient als zentraler **Agent Memory & Knowledge Core**. Es transformiert statische Repo-Daten (Code, Dokumentation, Governance) in ein querybares, graph-basiertes Wissensmodell. Ziel ist es, Agenten mit tiefem, belegbarem Kontext zu versorgen, um Entscheidungsqualität und Governance-Compliance zu maximieren.

## 2. Nicht-Ziele
- **Kein Trading-Runtime-Ersatz**: CIS verwaltet keine aktiven Trades, Orders oder Risk-States.
- **Keine autonome Ausführung**: CIS erteilt keine eigenständigen Freigaben für Live-Trading oder Repo-Mutationen.
- **Keine Geheimnis-Ablage**: CIS enthält keine API-Keys, Secrets oder Broker-Credentials.
- **Keine Schreib-Authority für Primärdaten**: CIS ist ein Spiegel; Änderungen an Code/Doku erfolgen ausschließlich über Git/PR.
- **Keine Live-Readiness-Inferenz**: CIS-Status impliziert kein Go für Echtgeld-Trading.

## 3. Systemgrenzen
- **Input**: Git-Repository (Working Repo Canon), Markdown-Dokumentation, GitHub-Issues/PRs, Evidence-Logs.
- **Output**: Agent-Briefings, Impact-Analysen, Context-Queries, Trust-Signale.
- **Boundary**: Das System ist strikt von der operativen Trading-Runtime (Execution, Broker-API) getrennt.

## 4. SurrealDB-Rolle
SurrealDB fungiert als **Multi-Model Intelligence Database**. Sie speichert den Knowledge Graph (Nodes & Edges) sowie Metadaten für das Retrieval. Sie ist ein **read-only Mirror** der Repo-Wahrheit und dient nicht als Source of Truth für den Systemzustand oder Trading-Daten.

## 5. CDB-MCP-Rolle
Die CDB-MCP-Bridge ist das operative Interface für Agenten. Sie stellt Tools bereit, um den Knowledge Graph abzufragen und Evidence zu validieren. Die Bridge erzwingt die Einhaltung der Read-only-Constraints und stellt sicher, dass Context-Antworten source- und evidence-fähig sind.

## 6. Verhältnis zu Governance Mirror und shared_memory
- **Governance Mirror**: Das CIS integriert und erweitert die bestehenden Prinzipien aus `docs/surrealdb/data-ownership-matrix.md`.
- **shared_memory (Abgrenzung)**: `shared_memory` wird als abzugrenzende Kontext-/Memory-Fläche betrachtet. Die genaue technologische Verzahnung und die spezifische Rolle von `shared_memory` sind aktuell nicht final belegt und werden als spätere Spezifikations- und Abgrenzungsfrage behandelt. Das CIS fokussiert primär auf langfristigen, auditierbaren sowie source-, hash- und evidence-fähigen Kontext.

## 7. Zielarchitektur / Endbild
CIS bildet ein konsistentes Geflecht (Graph) aus Artefakten, deren Beziehungen (z. B. `Implements`, `Validates`, `DependsOn`) explizit modelliert sind. Jede Information im CIS muss über einen Source-Hash (Git/File) verifizierbar sein.

## 8. Kernkomponenten
1.  **Repo Brain**: Statische Analyse von Code-Symbolen, Imports und Strukturen.
2.  **Documentation Brain**: Ingestion und Chunking der Markdown-Doku-Hierarchie.
3.  **Knowledge Graph**: Semantische Verknüpfung von Code, Doku und Governance.
4.  **Evidence Fabric**: Verknüpfung von Claims mit realen Beweisen (Hashes, Logs).
5.  **Decision Graph**: Historie und Begründung von Architekturentscheidungen.
6.  **Agent Memory**: Scoped Memory für Agenten-Erfahrungen und Session-Kontext.
7.  **Retrieval Layer**: Hybrid Retrieval (Graph-/Metadaten-basiert, optional Vector-ready bei Bedarf).
8.  **Agent Briefing Engine**: Generierung aufgaben-spezifischer Kontext-Pakete.
9.  **Impact Radar**: Analyse der Auswirkungen von Änderungen auf das Gesamtsystem.
10. **Contradiction Detection**: Identifikation von Widersprüchen zwischen Doku und Realität.
11. **Scope Drift Firewall**: Warnung bei Abweichungen vom kanonischen Mission-Scope.
12. **Self-Explanation Layer**: Fähigkeit des Systems, seine Antworten kontextuell zu begründen.
13. **Agent OS**: Framework für die Interaktion zwischen CIS und Agenten-Runtimes.

## 9. Erlaubte Datenklassen
- Repository-Metadaten (Pfade, Hashes, Commits).
- Statische Code-Symbole (Klassen, Funktionen, Typen).
- Dokumentations-Inhalte (Markdown, strukturierte Texte).
- Governance-Regeln, Policies und Invarianten.
- Öffentliche Repo-/GitHub-Metadaten (Issues, PRs, Handles).

## 10. Verbotene Datenklassen
- **Trading-Zustände**: Orders, Positions, Fills, Balances.
- **Secrets**: API-Keys, Passwörter, Private Keys, Broker-Credentials.
- **Sensible/Personenbezogene Daten (PII)**: Keine privaten Daten außer den für die Repo-Arbeit notwendigen öffentlichen Metadaten.
- **Live Risk State**: Keine Echtzeit-Risiko-Metriken.

## 11. Trust- & Evidence-Prinzipien
- **Source-of-Truth**: Git/GitHub/Repo bleiben die alleinige SSoT für Code, Doku und Issue-Wahrheit.
- **Hash-Backed**: Context-Antworten müssen source-, hash- und evidence-fähig sein.
- **No Evidence, No Trust**: Nicht belegbare Informationen werden als "unverified" markiert.

## 12. Human-GO- & Stop-Condition-Prinzip
Das CIS identifiziert **Stop-Conditions** (z. B. Governance-Verstoß). Jede substantielle Aktion oder Zustandsänderung am System erfordert ein **explizites Human-GO**.

## 13. Abgrenzung zur Runtime
CIS läuft parallel zur Trading-Runtime. Ein Ausfall oder Drift im CIS darf das operative Trading-Verhalten nicht beeinflussen (Fail-safe). Es wird kein Runtime-/Trading-/Live-Readiness-Verhalten verändert.

## 14. Abhängigkeiten (Issues #1976–#2033)
Dieses Dokument bildet das Fundament für die Wellen 1–6:
- Wave 1–3: Ingestion & Graph Foundation (#1977–#2003)
- Wave 4–6: Evidence, Decisions & Quality Scoring (#2004–#2033)

## 15. Validierungs-Checkliste für dieses Dokument
- [ ] Entspricht das Dokument der Vision in Epic #1976?
- [ ] Sind alle Guardrails (kein Trading, keine Secrets) explizit genannt?
- [ ] Ist die Trennung zwischen Intelligence-Mirror und SSoT (Git) gewahrt?
- [ ] Sind alle 13 Kernkomponenten definiert?

## Provenance / Quellen
- **Issues**: #1976, #1977, #2034, #2035
- **Referenz-Dokumente**:
  - `docs/surrealdb/data-ownership-matrix.md`
  - `docs/surrealdb/dual-write-mirror-strategy.md`
  - `docs/surrealdb/ledger-importer.md`
  - `docs/surrealdb/rollback-cutover-plan.md`
