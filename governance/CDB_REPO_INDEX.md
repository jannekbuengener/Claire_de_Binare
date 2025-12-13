### Validierungsbericht

#### TIER 1 (t1)
WIRD REINGEHOLT WENN ORDNUNG IST!
*   **Missing:** Keine
*   **Too much:** Keine
*   **Wrong tier:** Keine
*   **Duplicates / Conflicts:** Keine
*   **Tier-Kommentar:** Das Tier 1 ist jetzt sauber und enthält ausschließlich Essential Core Komponenten.

#### TIER 2 (t2)
WIRD REINGEHOLT WENN TIER 1 MIGRIERT IST!
*   **Missing:** Keine
*   **Too much:** Keine
*   **Wrong tier:** Keine
*   **Duplicates / Conflicts:** Keine
*   **Tier-Kommentar:** Das Tier 2 ist jetzt sauber und enthält nur produktive Tools und DevOps-Elemente, die nicht explizit Tier 3 sind.

#### TIER 3 (t3)
WIRD REINGEHOLT WENN TIER 2 MIGRIERT IST!
*   **Missing:** Keine (Die laut Governance definierten, aber im Repo noch nicht vorhandenen T3-Dateien gelten hier nicht als Fehler.)
*   **Too much:** Keine
*   **Wrong tier:** Keine
*   **Duplicates / Conflicts:** Keine
*   **Tier-Kommentar:** Das Tier 3 enthält nun alle explizit definierten Research-, Legacy- und experimentellen Komponenten sowie die umklassifizierten Dateien aus T1 und T2.

---

### CDB_REPO_INDEX.md

#### Repository Overview

*   **/t1**: Enthält die Essential Core Komponenten des Systems, die für den grundlegenden Betrieb und die Kernfunktionalität unerlässlich sind.
*   **/t2**: Beherbergt produktive Werkzeuge und DevOps-Skripte, die den täglichen Betrieb unterstützen und nicht zum Kernsystem oder zu experimentellen Zwecken gehören.
*   **/t3**: Umfasst Research-, Legacy- und experimentelle Komponenten, sowie spezifische Ops-Extras, Heavy-Tests und alternative Service-Implementierungen.
*   **/governance**: Enthält die grundlegenden Dokumente, die die Prinzipien, die Governance und den Masterplan des gesamten CDB-Projekts beschreiben.

#### File Index

