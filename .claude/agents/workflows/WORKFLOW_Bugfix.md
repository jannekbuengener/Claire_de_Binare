# WORKFLOW_Bugfix

Reference: ../AGENTS.md

Goal: Reproduce the bug, find root cause, fix safely, and prevent regression.

Roles involved: [Orchestrator](../roles/ORCHESTRATOR_Codex.md), [System Architect](../roles/AGENT_System_Architect.md) (if architectural), [Canonical Governance Officer](../roles/AGENT_Canonical_Governance.md) (governance/audit), [Code Reviewer](../roles/AGENT_Code_Reviewer.md), [Test & Simulation Engineer](../roles/AGENT_Test_Engineer.md), [Refactoring Engineer](../roles/AGENT_Refactoring_Engineer.md), [Risk Architect](../roles/AGENT_Risk_Architect.md) (if risk), [Data Architect](../roles/AGENT_Data_Architect.md) (if schema/data), [DevOps Engineer](../roles/AGENT_DevOps_Engineer.md) (if pipeline/infra), [Repository Auditor](../roles/AGENT_Repository_Auditor.md) (if layout), [Documentation Engineer](../roles/AGENT_Documentation_Engineer.md). Optional intelligence support: [Gemini Research Analyst](../roles/AGENT_Gemini_Research_Analyst.md), [Gemini Data Miner](../roles/AGENT_Gemini_Data_Miner.md), [Gemini Sentiment Scanner](../roles/AGENT_Gemini_Sentiment_Scanner.md) for external context/datasets/sentiment.

Phases:
- Analysis (no changes):
  1. Orchestrator gathers bug description (logs, steps to reproduce), ranks severity.
  2. System Architect (if relevant) checks for structural/architecture implications.
  3. Test & Simulation Engineer reproduces and isolates with test cases/fixtures/simulations.
  4. Code Reviewer analyzes root-cause hypotheses, marks sensitive areas.
  5. Risk Architect evaluates business/live impact; sets blocks or safe modes if needed.
  6. Data Architect (if data issue) assesses schema/data impacts.
  7. Repository Auditor (if layout issue) flags structural fixes.
  8. Orchestrator summarizes fix plan, scope, success criteria; get user go.
- Delivery (changes allowed):
  1. Refactoring Engineer or responsible dev fixes cause and hardens code; pairs with Code Reviewer.
  2. Data Architect executes schema/migration changes if required with rollback.
  3. Test & Simulation Engineer adds regression tests/simulations to CI; verifies reproduction disappears.
  4. DevOps Engineer adjusts deployment/config if relevant; sets feature flags/kill switches for rollout.
  5. Repository Auditor applies approved layout/naming fixes if needed.
  6. Orchestrator checks CI, runs review, plans release with Risk Architect if live risk.
  7. Documentation Engineer records fix, runbook, and release notes.

Outputs:
- Reproducible tests, root-cause note, fix commit/PR.
- Green CI, temporary protections or flags if needed.
- Documented lessons learned and release note.
----

# WORKFLOW_Feature_Implementation

Reference: ../AGENTS.md

Goal: Design and implement a new function safely without live risk.

Roles involved: [Orchestrator](../roles/ORCHESTRATOR_Codex.md), [System Architect](../roles/AGENT_System_Architect.md), [Canonical Governance Officer](../roles/AGENT_Canonical_Governance.md), [Risk Architect](../roles/AGENT_Risk_Architect.md), [Data Architect](../roles/AGENT_Data_Architect.md) (if data changes), [Code Reviewer](../roles/AGENT_Code_Reviewer.md), [Test & Simulation Engineer](../roles/AGENT_Test_Engineer.md), [Refactoring Engineer](../roles/AGENT_Refactoring_Engineer.md), [DevOps Engineer](../roles/AGENT_DevOps_Engineer.md), [Repository Auditor](../roles/AGENT_Repository_Auditor.md) (structure), [Documentation Engineer](../roles/AGENT_Documentation_Engineer.md). Optional intelligence support: [Gemini Research Analyst](../roles/AGENT_Gemini_Research_Analyst.md), [Gemini Data Miner](../roles/AGENT_Gemini_Data_Miner.md), [Gemini Sentiment Scanner](../roles/AGENT_Gemini_Sentiment_Scanner.md).

