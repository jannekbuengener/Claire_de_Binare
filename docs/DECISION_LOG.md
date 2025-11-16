# Architektur-Entscheidungen (ADR-Style)

## ADR-009: Security Rerun Automation & Evidence Pipeline

**Datum**: 2025-11-11  
**Status**: ✅ Abgeschlossen  
**Kontext**: Sicherheits-Gates blockierten Releases, da Artefakte (Trivy, Gitleaks, Bandit) nicht konsolidiert waren und Nachweise (.env Hash, CVE-Vergleich, Reviewer-Checkliste) fehlten.

-**Entscheidung**: 
- Automatisierte Skripte (`scripts/scan_ports.py`, `scripts/log_parser.py`, `scripts/bandit_postprocess.py`, `scripts/verify_cve_fix.sh`, `scripts/run_hardening.py`, `scripts/cve_triage.py`) generieren Ports-, Logs-, Bandit- und CVE-Artefakte unter `artifacts/`.
- Neues Makefile erweitert um Guarded Targets (`deps_fix`, `trivy_local`, `trivy_triage`, `bandit`, `bandit_gate`, `gitleaks`, `gitleaks_gate`, `verify_cve`, `evidence_review`, `gates`); optionaler Registry-Vergleich via `REGISTRY_IMG` (`make trivy_registry` dokumentiert als Plan).
- `.github/REVIEW_TEMPLATE.md` standardisiert Reviewer-Checkpunkte inkl. Bandit-`justified`-Abnahme und Artefakt-Links.
- `requirements.lock` (per `pip freeze --require-virtualenv`) dient Audit-Nachweis; Evidence-Datei enthält SHA256 der lokalen `.env` und Gitignore-Kontrolle.

-**Ergebnis**:
- Trivy- und Pip-Audit-Daten werden über `scripts/verify_cve_fix.sh` abgeglichen (Pins `aiohttp==3.12.14`, `cryptography==42.0.4` bestätigt, HIGH/CRITICAL für lokale Images aktuell 120; `scripts/cve_triage.py` liefert JSON/Markdown-Matrix zur weiteren Triage).
- Bandit-Report erhält `justified`-Feld (Mapping via `scripts/bandit_justification.json` möglich); `unjustified_check.json` zeigt aktuell 37 offene HIGH/MEDIUM-Funde und blockiert Gates bis zur Abnahme.
- Gitleaks läuft mit gepflegter `.gitleaks.toml`; sowohl Primär- als auch Post-Clean-Scan liefern 0 Treffer, Gate bleibt grün.
- Ports-Scan & Log-Parser erzeugen JSON/Markdown-Artefakte für Reviewer; Evidence-Skript schreibt `evidence/TEST_RERUN_EVIDENCE_<DATE>.md` inklusive automatisiertem Review-Block und PR-Draft unter `artifacts/pr/`.
- Dokumentierter Plan: Registry-Scan (`make trivy_registry`) bleibt optional, Ergebnisse sollen künftig gegen lokale Pins verglichen und im Evidence-Text referenziert werden.

**Konsequenzen**:
- ➕ Wiederholbare Security-Runs mit einheitlichem Artefakt-Layout (`artifacts/security/*`, `artifacts/runtime/*`).
- ➕ Reviewer-Workflow beschleunigt (Checkliste + `justified`-Flag als Pflichtprüfung).
- ➕ CVE-Evidence kombiniert lokale Scans (Trivy) und Dependency-Audits (pip-audit, safety) mit JSON-Zusammenfassung.
- ➖ Trivy meldet aktuell 120 HIGH/CRITICAL Findings in Basis-Images → Folgeaufgabe: Registry-Scan + Upstream-Fix-Analyse.
- 🔄 Nächste Schritte: `scripts/bandit_justification.json` pflegen (false-positive Tracking) und bei Verfügbarkeit `REGISTRY_IMG` setzen, um lokale vs. Registry-Images im Evidence zu vergleichen.

## ADR-008: Tool Stack - Development & Management Tools

**Datum**: 2025-11-03  
**Status**: ✅ Abgeschlossen  
**Kontext**: Nach Implementierung von CDB (Business Logic) und MCP (Monitoring) fehlten Verwaltungs- und Entwicklungstools für effizientes Container-Management, Datenbank-Administration und Ressourcen-Überwachung.

**Entscheidung**: Separater Tool-Stack mit 5 spezialisierten Tools:

1. **Portainer** (portainer-ce:latest) - Docker Management UI
   - Container, Images, Volumes, Networks verwalten
   - Terminal-Zugriff (exec) in Container
   - Stack-Management & Logs
   
2. **pgAdmin** (dpage/pgadmin4:latest) - PostgreSQL UI
   - Vollständige Datenbank-Administration für cdb_postgres
   - Query-Tool mit Syntax-Highlighting
   - Backup/Restore-Funktionen
   
3. **Dozzle** (amir20/dozzle:latest) - Docker Logs Viewer
   - Real-time Log-Streaming aller Container
   - Multi-Container-Suche mit Regex
   - Kein Login nötig (localhost-only)
   
4. **Adminer** (adminer:latest) - Lightweight SQL UI
   - Schnelle DB-Queries ohne pgAdmin-Overhead
   - Single-File PHP App
   - Unterstützt PostgreSQL, MySQL, SQLite
   
5. **cAdvisor** (gcr.io/cadvisor/cadvisor:latest) - Resource Monitoring
   - Container CPU/Memory/Network/Disk-Usage
   - Live-Metriken & historische Graphen
   - Prometheus-Integration (Scrape-Target)

**Begründung**:

- **Naming Convention:** Alle Container mit `tool_` Präfix für sofortige Identifikation (analog zu `cdb_` und `mcp_`)
- **Dual-Network:** Alle Tools hängen in `tools_net` (intern) UND `cdb_network` (shared) für direkten Zugriff auf CDB/MCP-Services
- **No Authentication (localhost):** Dozzle und cAdvisor ohne Login, da nur auf localhost exponiert (Production: Reverse-Proxy mit Auth)
- **cAdvisor statt Prometheus Node-Exporter:** cAdvisor bietet Container-spezifische Metriken, Node-Exporter nur Host-Metriken

**Ports (alle localhost):**
- 9000: Portainer
- 5050: pgAdmin
- 9999: Dozzle (Logs)
- 8085: Adminer (SQL)
- 8080: cAdvisor

**Implementierung**:

- Compose-Datei: `docker/tools/docker-compose.tools.yml`
- Environment: `docker/tools/.env` (pgAdmin-Credentials)
- Volumes: `tool_portainer_data`, `tool_pgadmin_data` (persistent)
- Labels: `com.cdb.role=tool`, `com.cdb.service=<name>` für alle Container

**Ergebnis**:

- 5 Tool-Container operational
- Direkte Verbindung zu cdb_postgres (pgAdmin, Adminer)
- Real-time Logs aller CDB/MCP-Container (Dozzle)
- Container-Metriken in Prometheus (cAdvisor @ tool_resourceusage:8080)
- Deployment-Script: `docker/tools/deploy.ps1` (Pre-Flight Checks, Backup, Health-Checks)

**Konsequenzen**:

- ➕ **Developer Experience:** Grafische UIs statt CLI (pgAdmin > psql, Portainer > docker ps)
- ➕ **Debugging:** Dozzle ermöglicht schnelle Log-Suche über alle Container (kein `docker logs` nötig)
- ➕ **Resource-Awareness:** cAdvisor zeigt Memory-Leaks und CPU-Spikes sofort
- ➕ **Self-Service:** Entwickler können ohne Root-Zugriff Container verwalten (Portainer)
- ➖ **Zusätzliche Ressourcen:** 5 Container benötigen ~500 MB RAM
- ⚠️ **Security:** Portainer/pgAdmin Passwörter in `.env` (nicht committed), localhost-only Exposition empfohlen

**Integration mit MCP:**

```yaml
# In docker/mcp/prometheus/prometheus.yml:
- job_name: 'cadvisor'
  static_configs:
    - targets: ['tool_resourceusage:8080']
```

→ Container-Metriken direkt in Prometheus & Grafana verfügbar

**Dokumentation**: `docker/tools/README_TOOLS.md` (vollständige Tool-Beschreibungen, Setup-Guides, Troubleshooting)

**Referenzen**:
- Portainer: https://docs.portainer.io/
- pgAdmin: https://www.pgadmin.org/docs/
- Dozzle: https://github.com/amir20/dozzle
- Adminer: https://www.adminer.org/
- cAdvisor: https://github.com/google/cadvisor

---

## ADR-007: MCP Observability Stack - Monitoring & Alerting

**Datum**: 2025-11-03  
**Status**: ✅ Abgeschlossen  
**Kontext**: Nach Docker MVP (ADR-006) fehlte vollständige Observability-Infrastruktur für Metriken, Logs und Alerts. Produktions-Readiness erfordert Monitoring aller 8 CDB-Services, Alert-Pipeline und Log-Aggregation.

**Entscheidung**: Separater MCP (Monitoring/Control-Plane) Stack mit folgenden Komponenten:
- **Prometheus** (v2.54.1) - Metriken-Sammlung, 15d Retention
- **Alertmanager** (v0.27.0) - Alert-Routing, Slack-Integration
- **Grafana** (11.3.0) - Visualisierung
- **Loki** (3.2.0) - Log-Aggregation, 15d Retention
- **Promtail** (3.2.0) - Docker-Log-Collection
- **Redis Exporter** (v1.63.0) - Redis-Metriken
- **Postgres Exporter** (v0.15.0) - PostgreSQL-Metriken

**Begründung**:
- Separate Compose-Datei (`docker-compose.observability.yml`) für klare Trennung von Business-Logic (CDB) und Observability (MCP)
- Shared Network (`cdb_network`) für direkte Service-Discovery ohne Port-Exposition
- Prefix `mcp_` für alle MCP-Container zur sofortigen Identifikation
- 15-Tage-Retention als Balance zwischen Disk Space und Compliance
- Slack-Integration für Alert-Routing (Critical, Warning, Infrastructure)

**Implementierung**:
1. **Alert Rules (15+ konfiguriert)**:
   - ServiceDown, HighCPU, HighMemory, DiskSpaceLow
   - RedisBackpressure (evicted_keys > 100 oder memory > 80%)
   - PostgreSQLDown, PrometheusDown, LokiDown
   - NoAlertsReceived (Watchdog-Meta-Alert)

2. **Automation Scripts (PowerShell)**:
   - `deploy.ps1` - Full-Deployment mit Pre-Flight Checks
   - `sanity-check.ps1` - 8 Validierungskategorien (Container, API, Volumes, Network)
   - `fire-drill.ps1` - Alert-Pipeline-Test (Alertmanager → Slack)
   - `test-log-pipeline.ps1` - Loki-Ingestion-Validierung

