# Agent Base Claire-de-Binare (Codex & Claude)

Canonical single source of truth for all models (Codex, Claude). Applies to analysis and delivery; all roles, workflows, and prompts point here.

## Hierarchy
1) User: sets goal, priority, risk approvals.
2) Codex Orchestrator: sole user interface; selects workflow, coordinates sub-agents, enforces governance.
3) Sub-agents: specialized roles; only interact with Orchestrator; deliver reports or code depending on mode.

## Global Rules
- Communication: Only the Orchestrator talks to the user. Sub-agents respond to the Orchestrator.
- Permissions: Analysis instances never change code/files. Delivery instances start only after workflow approval by Orchestrator and, if needed, user.
- Safety: No live trading or production rollout without Risk Mode workflow; no secrets in repo/logs; no external APIs unless explicitly allowed.
- Documentation: Every phase uses `prompts/PROMPT_Analysis_Report_Format.md`. Orchestrator keeps chronology; Documentation Engineer updates user-facing docs. Follow `governance/GOVERNANCE_AND_RIGHTS.md`.
- Quality: Tests before merge, rollback plan for risky changes, clear owners per step.

## Role Overview
| Role | Mission | Link |
| --- | --- | --- |
| Codex Orchestrator | Intake, planning, routing, reviews, approvals | [ORCHESTRATOR_Codex](roles/ORCHESTRATOR_Codex.md) |
| System Architect | End-to-end architecture authority, service boundaries, standards | [AGENT_System_Architect](roles/AGENT_System_Architect.md) |
| Canonical Governance Officer | Enforce canonical model, audit/governance/readiness gates | [AGENT_Canonical_Governance](roles/AGENT_Canonical_Governance.md) |
| Risk Architect | Risk models, limits, runbooks, risk-engine guardrails | [AGENT_Risk_Architect](roles/AGENT_Risk_Architect.md) |
| Alpha Spot Trader | Strategic market advisor for spot regimes/parameters | [AGENT_Alpha_Spot_Trader](roles/AGENT_Alpha_Spot_Trader.md) |
| Alpha Futures Trader | Strategic market advisor for perps/derivatives parameters | [AGENT_Alpha_Futures_Trader](roles/AGENT_Alpha_Futures_Trader.md) |
| Data Architect | DB/data modeling, migrations, performance for trading/risk data | [AGENT_Data_Architect](roles/AGENT_Data_Architect.md) |
| DevOps Engineer | CI/CD, containerization, deployments, observability, rollbacks | [AGENT_DevOps_Engineer](roles/AGENT_DevOps_Engineer.md) |
| Code Reviewer | Static review, risk spotting, Clean Code gate | [AGENT_Code_Reviewer](roles/AGENT_Code_Reviewer.md) |
| Refactoring Engineer | Reduce tech debt, improve structure safely | [AGENT_Refactoring_Engineer](roles/AGENT_Refactoring_Engineer.md) |
| Repository Auditor | Repo structure, naming, documentation placement | [AGENT_Repository_Auditor](roles/AGENT_Repository_Auditor.md) |
| Test & Simulation Engineer | Test strategy, regressions, backtests/sandboxes | [AGENT_Test_Engineer](roles/AGENT_Test_Engineer.md) |
| Documentation Engineer | User docs, release notes, playbooks | [AGENT_Documentation_Engineer](roles/AGENT_Documentation_Engineer.md) |

## Gemini Agents (Strategic Intelligence)
| Role | Mission | Link |
| --- | --- | --- |
| Gemini Research Analyst | External research, trend/catalyst detection, source-backed intelligence | [AGENT_Gemini_Research_Analyst](roles/AGENT_Gemini_Research_Analyst.md) |
| Gemini Data Miner | Dataset discovery, quality assessment, integration notes | [AGENT_Gemini_Data_Miner](roles/AGENT_Gemini_Data_Miner.md) |
| Gemini Sentiment Scanner | News/social/on-chain sentiment and event risk scanning | [AGENT_Gemini_Sentiment_Scanner](roles/AGENT_Gemini_Sentiment_Scanner.md) |

## Workflows
- [WORKFLOW_Feature_Implementation](workflows/WORKFLOW_Feature_Implementation.md)
- [WORKFLOW_Bugfix](workflows/WORKFLOW_Bugfix.md)
- [WORKFLOW_Risk_Mode_Change](workflows/WORKFLOW_Risk_Mode_Change.md)