Phases:
- Analysis (no changes):
  1. Orchestrator: intake with Task Brief, capture goals/scope/KPIs, confirm this workflow.
  2. System Architect: assess design options, service boundaries, event/bus impacts.
  3. Risk Architect: impact analysis; define needed limits/flags/telemetry.
  4. Data Architect (if needed): propose schema/migration/data impacts.
  5. Code Reviewer: identify hotspots and tech debt.
  6. Test & Simulation Engineer: propose test plan, coverage targets, simulations/backtests if applicable.
  7. Repository Auditor (if structural moves): flag layout/naming changes.
  8. Orchestrator: consolidate decision note with options, effort, risks; get user go.
- Delivery (changes allowed):
  1. Orchestrator starts delivery, sets branch/work area.
  2. System Architect validates structural choices during implementation.
  3. Refactoring Engineer implements feature/refactors per plan; Code Reviewer shadows.
  4. Data Architect executes migrations/schema changes (if any) with rollback plan.
  5. Test & Simulation Engineer implements/updates tests and simulations; DevOps Engineer updates CI/CD and feature-flag/rollout plan.
  6. Risk Architect checks limits/flags and monitoring are active.
  7. Repository Auditor applies approved structure/naming adjustments if needed.
  8. Documentation Engineer updates user docs and changelog text.
  9. Orchestrator runs reviews, checks CI, issues final report.

Outputs:
- Analysis reports per role; consolidated decision and implementation plan.
- Implemented feature with tests, green CI, documented rollout strategy.
- Updated documentation and approval status.

---

# WORKFLOW_Governance_Update – Agenten & DECISION_LOG

## Ziel

Sicherstellen, dass:

- neue Agenten-Rollen, Capabilities und Workflows aus Brainstorming-Sessions
  sauber in `AGENTS.md` nachgeführt werden,
- der DECISION_LOG alle wichtigen Governance-Entscheidungen protokolliert.

---

## Preconditions

- User-Session, in der neue Rollen/Capabilities/Workflows besprochen wurden.
- MCP-Server aktiv: `agents-sync`, `filesystem`, `github-official`, `cdb-logger`.

---

## Phase A – Analyse

1. Session-Auswertung
   - Orchestrator extrahiert aus der aktuellen Unterhaltung:
     - neu definierte Rollen,
     - geänderte Verantwortlichkeiten,
     - neue oder angepasste Workflows.
2. Abgleich mit bestehender Governance
   - `filesystem.read_file("AGENTS.md")`.
   - Optional: weitere Governance-Dokumente (z. B. `governance/GOVERNANCE_AND_RIGHTS.md`).
3. Gap-Analyse
   - Welche Agenten sind neu und fehlen?
   - Welche Rollen haben neue Capabilities bekommen?
   - Welche Workflows müssen ergänzt/aktualisiert werden?
4. Logging
   - `cdb-logger.log_event` – `GOVERNANCE_ANALYSIS_COMPLETED`.
5. Output
   - Vorschlag, wie `AGENTS.md` und ggf. die verlinkten Rollen-/Workflow-Dateien angepasst werden sollen.

---

## Phase B – Delivery (nach Freigabe)

1. Branching
   - Branch-Name: `governance-update-YYYYMMDD`.
2. Governance-Dateien aktualisieren
   - `filesystem.write_file`:
     - Aktualisierung von `AGENTS.md` (Tabellen- / Link-Updates).
     - ggf. neue Dateien in `roles/` und `workflows/` anlegen.
3. DECISION_LOG pflegen
   - `cdb-logger.append_markdown`:
     - Governance-Entscheidung dokumentieren (Datum, Session-Kontext, Kurzinhalt).
4. Commit & PR
   - `github-official`:
     - Commit mit Message „Update agent governance & decision log“.
     - PR Richtung `main` mit:
       - Übersicht aller Governance-Änderungen,
       - Motivation und Risiken.

---

## Erfolgsindikatoren

- `AGENTS.md` spiegelt die real genutzten Agenten und Workflows korrekt wider.
- DECISION_LOG enthält nachvollziehbare Einträge zu Governance-Änderungen.
- Neue Rollen/Workflows sind referenziert und können von `agents-sync` sauber geladen werden.

----

# WORKFLOW_Risk_Mode_Change

Reference: ../AGENTS.md

Goal: Safely plan, validate, and execute operating-mode or limit changes (e.g., paper -> live, limit adjustments).