3. **Dokumentation**:
   - `README.md` (10+ Seiten) - Vollständige Referenz mit Mini-Runbooks für 5 häufige Alerts
   - `QUICK_START.md` - 5-Minuten-Installation mit Slack-Setup
   - Troubleshooting-Guides für ServiceDown, RedisBackpressure, PrometheusDown, LokiDown

**Ergebnis**:
- 7 MCP-Container operational (Prometheus, Alertmanager, Grafana, Loki, Promtail, Redis Exporter, Postgres Exporter)
- 10+ Prometheus-Targets konfiguriert (CDB-Services, Redis, PostgreSQL, MCP-Services selbst)
- Slack-Integration aktiv (3 Alert-Kategorien: critical, warning, infrastructure)
- Log-Pipeline validiert (Docker → Promtail → Loki → Grafana Explore)
- Fire-Drill-Tests bestanden (Alert-Fire & Resolve funktionsfähig)
- Retention: 15 Tage für Prometheus + Loki

**Konsequenzen**:
- ➕ **Produktions-Readiness**: Vollständige Observability für alle CDB-Services
- ➕ **Proaktive Alerts**: Slack-Benachrichtigungen bei Service-Problemen (< 1min Latenz)
- ➕ **Root-Cause-Analysis**: Logs in Loki + Metriken in Prometheus ermöglichen schnelles Debugging
- ➕ **Automatisierte Validierung**: Sanity-Checks in < 60 Sekunden durchführbar
- ➕ **Self-Monitoring**: MCP überwacht sich selbst (PrometheusDown, LokiDown Alerts)
- ➖ **Zusätzliche Ressourcen**: 7 Container benötigen ~1-2 GB RAM und ~500 MB Disk pro Tag
- 🔄 **Nächste Schritte**: Grafana-Dashboards importieren, Alert-Tuning nach Produktion-Load

**Technische Details**:
- **Netzwerk**: Shared `cdb_network` (bridge) - keine separaten Netze, direkte Service-Discovery
- **Volumes**: 3 persistente Volumes (`mcp_prometheus_data`, `mcp_grafana_data`, `mcp_loki_data`)
- **Ports**: 9090 (Prometheus), 9093 (Alertmanager), 3000 (Grafana), 3100 (Loki), 9080 (Promtail)
- **Secrets**: Credentials in `.env` (nicht committed), Template in `.env.example`
- **Health-Checks**: Alle Container mit Health-Check konfiguriert (interval: 30s, timeout: 10s)

**Dokumentation**: `docker/mcp/README.md`, `docker/mcp/QUICK_START.md`, `backoffice/CHECKPOINT_INDEX.md` (MCP-Abschnitt)

**Referenzen**:
- Prometheus-Dokumentation: https://prometheus.io/docs/
- Loki-Dokumentation: https://grafana.com/docs/loki/
- Alertmanager-Routing: https://prometheus.io/docs/alerting/latest/configuration/

---

## ADR-006: Docker MVP Complete - Checkpoint Reset/Joined

**Datum**: 2025-11-03  
**Status**: ✅ Abgeschlossen  
**Kontext**: Vollständige Implementierung aller 6 Kern-Services mit Docker, inklusive Health-Checks, korrekter ENV-Konfiguration und vollständigem DB-Schema.  
**Entscheidung**: Alle Services mit `cdb_` Präfix, einheitliche Port-Struktur (8000-8003 für Services), vollständige Healthcheck-Integration.  
**Ergebnis**:
- 8 Container running & healthy (redis, postgres, prometheus, grafana, ws, core, risk, execution)
- 6 persistente Volumes
- 11 DB-Tabellen/Views geladen
- Alle ENV-Keys vollständig konfiguriert
- Health-Endpoints auf allen Services verfügbar

**Dokumentation**: `backoffice/CHECKPOINT_RESET_JOINED_2025-11-03.md`  
**Konsequenzen**:
- ➕ Stabiler Ausgangspunkt für E2E-Tests
- ➕ Vollständige Nachvollziehbarkeit aller Build-Artefakte
- ➕ Klare Service-Hierarchie und Dependencies
- 🔄 Nächster Schritt: Redis Pub/Sub Tests & Pipeline-Validierung

---

## ADR-001: Message-Bus-Wahl (Redis statt NATS)

**Datum**: 2025-01-XX  
**Status**: ✅ Beschlossen  
**Kontext**: Brauchten Pub/Sub für Service-Kommunikation  
**Entscheidung**: Redis (simpler Setup, direkt in Docker)  
**Konsequenzen**:

- ➕ Kein zusätzlicher Infra-Stack
- ➕ Persistenz möglich (List/Stream)
- ➖ Weniger Features als NATS (kein Clustering)

## ADR-002: SQLite für MVP

**Datum**: 2025-01-XX  
**Status**: ✅ Beschlossen  
**Kontext**: Datenbank für Audit-Trail  
**Entscheidung**: SQLite embedded, später PostgreSQL  
**Konsequenzen**:
- ➖ Single-Writer-Limitation
- 🔄 Migration auf Postgres bei Multi-Instance

## ADR-003: Telegram-Alerts deprecated

**Kontext**: Roadmap fordert interne Push-Lösung  
**Entscheidung**: Primär Web-Push (VAPID), Telegram nur Legacy  
**Konsequenzen**:

- ➕ Datenschutz (kein Drittanbieter-Zwang)
- ➕ Konsistent mit Roadmap-Vision

## ADR-004: Backup-Skripte zentral in operations/backup

**Datum**: 2025-10-25  
**Status**: ✅ Beschlossen  
**Kontext**: Mehrere Backup-Skripte/Anleitungen existierten doppelt im Repository und führten zu veralteten Pfadangaben.  
**Optionen**:  

- A) Alles im Projekt-Root behalten  
- B) Skripte und Doku unter `operations/backup/` bündeln  
- C) Externes Repo nur für Betrieb anlegen  
**Entscheidung**: Option B – alle aktiven Skripte/Dokumente liegen unter `operations/backup/`, Root-Dateien bleiben als Weiterleitung bzw. Legacy-Hinweis bestehen.

## ADR-005: compose.yaml Removal - Nur docker-compose.yml verwenden

**Datum**: 2025-10-30  
**Status**: ✅ Beschlossen  
**Kontext**: System hatte zwei konkurrierende Docker Compose Konfigurationen (`docker-compose.yml` + `compose.yaml`), die parallel liefen und zu Restart-Loops aller Python-Services führten.

**Problem**:
- Docker Compose bevorzugt automatisch `compose.yaml` über `docker-compose.yml` (neuere Namenskonvention)
- Beide Container-Sets versuchten parallel zu laufen (Port-Konflikte 8001-8003)
- `compose.yaml` hatte fehlerhafte Network-Definition → DNS-Auflösung fehlgeschlagen
- 90 Minuten Downtime für Signal Engine, Risk Manager, Execution Service

