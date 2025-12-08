# WORKFLOW_Supervisor_Playbook v0.1

Reference: AGENTS.md (governance, routing, roles), DECISION_MCP_STACK_BASELINE.md (MCP stack), roles/ORCHESTRATOR_Codex.md (identity), WORKFLOW_ORCHESTRATION_BLUEPRINTS.md (patterns).

## Zweck & Scope
- Leitfaden fr ORCHESTRATOR_Codex, wie jede neue Aufgabe gefhrt wird (Analyse  Delegation  Review  Abschluss).
- Single Orchestrator spricht mit User; Sub-Agenten laufen nur ber das Projekt-Gehirn (Visionary/Visualizer/Stability) und definierte Workflows.
- Gilt fr alle Tasks, egal ob Feature, Bugfix, Governance, Research.

## Preconditions (Runtime)
- Docker MCP Gateway aktiv mit: agents-sync, filesystem, github-official, playwright, cdb-logger.
- Zugriffspfade: C:\Users\janne\Documents\GitHub\Workspaces\AGENTS und Claire_de_Binare (per filesystem server/config.yaml).
- Phase kl1ren: Analyse = read-only; Delivery = nur nach Freigabe, immer Branch + PR, kein Direkt-Commit auf main.
- Secrets-Trennung respektieren (.env neutral, ./cdb_secrets/*.txt real secrets, read-only mount f1r Docker).

## Session-Lifecycle (Orchestrator)
1) Start
- Session-Kontext setzen: Task-Beschreibung, Repos/Services, Risiko-Level, Deadline.
- Governance laden: AGENTS.md, relevante Rollen/Workflows; bei Bedarf DECISION_MCP_STACK_BASELINE.md.
- Phase festlegen (Analyse vs Delivery). Wenn unklar  default Analyse.
- Log: cdb-logger STATUS "SUPERVISOR_SESSION_STARTED" mit Task/Scope.

2) Analyse (read-only)
- Routing bestimmen: mappe Task  Work-Item  zust1ndiger Strang (Visionary intake, Visualizer planning, Stability signals).
- Informationssammeln ohne 1nderungen: Files lesen, Metriken/Pipelines checken (Playwright/Filesystem), bestehende Issues/PRs via github-official.
- Hypothesen, Risiken, Abh1ngigkeiten notieren. Entscheide, ob Fachagenten gebraucht werden.
- Log: "SUPERVISOR_ANALYSIS_COMPLETED" mit Haupt-Hypothesen + n1chste Schritte.

3) Delegation / Ausf1hrung
- Project_Visionary: erstellt/labelt Work-Items (Issues/MRs) aus Eingangssignalen.
- Project_Visualizer: ordnet zu Boards/Epics, Sequencing Now/Next/Later.
- Stability_Guardian: zieht CI/CD-, Security-, Hygiene-Signale; erzeugt Stab.-Tickets.
- Fachagenten: erhalten nur vorbereitete Work-Items aus obigem Dreiklang. Kein direkter User-Kontakt.
- Branch/PR-Setup: Delivery nur auf neuem Branch (z. B. supervisor-playbook-YYYYMMDD oder task-scope-YYYYMMDD). Feature/Refactor 1ber WORKFLOW_Feature_Implementation. Docs/Governance 1ber WORKFLOW_Governance_Update. Status 1ber WORKFLOW_Status_Update. Signal-Tuning 1ber WORKFLOW_Signal_Tuning.
- Log: f1r jede Delegation "SUPERVISOR_DELEGATED" mit Agent/Work-Item.

4) Review / Konsolidierung
- Sammle Outputs der Agenten (Reports, Diffs, Tickets). Pr1fe Konsistenz mit Governance (Single Orchestrator, Secrets, Runtime-first, WS-H1rtung, Single PG User/Pass).
- Risk/Governance-Gates pr1fen (Matrix siehe unten). Stoppe oder fordere Nachbesserung, falls Gates nicht erf1llt.
- PR-Qualit1t pr1fen: Scope klar, Tests/CI gr1n, Risiko/Rollback beschrieben, Doku/Log aktualisiert.
- Log: "SUPERVISOR_REVIEW_COMPLETED" mit Entscheidungen.

5) Abschluss
- Nutzer-Update: kurz, faktenbasiert, Optionen/Entscheidungspunkte hervorheben.
- Logging: cdb-logger "SUPERVISOR_SESSION_COMPLETED" + relevante PR/Issue-Links; DECISION_LOG-Eintr1ge, falls Governance-/Risk-Entscheidungen.
- Plateau-Prinzip: k1hlen, validieren, aufr1umen, erst dann n1chster Schritt.

## Routing-Regeln (konkret)
- Neue Signals (Issues/MRs/Research/Risk/CI): immer zuerst zu AGENT_Project_Visionary (Label/Impact/Links).
- Planung/Sichtbarkeit: AGENT_Project_Visualizer (Epics, Boards, Timelines, Storyline).
- CI/CD/Security/Hygiene: AGENT_Stability_Guardian (Tickets, Trends, Hygiene-Fixes low-risk).
- Fachagenten-Auswahl:
  - Struktur/Repo: AGENT_Repository_Auditor
  - Docs: AGENT_Documentation_Engineer
  - Refactor/Arch: AGENT_Refactoring_Engineer, AGENT_System_Architect
  - Risk/Signals: AGENT_Risk_Architect, Signal-spezifische Rollen
  - Tests: AGENT_Test_Engineer; Code-Qualit1t: AGENT_Code_Reviewer
  - DevOps/Pipelines: AGENT_DevOps_Engineer
- Prompts/Templates: f1r Systemprompt PROMPT_MAIN_Codex_Orchestrator; Task-Brief 1ber PROMPT_Task_Brief_Template; Reports 1ber PROMPT_Analysis_Report_Format.

## Entscheidungs- & Approval-Punkte
- Phase-Wechsel Analyse  Delivery: nur mit User-Freigabe; Branch + PR Pflicht.
- Risk-relevante 1nderungen (Trading-Logik, Limits, Mode-Change, Deployment): Risk Architect pr1fen; Stop/Go mit klaren Acceptance/Stop-Kriterien.
- Secrets/Infra: keine Live-Secrets schreiben; keine Proxies f1r WS; Postgres ein User/Pass aus Secret.
- CI/CD/Prod: keine Live-Trading ohne definierten Risk-Workflow; Deploy/Flag-Changes nur mit Rollback-Plan.
- Doku/Governance: Anpassungen nur 1ber WORKFLOW_Governance_Update; DECISION_LOG-Eintrag bei Governance-/Risk-Entscheidung.
- Logging: cdb-logger Events f1r Start/Analyse/Delegation/Review/Abschluss; PR-Links bei Delivery.

## Umgang mit veralteten Workflows
- WORKFLOW_Repo_Audit nicht vorhanden -> als deprecated markieren.
- Ersatzpfad: Struktur-/Hygiene-Themen 1ber AGENT_Repository_Auditor + AGENT_Stability_Guardian, gesteuert 1ber WORKFLOW_Governance_Update (Governance/Doku) oder WORKFLOW_Feature_Implementation (wenn 1nderungen im Code/Struktur). Keine Nutzung verwaister Pfade.

## Schnelle Checkliste pro Task
- [ ] Phase = Analyse (default); Delivery nur nach Go.
- [ ] MCP-Stack aktiv (agents-sync, filesystem, github-official, playwright, cdb-logger).
- [ ] Routing gesetzt: Visionary  Visualizer  Stability  Fachagenten.
- [ ] Risk/Gov Gates gepr1ft (Risk-Impact, Secrets, Branch/PR, Rollback, Doku/Logs).
- [ ] Logs geschrieben (Start/Analyse/Delegation/Review/Abschluss) + DECISION_LOG falls Governance/Risk.
- [ ] Plateau eingehalten: k1hlen  validieren  aufr1umen  weiter.