Roles involved: [Orchestrator](../roles/ORCHESTRATOR_Codex.md), [System Architect](../roles/AGENT_System_Architect.md) (architecture impact), [Canonical Governance Officer](../roles/AGENT_Canonical_Governance.md) (governance/audit/readiness), [Risk Architect](../roles/AGENT_Risk_Architect.md), [DevOps Engineer](../roles/AGENT_DevOps_Engineer.md), [Test & Simulation Engineer](../roles/AGENT_Test_Engineer.md), [Code Reviewer](../roles/AGENT_Code_Reviewer.md), [Documentation Engineer](../roles/AGENT_Documentation_Engineer.md). Optional intelligence support: [Gemini Research Analyst](../roles/AGENT_Gemini_Research_Analyst.md), [Gemini Data Miner](../roles/AGENT_Gemini_Data_Miner.md), [Gemini Sentiment Scanner](../roles/AGENT_Gemini_Sentiment_Scanner.md) for external market/risk signals.

Phases:
- Analysis (no changes):
  1. Orchestrator documents request (target mode, reason, duration, success criteria, rollback).
  2. System Architect (if needed) assesses architecture or service-boundary impact.
  3. Risk Architect evaluates exposure; defines needed limits/flags/monitoring; sets stop criteria and observations.
  4. DevOps Engineer checks switches (feature flags, config, secrets, deployment guardrails).
  5. Code Reviewer lists risky code paths; Test & Simulation Engineer plans risk-specific tests/probes.
  6. Orchestrator drafts decision note with approval conditions; get user go.
- Delivery (changes allowed):
  1. Risk Architect grants green light for concrete steps; Orchestrator sequences execution.
  2. DevOps Engineer applies config/flag/deployment changes with rollback path; Test & Simulation Engineer runs checks/smokes/probes.
  3. Orchestrator monitors metrics vs stop criteria; trigger immediate rollback if needed.
  4. Documentation Engineer updates ops and incident runbooks; Risk Architect records risk log.

Outputs:
- Approval doc with conditions, active limits/flags, and monitors.
- Evidence of tests/probes and any rollback performed.
- Updated ops docs, including return path and owners.

---

# WORKFLOW_Signal_Tuning – Handelsfrequenz & Signalqualität

## Ziel

Anpassung der Signalkonfiguration (z. B. Momentum-Schwellen, Filter wie RSI) mit dem Ziel:

- Handelsfrequenz moderat erhöhen,
- Winrate ≥ 50 % beibehalten,
- bestehende Risikoarchitektur respektieren.

---

## Preconditions

- Aktuelle Signalkonfig im Repo vorhanden (z. B. `backoffice/services/signal_engine/config.py`).
- Analyse-Dokument „Handelsfrequenz und Signalqualität“ liegt im Backoffice vor.
- MCP-Server aktiv: `filesystem`, `agents-sync`, `github-official`, `cdb-logger`.

---

## Phase A – Analyse

1. Governance & Rolle
   - Orchestrator zieht Definition für „Strategy/Signal Engineer“ aus `AGENTS.md` via `agents-sync`.
2. Input-Dokumente
   - `filesystem.read_file`:
     - Signalkonfig (z. B. `signal_engine/config.py`),
     - Analyse-Dokument zu Handelsfrequenz/Signalqualität.
3. Daten / Kennzahlen (optional)
   - Falls vorhanden: Analytics-Skripte / Metriken aus Tests/Backtests einbeziehen.
4. Vorschlag erarbeiten
   - Ableitung eines Parameter-Sets:
     - neue Schwellenwerte,
     - zusätzliche Filter (RSI, Trendfilter, Volumenfilter),
     - Schutzmechanismen gegen zu aggressive Frequenz.
5. Logging
   - `cdb-logger.log_event` – `SIGNAL_TUNING_ANALYSIS_COMPLETED`.
6. Output
   - Analyse-Report:
     - IST-Parameter,
     - SOLL-Parameter,
     - erwartete Auswirkungen (Trades/Tag, Winrate, Drawdown),
     - Rollback-Plan.

---

## Phase B – Delivery (nach Freigabe)

1. Branching
   - Branch-Name: `signal-tuning-YYYYMMDD`.
