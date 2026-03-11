# IST-ZUSTAND: cdb_grafana

**ID:** `cdb_grafana`
**Typ:** Monitoring & Visualisierung
**Technologie:** Grafana (Docker Image)

---

## 1. Kurzbeschreibung

`cdb_grafana` ist der zentrale Visualisierungs-Service des Stacks. Er nutzt Grafana, um Metriken, Logs und Geschäftsdaten aus verschiedenen Quellen (Prometheus, PostgreSQL) in Dashboards darzustellen. Der Service ist als Standard-Grafana-Container konfiguriert und wird über Docker Compose gesteuert.

## 2. Kernfunktionen & Verantwortlichkeiten

- **Visualisierung von Systemmetriken:** Darstellung von CPU-, Speicher- und Netzwerk-Metriken, die von Prometheus gesammelt werden.
- **Darstellung von Anwendungs-KPIs:** Visualisierung von Geschäftsmetriken wie die Anzahl der Trades, Signale, PnL (Profit and Loss) und die Portfolio-Zusammensetzung.
- **Fehler- und Performance-Analyse:** Bietet Dashboards zur Überwachung der Service-Gesundheit, Latenzzeiten und Fehlerraten.
- **Zentrales Monitoring-Hub:** Dient als einheitliche Schnittstelle für das Echtzeit-Monitoring des gesamten Handelssystems.

## 3. Architektur & Integration

- **Containerisierung:** Der Service läuft als `grafana/grafana:latest` Docker-Container, definiert in `docker-compose.yml` und `docker-compose.base.yml`.
- **Datenquellen (Datasources):**
    - **Prometheus (`cdb_prometheus`):** Hauptquelle für System- und Anwendungsmetriken. Die Konfiguration erfolgt durch Provisioning (`infrastructure/monitoring/grafana/provisioning/datasources/prometheus.yml`).
    - **PostgreSQL (`cdb_postgres`):** Direkter Zugriff auf die Handelsdatenbank (`claire_de_binare`) zur Visualisierung von Trades, Orders und Portfolio-Snapshots. Konfiguration erfolgt durch Provisioning (`infrastructure/monitoring/grafana/provisioning/datasources/postgres.yml`).
- **Dashboards:**
    - Dashboards sind als JSON-Dateien im Verzeichnis `infrastructure/monitoring/grafana/dashboards/` gespeichert.
    - Sie werden beim Start des Containers automatisch provisioniert (`/etc/grafana/provisioning/dashboards/` und `/var/lib/grafana/dashboards/`).
    - **Beispiele für Dashboards:**
        - `claire_dark_v1.json`: Haupt-Dashboard.
        - `claire_execution_v1.json`: Überwachung des Execution Service.
        - `claire_risk_manager_v1.json`: Risiko-Metriken.
        - `claire_system_performance_v1.json`: System-Performance.
- **Persistenz:** Grafana-spezifische Daten (z.B. Benutzer, Einstellungen) werden in einem Docker-Volume namens `grafana_data` gespeichert, um sie über Container-Neustarts hinweg zu erhalten.
- **Security:** Das Admin-Passwort wird über ein Docker Secret (`grafana_password`) sicher an den Container übergeben.

## 4. Abhängigkeiten

- **Upstream:**
    - `cdb_prometheus`: Liefert die meisten Zeitreihen-Metriken.
    - `cdb_postgres`: Dient als Quelle für relationale Geschäftsdaten.
- **Konfiguration:**
    - `docker-compose.yml`: Definiert den Service, Ports und Volumes.
    - `./.secrets/grafana_password`: Enthält das Admin-Passwort.
    - `infrastructure/monitoring/grafana/`: Beinhaltet alle Provisioning-Konfigurationen für Datenquellen und Dashboards.

## 5. Status & Bewertung

- **Zustand:** Funktional und gut integriert.
- **Stärken:**
    - Nutzt das "Configuration as Code"-Prinzip durch Provisioning von Datenquellen und Dashboards, was die Reproduzierbarkeit sicherstellt.
    - Klare Trennung von Konfiguration (im Git-Repo) und Laufzeitdaten (im Docker-Volume).
    - Sicherheit durch die Verwendung von Docker Secrets für das Passwort.
- **Potenzielle Risiken/Schwächen:**
    - Das `latest`-Tag für das Grafana-Image kann bei Updates zu unerwarteten Änderungen führen. Eine feste Version (z.B. `grafana/grafana:10.2.2`) wird empfohlen.
    - Bei einer großen Anzahl von Dashboards kann die Verwaltung der JSON-Dateien unübersichtlich werden.

**Fazit:** Der Service ist robust und nach Best Practices für einen Docker-basierten Betrieb aufgesetzt. Er ist eine kritische Komponente für die Beobachtbarkeit des Systems.