**Optionen**:
- A) `compose.yaml` fixen und als primäre Config verwenden (kurze Namen: cdb-exec:v1)
- B) `docker-compose.yml` behalten, `compose.yaml` entfernen (lange Namen: claire_de_binare-*)
- `docker-compose.yml` war bereits funktionsfähig und stabil (alle Services healthy)
- Kurze Container-Namen sind Nice-to-Have, aber System-Stabilität ist kritischer
- Eine einzige Source of Truth verhindert zukünftige Konflikte
**Implementation**:
```bash
docker rm -f cdb-exec cdb-risk cdb-signal  # Störende Container entfernen
**Validation**:
- ✅ Alle Services healthy innerhalb 2 Minuten
- ✅ Health-Endpoints antworten korrekt
- Recovery Report: `backoffice/audits/2025-10-30_RECOVERY_REPORT.md`
- Funktionierende Config: `docker-compose.yml` (Root-Verzeichnis)  
**Konsequenzen**:
- ➖ Benutzer müssen neuen Pfad kennen (wird in Root-Docs kommuniziert)

## ADR-005: Unix-Timestamp für Datenbank-Zeitstempel
**Problem**: Code verwendete `datetime.utcnow()` (Python datetime-Objekt), DB-Schema erwartet `bigint` (Unix-Timestamp)  
**Optionen**:  

- A) DB-Schema ändern zu `timestamp without time zone`  
- B) Code ändern zu `int(time.time())` (Unix-Timestamp)  
- C) Beide Formate hybrid unterstützen

**Entscheidung**: Option B – Code auf `int(time.time())` umgestellt  
**Rationale**:

- DB-Schema ist bewusst mit `bigint` designed (EVENT_SCHEMA.json Standard)
- Unix-Timestamps sind plattformübergreifend eindeutig
- `save_order()`: `submitted_at` und `filled_at` auf `int(time.time())` umgestellt
- Bestehende `save_trade()` bereits korrekt (konvertiert ISO-String zu Unix)

- ➕ Konsistenz zwischen Events und DB
- ➕ E2E Test-Success-Rate: 90% → 100%
- ➖ Keine (Code war fehlerhaft, DB-Schema korrekt)
**Status**: ✅ Beschlossen  
**Kontext**: Mehrere Komponenten (Apprise-Alerts, MCP-Dokument, Master-Übersicht) sind durch neuere Strukturen ersetzt worden und führen zu Verwirrung/Duplikaten.  
**Optionen**:  
**Entscheidung**: Option B – Komponenten werden in `archive/` verschoben mit README zur Dokumentation der Gründe und Archivierungsdaten.  
**Konsequenzen**:

- ➕ Git-Historie bleibt erhalten, kein Datenverlust  
- ➕ Nachvollziehbare Projektentscheidungen  
- ➕ Sauberer Root-Ordner ohne veraltete Dateien  
- ➖ Zusätzlicher Verwaltungsaufwand für Archiv-Dokumentation

## ADR-006: Governance-Ordner & Leitplanken

**Datum**: 2025-10-25  
**Status**: ✅ Beschlossen  
**Kontext**: Wiederkehrende Audit-Feststellungen (ENV-Duplikate, fehlende Logging-Standards) verlangten nach klaren Strukturen für Automatisierung, Templates und CI.  
**Optionen**:  

- A) Bestehende Dateien erweitern und verstreut ablegen  
- B) Neue Ordner unter `backoffice/` schaffen (`automation/`, `ci/`, `templates/`) und Regeln in separatem Dokument pflegen  
- C) Externes Wiki verwenden  
**Entscheidung**: Option B – dedizierte Governance-Ordner plus `docs/ARCHITEKTUR_REGELN.md` als Verbindlichkeit für Services.  
**Konsequenzen**:  

- ➕ Klare Ablageorte für Skripte, Pipelines und Vorlagen  
- ➕ Architektur- und Logging-Regeln sind zentral versioniert  
- ➖ Initialer Pflegeaufwand (Templates/Skripte müssen gefüllt werden)  

## ADR-007: Automatisiertes Repository-Inventar

**Datum**: 2025-10-25  
**Status**: ✅ Beschlossen  
**Kontext**: KI-Agenten verlieren Zeit beim manuellen Erfassen des Dateibestands; Audits verlangen nachvollziehbare Snapshots pro Session.  
**Optionen**:  

- A) Rein manuelle Sichtprüfung der Ordnerstruktur  
- B) Nutzung vorhandener Backup-Skripte für Inventarinformationen  
- C) Eigenständiges Repository-Inventar-Skript mit JSON-Ausgabe in `backoffice/logs/inventory/`  
**Entscheidung**: Option C – dediziertes Skript `scripts/inventory.ps1`, das bei Session-Start ein Inventar schreibt und `latest.json` für schnelle Diffs bereitstellt.  
**Konsequenzen**:  

- ➕ Einheitliche Start-Routine für alle Agenten  
- ➕ Nachvollziehbarkeit von Strukturänderungen über JSON-Historie  
- ➖ Leichter Pflegeaufwand für Skript bei Strukturänderungen  

## ADR-008: Geheimnisrotation & Container-Hardening

**Datum**: 2025-10-25  
**Status**: ✅ Beschlossen  
**Kontext**: Audit 2025-10-25 identifizierte ungeschützte Redis-/Postgres-Zugänge sowie Root-Container ohne Hardening. Risiko: Order-Manipulation, Datenverlust, Privilege Escalation.  
**Optionen**:  

- A) Nur Dokumentation ergänzen und manuelle Erinnerung an Secret-Rotation  
- B) Compose/Dockerfiles härten, Secrets erzwingen, Host-Exponierung einschränken  
- C) Komplettumstieg auf Managed Services mit externem Secret-Store  
**Entscheidung**: Option B – unmittelbare technische Absicherung durch Pflicht-ENV-Variablen, `--requirepass` für Redis, entfernte Passwort-Fallbacks, Non-Root-Execution-Service und Security-Optionen in Compose.  
**Konsequenzen**:  
- ➕ Reduzierte Angriffsfläche, Redis/Postgres nur mit gültigem Secret erreichbar  
- ➕ Container laufen ohne Root-Capabilities (`no-new-privileges`, `cap_drop`, Non-Root-User)  
- ➖ Betreiber müssen Secrets vor Deploy setzen; fehlende Variablen verhindern Start (Intentional Fail-Fast)  

## ADR-009: Execution-Feedback im Risk-Loop

**Datum**: 2025-10-25  
**Status**: ✅ Beschlossen  
**Kontext**: Der Execution-Service publiziert `order_result` Events, der Risk-Manager nutzte diese bislang nicht. Exposure-Limits und Circuit-Breaker reagierten daher nicht auf tatsächliche Ausführungen, was auditrelevante Lücken ließ.  
**Optionen**:  

- A) Weiterhin nur Signal-Events berücksichtigen und Exposure manuell resetten  
- B) Risk-Manager erweitert um Listener für `order_result`, Aktualisierung von Exposure/Pending Orders  
- C) Separaten Persistenz-Service vorsehen, der Limits periodisch neu berechnet  
**Entscheidung**: Option B – direkter Listener im Risk-Manager synchronisiert Pending Orders, Positions-Exposure und Execution-Rejections in Echtzeit.  
**Konsequenzen**:  
- ➕ Exposure- und Circuit-Breaker-Logik basiert auf real ausgeführten Orders  
- ➕ Einheitliche Metriken (`order_results_received`, `orders_rejected_execution`) erlauben Monitoring  
- ➖ Zusätzlicher Redis-Listener/Thread erhöht Komplexität minimal  

## ADR-010: Docker Compose als Standard-Orchestrierung

**Datum**: 2025-10-25  
**Status**: ✅ Bestätigt  
**Kontext**: Diskussion, ob Docker Desktop ohne Compose-Befehle ausreicht. Die Plattform umfasst mehrere Container (Redis, Postgres, Prometheus, Grafana, Services) mit gemeinsamen Netzwerken/Volumes.  
**Optionen**:  

- A) Reine Docker-Desktop-GUI oder Einzel-`docker run` Kommandos  
- B) Docker Desktop inklusive CLI `docker compose` als verbindlicher Weg  
- C) Alternative Orchestrierung (k3s, Nomad)  
**Entscheidung**: Option B – Docker Desktop bleibt Voraussetzung, Compose-CLI wird verbindlich für Mehrcontainer-Start/Stop/Tests verwendet.  
**Konsequenzen**:  
- ➕ Einheitliche Skripte und Doku bleiben gültig (`docker compose up …`)  
- ➕ Health-/Security-Checks (Audit 2025-10-25) lassen sich automatisiert ausführen  
- ➖ Bedienung ohne CLI nicht unterstützt; reine GUI-Nutzung bleibt optional für Einzelcontainer  

## Template für neue ADRs

### ADR-XXX: [Titel]

**Datum**: YYYY-MM-DD  
**Status**: 🔄 Vorgeschlagen / ✅ Beschlossen / ❌ Verworfen  
**Kontext**: Warum brauchen wir eine Entscheidung?  
**Optionen**: A, B, C...  
**Entscheidung**: Wir wählen X weil...  
**Konsequenzen**: Pro/Contra, Risiken

## ADR-011: Vereinheitlichung DB-Credentials und Prometheus-Healthcheck

**Datum**: 2025-10-26  
**Status**: ✅ Beschlossen  
**Kontext**: Postgres-Container startete mit bestehendem Datenverzeichnis; Credentials aus `.env` und realer DB-Instanz wichen ab. Zudem war der Prometheus-Healthcheck im Compose mit `curl` definiert, das im `prom/prometheus`-Image nicht verfügbar ist.  
**Optionen**:


- A) Passwort des bestehenden DB-Benutzers im laufenden Container angleichen  
- B) Postgres-Volume neu initialisieren und User/Pass aus `.env` übernehmen  
- C) Compose an `.env` koppeln (POSTGRES_USER variabel) und Prometheus-Healthcheck auf `wget` umstellen  

**Entscheidung**: Kombination aus B und C  


- Postgres-Volume zurückgesetzt und Neuinitialisierung mit `.env`-Werten vorgenommen (`POSTGRES_USER=admin`, `POSTGRES_PASSWORD=…`).  
- `docker-compose.yml`: `POSTGRES_USER` an `.env` gekoppelt; Prometheus-Healthcheck auf `wget` umgestellt.  

**Konsequenzen**:  

- ➕ Eindeutige, zentrale Steuerung der DB-Credentials über `.env`  
- ➕ Prometheus wird korrekt als „healthy" erkannt  
- ➖ Daten im alten Postgres-Volume wurden verworfen (bewusst, MVP-Phase)  

---

## ADR-012: bot_rest ohne Healthcheck betreiben

**Datum**: 2025-10-26  
**Status**: ✅ Beschlossen  
**Kontext**: `bot_rest` Container wurde als "unhealthy" gemeldet, obwohl er korrekt funktioniert. Service läuft in Periodik-Loop (alle 300s) ohne HTTP-Server, der Healthcheck via curl schlug daher immer fehl.  
**Optionen**:  

- A) HTTP-Server in bot_rest einbauen nur für /health Endpoint  
- B) Healthcheck entfernen und Status via docker logs überwachen  
- C) Healthcheck auf Script-Check umstellen (ps, pidof)  

**Entscheidung**: Option B – Healthcheck aus `docker-compose.yml` entfernt mit Kommentar "No healthcheck - service runs in periodic loop without HTTP server"  
**Konsequenzen**:  

- ➕ Container-Status zeigt "running" statt "unhealthy"  
- ➕ Keine unnötige Komplexität durch HTTP-Server nur für Health-Check  
- ➕ Service-Funktion bestätigt durch docker logs (regelmäßige Outputs)  
- ➖ Kein automatisches Health-Signal für Monitoring; manuelles Log-Monitoring erforderlich  

---

## ADR-013: MCP-Server Integration für erweiterte Development-Tools

**Datum**: 2025-10-26  
**Status**: ✅ Beschlossen  
**Kontext**: GitHub Copilot bietet über Model Context Protocol (MCP) spezialisierte Tool-Server für Docker-Management, Python-Analyse, Dokumentation und Diagramme. Integration erweitert Development-Workflow mit semantischen Abfragen, automatischem Refactoring und visueller Dokumentation.  
**Optionen**:  

- A) Nur Standard VS Code Extensions nutzen (ohne MCP)  
- B) Ausgewählte MCP-Server konfigurieren (Docker, Pylance, Context7, Mermaid)  
- C) Alle verfügbaren MCP-Server installieren (inkl. experimentelle)  

**Entscheidung**: Option B – 4 MCP-Server strategisch ausgewählt und konfiguriert:

1. **Docker MCP**: Knowledge Graph für Container-Infrastruktur (9 Container, 4 Volumes, 24 Relations)
2. **Pylance MCP**: Python Code-Analyse, Refactoring, Snippet-Execution
3. **Context7**: Library-Dokumentation (fastapi, redis, psycopg2, pydantic)
4. **Mermaid Chart**: Diagramm-Erstellung und Validierung (Flowcharts, Sequence, ER)

**Implementierung**:  

- Zentrale Konfiguration: `backoffice/mcp_config.json`
- Dokumentation: `docs/MCP_SETUP_GUIDE.md` (420+ Zeilen)
- Docker Knowledge Graph initialisiert mit allen System-Entities und Relations
- Chatmodes erweitert: `.github/chatmodes/*` integrieren MCP-Tools

**Konsequenzen**:  

- ➕ Semantische Suche über Container-Topologie (mcp_mcp_docker_search_nodes)
- ➕ Automatisches Refactoring (Unused Imports, Format Conversion)
- ➕ Code-Snippets direkt im Workspace-Environment testbar (ohne Terminal-Escaping)
- ➕ Aktuelle Library-Docs on-demand (pypi, npm, GitHub)
- ➕ Diagramm-Validierung vor Commit (Syntax-Checks, Live-Preview)
- ➕ Dokumentation der Service-Beziehungen im Knowledge Graph persistiert
- ➖ MCP-Server sind nicht persistent (Docker Graph muss nach Restart neu befüllt werden)
- ➖ Context7 erfordert Internet-Verbindung für Doc-Abruf
- 🔄 Wartung: Quartalsmäßige Review der MCP-Konfiguration (nächster Termin: 2025-11-26)

**Metriken**:  

- Docker-Entities: 14 (9 Container, 1 Network, 4 Volumes)
- Docker-Relations: 24 (Pub/Sub, Network, Volume-Mounts, Metrics)
- Python-Services: 3 (signal_engine, risk_manager, execution_service)
- Dokumentierte Libraries: 6 (fastapi, redis-py, psycopg2-binary, prometheus-client, pydantic, httpx)

---

## ADR-014: Docker MCP Toolkit Integration für Gordon AI-Agent

**Datum**: 2025-10-26  
**Status**: ✅ Beschlossen  
**Kontext**: Während der MCP-Server-Integration (ADR-013) wurde festgestellt, dass das offizielle **Docker MCP Toolkit** (Beta-Feature in Docker Desktop) eine dedizierte Lösung für AI-Agenten wie Gordon bietet. Das Toolkit ermöglicht Cross-LLM-Kompatibilität, Zero-Setup-Orchestration und sichere Tool-Verwaltung via MCP Gateway.

**Problem**: Bestehende VS Code MCP-Server (ADR-013) sind ausschließlich für VS Code Copilot optimiert. Für Container-Management und Live-Operations benötigen wir einen AI-Agenten mit direktem Docker-CLI-Zugriff und Dateioperationen.

**Optionen**:  

- A) Nur VS Code MCP-Server nutzen und Terminal-Befehle manuell ausführen  
- B) Docker MCP Toolkit aktivieren und Gordon als separaten AI-Agenten für DevOps-Tasks nutzen  
- C) Eigenen MCP-Server für Claire de Binaire entwickeln und im Docker Catalog veröffentlichen  

**Entscheidung**: Kombination aus B und C (langfristig)  

**Phase 1 (sofort)**:  

- Docker MCP Toolkit Beta-Feature in Docker Desktop aktivieren
- Gordon via MCP Gateway für Container-Management, Health-Checks und Log-Analyse nutzen
- Workflow definiert: VS Code Copilot (Code/Architektur) + Gordon (Operations/Debugging)

**Phase 2 (Q4 2025)**:  

- Custom MCP-Server für Claire de Binaire entwickeln (`claire-de-binare-mcp`)
- Tools: `get_latest_trades`, `get_signal_count`, `check_risk_limits`, `analyze_performance`
- Veröffentlichung im Docker MCP Catalog (optional)

**Implementierung (Phase 1)**:  

- Dokumentation: `docs/DOCKER_MCP_TOOLKIT_SETUP.md` (500+ Zeilen)
- Bereiche: Toolkit-Aktivierung, Gordon-Setup, Security (OAuth, Secrets), Custom Server Template
- Gordon Test-Prompts für Claire de Binaire erstellt (Container-Status, Health-Checks, Log-Analyse)
- MCP Gateway Security dokumentiert (Resource Limits, Image Signing, Request Interception)

**Docker MCP Toolkit Features**:  

- ✅ Cross-LLM Kompatibilität (Gordon, Claude Desktop, Cursor)
- ✅ Zero Manual Setup (keine Dependency-Verwaltung, Auto-Discovery via Docker Catalog)
- ✅ Security: Passive (Image Signing, SBOM) + Active (Resource Limits, Request Interception)
- ✅ Portabilität: Tools funktionieren plattformübergreifend ohne Code-Änderungen
- ✅ MCP Gateway: Sichere Orchestration zwischen AI-Clients und MCP-Servern

**Gordon Use Cases für Claire de Binaire**:  

1. **Container-Management**: `docker ps`, `docker logs`, `docker restart` via natürliche Sprache
2. **Database-Queries**: PostgreSQL-Abfragen via MCP Tools (nach Custom Server-Implementierung)
3. **Health-Monitoring**: Automatische Prüfung aller Health-Endpoints (8001, 8002, 8003)
4. **Log-Analyse**: Fehlersuche in Echtzeit-Logs mit semantischer Filterung
5. **OAuth-Integration**: GitHub-API-Zugriff für PR-Management, Issue-Tracking

**Workflow-Abgrenzung (Copilot vs. Gordon)**:  

| Aufgabe | VS Code Copilot | Gordon (Docker MCP) |
|---------|-----------------|---------------------|
| Code-Analyse & Review | ✅ Primär | ➖ |
| Architektur-Entscheidungen | ✅ Primär | ➖ |
| Docker Container-Management | ➖ | ✅ Primär |
| Datei-Bulk-Operationen | ➖ | ✅ Primär |
| Dokumentations-Erstellung | ✅ Primär | ➖ |
| Live-Debugging (Logs, Metrics) | ➖ | ✅ Primär |
| Database-Queries | ➖ | ✅ Primär (Phase 2) |

**Konsequenzen**:  

- ➕ Separation of Concerns: Code-Tasks (Copilot) vs. Operations-Tasks (Gordon)
- ➕ Gordon kann Docker-CLI ohne PowerShell-Escaping-Probleme nutzen
- ➕ Höhere Datei-Operationslimits (Gordon: 1000 Zeilen read, 50 write vs. Copilot-Tools)
- ➕ MCP Gateway enforcement von Security-Policies (Resource Limits, OAuth-Token-Rotation)
- ➕ Custom MCP-Server ermöglicht trading-spezifische Tools (Trade-Queries, Risk-Metrics)
- ➖ Gordon erfordert Docker Desktop Beta-Features (experimentell, potenzielle Breaking Changes)
- ➖ Zusätzlicher Kontext-Switch zwischen VS Code (Copilot) und Docker Desktop (Gordon)
- ➖ MCP-Server im Docker Catalog sind public (Custom Server nur lokal oder nach Review veröffentlichbar)
- 🔄 Wartung: Custom MCP-Server (Phase 2) erfordert Dockerfile, server.yaml und tools.json Pflege

**Security-Maßnahmen**:  

1. **Secrets Management**: `docker mcp secret set` für DB-Credentials, API-Keys
2. **Resource Limits**: Memory 512M, CPU 0.5, Network restricted
3. **OAuth-Flow**: GitHub OAuth via `docker mcp oauth authorize github`
4. **Image Signing**: Docker-built images im `mcp/` namespace mit kryptographischen Signaturen
5. **Request Interception**: MCP Gateway überwacht alle Tool-Calls auf Policy-Verletzungen

**Metriken**:  

- Dokumentation: 500+ Zeilen (DOCKER_MCP_TOOLKIT_SETUP.md)
- MCP-Server-Typen: 2 (VS Code: 4 Server, Docker Desktop: Gordon + Custom Server in Phase 2)
- Gordon-Prompts: 6 (Status-Check, Container-Neustart, Database-Check, Rebuild, Health-Check, Log-Analyse)
- Custom Server Templates: 3 (Dockerfile, server.yaml, main.py)

**Nächste Schritte (Phase 2 - Q4 2025)**:  

1. Custom MCP-Server `claire-de-binare-mcp` entwickeln (Python, FastAPI-basiert)
2. Tools implementieren: `get_latest_trades`, `get_signal_count`, `check_risk_limits`, `analyze_performance`
3. Docker Catalog Submission vorbereiten (optional, nach intern. Testing)
4. Gordon-Integration in CI/CD-Pipeline (automatische Health-Checks pre-deployment)

---

## ADR-015: Sofortige Handlungsdokumentation im Copilot-Workflow

**Datum**: 2025-10-27  
**Status**: ✅ Beschlossen  
**Kontext**: Während der laufenden Paper-Trading-Testphase sind präzise und zeitnahe Protokolle jedes KI-Schritts erforderlich. Bisher wurden Aktionen häufig erst am Sessionende gesammelt festgehalten, was das Nachvollziehen einzelner Eingriffe erschwerte.

**Optionen**:  

- A) Bisherige Sammeldokumentation am Sessionende beibehalten  
- B) Manuelle Protokollierung nach eigenem Ermessen  
- C) Verpflichtende Dokumentation nach jeder abgeschlossenen Handlung in Session-Memo oder DECISION_LOG

**Entscheidung**: Option C – Jede Aktion wird unmittelbar nach Abschluss dokumentiert. Für kleinere operative Schritte genügt ein Eintrag im laufenden Session-Memo; strukturrelevante Anpassungen werden zusätzlich im DECISION_LOG festgehalten.

**Konsequenzen**:  

- ➕ Lückenlose Rückverfolgbarkeit einzelner KI-Handlungen  
- ➕ Schnellere Auditierbarkeit während des 7-Tage-Tests  
- ➕ Klarer Hand-off zwischen Copilot und Gordon dank identischer Protokollierungspflicht  
- ➖ Geringfügiger Mehraufwand pro Schritt (sofortige Notizen erforderlich)

**Umsetzung**: Copilot-Instruktionen aktualisiert (`.github/copilot-instructions.md`), inklusive Autonomie-Hinweis für Terminalaufgaben und Pflicht zur direkten Dokumentation.

**Follow-up 2025-10-27**: Build-Kontexte in `compose.yaml` auf `backoffice/services/...` angepasst, damit `docker compose` die Service-Verzeichnisse findet; Docker-Start bleibt blockiert, solange das `risk_manager` Service-Verzeichnis fehlt.

**Follow-up 2025-10-27 (Bereinigung)**: `compose.yaml` enthielt doppelte Service-Definitionen zu `docker-compose.yml`. Da `docker-compose.yml` bereits vollständig konfiguriert ist (9 Container inkl. Redis, Postgres, Monitoring) und stabil läuft, wurde `compose.yaml` entfernt aus dem aktiven Setup. Die fehlgeschlagenen Container-Instanzen (Signal, Risk, Execution aus `compose.yaml`) wurden gestoppt; nur die Haupt-Services aus `docker-compose.yml` bleiben aktiv. Haupt-Compose ist vollständige Infrastruktur inkl. Redis/Postgres, während `compose.yaml` isolierte Service-Tests ohne Abhängigkeiten war – Entscheidung: Haupt-Compose als einzige produktive Konfiguration nutzen. Postgres-Container war gestoppt; nach Neustart ist Execution-Service nun stabil (10/10 Container healthy).

---

## ADR-016: Tool Layer Registry für zentrale Tool-Verwaltung

**Datum**: 2025-10-27  
**Status**: ✅ Beschlossen  
**Kontext**: Mit wachsender MCP-Server-Integration, DevOps-Tools und ML-Komponenten fehlte eine zentrale Übersicht aller verfügbaren Tools. Entscheidungen über neue Integrationen wurden ad-hoc getroffen, ohne strukturierte Kategorisierung oder Status-Tracking.

**Optionen**:

- A) Tools weiterhin dezentral in einzelnen Dokumenten pflegen
- B) Zentrale Tool Registry mit Kategorisierung (GO TO USE / NICE TO HAVE)
- C) Externe Plattform (Notion, Confluence) für Tool-Management

**Entscheidung**: Option B – Zentrale Tool Registry in `docs/TOOL_LAYER.md` mit klarer Kategorisierung und Statusverfolgung.

**Struktur**:

- **GO TO USE**: Produktiv eingebundene Tools (11 MCP-Server, 10 Docker-Container, 4 Monitoring-Tools)
- **NICE TO HAVE**: Geplante Erweiterungen (NotebookLM, Vault, Autogen Studio)
- Status-Kennzeichnung: ✅ aktiv, 🟢 bereit, 🧪 experimentell, 🔜 geplant

**Kategorien**:

1. Core Integrationen / MCP-Server (6): github-mcp, postman-mcp, mcp-grafana, mcp-redis, mongodb-mcp, hub-mcp
2. DevOps & Automation (4): n8n, self-hosted-ai-starter-kit, git-credential-manager, mcp-registry
3. Monitoring & Observability (5): Prometheus, Grafana, Loki, Pyroscope, Sift
4. Core Daten & Persistenz (5): PostgreSQL, Redis, SQLite, MongoDB Atlas, Qdrant
5. Forschung & ML-Advisor (5): TensorFlow, XGBoost, SHAP, W&B, Neptune.ai
6. Wissens- & Doku-Assistenz (3): NotebookLM, Notion API, Obsidian
7. Design & Präsentation (2): Figma/Canva SDK, Plotly/Matplotlib

---

## ADR-017: Query Service für READ-ONLY Data Access Layer

**Datum**: 2025-10-30  
**Status**: ✅ Beschlossen  
**Kontext**: MCP-Server und externe Tools benötigen strukturierten, READ-ONLY Zugriff auf Postgres-Tabellen (signals, risk_positions) und Redis-Streams (event streams). Bisherige Ad-Hoc-Queries erschwerten Wartbarkeit und fehlende Type-Safety führte zu inkonsistenten Datenformaten.

**Problem**: Fragmentierter Datenzugriff über verschiedene Services und Tools ohne zentrale Schnittstelle. Gordon AI-Agent und Monitoring-Dashboards benötigen deterministische, einheitliche JSON-Responses.

**Optionen**:

- A) Direkter Postgres/Redis-Zugriff aus jedem Tool (Status Quo)
- B) REST API mit FastAPI entwickeln (zusätzlicher HTTP-Server)
- C) Python Query Service Library mit CLI und programmatischer API

**Entscheidung**: Option C – Lightweight Python Query Service als Library mit CLI-Interface

**Implementierung**:

- Location: `backoffice/services/query_service/`
- Komponenten:
  - `service.py`: Hauptklasse mit async Postgres/Redis queries
  - `config.py`: Environment-basierte Konfiguration
  - `models.py`: Type-safe Dataclasses (SignalRecord, RiskRecord, RedisEvent)
  - `cli.py`: Command-line Interface für interaktive Nutzung
  - `examples.py`: Vollständige Beispiele für alle Queries
  - `API_SPEC.json`: Formale Spezifikation gemäß User-Request
- Dependencies: `asyncpg>=0.29.0`, `redis>=5.0.0`

**Verfügbare Queries**:

1. **signals_recent** (Postgres): Letzte N Signals für Symbol (BTCUSDT default)
   - Filter: symbol, since_ms, limit (max 1000)
   - Output: timestamp, symbol, side, price, confidence, reason, volume, pct_change

2. **risk_overlimit** (Postgres): Risk-Positionen über Limit
   - Filter: symbol (optional), only_exceeded, limit
   - Output: timestamp, symbol, exposure, limit

3. **redis_tail** (Redis): Letzte N Events aus Stream
   - Filter: channel (signals:BTCUSDT default), count
   - Output: event_id, timestamp, payload

**Output-Format (einheitlich)**:

```json
{
  "result": [/* records */],
  "count": 123,
  "query": "signals_recent",
  "timestamp_utc": "2025-10-30T10:45:00.123456+00:00"
}
```

**Constraints**:

- ✅ READ_ONLY (keine INSERT/UPDATE/DELETE)
- ✅ Deterministische Sortierung (timestamp DESC)
- ✅ Connection Pooling (Postgres: 1-5 Connections)
- ✅ Timeouts (Postgres: 30s, Redis: 5s)
- ✅ Limit Enforcement (max 1000 pro Query)

**Konsequenzen**:

- ➕ Zentrale, wartbare Datenzugriffsschicht
- ➕ Type-Safety durch Pydantic-Dataclasses
- ➕ CLI für manuelle Exploration und Debugging
- ➕ Gordon AI-Agent kann strukturierte Queries ohne SQL-Injection-Risiko ausführen
- ➕ Einheitliches JSON-Format für alle Monitoring-Tools
- ➕ Async-First Design (skalierbar für parallel queries)
- ➖ Zusätzliche Dependency-Layer (asyncpg, redis-py)
- ➖ Kein HTTP-Endpoint (nur Library-Import oder CLI)
- 🔄 Future: REST API Wrapper für externe Tools (FastAPI optional in Phase 2)

**Integration**:

- **Gordon AI-Agent**: Via CLI oder direkter Python-Import für Container-Diagnostik
- **Monitoring-Dashboards**: Grafana kann CLI-Output als JSON Data Source nutzen
- **MCP-Server (Phase 2)**: Custom Claire de Binaire MCP-Server nutzt Query Service intern
- **Jupyter Notebooks**: Direkter Import für Backtesting und Analyse

**Sicherheit**:

- ✅ Postgres-User hat nur SELECT-Rechte (Role-based in Phase 7)
- ✅ Redis-Client nutzt READ-ONLY Kommandos (XREVRANGE, keine DEL/EXPIRE)
- ✅ Connection-Strings niemals in Logs (nur ENV-Variablen)
- ✅ SQL-Injection-sicher (asyncpg Prepared Statements)

**Wartung**:

- Monatliches Review: Query-Performance-Metriken (Query-Dauer, Ergebnis-Counts)
- Quartalsweise: Schema-Alignment-Check gegen `DATABASE_SCHEMA.sql`
- Bei Änderungen in `EVENT_SCHEMA.json`: models.py synchronisieren

**Metriken**:

- Code: 700+ Zeilen (Python)
- Dokumentation: 300+ Zeilen (README.md)
- Tests: 7 Test-Cases (pytest)
- API-Spec: Vollständig JSON-dokumentiert (API_SPEC.json)

**Nächste Schritte**:

1. Dependencies installieren: `pip install -r backoffice/services/query_service/requirements.txt`
2. CLI-Test: `python -m backoffice.services.query_service.cli --query signals_recent --symbol BTCUSDT`
3. Integration-Tests: `pytest backoffice/services/query_service/test_service.py -v`
4. Gordon-Prompts erweitern: "Zeige die letzten 50 Signals für BTCUSDT"
8. Security & Governance (3): HashiCorp Vault, Trivy/Grype, OPA
9. KI-Orchestrierung & Agent Frameworks (2): LangSmith/LangFuse, Autogen Studio

**Konsequenzen**:

- ➕ Zentrale Übersicht aller verfügbaren Tools für AI-Agenten (Copilot, Gordon)
- ➕ Strukturierter Entscheidungsprozess für neue Tool-Integrationen
- ➕ Klare Statusverfolgung (aktiv, bereit, experimentell, geplant)
- ➕ Automatische Referenz in AI-Prompts ("Nutze mcp-redis für Pub/Sub-Analyse")
- ➕ Wartungs-Strategie definiert (wöchentlich, monatlich, quartalsweise Reviews)
- ➖ Zusätzlicher Pflegeaufwand bei Tool-Updates (Status-Änderungen dokumentieren)

**Integration**:

- Verweis in `ARCHITEKTUR.md` (neuer Abschnitt "Tool Layer Integration")
- Verknüpfung mit `MCP_DOCUMENTATION_INDEX.md` (technische Details)
- Update `PROJECT_STATUS.md` (Metriken: 11 MCP-Server, 30+ Tools dokumentiert)

**Metriken**:

- GO TO USE Tools: 30 (davon 11 MCP-Server, 10 Docker-Container)
- NICE TO HAVE Tools: 12 (geplante Erweiterungen)
- Dokumentierte Kategorien: 9
- Gesamtumfang: 280+ Zeilen Dokumentation

**Integration abgeschlossen (2025-10-27)**:

- ✅ `ARCHITEKTUR.md` erweitert (Abschnitt "Tool Layer Integration")
- ✅ `PROJECT_STATUS.md` aktualisiert (Phase 6.3, 10/10 Container healthy)
- ✅ `MCP_DOCUMENTATION_INDEX.md` verlinkt auf TOOL_LAYER.md
- ✅ Container-Status validiert: 10/10 healthy (inkl. Execution-Service nach Postgres-Fix)

---

## ADR-017: Gordon-Konsultation vor Docker-Eingriffen

**Datum**: 2025-10-27  
**Status**: ✅ Beschlossen

**Kontext**: Wiederholte Container-Restarts und unvollständige Infrastruktur-Kontexte haben gezeigt, dass spontane Docker-Eingriffe ohne Gordon-Abstimmung zu Instabilität führen. Gordon fungiert als zentrale Kontrollinstanz für Infrastruktur-Änderungen über das MCP-Toolkit.

**Optionen**:

- A) Copilot führt Docker-Operationen eigenständig durch
- B) Vor jedem docker compose / docker CLI Eingriff Gordon über MCP konsultieren und Freigabe dokumentieren
- C) Alle Docker-Aktionen vollständig an Gordon delegieren

**Entscheidung**: Option B – Copilot holt vor jedem Docker-Befehl (compose up/down, build, prune, rm, volume/network-Änderungen) eine Gordon-Freigabe ein. Ohne dokumentierte Freigabe dürfen keine Container-, Netzwerk- oder Volume-Operationen erfolgen.

**Konsequenzen**:

- ➕ Verhindert inkonsistente Compose-Starts bei unvollständiger Umfeld-Konfiguration
- ➕ Einheitlicher Freigabeprozess via MCP, nachvollziehbar im Session-Memo
- ➕ Gordon behält Gesamtüberblick über Infrastrukturzustand und Ressourcenplanung
- ➖ Zusätzlicher Kommunikationsschritt vor operativen Docker-Befehlen

**Umsetzung**:

- Copilot dokumentiert jede Gordon-Anfrage im laufenden Session-Memo (Zeitstempel, angefragte Aktion, Ergebnis)
- Docker-Runbooks im `docs/ops/RUNBOOK_DOCKER_OPERATIONS.md` und in der `EXECUTION_DEBUG_CHECKLIST.md` verweisen auf verpflichtende Gordon-Freigabe
- Automatische Checks: Vor Docker-Kommandos wird geprüft, ob aktuelle Gordon-Freigabe vorliegt (Session-Notiz oder Ticket)

---

## ADR-018: README Guide & Dashboard-V5-Standardisierung

**Datum**: 2025-11-01  
**Status**: ✅ Beschlossen  
**Kontext**: README-Dateien waren inkonsistent strukturiert, enthielten veraltete Ports/Topics
und widersprüchliche ENV-Hinweise. Audit-Anforderungen forderten einen einheitlichen
Dashboard-V5-Auftritt.

**Optionen**:

- A) Nur Root-README anpassen, restliche Dateien schrittweise bei Bedarf
- B) Verbindlichen Leitfaden `README_GUIDE.md` erstellen und alle Readmes daran ausrichten
- C) Readmes durch externes Wiki ersetzen

**Entscheidung**: Option B – `README_GUIDE.md` definiert verpflichtend Aufbau, Tabellenlayout,
Visuelle Elemente (Dashboard-V5-Stil) und Referenzlinks. Alle bestehenden Readmes wurden
entsprechend migriert.

**Konsequenzen**:

- ➕ Einheitliche Darstellung für alle Services, Module und Ordner
- ➕ Zentrale Quelle für Ports, Topics, ENV, Metriken hält Docs synchron mit Architektur
- ➕ Vereinfachte Reviews dank klarer Strukturblöcke (Überblick, Architektur, Setup, Monitoring)
- ➖ Initialer Migrationsaufwand für Bestandsdateien

**Validierung**:

- `README_GUIDE.md` im Repo-Root eingeführt (Dashboard-V5-Vorgaben)
- Alle aktualisierten Readmes verlinken konsistent auf `ARCHITEKTUR.md`,
  `Service-Kommunikation & Datenflüsse.md`, `Risikomanagement-Logik.md`
- `.env` und Ports/Topics-Tabellen in den Readmes decken sich mit Compose & Event-Schema

---

## ADR-019: Wissensgraph Phase 2 – smarter_assistant Integration

**Datum**: 2025-11-02  
**Status**: ✅ Beschlossen  
**Kontext**: Mit `knowledge_inventory.json`, `semantic_map.md`, `refactor_plan.md`, `consistency_audit.md` und `learning_path.md` existieren neue Wissensartefakte, die bislang als isolierte Dokumente geführt wurden. Für Phase 3 (2-Hop-Konsolidierung) ist ein konsistenter Wissensgraph erforderlich.

**Optionen**:

- A) Weiterhin rein textuelle Dokumente verwenden und Abhängigkeiten ad hoc verfolgen
- B) Smarter-Assistent-Artefakte in bestehenden Listen verlinken, aber ohne Graph-Struktur
- C) Einen formalen Wissensgraph etablieren (Primärdokument `semantic_map.md`, menschliche Navigationsschicht `Knowledge_Map.md`, Maschinen-Layer `semantic_index.json`)

**Entscheidung**: Option C – Vollständige Integration aller smarter_assistant-Artefakte in einen Knowledge Graph mit maschinenlesbarem Index und menschlichem Navigationslayer.

**Konsequenzen**:

- ➕ Phase-3-Konsolidierung kann gezielt 1-Hop- und 2-Hop-Abhängigkeiten analysieren
- ➕ Neue Artefakte erhalten Primärstatus und verlieren ihren Inselcharakter
- ➕ Automatisierungen können über `semantic_index.json` Beziehungen programmatisch auswerten
- ➕ `knowledge_inventory.json` bleibt Datenquelle, aber Graph regelt Priorisierung
- ➖ Laufender Pflegeaufwand: Jede Relation muss im Index und in der Knowledge Map nachgetragen werden

**Umsetzung**:

- `semantic_map.md` als Primärdokument markiert und um Graphstatus erweitert
- `docs/smarter_assistant/Knowledge_Map.md` erstellt (Navigation, 1/2-Hop-Ketten)
- `docs/smarter_assistant/semantic_index.json` erzeugt (Knoten, Kanten, Cluster)
- `PROJECT_STATUS.md` unter "Technische Verbesserungen" mit Phase-2-Vermerk ergänzt

**Abhängigkeiten**:

- Phase 3 stützt sich auf diese Artefakte, um Redundanzen (ENV, Ports, Topics) zu beseitigen
- Phase 4 setzt Wissensanker erst nach Abschluss der Phase-3-Maßnahmen

---

## ADR-020: Phase-3-Normalisierung – Konfliktregister

**Datum**: 2025-11-02  
**Status**: ✅ Beschlossen  
**Kontext**: Phase 3 soll 1-/2-Hop-Konflikte (Ports, Secrets, Event-Literals) konsistent beheben. Bisherige Artefakte (PROJECT_STATUS, Service-Dokumente, Schema) führten zu widersprüchlichen Angaben, was Phase-4-Wissensanker blockiert.

**Optionen**:

- A) Konflikte jeweils direkt in den betroffenen Dokumenten notieren (Projektstatus, Service-Doku, Schema)
- B) Session-Memos erweitern und Konflikte temporär dokumentieren
- C) Zentrales Normalisierungs-Register erstellen (`Normalization_Report.md`) und maschinenlesbare Referenzen im `semantic_index.json` pflegen

**Entscheidung**: Option C – eigenes Konfliktregister mit Maßnahmenliste und Graph-Verankerung, damit Phase-3-Konsolidierung nachvollziehbar und auditierbar bleibt.

**Konsequenzen**:

- ➕ Port- und Secret-Divergenzen werden in einem Dokument zentral verfolgt
- ➕ Schema-Abweichungen zwischen Beispieldokumentation und `EVENT_SCHEMA.json` sind eindeutig adressiert
- ➕ `semantic_index.json` bildet Konfliktkanten (`conflicts_with`, `tracks_issue`) für Automatisierungen ab
- ➕ Governance-Dokumente (`PROJECT_STATUS.md`, `DECISION_LOG.md`) verweisen auf die Normalisierung als laufende Aktivität
- ➖ Zusätzlicher Pflegeaufwand, bis alle Konflikte behoben sind und auf `verified=true` gesetzt werden können

**Validierung**:

- `docs/smarter_assistant/Normalization_Report.md` erstellt (Port-, Secret-, Event-/Alert-Deltas dokumentiert)
- `semantic_index.json` um Knoten `normalization_report`, `env_file`, `service_dataflow_doc`, `risk_logic_doc` und Konfliktkanten erweitert
- `Knowledge_Map.md`, `semantic_map.md`, `PROJECT_STATUS.md` auf Phase-3-Status und Normalisierungseinträge aktualisiert

**Abhängigkeiten**:

- Umsetzung der Maßnahmen aus dem Normalization Report ist Voraussetzung für Phase-4-Wissensanker
- Änderungen an Ports/Secrets/Schemas müssen nach Umsetzung in allen Primärquellen synchronisiert werden

---

## ADR-022: REST-Port-Governance-Normalisierung

**Datum**: 2025-11-02  
**Status**: ✅ Beschlossen  
**Kontext**: Runtime (`docker-compose.yml`, `.env`, Container-Status) exponiert den REST-Screener auf Host-Port 8080, während Governance-Artefakte (`PROJECT_STATUS.md`, `Normalization_Report.md`, Session-Memos) noch 8010 führten und Health-/Runbook-Checks fehlleiteten.

**Optionen**:

- A) Dokumentation unverändert lassen und auf Runtime als maßgebliche Quelle verweisen
- B) Host-Port 8080 in allen Governance-Dokumenten vereinheitlichen und Konflikt im Wissensgraphen als verifiziert markieren
- C) REST-Service auf 8010 zurücksetzen, um Dokumentation anzupassen

**Entscheidung**: Option B – Governance-Artefakte und Session-Memo auf 8080 angleichen und Relation `project_status → docker_compose` im Wissensgraphen als `verified=true` mit `normalized_value: "8080"` kennzeichnen.

**Konsequenzen**:

- ➕ Health-Checks, Runbooks und Monitoring-Dokumente referenzieren denselben Port (8080)
- ➕ Wissensgraph spiegelt die Normalisierung über Metadaten (`verified`, `normalized_value`) wider
- ➕ Phase-4-Port-Loop abgeschlossen, Session-Memo dokumentiert den Abschluss
- ➖ Laufende Normalisierungsschleifen benötigen konsistente Pflege der Wissensgraph-Metadaten

---

## ADR-023: Redis Secret Alignment

**Datum**: 2025-11-02  
**Status**: ✅ Beschlossen  
**Kontext**: Die Runtime verwendet `REDIS_PASSWORD=REDACTED_REDIS_PW` ( `.env`, `docker-compose.yml`, Container-Startup). Governance-Dokumente referenzierten weiterhin `REDACTED_REDIS_PW$$`, wodurch Secretsync und Runbooks divergierten.

**Optionen**:

- A) Runtime-Secret auf `REDACTED_REDIS_PW$$` zurückdrehen und Container neu provisionieren
- B) `.env`, `PROJECT_STATUS.md`, `Risikomanagement-Logik.md` und Wissensgraph auf den Runtime-Wert **REDACTED_REDIS_PW** harmonisieren
- C) Redis ohne Passwort betreiben und Auth nur in Dokumentation erwähnen

**Entscheidung**: Option B – Runtime gilt als autoritative Quelle. Alle Governance-Artefakte werden auf `REDIS_PASSWORD=REDACTED_REDIS_PW` aktualisiert, `semantic_index.json` dokumentiert den verifizierten Wert (`normalized_value: "${REDIS_PASSWORD}"`).

**Konsequenzen**:

- ➕ Secrets in Runtime, Dokumentation und Graph identisch; Runbooks funktionieren ohne Korrekturen
- ➕ Risk Manager Security-Abschnitt verweist auf ENV-Ladung gemäß `.env`
- ➕ ADR-Referenz für zukünftige Rotation vorhanden (siehe Session Memo 2025-11-02)
- ➖ Rotationen erfordern Pflege der Wissensgraph-Metadaten und Session-Memos

---

## ADR-024: Event Literal Standardization

**Datum**: 2025-11-02  
**Status**: ✅ Beschlossen  
**Kontext**: Dokumentationsbeispiele (Service-Kommunikation & Datenflüsse, Risikomanagement-Logik) nutzten abweichende Event- und Alert-Bezeichner (`order_results`, `filled_qty`, `DAILY_LIMIT`). `EVENT_SCHEMA.json` definiert jedoch `order_result`, `filled_quantity`, `RISK_LIMIT`, `DATA_STALE`, `CIRCUIT_BREAKER` als verbindliche Literale.

**Optionen**:

- A) Dokumentation unverändert lassen und Abweichungen in Fußnoten erklären
- B) Beispiele auf Schema-Enums angleichen und Wissensgraph-Relationen als `verified` markieren
- C) Schema an Dokumentation anpassen und Konfliktregister erweitern

**Entscheidung**: Option B – Schema bleibt maßgeblich. Alle Beispiele werden angepasst, und `semantic_index.json` markiert die Relationen `event_schema → service_dataflow_doc` und `event_schema → risk_logic_doc` als `relation: "normalized"`, `verified: true`.

**Konsequenzen**:

- ➕ Einheitliche Payload-Literale eliminieren Tool- und Validierungsfehler
- ➕ Risk-Alerts nutzen kanonische Codes, wodurch Downstream-Filter funktionieren
- ➕ Normalization Report kann Phase 3 als abgeschlossen markieren
- ➖ Künftige Schemaänderungen erfordern unmittelbare Doku-Anpassungen + Graph-Update

---

## ADR-027: Kontrollierter Archiv-Migrationsprozess (Phase 5)

**Datum**: 2025-11-02  
**Status**: ✅ Beschlossen  
**Kontext**: Für den Abschluss von Phase 5 müssen Legacy-Dokumente aus `docs/` in das Archiv überführt werden. Frühere Ad-hoc-Moves führten zu Wissenslücken und widersprüchlichen Referenzen (fehlende Frontmatter, unvollständige Knowledge-Graph-Updates, kein Dry-Run). Der neue Prozess soll Archivierung, Governance und Wissensgraph synchron halten.

**Optionen**:

- A) Dokumente bei Bedarf direkt verschieben und Migrationen manuell dokumentieren
- B) Einmalige Bulk-Migration durchführen und Nacharbeiten später erledigen
- C) Einen kontrollierten Workflow mit Review-Plan, Dry-Run und gebundener Dokumentationspflicht einführen ("Safety over neatness")

**Entscheidung**: Option C – Gesteuerter Archivierungsprozess mit verpflichtendem Review, Dry-Run-Report und Governance-Spiegelung. Verschiebungen erfolgen nur bei `migration_status = approved` und gesetztem `approved_target`.

**Konsequenzen**:

- ➕ Einheitlicher Blick auf alle Kandidaten über `docs/smarter_assistant/migration_plan.md`
- ➕ Dry-Run (`migration_report_preview.md`) verhindert unbeabsichtigte Moves
- ➕ Frontmatter (`status`, `source`, `migrated_to`) und Knowledge-Graph bleiben konsistent
- ➕ Governance-Dokumente (PROJECT_STATUS, SESSION_MEMO_ORGANISATION) spiegeln Migrationen sofort wider
- ➖ Höherer Aufwand pro Migration, da Review und Dokumentationsschritte verpflichtend sind

**Umsetzung**:

- `migration_plan.md` als Primärquelle für Status (`planned_target`, `approved_target`, `migration_status`, Review-Notizen)
- Pilot-Migration `7D_PAPER_TRADING_TEST.md` in `archive/docs/` inklusive YAML-Frontmatter (`status: archived`, `migrated_to` gesetzt)
- Einrichtung eines Dry-Run-Reports (`migration_report_preview.md`) vor weiteren Moves
- 2025-11-02: Dry-Run für README_GUIDE.md → `archive/docs/README_GUIDE.md` erstellt; Graph-Kanten `archived_from`/`migrated_to` vorerst mit `verified:false` hinterlegt
- 2025-11-02: Produktive Archivierung freigegeben – Datei liegt unter `archive/docs/README_GUIDE.md`, Frontmatter erweitert, Relationen auf `verified:true` gesetzt
- Nach jeder Freigabe: Updates in `PROJECT_STATUS.md`, `Knowledge_Map.md`, `semantic_index.json` und Session-Memo 2025-11-02
- Beibehaltung der Schutzregel `pending` → kein Move, bis Review abgeschlossen ist

**Abhängigkeiten**:

- Wissensgraph-Artefakte (`Knowledge_Map.md`, `semantic_index.json`) müssen nach tatsächlicher Migration angepasst werden
- Archiv-Strukturen (`archive/docs/reports`, `archive/docs/research`, `archive/logs/inventory`) werden vor jedem Move auf Existenz geprüft
- Governance bleibt führend: Abweichungen oder Sonderfälle werden in `SESSION_MEMO_ORGANISATION_2025-11-02.md` dokumentiert


## ADR-029-R: Soft-Freeze & Continuous Learning Framework

**Datum**: 2025-11-02  
**Status**: ✅ Beschlossen  
**Kontext**: Nach Abschluss der produktiven Archivierung (ADR-027) soll das Repository auditierbar bleiben, ohne den laufenden Betrieb zu blockieren. Reviewer benötigen weiter Zugriff auf konsistente Artefakte, während Operationsteam und Agenten Wissen und Code fortlaufend pflegen.

**Optionen**:
- A) Bisherigen Hard-Lock beibehalten (keine Änderungen bis Review-Ende)
- B) Soft-Freeze mit Audit-Baseline und verpflichtender Protokollierung
- C) Vollständige Entsperrung ohne zusätzliche Kontrollen

**Entscheidung**: Option B – Soft-Freeze. Audit-Baseline (`audit_snapshot_2025-11-02.json`) bleibt Referenz, Delta-Audits protokollieren Änderungen, Live-Writes bleiben unter ADR-027-Sicherheitsregeln erlaubt.

**Konsequenzen**:
- ➕ Repository bleibt produktiv nutzbar (Paper/Live Trading, Wissenspflege)
- ➕ Jede Änderung bleibt rückverfolgbar (Snapshot + Delta-Audit, Session-Memo)
- ➖ Zusätzlicher Aufwand für kontinuierliche Delta-Dokumentation

**Folgeaktionen**:
- `PROJECT_STATUS.md`: Governance Mode Abschnitt mit Soft-Freeze-Status
- `SESSION_MEMO_ORGANISATION_2025-11-02.md`: Kontinuierliche Operation samt Delta-Audit-Vermerk dokumentiert
- `backoffice/audits/`: Delta-Audit-Dateien pro Lauf anlegen; Baseline regelmäßig erneuern


## Audit-Review-Abschluss: Keine Findings, ADR-030 nicht erforderlich

**Datum**: 2025-11-02 18:30 UTC  
**Status**: ✅ Abgeschlossen  
**Kontext**: Nach Handover Report 2025-11-02 17:00 UTC hat Audit-Team (GitHub Copilot) unabhängigen 7-Phasen-Review nach REVIEW_README.md-Protokoll durchgeführt. Ziel war Verifikation von Governance-Kohärenz, Knowledge-Graph-Konsistenz und technischer Integrität.

**Prüfumfang**:
1. **Audit-Artefakte**: `audit_snapshot_2025-11-02.json`, `delta_audit_2025-11-02T16-45Z.json`, `semantic_index_export.graphml`
2. **Governance**: ADR-027 → ADR-029-R Chain, Continuous Operation Mode, Git-Refs
3. **Knowledge-Layer**: `semantic_index.json` (≥95% verified:true), `Knowledge_Map.md`, Archive-Cluster
4. **Technik**: Docker-Status (10/10 Container healthy), ENV/Compose-Konsistenz, requirements.txt
5. **Review-Bericht**: `HANDOVER_REVIEW_REPORT_2025-11-02T18-30Z.md` (450+ Zeilen)

**Ergebnis**:
- ✅ **Governance**: ADR-Chain vollständig (ADR-027 → ADR-029-R), Continuous Operation Mode aktiv
- ✅ **Knowledge-Graph**: 100% Relations `verified:true` (manuelle Prüfung bestätigt ≥95%-Anforderung erfüllt)
- ✅ **Technik**: 10/10 Container healthy (6h+ Uptime), ENV/Compose konsistent (REDIS_PASSWORD = REDACTED_REDIS_PW, POSTGRES_PASSWORD = cdb_secure_password_2025)
- ✅ **Link-Audit**: Letzter Run 2025-11-02 15:10 UTC → 0 Fehler
- 🟡 **Optionale Empfehlungen**: 2 Package-Updates (redis 7.0.0→7.0.1, ruff 0.14.2→0.14.3), 1 Doku-Ergänzung (GraphML-Viewer-Hinweis)

**Entscheidung**: **ADR-030 nicht erforderlich**  
**Begründung**: Keine kritischen Findings, keine Governance-Abweichungen, System operational-ready. Optionale Package-Updates können im Rahmen regulärer Maintenance erfolgen (kein Audit-Blocker).

**Konsequenzen**:
- ➕ Phase 7 (Paper Trading) genehmigt – System bereit für Produktivbetrieb
- ➕ Continuous-Operation-Mode bleibt aktiv (ADR-029-R), keine Sperren
- ➕ Repository weiterhin schreibfähig unter ADR-027-Safety-Protokoll
- ➖ Optionale Package-Updates bleiben dokumentiert (code_review_prep.md), aber nicht verpflichtend

**Deliverables**:
- `HANDOVER_REVIEW_REPORT_2025-11-02T18-30Z.md` (backoffice/audits/)
- `PROJECT_STATUS.md` aktualisiert (Phase 6.8: Audit-Team Review)
- `DECISION_LOG.md` (dieser Eintrag)

**Sign-Off**: GitHub Copilot (Audit-Team) → IT-Chef  
**Freigabe**: Repository operational-ready, Phase 7 kann starten.

---

## ADR-031: Development Philosophy - Quality over Speed

**Datum**: 2025-11-03  
**Status**: ✅ Beschlossen  
**Kontext**: Nach erfolgreicher Stabilisierung in Phase 7 soll die Entwicklungsphilosophie explizit formalisiert werden: **Qualität und Sorgfalt haben Vorrang vor Geschwindigkeit**. Dies reflektiert die bewährten Praktiken, die zum aktuellen stabilen Zustand geführt haben.

**Problem**:
- Schnelle, ungeprüfte Änderungen führten historisch zu Instabilitäten (z.B. compose.yaml-Konflikt, ADR-005)
- Dokumentations-Lücken erschwerten Debugging und Onboarding
- Fehlende Governance-Prozesse verzögerten Reviews und Audits

**Entscheidung**: Etablierung verbindlicher Entwicklungsprinzipien:

### 1. **Dokumentation vor Code**
- Jede Änderung wird **erst dokumentiert, dann implementiert**
- Architektur-Änderungen → `ARCHITEKTUR.md` + ADR in `DECISION_LOG.md`
- Event-Schema-Änderungen → `EVENT_SCHEMA.json` + betroffene `models.py`
- Konfigurationsänderungen → `.env`, `docker-compose.yml` + Validierung

### 2. **Schrittweise Umsetzung**
- Keine "Big Bang"-Änderungen; iterative, validierte Schritte
- Nach jeder Änderung: `docker compose config`, Health-Checks, Tests
- Bei Unsicherheit: **lieber nachfragen statt raten**

### 3. **Ordnung als Priorität**
- Keine temporären Workarounds im produktiven Code
- Deprecated Code → `archive/` mit Begründung
- Duplikate vermeiden, bestehende Strukturen nutzen

### 4. **Mandatory Review-Checkpoints**
- Vor jedem Commit: Review-Checkliste aus `DEVELOPMENT.md` durchgehen
- Bei strukturellen Änderungen: Audit-Snapshot + Delta-Audit
- Session-Ende: `SESSION_MEMO` mit Zeitstempel + Entscheidungen

### 5. **Fehlerkultur**
- Fehler sind Lernchancen, nicht Blocker
- Incident Reports dokumentieren Root Cause + Prevention (siehe `2025-10-30_RECOVERY_REPORT.md`)
- Knowledge Base wird kontinuierlich erweitert (Research-Dokumente)

**Implementierung**:
- `DEVELOPMENT.md` erweitert um "0️⃣ Entwicklungsphilosophie"-Abschnitt
- `ARCHITEKTUR_REGELN.md` um Abschnitt "6. Entwicklungstempo" ergänzt
- `SESSION_MEMO_PHILOSOPHY_2025-11-03.md` als Einführungsdokument

**Konsequenzen**:
- ➕ Stabilität und Wartbarkeit haben Vorrang
- ➕ Neue Entwickler können sich auf klare Prinzipien verlassen
- ➕ Audits und Reviews werden beschleunigt (weniger Nacharbeiten)
- ➖ Entwicklungszyklen werden länger (bewusst akzeptiert)
- ➖ Erfordert Disziplin und kontinuierliche Dokumentation

**Validation**:
- Alle zukünftigen PRs müssen Review-Checkliste erfüllen
- Session-Memos sind verpflichtend für strukturelle Änderungen
- Continuous Operation Mode (ADR-029-R) bleibt aktiv, aber Safety-Protokoll wird strenger

**Referenzen**:
- `DEVELOPMENT.md` - Entwicklungsrichtlinien
- `ARCHITEKTUR_REGELN.md` - Operative Leitplanken
- `2025-10-30_RECOVERY_REPORT.md` - Lessons Learned aus Stabilisierungsphase

**Sign-Off**: GitHub Copilot (Development Philosophy Initiative)  
**Gültigkeit**: Ab sofort für alle Repository-Änderungen

---

## ADR-032: Python Base Image Pin auf 3.13-slim (statt 3.14-slim)

**Datum**: 2025-11-09  
**Status**: ✅ Beschlossen  
**Kontext**: Dependabot schlug Updates von `python:3.11-slim` → `python:3.14-slim` für alle Dockerfiles vor (PRs #15, #13, #12). Python 3.14.0 wurde am 15.10.2024 released und ist auf Docker Hub verfügbar.

**Problem**:
- Python 3.14 ist erst seit ~3 Wochen stabil (released 15.10.2024)
- Production-Systeme benötigen bewährte, stabile Versionen
- 3 Major-Bumps (3.11→3.12→3.13→3.14) erhöhen Risiko für Breaking Changes
- Dependabot empfiehlt automatisch die neueste verfügbare Version (nicht immer optimal)

**Evaluierte Optionen**:

1. **Python 3.14-slim** (neueste)
   - ➕ Neueste Features & Security-Patches
   - ➖ Erst seit 3 Wochen stabil
   - ➖ Unbekannte Production-Erfahrungen
   - ➖ 3 Major-Bumps erhöhen Test-Aufwand

2. **Python 3.13-slim** (empfohlen)
   - ➕ Released 2024-10-07 (bereits 1 Monat stabil)
   - ➕ EOL: 2029-10 (guter Support-Zeitraum)
   - ➕ Gut getesteter Upgrade-Pfad 3.11→3.13
   - ➕ Balance zwischen Aktualität und Stabilität
   - ➖ Nicht die absolute neueste Version

3. **Python 3.12-slim** (konservativ)
   - ➕ LTS-Version, sehr stabil
   - ➕ EOL: 2028-10
   - ➖ Weniger neue Features

**Entscheidung**: Pin auf **python:3.13-slim** für alle Services

**Begründung**:
- **Produktions-Stabilität:** Python 3.13 hat bereits ~1 Monat Production-Erprobung
- **Sicherheits-Unterstützung:** EOL 2029-10 deckt Multi-Jahr-Support ab
- **Bewährter Upgrade-Pfad:** 3.11→3.13 ist gut dokumentiert & getestet
- **Risk-Mitigation:** 2 Major-Bumps statt 3 reduziert Breaking-Change-Risiko
- **Best Practice:** Production-Systeme sollten nicht auf bleeding-edge Versionen laufen

**Alternative für 3.14-Fans**:
Falls Python 3.14 gewünscht wird, exakte Version pinnen:
```dockerfile
FROM python:3.14.0-slim
```
Statt `3.14-slim` (verhindert auto-upgrade auf 3.14.1, 3.14.2, etc.)

**Implementierung**:
- PRs #15, #13, #12: Änderung von `3.14-slim` → `3.13-slim` committen
- Docker Compose Build-Tests durchführen
- Service-Start & Health-Checks validieren
- Nach grünen Tests → mergen

**Betroffene Dateien**:
- `backoffice/services/signal_engine/Dockerfile`
- `backoffice/services/risk_manager/Dockerfile`
- `Dockerfile` (root, für Screener)

**Rollback-Plan**:
Falls Kompatibilitätsprobleme auftreten:
```dockerfile
FROM python:3.11-slim
```

**Testing-Protokoll**:
- ✅ Docker Hub Tag-Verfügbarkeit geprüft (3.13-slim verfügbar)
- ⏳ Docker Build Tests (nach Commit)
- ⏳ Service Health-Checks (nach Deployment)
- ⏳ E2E-Test (optional, da kein Breaking Change erwartet)

**Konsequenzen**:
- ➕ Stabile, production-ready Python-Version
- ➕ Reduziertes Risiko für Breaking Changes
- ➕ Multi-Jahr-Support durch EOL 2029
- ➖ Verzicht auf absolute neueste Features (Python 3.14)
- ➖ Erfordert manuellen Dependabot-Override (statt auto-merge)

**Related PRs**:
- PR #15: signal_engine Docker Update
- PR #13: root Docker Update
- PR #12: risk_manager Docker Update

**Referenzen**:
- [Python Release Schedule](https://peps.python.org/pep-0619/)
- [Docker Hub python:3.13-slim](https://hub.docker.com/_/python?tab=tags&name=3.13-slim)
- `docs/PR_REVIEW_BATCH_2025_11_09.md` (Detailanalyse)

**Sign-Off**: GitHub Copilot Coding Agent (PR Review Session)  
**Gültigkeit**: Ab sofort für alle Python-Dockerfile-Updates




---

## ADR-032: Copilot-Instructions Update - Issue #6 Integration

**Datum**: 2025-11-09  
**Status**: ✅ Beschlossen  
**Kontext**: Issue #6 enthielt umfangreiche Application-Configuration für Copilot Coding Agent mit operativen Anweisungen, die in der aktuellen `copilot-instructions.md` fehlten. Diese sollten mit der bestehenden Konfiguration verglichen und bei Verbesserungen übernommen werden.

**Problem**: 
- Aktuelle `copilot-instructions.md` (80 Zeilen) fokussierte sich auf allgemeine Leitplanken
- Issue #6 Content enthielt spezifische operative Anweisungen:
  - Session-Start-Pflicht (Docker-Container prüfen/starten)
  - Audit-Referenzen mit konkreten Dateipfaden
  - Architekturfluss (Event-Pipeline)
  - Logging-Regeln
  - Sofortige Dokumentationspflicht
  - Konkrete Validierungsbefehle

**Optionen**:
- A) Issue #6 Content komplett übernehmen und bestehende Struktur ersetzen
- B) Nur neue Inhalte minimal-invasiv in bestehende Struktur integrieren
- C) Separate Datei für operative Anweisungen erstellen

**Entscheidung**: Option B - Minimal-invasive Erweiterung der bestehenden Struktur

**Implementierung**:

### 1. Abschnitt 2 erweitert: "Session-Start & Sicherheits-Regeln"
- **Neu 2.1 Session-Start-Routine (PFLICHT)**:
  - Container-Status prüfen: `docker ps --filter "name=cdb_"`
  - Falls Container fehlen: `docker compose up -d`
  - 10 Sekunden warten und Health-Status prüfen
  - `PROJECT_STATUS.md` lesen vor weiteren Aufgaben
- **2.2 Sicherheits- & Compliance-Regeln** (bestehend, unverändert)

### 2. Abschnitt 6 erweitert: "Arbeitsrichtlinien (Do)"
- **Architekturfluss**: `market_data` → `signals` → `orders` → `order_results`
- **Payload-Validierung**: EVENT_SCHEMA.json Pflicht, Änderungen in models.py spiegeln
- **Logging-Regel**: Nur über `backoffice/logging_config.json` (keine Inline-Logger)
- **Sofortige Dokumentation**: Nach jeder Handlung dokumentieren, nicht erst am Sessionende (entspricht ADR-015)

### 3. Abschnitt 7 erweitert: "Tests & Validierungen"
- **Validierung vor Merge (PFLICHT)** hinzugefügt:
  - `docker compose config` ohne Fehler
  - Services mit Health-Checks grün (`/health`, `/status`, `/metrics`)
  - `.env` ohne Duplikate; Ports und DB-Name konsistent
  - Schema- und Event-Checks gegen `EVENT_SCHEMA.json`

### 4. Neuer Abschnitt 11: "Audit-Referenzen"
- **Aktuellste Audits** mit konkreten Dateipfaden:
  - `HANDOVER_REVIEW_REPORT_2025-11-02T18-30Z.md` (neuester)
  - `HANDOVER_REPORT_2025-11-02.md`
  - `2025-10-30_RECOVERY_REPORT.md`
  - `AUDIT_SUMMARY.md`, `DIFF-PLAN.md`
- **Audit-Vorgaben**: DIFF-PLAN.md als Quelle nutzen, Abweichungen dokumentieren

**Konsequenzen**:
- ➕ Operative Stabilität durch Session-Start-Routine sichergestellt
- ➕ Klare Audit-Referenzen für Nachvollziehbarkeit
- ➕ Architekturfluss und Logging-Regeln explizit dokumentiert
- ➕ Konkrete Validierungsbefehle vermeiden Fehler vor Merge
- ➕ Bestehende Struktur (10 Abschnitte) bleibt erhalten, nur erweitert
- ➖ Datei wächst von 80 auf 109 Zeilen (+36%)

**Validation**:
- ✅ Alle 11 Abschnitte vorhanden und korrekt strukturiert
- ✅ Neue Inhalte sinnvoll in bestehende Abschnitte integriert
- ✅ Audit-Dateipfade gegen `backoffice/audits/` validiert
- ✅ Keine bestehenden Inhalte überschrieben oder entfernt

**Referenzen**:
- Issue #6: "Application Adolph" - GitHub Issue mit Copilot-Konfiguration
- ADR-015: Sofortige Handlungsdokumentation im Copilot-Workflow
- ADR-031: Development Philosophy - Quality over Speed
- `backoffice/audits/` - Referenzierte Audit-Dateien

**Sign-Off**: GitHub Copilot  
**Gültigkeit**: Ab sofort für alle Copilot-Sessions

---

## ADR-033: Titel-Norm & Board-Automatisierung aktiviert

**Datum**: 2025-11-09
**Status**: Entwurf / Implemented (tools added: PR Title Lint, Labeler)

Kurz: Standardisierung von PR/Issue-Titeln und Einführung leichtgewichtiger Automatisierungen für das Kanban-Board (Saved Views, Felder, Automationen als Spezifikation). Actions zur Titel-Prüfung und automatisches Labeling wurden als PR zur Überprüfung hinzugefügt.

Referenzen:
- docs/KANBAN_SETUP.md

---

## ADR-034: Copilot-Instructions Update - Verantwortlicher gesetzt

**Datum**: 2025-11-10  
**Status**: ✅ Beschlossen

**Kontext**: Die Copilot-Instruktionen enthielten bei der Verantwortlichkeit für das letzte Update den Platzhalter "TBD".

**Änderung**: Aktualisierung der Zeile "Letztes Update" in `.github/copilot-instructions.md`:
- Von: `Verantwortlich: TBD`
- Zu: `Verantwortlich: jannekbuengener`

**Begründung**: Klare Zuordnung der Verantwortlichkeit für die Copilot-Instruktionen an den Repository-Owner.

**Konsequenzen**:
- ➕ Klare Verantwortlichkeit dokumentiert
- ➕ Vollständige Audit-Trail für Copilot-Konfiguration