2. Änderungen im Repo
   - `filesystem.write_file`:
     - Anpassung der Signalkonfiguration gemäß Change-Plan.
   - Optional: ergänzende Doku in:
     - `Risikomanagement-Logik.md`,
     - Service-README des Signal-Engines.
3. Commit & PR
   - `github-official`:
     - Commit mit Message „Signal engine parameter tuning (frequency & quality)“.
     - PR Richtung `main` inkl.:
       - Parameterdiff,
       - Verweis auf Analyse-Dokument,
       - geplanten Monitoring-/Backtest-Step nach Merge.
4. Logging
   - `cdb-logger.log_event` – `SIGNAL_TUNING_PR_CREATED` + PR-URL.

---

## Phase C – Beobachtung (optional)

- Nach Deploy / Papertrading:
  - Orchestrator kann in einem Follow-up-Workflow
    - neue Performance-Metriken sammeln,
    - Abweichungen dokumentieren,
    - ggf. Rollback oder weitere Feintuning-Schritte vorschlagen.

---

## Erfolgsindikatoren

- Mehr Trades/Tag innerhalb des definierten Zielkorridors.
- Winrate bleibt ≥ 50 %.
- Kein Verstoß gegen bestehende Risikolimits.

---

# WORKFLOW_Status_Update – AKTUELLER_STAND Auto-Refresh

## Ziel

Halte `AKTUELLER_STAND.md` konsistent mit:

- der real laufenden Infrastruktur (Docker-Services),
- den Monitoring-Daten (Prometheus/Grafana),
- den Backoffice-Dokumenten (Architektur, Risiko, Analysen).

Dieser Workflow wird vom Codex Orchestrator gesteuert und läuft in zwei Phasen: Analyse → Delivery.

---

## Preconditions

- CDB-Docker-Stack läuft (Postgres, Redis, Services, Prometheus, Grafana).
- Docker MCP Gateway aktiv mit:
  - `filesystem`
  - `playwright`
  - `agents-sync`
  - `github-official`
  - `cdb-logger`

---

## Phase A – Analyse (read-only)

1. Governance & Template laden
   - `agents-sync.get_workflow("Status_Update")` (optional, meta).
   - `filesystem.read_file`:  
     - `AKTUELLER_STAND.md`  
     - `PROJEKT_BESCHREIBUNG.md`  
     - ggf. weitere relevante Backoffice-Dokumente.
2. Monitoring & Metriken
   - `playwright`:
     - öffnet Grafana (`http://localhost:3000`),
     - liest/analysiert relevante Panels (System Health, Trading Performance, Risk).
   - Optional: Prometheus-Metriken (`http://localhost:9090`) als Textquelle.
3. Gap-Analyse
   - Orchestrator identifiziert:
     - veraltete Einträge,
     - fehlende Services/Metriken,
     - Diskrepanzen zwischen Doku und aktuellem Zustand.
4. Logging
   - `cdb-logger.log_event` – `STATUS_UPDATE_ANALYSIS_STARTED` / `..._COMPLETED`.
5. Output
   - Analyse-Report im Standardformat mit:
     - Ist-Zustand (Doku),
     - Ist-Zustand (real),
     - Abweichungen,
     - geplanter Update-Plan (Change-Plan).

---

## Phase B – Delivery (nach Freigabe)

1. Branching
   - Branch-Namen: `status-update-YYYYMMDD`.
   - `github-official` – Branch von `main` erstellen.
2. Änderungen anwenden
   - `filesystem.write_file`:
     - Aktualisierung von `AKTUELLER_STAND.md` gemäß Change-Plan.
   - Optional: weitere Doku-Files (z. B. Ergänzungen in PROJEKT_BESCHREIBUNG).
3. Commit & PR
   - `github-official`:
     - Commit mit klarer Message (z. B. „Update AKTUELLER_STAND via MCP Status Workflow“).
     - PR Richtung `main` mit:
       - Kurzbeschreibung,
       - Referenz auf Analyse-Report,
       - Risiken/Offene Punkte.
4. Logging
   - `cdb-logger.log_event` – `STATUS_UPDATE_PR_CREATED` + PR-URL.

---

## Erfolgsindikatoren

- `AKTUELLER_STAND.md` spiegelt Services, Tests, Monitoring realistisch wider.
- PR ist sauber strukturiert und referenziert Analyse-Report.
- DECISION_LOG beinhaltet Eintrag zum Status-Update.