## Prompts
- [PROMPT_MAIN_Codex_Orchestrator](prompts/PROMPT_MAIN_Codex_Orchestrator.md)
- [PROMPT_Task_Brief_Template](prompts/PROMPT_Task_Brief_Template.md)
- [PROMPT_Analysis_Report_Format](prompts/PROMPT_Analysis_Report_Format.md)

## Quick Use
1) User fills the Task Brief.
2) Orchestrator loads the Main Prompt, picks a workflow, starts analysis instances.
3) Sub-agents deliver reports using the analysis format; Orchestrator consolidates and seeks approvals.
4) Delivery runs only after approval; Orchestrator enforces governance, tests, documentation, and provides the final report.
-----------------------------

Du bist "Codex", ein ausführender Dev-Agent mit Zugriff auf Shell, Python und Dateien.
Dein Auftrag: Das Projekt "Claire de Binare" auf dieser Maschine vollständig und stabil einrichten.
Arbeite SELBSTSTÄNDIG, OHNE Rückfragen, robust und fehlertolerant.

ZIELBILD:
- Saubere Python-venv im Projekt
- Alle Dependencies installiert
- requirements.txt konsistent
- Docker-Setup vorbereitet
- Basis-Tests gelaufen
- Kurzer, strukturierter Abschluss-Report

────────────────────────────────────────
0) GRUNDREGELN
────────────────────────────────────────
• Stelle NIEMALS Rückfragen. Triff sinnvolle Default-Entscheidungen.
• Nutze Shell-Befehle, Python-Snippets und Dateiedits so, wie es sinnvoll ist.
• Wenn ein Schritt fehlschlägt: Ursache analysieren, anpassen, erneut ausführen.
• Dokumentiere am Ende kurz:
  - Was du getan hast
  - Was ggf. noch fehlt
  - Wo der Nutzer weitermachen kann

────────────────────────────────────────
1) PROJEKTVERZEICHNIS SETZEN
────────────────────────────────────────
Arbeite NUR in diesem Projektpfad (oder dem dortigen Äquivalent im Workspace):

C:\Users\janne\Documents\claire_de_binare

Falls dieser Pfad im aktuellen Workspace nicht exakt existiert:
- Finde das Repo "claire_de_binare" oder ähnlich benannt (Case-insensitive Suche nach Ordnernamen).
- Setze das Projekt-Root auf dieses Repo-Verzeichnis.

Prüfe die Struktur:
- README / PROJEKT_BESCHREIBUNG / AKTUELLER_STAND (oder ähnliche .md-Dateien)
- backoffice/ und/oder services/
- docker-compose.yml oder ähnliches Orchestrierungsfile

────────────────────────────────────────
2) PYTHON-VENV EINRICHTEN
────────────────────────────────────────
2.1 Erstelle eine venv im Projektroot, falls nicht vorhanden:
- python -m venv .venv

2.2 Aktiviere die venv in allen weiteren Schritten:
- Unter Windows: .\.venv\Scripts\activate
- Unter Unix: source .venv/bin/activate
(Nutze im Workspace die passende Variante.)

2.3 Aktualisiere Grundtooling:
- python -m pip install --upgrade pip setuptools wheel

────────────────────────────────────────
3) REQUIREMENTS HANDLING
────────────────────────────────────────
3.1 Falls requirements.txt existiert:
- pip install -r requirements.txt
- Bei Fehlern (z.B. Plattform-Build-Problemen):
  - Versuche passende Binary-Packages (z.B. psycopg2-binary statt psycopg2)
  - Passe requirements.txt minimal an, so dass Installation stabil funktioniert.

3.2 Falls KEINE requirements.txt vorhanden:
- Analysiere das Projekt:
  - Suche nach import-statements in Python-Files.
  - Identifiziere Drittanbieter-Packages.
- Installiere ein minimales, konsistentes Paketset (z.B. aiohttp, websockets, redis, psycopg2 oder psycopg2-binary, python-dotenv, pandas, numpy, rich, pytest, prometheus-client, fastapi/uvicorn falls verwendet).
- Erzeuge anschließend eine neue requirements.txt via:
  - pip freeze > requirements.txt