**governance/**
*   `governance/CDB_FOUNDATION.md` – Beschreibt die grundlegenden Prinzipien und Werte des CDB-Projekts.
*   `governance/CDB_GOVERNANCE.md` – Legt die Regeln und Strukturen für die Projektverwaltung und Entscheidungsfindung fest.
*   `governance/CDB_INSIGHTS.md` – Enthält strategische Einblicke und Analysen zur Weiterentwicklung des Projekts.
*   `governance/CDB_MASTER_PLAN.md` – Der umfassende Masterplan und die Roadmap für das CDB-Projekt.
*   `governance/CDB_WORKFLOWS.md` – Dokumentiert die operativen Workflows und Prozesse innerhalb des Projekts.

**t1/**
*   `t1/.dockerignore` – Definiert Dateien und Verzeichnisse, die von Docker-Builds ausgeschlossen werden sollen.
*   `t1/.env.example` – Eine Vorlage für Umgebungsvariablen, die für die Anwendung benötigt werden.
*   `t1/.gitignore` – Spezifiziert Dateien und Verzeichnisse, die von der Git-Versionskontrolle ignoriert werden sollen.
*   `t1/cdb_paper_runner.Dockerfile` – Dockerfile für den Kernservice des Paper Runners.
*   `t1/DATABASE_SCHEMA.sql` – Definiert das Datenbankschema für die zentralen Datenbanken des Projekts.
*   `t1/docker-compose.yml` – Definiert die Multi-Container-Docker-Anwendung für die lokale Entwicklung und Bereitstellung.
*   `t1/Dockerfile` – Das Haupt-Dockerfile für die Kernanwendung oder den Arbeitsbereich.
*   `t1/Makefile` – Enthält Automatisierungsskripte für Build-, Test- und Deployment-Aufgaben.
*   `t1/prometheus.yml` – Konfiguration für das Monitoring-System Prometheus.
*   `t1/pytest.ini` – Konfigurationsdatei für das Pytest-Test-Framework.
*   `t1/requirements-dev.txt` – Listet die Python-Abhängigkeiten für die Entwicklungsumgebung auf.
*   `t1/requirements.txt` – Listet die Produktions-Python-Abhängigkeiten auf.
*   `t1/run-tests.ps1` – Ein PowerShell-Skript zum Ausführen der Tests.
*   `t1/.github/workflows/ci.yaml` – GitHub Actions Workflow-Definition für Continuous Integration.
*   `t1/cdb_paper_runner/Dockerfile` – Dockerfile spezifisch für den Paper Runner Dienst.
*   `t1/cdb_paper_runner/requirements.txt` – Python-Abhängigkeiten für den Paper Runner Dienst.
*   `t1/db_writer/db_writer/__init__.py` – Initialisierungsdatei für das db_writer Python-Modul.
*   `t1/db_writer/db_writer/db_writer.py` – Implementiert die Logik zum Schreiben von Daten in die Datenbank.
*   `t1/db_writer/Dockerfile` – Dockerfile für den db_writer Dienst.
*   `t1/execution_service/execution_service/__init__.py` – Initialisierungsdatei für das execution_service Python-Modul.
*   `t1/execution_service/execution_service/config.py` – Konfigurationseinstellungen für den Execution Service.
*   `t1/execution_service/execution_service/database.py` – Datenbank-Konnektivität und Operationen für den Execution Service.
*   `t1/execution_service/execution_service/EXECUTION_SERVICE_STATUS.md` – Dokumentiert den Status des Execution Service.
*   `t1/execution_service/execution_service/mock_executor.py` – Stellt eine Mock-Implementierung für Ausführungslogik bereit.
*   `t1/execution_service/execution_service/models.py` – Datenmodelle für den Execution Service.
*   `t1/execution_service/execution_service/requirements.txt` – Python-Abhängigkeiten für den Execution Service.
*   `t1/execution_service/execution_service/service.py` – Die Hauptlogik des Execution Service.
*   `t1/execution_service/Dockerfile` – Dockerfile für den Execution Service.
*   `t1/grafana/DASHBOARD_IMPORT.md` – Anweisungen zum Importieren von Grafana-Dashboards.
*   `t1/grafana/dashboards/claire_dark_v1.json` – Grafana-Dashboard-Definition für das "Claire Dark" Layout.
*   `t1/grafana/dashboards/claire_execution_v1.json` – Grafana-Dashboard für die Überwachung der Ausführung.
*   `t1/grafana/dashboards/claire_paper_trading_v1.json` – Grafana-Dashboard für Paper Trading-Analysen.
*   `t1/grafana/dashboards/claire_risk_manager_v1.json` – Grafana-Dashboard zur Überwachung des Risikomanagers.
*   `t1/grafana/dashboards/claire_signal_engine_v1.json` – Grafana-Dashboard zur Überwachung der Signal Engine.
*   `t1/grafana/dashboards/claire_system_performance_v1.json` – Grafana-Dashboard zur Analyse der Systemleistung.
*   `t1/grafana/provisioning/dashboards/claire.yml` – Grafana-Provisioning-Datei für "Claire"-Dashboards.
*   `t1/grafana/provisioning/datasources/postgres.yml` – Grafana-Provisioning-Datei für die PostgreSQL-Datenquelle.
*   `t1/grafana/provisioning/datasources/prometheus.yml` – Grafana-Provisioning-Datei für die Prometheus-Datenquelle.
*   `t1/migrations/002_orders_price_nullable.sql` – Datenbank-Migrationsskript zur Anpassung der "orders"-Tabelle.
*   `t1/risk_manager/risk_manager/__init__.py` – Initialisierungsdatei für das risk_manager Python-Modul.
*   `t1/risk_manager/risk_manager/config.py` – Konfigurationseinstellungen für den Risk Manager.
*   `t1/risk_manager/risk_manager/models.py` – Datenmodelle für den Risk Manager.
*   `t1/risk_manager/risk_manager/README.md` – Dokumentation für den Risk Manager.
*   `t1/risk_manager/risk_manager/requirements.txt` – Python-Abhängigkeiten für den Risk Manager.
*   `t1/risk_manager/risk_manager/service.py` – Die Hauptlogik des Risk Manager Dienstes.
*   `t1/risk_manager/Dockerfile` – Dockerfile für den Risk Manager Dienst.
*   `t1/signal_engine/signal_engine/__init__.py` – Initialisierungsdatei für das signal_engine Python-Modul.
*   `t1/signal_engine/signal_engine/config.py` – Konfigurationseinstellungen für die Signal Engine.
*   `t1/signal_engine/signal_engine/models.py` – Datenmodelle für die Signal Engine.
*   `t1/signal_engine/signal_engine/README.md` – Dokumentation für die Signal Engine.
*   `t1/signal_engine/signal_engine/requirements.txt` – Python-Abhängigkeiten für die Signal Engine.
*   `t1/signal_engine/signal_engine/service.py` – Die Hauptlogik des Signal Engine Dienstes.
*   `t1/signal_engine/Dockerfile` – Dockerfile für die Signal Engine.
*   `t1/tests/README.md` – Allgemeine Dokumentation für die Kern-Testsuite.
*   `t1/tests/unit/execution_service/` – Verzeichnis für Unit-Tests des Execution Service (aktuell leer).
*   `t1/tests/unit/risk_manager/` – Verzeichnis für Unit-Tests des Risk Managers (aktuell leer).
*   `t1/tests/unit/signal_engine/` – Verzeichnis für Unit-Tests der Signal Engine (aktuell leer).

**t2/**
*   `t2/.github/PULL_REQUEST_TEMPLATE.md` – Vorlage für Pull Requests zur Standardisierung von Beitrags-Workflows.
*   `t2/.github/ISSUE_TEMPLATE/bug_report.md` – Vorlage für Fehlerberichte zur strukturierten Meldung von Problemen.
*   `t2/.github/ISSUE_TEMPLATE/feature_request.md` – Vorlage für Feature-Anfragen zur Erfassung neuer Ideen und Anforderungen.
*   `t2/services/execution_simulator.py` – Ein Simulationswerkzeug zur Nachbildung von Ausführungsabläufen.

**t3/**
*   `t3/backoffice/automation/check_env.ps1` – Ein Skript zur Überprüfung der Umgebungseinstellungen (OPS & MAINTENANCE EXTRA).
*   `t3/backoffice/scripts/systemcheck.py` – Ein Python-Skript zur Durchführung von Systemprüfungen (OPS & MAINTENANCE EXTRA).
*   `t3/backoffice/scripts/backup_postgres.ps1` – Ein PowerShell-Skript zur Sicherung der PostgreSQL-Datenbank (OPS & MAINTENANCE EXTRA).
*   `t3/backoffice/scripts/daily_check.py` – Ein Python-Skript für tägliche Überprüfungsaufgaben (OPS & MAINTENANCE EXTRA).
*   `t3/backoffice/scripts/query_analytics.py` – Ein Python-Skript zur Durchführung von Analyse-Abfragen (OPS & MAINTENANCE EXTRA).
*   `t3/backoffice/scripts/setup_backup_task.ps1` – Ein Skript zur Einrichtung von Backup-Aufgaben (OPS & MAINTENANCE EXTRA).
*   `t3/backoffice/services/portfolio_manager/portfolio_manager.py` – Der Portfoliomanager-Dienst, eine alternative oder experimentelle Implementierung (AUXILIARY SERVICES EXTRA).
*   `t3/scripts/link_check.py` – Ein Skript zur Überprüfung von Links (DEV & CODE-TOOLS EXTRA).
*   `t3/scripts/provenance_hash.py` – Ein Skript zur Generierung von Provenance-Hashes (DEV & CODE-TOOLS EXTRA).
*   `t3/scripts/migration/cleanroom_migration_script.ps1` – Ein PowerShell-Skript für die einmalige Cleanroom-Migration (RESEARCH / EXPERIMENTAL).
*   `t3/scripts/migration/pre_migration_tasks.ps1` – Ein PowerShell-Skript für Aufgaben vor der Migration (RESEARCH / EXPERIMENTAL).
*   `t3/scripts/migration/pre_migration_validation.ps1` – Ein PowerShell-Skript zur Validierung vor der Migration (RESEARCH / EXPERIMENTAL).
*   `t3/scripts/security_audit.sh` – Ein Skript für Sicherheitsaudits (DEV & CODE-TOOLS EXTRA).
*   `t3/services/cdb_paper_runner/email_alerter.py` – Ein Zusatzmodul für E-Mail-Benachrichtigungen des Paper Runners (AUXILIARY SERVICES EXTRA).
*   `t3/services/cdb_paper_runner/service.py` – Eine alternative oder experimentelle Implementierung des Paper Runner Dienstes (AUXILIARY SERVICES EXTRA).
*   `t3/tests/mexc_top5_ws.py` – Ein Test für die mexc_top5_ws-Funktionalität (RESEARCH / EXPERIMENTAL).
*   `t3/tests/test_smoke_repo.py.skip` – Eine übersprungene Testdatei, die zu den erweiterten Tests gehört (DEV & CODE-TOOLS EXTRA).

#### Classification Integrity

Nach der Bereinigung ist die Klassifizierung der Tiers strukturell konsistent und entspricht den vorgegebenen Regeln. Alle Dateien sind korrekt den drei Tiers oder dem Governance-Ordner zugeordnet, und keine Konflikte oder falsch platzierte Elemente wurden gefunden.