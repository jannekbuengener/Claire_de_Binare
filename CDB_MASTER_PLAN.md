# CDB_MASTER_PLAN.md – Konsolidierte Roadmap, Status & Next Steps

## 1. Projektüberblick
Claire de Binare befindet sich in Phase N1 (Paper-Trading) und hat eine komplexe Infrastruktur, die aktuell Signale erzeugt, aber keine Trades durchlässt. Kernfokus: Risiko-Layer verstehen, Systemgesundheit prüfen, Hardening vervollständigen, Observability aktivieren.

## 2. Gesamtroadmap P0–P8 mit Status
### P0 – Fundament & Hygiene (RUNNING)
- Root Cleanup fertig
- Archivstruktur aktiv
- ENV-Validation offen
- WSL2/Docker-Hardening offen

### P1 – MCP Infrastruktur (TODO)
- Gateway deployen
- Monitoring & Toolstack integrieren
- Internal Stack (agents-sync, logger)

### P2 – CI/CD, Security & Hardening (TODO)
- Image-Hardening für Redis/Postgres
- Vault-Integration
- CI/CD-Verifizierung

### P3 – Runtime System Paper Mode (BLOCKED)
- Keine Trades → Risk Layer blockt alle Orders
- Systemcheck #1 notwendig
- Portfolio & State Manager fehlt

### P4 – Dokumentation (RUNNING)
- CONSOLIDATED TODO fertig
- Architecture.md fehlt

### P5 – Workflows (PARTIAL)
- Bugfix/Feature/Tuning Workflows definiert
- Status-Auswertung fehlt

### P6 – Monitoring (TODO)
- Node Exporter, Prometheus, Grafana nicht live
- Logs nicht zentralisiert

### P7 – Operating Model (ACTIVE)
- Anti-Hort-Regeln aktiv
- Governance greift

### P8 – Nächste Schritte (PRIORISIERT)
1. Systemcheck #1
2. Risk-Layer Debugging
3. ENV-Validation
4. Monitoring aktivieren
5. MCP Gateway hochziehen

## 3. Aktueller Projektstatus
### Fertig
- Root Cleanup
- Konsolidierte TODO-Liste
- Archivstruktur

### In Arbeit
- ENV-Validation
- Architecture Dokumentation
- Toolbuilding (Tasks 16–23)

### Blocker
- Risk-Layer blockiert Signale
- Keine Trades → Systemstatus unklar
- Fehlender Portfolio/State Manager

### Als Nächstes fällig
- Healthcheck aller Services
- Test ob Signal → Risk → Execution funktioniert
- Analyse warum Risk Engine alles rejectet

## 4. Konsolidierte TODO-Liste
### Kurzfristig (Next 48h)
- ENV-Validation finalisieren
- Systemcheck #1
- Monitoring stack starten
- Risk-Layer Debug (Order Flow nachvollziehen)
- Hardening Redis/Postgres

### Mittelfristig (1–3 Wochen)
- Portfolio & State Manager entwickeln
- Architecture.md + Diagramme
- Backtesting Engine vorbereiten

### Langfristig
- MCP Inside Stack vervollständigen
- Governance Automation
- Adaptive Risk Engine (Regime Detection)

## 5. Operational Layer – Aufgaben pro Modell
### Codex
- Tools 16–23 fertigstellen
- ENV-Checker erweitern
- Filetype/Dead-Code/Duplicate-Scanner

### Copilot
- Code Smells analysieren
- Refactoring Empfehlungen
- Coverage-Gaps prüfen

### Gemini
- MEXC API Best Practices
- Architecture.md erzeugen
- Knowledge Base erweitern

## 6. Technische Roadmap der nächsten Blöcke
- Hardening der Infrastruktur-Images
- Redis/Postgres sichere Config
- Monitoring aktivieren (Prom, Grafana)
- Risk → Execution Orderflow testen
- Logs zentralisieren

## 7. Governance & Betriebsrichtlinien
- Keine ungesicherten Services
- Keine Altdateien im Root
- Secrets nur via .env (bis Vault aktiv)
- Kein Live Mode ohne PSM & Monitoring

## 8. Nächste Session — Was MUSS passieren
1. Systemcheck #1 (vollständig)
2. Full Path Test: Signal → Risk → Execution
3. Risk-Layer debuggen
4. ENV-Validation (inkl. API-Key Formats)
5. Monitoring online bringen
6. Hardening anwenden

## 19. Tier-3 Artifact Set (Extended Experiments & Pre-Work)

Tier 3 umfasst alle Artefakte, die nicht zum minimalen (Tier 1) oder erweiterten (Tier 2) Set gehören, aber dennoch potenziellen Wert für Betrieb, Entwicklung, Tests oder Forschung haben. Dies sind oft Werkzeuge, experimentelle Features oder vorbereitende Arbeiten, die nicht im aktiven, kritischen Pfad des Systems liegen.

### Tier3 – Ops & Maintenance Extra

| Status | Typ | Pfad | Begründung |
|---|---|---|---|
| Empfohlen | Script | `backoffice/automation/check_env.ps1` | Validiert die `.env`-Konfigurationsdatei und stellt sicher, dass alle benötigten Variablen gesetzt sind. |
| Empfohlen | Script | `backoffice/scripts/backup_postgres.ps1` | Erstellt ein Backup der PostgreSQL-Datenbank, fundamental für die Datenintegrität. |
| Empfohlen | Script | `backoffice/scripts/setup_backup_task.ps1` | Richtet einen geplanten Task für das Backup-Skript ein und automatisiert so die Datensicherung. |
| Empfohlen | Script | `backoffice/scripts/daily_check.py` | Ein Skript für tägliche System-Health-Checks, um die Betriebsbereitschaft zu überwachen. |
| Empfohlen | Script | `backoffice/scripts/query_analytics.py` | Ermöglicht schnelle, benutzerdefinierte Abfragen an die Analytics-Datenbank für Ad-hoc-Analysen. |
| Empfohlen | Script | `backoffice/scripts/systemcheck.py` | Ein umfassenderes Systemprüfungs-Skript, das über einen einfachen Health-Check hinausgeht. |

