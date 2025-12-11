# AGENTS

## Zweck
Dieses Dokument beschreibt alle verfügbaren Fachagenten.

- **Agents** → vollständig definierte Rollen, die bei Bedarf dazugenommen werden können

## Prinzipien
- Agenten sind optional.
- Jeder Agent hat klar abgegrenzte Verantwortung.
- Agenten handeln niemals autonom, sondern nur auf Anweisung des Hauptmodells.
- Zu jeder Rolle existiert genau eine Datei `agent_<role>.md`.
- Jede Agenten-Datei beginnt mit Frontmatter:
  - `name` = `agent_<role>`
  - `role` = kurzer Titel
  - `description` = ein Satz zur Rolle
---

## Agents

Diese Rollen gelten als „online“ und werden vom Hauptmodell / Orchestrator standardmäßig verwendet.

### data-analyst
- Bereiche: Auswertung von Daten, Metriken, Backtests, Performance-Analysen.
- Datei: `agent_data-analyst.md`

### dataflow-enhancer
- Bereiche: Entwicklungsfluss, Repostruktur, PR-/Issue-Kontext, CI/CD-Sicht auf Fluss.
- Datei: `agent_dataflow-enhancer.md`

### system-architect
- Bereiche: Architekturentscheidungen, Systemzuschnitt, Schnittstellen, Modularität.
- Datei: `agent_system-architect.md`

### code-reviewer
- Bereiche: Code-Qualität, Stil, Lesbarkeit, Anti-Patterns.
- Datei: `agent_code-reviewer.md`

### devops-engineer
- Bereiche: CI/CD, Infrastruktur, Deploy-Pfade, Observability-Integration.
- Datei: `agent_devops-engineer.md`

### test-engineer
- Bereiche: Teststrategie, Testdesign, Testabdeckung, Regressionstests.
- Datei: `agent_test-engineer.md`

### documentation-engineer
- Bereiche: Systemdokumentation, Nutzer-Doku, Änderungsprotokolle.
- Datei: `agent_documentation-engineer.md`

### risk-architect
- Bereiche: Risikomodelle, Limits, Guardrails, Risk-Mode-Änderungen.
- Datei: `agent_risk-architect.md`

### canonical-governance
- Bereiche: Pflege der Governance-Schicht (GOVERNANCE_AND_RIGHTS, DECISION_LOG, Workflows).
- Datei: `agent_canonical-governance.md`

### knowledge-architect
- Bereiche: Wissensstrukturen, Dokumentations-Landkarte, Informationsarchitektur.
- Datei: `agent_knowledge-architect.md`

### refactoring-engineer
- Bereiche: größere Refactors, Schuldenabbau, Strukturverbesserungen ohne Verhaltensänderung.
- Datei: `agent_refactoring-engineer.md`

### repository-auditor
- Bereiche: Repository-Scanning, Konsistenzprüfungen, Altlasten, Dead Code.
- Datei: `agent_repository-auditor.md`

### stability-guardian
- Bereiche: Stabilität, Resilienz, Fehlerpfade, Degradationsstrategien.
- Datei: `agent_stability-guardian.md`

### market-analyst
- Bereiche: Marktsituation, Makro-Kontext, Produkt- und Markt-Insights.
- Datei: `agent_market-analyst.md`

### derivatives-analyst
- Bereiche: Derivate, komplexe Produkte, Payoffs, Szenario-Analysen.
- Datei: `agent_derivatives-analyst.md`

### spot-trader
- Bereiche: Spot-Handel, Orderlogik, Ausführungstaktiken.
- Datei: `agent_spot-trader.md`

### futures-trader
- Bereiche: Terminkontrakte, Roll-Strategien, Terminkurven.
- Datei: `agent_futures-trader.md`

### project-visionary
- Bereiche: Produktvision, Roadmap, Zielbilder, Narrative.
- Datei: `agent_project-visionary.md`

### project-visualizer
- Bereiche: Visualisierungen, Diagramme, Storyboards, Kommunikationsgrafik.
- Datei: `agent_project-visualizer.md`

---

## Nutzung

- Workflows referenzieren Agenten ausschließlich über die Rollennamen  
  (z. B. `system-architect`, `test-engineer`).

- Governance-Änderungen laufen über `WORKFLOW_Governance.md`.
