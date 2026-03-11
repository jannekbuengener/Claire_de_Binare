============================================================
CLAIRE DE BINARE - MASTER ROADMAP (CANONICAL)
============================================================

ZWECK
-----
Dieses Dokument ist die vollstaendige, konsolidierte Roadmap
fuer das Projekt "Claire de Binare".

Es ersetzt:
- fragmentierte Roadmaps
- Einzelnotizen
- implizite Abhaengigkeiten
- widerspruechliche Planungen

Es dient als:
- Single Source of Truth
- Grundlage fuer GitHub Issues
- Arbeitsplan fuer Agenten
- Gemeinsames mentales Modell


============================================================
AGENTEN-GOVERNANCE (VERBINDLICH)
============================================================

CLAUDE (Claude Code)
-------------------
- EINZIGER Agent, der am Docker-Stack arbeitet
- Zustaendig fuer:
  - docker-compose
  - Container und Images
  - Redis / Postgres / Grafana Konfiguration
  - Runtime-Wiring
  - Stack-Security-Fixes
  - CI-relevante Infra-Aenderungen

GEMINI
------
- ANALYSE UND AUDIT ONLY
- Darf:
  - Grafana analysieren
  - Redis-Zustaende auswerten
  - Risiken und Findings formulieren
- Darf NICHT:
  - Dockerfiles aendern
  - Compose aendern
  - Konfiguration implementieren

CODEX
-----
- Code-Implementierung im Working Repo
- Keine Docker-, Infra- oder Stack-Arbeit

COPILOT
-------
- Hygiene, Assistenz, Vorschlaege
- Keine kritischen oder systemrelevanten Aenderungen


============================================================
PHASE 0 - FUNDAMENT UND REPRODUZIERBARKEIT
============================================================

ZIEL
----
Der Stack startet reproduzierbar mit einem Befehl
und bleibt stabil.

AUFGABEN
--------
- docker compose kanonisch machen
- Crash- und Restart-Loops eliminieren
- Monitoring automatisch provisionieren

BESTEHENDE ISSUES
-----------------
- #232 Compose project/network name
- #231 Compose env wiring + Grafana provisioning
- #223 Dataclass field order crash
- #226 Risk service import crash

NEUE ISSUE-IDEEN
----------------
- Canonical Known-Good Stack Definition
- Startup Health Contract
- Crash-Loop Detection Rule

AGENT
-----
Claude


============================================================
PHASE 1 - SECURITY BASELINE
============================================================

ZIEL
----
Der Stack ist stabil UND sicher.

AUFGABEN
--------
- Redis Base Image aktualisieren (CRITICAL CVEs)
- Postgres Base Image aktualisieren
- Secrets robust laden (File/Directory/Env)
- Postgres RBAC umsetzen
- CI Vulnerability Scan einfuehren

NEUE ISSUE-IDEEN
----------------
- Redis Base Image Upgrade
- Postgres RBAC Hardening
- CI Security Gate

AGENT
-----
Claude

AUDIT
-----
Gemini


============================================================
PHASE 2 - PAPER TRADING END-TO-END
============================================================

ZIEL
----
Deterministischer, persistenter Paper-Trading-Fluss.

IST-ZUSTAND
-----------
- MockExecutor aktiv
- PaperTradingEngine existiert, aber nicht verdrahtet
- Risk-Metriken sind Placeholder

BESTEHENDE ISSUES
-----------------
- #225 order_results not published
- #229 P0 E2E validation
- #230 test harness bug
- #231 drawdown und circuit breaker cases
- #227 deterministic breaker reset

NEUE ISSUE-IDEEN
----------------
- PaperTradingEngine in Execution integrieren
- Pluggable Execution Interface
- Persistente Paper-Trading-Sessions
- Deterministischer Replay-Modus

AGENT RUNTIME
-------------
Claude

AGENT CODE
----------
Codex

AUDIT
-----
Gemini


============================================================
PHASE 3 - OBSERVABILITY UND PERFORMANCE
============================================================

ZIEL
----
Systemverhalten ist messbar und vergleichbar.

AUFGABEN
--------
- Performance-Baselines definieren
- End-to-End-Latenzen messen
- Sinnvolle Alerts definieren

NEUE ISSUE-IDEEN
----------------
- End-to-End Latency Tracing
- Automatische Baseline Snapshots
- Alerting Contracts

AGENT
-----
Claude

AUDIT
-----
Gemini


============================================================
PHASE 4 - TESTNET UND VALIDATION GATES
============================================================

ZIEL
----
Reale Marktbedingungen ohne Echtgeld.

AUFGABEN
--------
- MEXC Testnet Executor
- 72h Validierung mit echten Metriken
- Automatische Freigabe oder Blockade

NEUE ISSUE-IDEEN
----------------
- Testnet Execution Adapter
- Validation Gate Engine
- Auto-Freeze bei Failure

AGENT RUNTIME
-------------
Claude

AGENT CODE
----------
Codex


============================================================
PHASE 5 - REAL MONEY TRADING
============================================================

ZIEL
----
Kontrollierter Uebergang zu Echtgeld.

AUFGABEN
--------
- Feature Flags fuer Trading Modes
- Emergency Stop (manuell und automatisch)
- Human-in-the-Loop Oversight

BASIS
-----
REAL_MONEY_TRADING_ROADMAP.md

AGENT
-----
Claude

AUDIT
-----
Gemini


============================================================
PHASE 6 - WORKFLOW UND AGENTEN-ORCHESTRIERUNG
============================================================

ZIEL
----
Nachhaltige Weiterentwicklung ohne Chaos.

AUFGABEN
--------
- Single-Orchestrator-Workflow durchsetzen
- Agent Guardrails validieren
- Roadmap zu Issue Automatisierung

AGENT
-----
Claude

SUPPORT
-------
Copilot


============================================================
ABSCHLUSS
============================================================

Diese Roadmap ist die Karte.

Ab jetzt gilt:
- Fortschritt = Issues schliessen
- Klarheit = Reihenfolge einhalten
- Sicherheit = Agenten-Grenzen respektieren

Kein neues Denken.
Nur noch saubere Ausfuehrung.
============================================================