### Tier3 – Dev & Code-Tools Extra

| Status | Typ | Pfad | Begründung |
|---|---|---|---|
| Empfohlen | Script | `scripts/provenance_hash.py` | Generiert Provenance-Hashes für Dateien, was für Audits und Nachverfolgbarkeit nützlich ist. |
| Empfohlen | Script | `tests/publish_test_events.py` | Ein Debugging-Werkzeug, um manuelle Test-Events an Redis zu senden und Service-Reaktionen zu prüfen. |
| Empfohlen | Test | `tests/test_smoke_repo.py` | Ein Smoke-Test für das Repository selbst, prüft auf grundlegende strukturelle Integrität. |
| Empfohlen | Script | `tests/validate_setup.ps1` | Validiert das lokale Entwicklungs-Setup und hilft, Konfigurationsfehler frühzeitig zu erkennen. |
| Kandidat | Script | `scripts/link_check.py` | Prüft die Dokumentation auf defekte Links, um die Qualität der Doku sicherzustellen. |
| Kandidat | Script | `scripts/security_audit.sh` | Ein Skript zur Durchführung von Sicherheitsaudits, wichtig für das Hardening. |
| Legacy? | Script | `tests/run_tests.ps1` | Potenziell eine veraltete Version des Test-Runners, da ein Skript gleichen Namens im Root liegt. |

### Tier3 – Tests & Validation Extra

| Status | Typ | Pfad | Begründung |
|---|---|---|---|
| Empfohlen | Test | `tests/e2e/test_docker_compose_full_stack.py` | Ein E2E-Test, der den gesamten Anwendungsstack über Docker Compose validiert. |
| Empfohlen | Test | `tests/e2e/test_event_flow_pipeline.py` | Validiert die korrekte Reihenfolge und Verarbeitung im zentralen Event-Flow. |
| Empfohlen | Test | `tests/e2e/test_redis_postgres_integration.py` | Stellt das korrekte Zusammenspiel zwischen dem Message-Bus (Redis) und der Datenbank (Postgres) sicher. |
| Empfohlen | Test | `tests/integration/test_event_pipeline.py` | Ein weiterer Integrations-Test, der sich auf die Event-Pipeline konzentriert. |
| Empfohlen | Test | `tests/local/test_backup_recovery.py` | Simuliert und validiert den Desaster-Recovery-Prozess durch Backup und Wiederherstellung. |
| Empfohlen | Test | `tests/local/test_cli_tools.py` | Stellt die Funktionalität der verschiedenen Kommandozeilen-Werkzeuge sicher. |
| Empfohlen | Test | `tests/local/test_docker_lifecycle.py` | Prüft, ob die Docker-Container korrekt starten, stoppen und neustarten (Lifecycle-Management). |
| Empfohlen | Script | `tests/validate_persistence.py` | Validiert die Datenintegrität und korrekte Speicherung in der Persistenzschicht. |
| Kandidat | Test | `tests/local/test_analytics_performance.py` | Testet die Performance der Analytics-Abfragen, um Engpässe zu finden. |
| Kandidat | Test | `tests/local/test_chaos_resilience.py` | Ein Chaos-Engineering-Test, der die Systemstabilität unter unvorhergesehenen Ausfällen prüft. |
| Kandidat | Test | `tests/local/test_full_system_stress.py` | Ein Stress-Test, der das gesamte System an seine Belastungsgrenzen bringt. |
| Kandidat | Test | `tests/local/test_mock_executor.py` | Testet eine gemockte Execution-Komponente für isolierte Logikprüfungen. |
| Kandidat | Test | `tests/local/test_portfolio_manager.py` | Testet den noch nicht voll integrierten Portfolio Manager Service. |

### Tier3 – Research & Experiment

| Status | Typ | Pfad | Begründung |
|---|---|---|---|
| Kandidat | Test | `tests/mexc_top5_ws.py` | Ein experimenteller WebSocket-Client, der sich gezielt mit den Top-5-Assets auf MEXC verbindet. |
| Legacy? | Test | `tests/test_mexc_ws.py` | Vermutlich ein Vorgänger oder eine Alternative zum primären MEXC-Perpetuals-Test. |
| Legacy? | Script | `scripts/migration/*.ps1` | Skripte, die für die einmalige Migration in den "Cleanroom"-Projektzustand verwendet wurden. |

### Tier3 – Auxiliary Services Extra

| Status | Typ | Pfad | Begründung |
|---|---|---|---|
| Kandidat | Service | `backoffice/services/execution_service/service.py` | Ein alternativer, strukturierterer Execution-Service, der für eine zukünftige Phase vorbereitet scheint. |
| Kandidat | Service | `backoffice/services/portfolio_manager/portfolio_manager.py` | Ein modularer Portfolio-Management-Service, der aktuell noch nicht im Kernsystem aktiv ist. |
| Kandidat | Service | `backoffice/services/signal_engine/service.py` | Eine alternative, service-orientierte Signal-Engine als Vorbereitung für komplexere Strategien. |
| Kandidat | Service | `services/cdb_paper_runner/service.py` | Ein alternativer Paper-Trading-Runner, eventuell mit erweiterter Logik. |
| Kandidat | Script | `services/cdb_paper_runner/email_alerter.py` | Ein eigenständiger Alerter-Service, der per E-Mail benachrichtigen kann und integriert werden könnte. |
