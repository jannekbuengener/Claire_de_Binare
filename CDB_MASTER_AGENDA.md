# Claire de Binare – MASTER-AGENDA (AKTUALISIERT)

> Single Source of Truth für Architektur, Stack, Workflows und Betrieb

---

## P0 – Fundament, Hygiene, WSL2-Migration

### 0.1 Repo-Root aufrollen (Kellerkiste-Policy)
- Aktive Struktur im Root:
  - `/src`, `/infra`, `/docker`, `/docs`, `/agents`, `/workflows`, `/backoffice`
- Altmaterial verschieben nach: `/_archive/_kellerkiste_YYYYMM/`
- `/_archive/README.md` mit kurzer Übersicht, was archiviert wurde
- Prinzip: keine Hortkultur – alles hat Lifecycle (Archiv → ggf. löschen)

### 0.2 WSL2-Architektur finalisieren
- Zielbild: **Windows Host → WSL2 (Ubuntu) → Docker Engine**
- Haupt-Repo liegt nur im Linux-Filesystem: `/home/<user>/cdb`
- Docker Desktop nutzt WSL2 als Backend
- Klare Regeln für:
  - Host-Editor vs. WSL2-Pfade
  - Port-Nutzung (localhost-only)
  - Volumes / Bind-Mounts

### 0.3 Docker Performance & Sicherheit
- Projektverzeichnisse ausschließlich unter `/home/<user>/...`
- Keine Container mit offenen Public-Ports
- Logging-Ordner: `/var/log/cdb` oder `./logs/...` mit Mounts

---

## P1 – MCP Infrastruktur (Toolstack + Inside Stack)

### 1.1 MCP Gateway (Basis)
- Docker MCP Gateway als Single Entry Point
- Aktivierte MCP-Server:
  - `filesystem` (mit neuer Root-/Kellerkisten-Struktur)
  - `github-official` oder `gitlab`
  - `agents-sync`
  - `cdb-logger`
- Ziel: Von außen immer nur über MCP arbeiten

### 1.2 MCP Toolstack (extern)

**Monitoring & Metriken**
- `grafana/grafana:latest`
- `prom/prometheus:latest`
- `prom/node-exporter:latest`
- `gcr.io/cadvisor/cadvisor:latest`
- `telegraf:latest`
- `influxdb:latest` (optional, wenn zusätzlich zu Prometheus benötigt)

**Docker-Management**
- `portainer/portainer-ce:latest`
- `containrrr/watchtower:latest` (Option: automatische Updates)

**Logging (ELK)**
- `elasticsearch:latest`
- `logstash:latest`
- `kibana:latest`

Ziel:
- Alle Container-Metriken via Prometheus + Grafana
- Alle Logs zentral via ELK

### 1.3 MCP Inside Stack (intern, CDB-spezifisch)
- `agents-sync-server`
  - Verwaltet Workflows, Agenten-Metadaten, Governance
- `cdb-logger-server`
  - Strukturierte Logs für Sessions, Entscheidungen, Status
- Optionale interne MCP-Services:
  - Status Engine
  - Dokumentations-Refresher (AKTUELLER_STAND)
  - Governance-Updater (DECISION_LOG)
  - Event-Flow-Validator

---

## P2 – DevOps, CI/CD, Security, Qualität

### 2.1 CI/CD – `/install-github-actions`
- Script/Workflow:
  - Build
  - Tests
  - Lint/Format
  - Security-Checks
  - (Paper-)Deploy
- GitHub Actions oder GitLab CI als primäre Pipeline
- Branch-Policy: kein Merge ohne grüne Pipeline

### 2.2 SonarQube
- SonarQube-Instanz (lokal/remote)
- Projekt in CI integrieren
- Quality Gates definieren:
  - Keine Blocker-Bugs
  - Minimale Coverage
  - Kritische Smells verboten

### 2.3 HashiCorp Vault
- Vault als zentrale Secret-Quelle
- Alle Secrets aus .env/.yaml entfernen
- Applikation/Agents lesen Secrets ausschließlich aus Vault
- Vault-Zugriff über Tokens/Policies sauber regeln

### 2.4 Docker Observability
- Node Exporter: Host-Metriken (CPU, RAM, Disk)
- cAdvisor: Container-Metriken
- Prometheus: Scrapes Host + Container
- Grafana: Standard-Dashboards für:
  - System-Gesundheit
  - Container-Status
  - App-spezifische KPIs

---

## P3 – CDB Runtime System (Paper Mode)

### 3.1 Core Services (als Docker-Stack)
Typische Services (Beispiel-Set):
- `cdb_core`, `cdb_ws`, `cdb_risk`, `cdb_execution` (Paper), `cdb_db_writer`
- `postgres`, `redis`
- `cdb_prometheus`, `cdb_grafana`

Ziel:
- Vollständiger, aber sicherer Paper-Trade-Betrieb
- Kein echter Kapitalfluss, aber echte Komplexität

### 3.2 Zero-Activity-Incident Logic
Basierend auf CLAUDE.md:
- Kein Handeln, bevor:
  - Logs geprüft
  - Event-Flow validiert
  - Risk-Layer bestätigt
  - DB/Reports konsistent
  - Smoke/E2E Tests bestanden