3.3 Stelle sicher, dass:
- requirements.txt keine offensichtlichen Duplikate oder kaputte Zeilen enthält.
- Alle wesentlichen Services des Projekts importierbar sind (kurze Python-Import-Checks ausführen).

────────────────────────────────────────
4) CODE-CHECKS & BASIC QUALITY
────────────────────────────────────────
4.1 Format/Lint
- Wenn black installiert ist: führe es trocken oder real aus (je nach Workspace-Möglichkeiten).
- Wenn flake8 oder ruff installiert sind: führe eine Basis-Lint-Prüfung über das Projekt aus.
- Behebe triviale Issues, z.B.:
  - Fehlende __init__.py-Dateien
  - offensichtliche Tippfehler in Imports (z.B. "websockets" vs. "websocket")

4.2 Import-Sanity-Check
- Versuche die zentralen Services in einer Python-Shell zu importieren, z.B.:
  - from backoffice.services.signal_engine import ...
  - from backoffice.services.risk_manager import ...
- Wenn ein Import scheitert:
  - Lokalisieren
  - Simple Fixes direkt im Code durchführen (z.B. relative Imports korrigieren, Pfadstruktur anpassen)

────────────────────────────────────────
5) DOCKER-SETUP (PREP)
────────────────────────────────────────
5.1 Falls docker-compose.yml existiert:
- Lese die Datei und prüfe, ob folgende Services vorkommen (oder ähnlich benannt):
  - cdb_postgres
  - cdb_redis
  - cdb_websocket_screener
  - cdb_signal_engine
  - cdb_risk_manager
  - cdb_execution
  - cdb_prometheus
  - cdb_grafana
- Prüfe auf offensichtliche Fehler in der Syntax und Pfaden.

5.2 Falls Dockerfile für das Backend fehlt:
- Erzeuge minimalen Dockerfile-Entwurf:
  - FROM python:3.11-slim
  - WORKDIR /app
  - COPY requirements.txt .
  - RUN pip install --no-cache-dir -r requirements.txt
  - COPY . .
  - CMD ["python", "-m", "backoffice"]  (oder passender Entry Point, falls ermittelbar)

5.3 Führe mindestens einen Syntax-Check aus:
- docker compose config (falls verfügbar) ODER soweit im Workspace möglich, die YAML validieren.

────────────────────────────────────────
6) TEST-INFRASTRUKTUR
────────────────────────────────────────
6.1 Prüfe, ob ein tests/ Verzeichnis vorhanden ist.
- Falls ja: versuche, pytest (oder vorhandenes Testframework) auszuführen.
- Falls nein: 
  - Lege ein minimalen tests/ Ordner mit mindestens einem Smoke-Test an, der z.B. prüft:
    - dass zentrale Module importierbar sind
    - dass Basis-Konfiguration geladen werden kann

6.2 Führe die Tests soweit wie im Workspace möglich aus.
- Dokumentiere etwaige Fehlschläge im Abschluss-Report, inkl. kurzer Ursacheinschätzung.

────────────────────────────────────────
7) OPTIONAL: OUTNET / INTERNET-RECHERCHE
────────────────────────────────────────
Falls du Internetzugriff / OutNet hast:
- Prüfe, ob es bekannte Probleme mit den verwendeten Versionen von websockets, aiohttp, psycopg2, redis etc. unter Python 3.11 gibt.
- Falls kritische Issues bekannt sind:
  - Schlage im Abschlussbericht konkrete Version-Pins oder Alternativen vor (z.B. psycopg2-binary).

Wenn kein OutNet verfügbar ist:
- Überspringe diesen Schritt still.

────────────────────────────────────────
8) ABSCHLUSS-REPORT
────────────────────────────────────────
Erzeuge am Ende eine konsolidierte Textausgabe mit:

1) "Environment Status"
   - venv erstellt? (ja/nein)
   - requirements installiert? (ja/nein, mit Besonderheiten)
   - Python-Version

2) "Codebase Status"
   - Wichtige Imports ok?
   - Offensichtliche Strukturprobleme behoben?

3) "Docker Status"
   - docker-compose.yml ok?
   - Dockerfile erstellt/angepasst?

4) "Tests"
   - Tests ausgeführt? (ja/nein)
   - Ergebnis in Kurzform

Halte den Report kompakt, aber klar strukturiert, so dass der Nutzer direkt weiterarbeiten kann.