- Diese Checks als definierte Playbooks dokumentieren

### 3.3 Block-Workflow (72h + Analysephase)
- 3-Tage-Blöcke (Block #n)
- Am Blockende:
  - Analyse
  - KPIs
  - Lessons Learned
  - Updates in DECISION_LOG / Doku
- Nur neuer Block nach bestandenem Event-Flow-Test

---

## P4 – Dokumentation & Knowledge („Extec“)

### 4.1 Doku-Bibliothek
- Tool auswählen (z.B. Git-Wiki, MkDocs, BookStack, o.Ä.)
- Kernbereiche:
  - `01_Architektur`
  - `02_Prozesse & Workflows`
  - `03_Stacks (WSL2, MCP, Monitoring, CI/CD)`
  - `04_Incident-Management & CLAUDE`
  - `05_Governance & Policies`

Prinzip:
- Wissen kommt in die Doku, nicht lose ins Repo
- Repo enthält nur die aktuellen, benötigten Artefakte

### 4.2 Doku-Automation
- AKTUELLER_STAND:
  - Regelmäßige Status-Updates automatisiert erzeugen
- DECISION_LOG:
  - Wichtige Architektur-/Betriebsentscheidungen erfassen
- Session-/Runbooks:
  - Automatisiert generieren und ablegen

---

## P5 – Feature- & Bug-Workflows

### 5.1 Bugfix-Workflow
- Bug triagieren (Impact, Ursache)
- Fix-Plan skizzieren
- Umsetzung in Branch
- Tests (Unit, Integration, ggf. E2E)
- Merge + Doku-Update

### 5.2 Feature-Workflow
- Feature-Definition + Abgrenzung
- Architektur & Risk-Bewertung
- Implementierung in Feature-Branch
- Tests (Unit, Integration, ggf. E2E)
- Release + Doku (Doku-Bibliothek + Changelog)

### 5.3 Signal-Tuning
- Analyse der Signale (Performance, Drawdown, Noise)
- Anpassung von Parametern/Strategien
- Testphase in Paper Mode
- Monitoring via Grafana/Prometheus
- Entscheidung im DECISION_LOG dokumentieren

### 5.4 Governance-Updates
- Agents/Tools/Workflows regelmäßig überprüfen
- AGENTS.md / Governance-Dokumente aktualisieren
- Änderungen immer über PR + Review

### 5.5 Status Update Workflow
- Regelmäßige AKTUELLER_STAND-Updates
- Daten aus Monitoring/Logs automatisch einfließen lassen
- Ziel: Management-Readiness ohne Ad-hoc-Suche

---

## P6 – Erweiterter Monitoring-Agentenstack (Docker)

### 6.1 Standard-Container

**Monitoring & Metrik**
- `grafana/grafana:latest`
- `prom/prometheus:latest`
- `prom/node-exporter:latest`
- `gcr.io/cadvisor/cadvisor:latest`
- `telegraf:latest`
- `influxdb:latest` (optional)

**Docker-Management**
- `portainer/portainer-ce:latest`
- `containrrr/watchtower:latest` (optional)

**Logging (ELK)**
- `elasticsearch:latest`
- `logstash:latest`
- `kibana:latest`

### 6.2 Integrationsreihenfolge
1. Node Exporter + cAdvisor starten
2. Prometheus konfigurieren (Targets → Node Exporter, cAdvisor)
3. Grafana verbinden (Prometheus als Datasource)
4. Telegraf für zusätzliche Metrik-/Log-Sammlung einsetzen
5. ELK einführen für Log-Aggregation und Suche
6. Portainer optional für visuelles Docker-Management
7. Watchtower optional für automatische Updates

---

## P7 – Betriebsmodell „Neue Firma“

### 7.1 Anti-Hort-Regeln
- Keine wilden Ablagen im Repo-Root
- Alles, was unklar oder historisch ist:
  - Erst in `/_archive/_kellerkiste_YYYYMM/`
  - Nach definiertem Zeitraum ggf. löschen
- Wichtiges Wissen wandert in die Doku-Bibliothek

### 7.2 Qualitäts- und Security-Gates
- CI/CD mit Pflicht-Pipeline
- SonarQube-Gates
- Vault für Secrets
- MCP als Gatekeeper für Tools & Infrastruktur

### 7.3 MCP als Arbeitsoberfläche
- Interaktion mit Systemen primär über MCP-Server
- Agents folgen den definierten Workflows
- Governance & Logging immer über cdb-logger/agents-sync abbilden

---

## P8 – Next Steps (konkret)

1. P0 abschließen (Root-Aufräumen, Kellerkiste, WSL2-Zielbild)
2. WSL2 + Docker performancestark konfigurieren
3. Monitoring-Stack starten (Prometheus, Node Exporter, cAdvisor, Grafana)
4. MCP Gateway + Toolstack minimal hochziehen
5. MCP Inside Stack (agents-sync, cdb-logger) implementieren
6. CI/CD + Sonar + Vault integrieren
7. Paper-Mode-Services starten und an Monitoring anschließen
8. Doku-Bibliothek (Extec) mit Kerninhalten füllen
9. Governance- und Status-Workflows (AKTUELLER_STAND, DECISION_LOG) aktivieren
