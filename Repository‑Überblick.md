## Repository‑Überblick

* **Name:** `Claire_de_Binare` (Privates Repo, Default‑Branch: `main`).
* **Aktuelle offene Pull‑Requests (Auswahl):** Es gibt viele offene PRs, z. B. #493 „Smart PR Auto‑Labeling & Branch Review“, #495 „Kubernetes‑Deployment + GitOps“, #497 „Advanced Docker Workflow (Gordon)“ sowie diverse Dependabot‑Updates und CI‑Bugfixes.
* **Wichtige Themen in offenen PRs:** Kubernetes‑Bereitstellung, CI‑Optimierungen, Sicherheitsfixes (z. B. Code‑Injection in Workflows), automatisches PR‑Labeling und Governance‑Checks.

## Aufgaben für Copilot

Im Folgenden sind Aufgaben aus offenen Issues zusammengestellt, die speziell Copilot betreffen. Sie sind nach Themen gruppiert und mit den entsprechenden Issue‑Referenzen versehen:

### Workflow‑Automatisierung & Issue‑Management

* **Smart Issue Management (#169):**

  * Workflow `copilot-housekeeping.yml` mit intelligenter Kategorisierung erweitern und einen Issue‑Progress‑Tracker aufbauen.
  * Ein Stabilisations‑Dashboard erstellen und automatische Benachrichtigungen bei kritischen Blockern einrichten.
* **Smart PR‑Auto‑Labeling (#145):**

  * Auf Basis von Dateitypen und Titelmustern automatische Labels setzen (Area, Type, Size etc.) und Governance‑Verstöße erkennen.
  * Einen GitHub‑Action‑Workflow entwickeln, der PRs analysiert, Labels anwendet und bei Verstößen Kommentare ausgibt.
* **GitHub‑Project‑Board erstellen (#114):**

  * Ein Projekt „CDB – Master Roadmap“ mit den Spalten Backlog, Ready, In Progress, Review, Done anlegen und 20+ Issues einpflegen.
  * Automationsregeln konfigurieren, sodass Label‑Änderungen Issues automatisch verschieben.

### CI/CD und DevOps

* **Dual‑Pipeline‑Konsolidierung (#155):**

  * Workflow‑Redundanz zwischen GitLab CI und GitHub Actions analysieren; Workflows optimieren und überwachen.
  * CI‑Dokumentation und Pipeline‑Monitoring einrichten, Performance‑Tracking hinzufügen.
* **Performance‑Tests & Baselines (#162, #168):**

  * Performance‑ und Lasttests in die CI/CD‑Pipeline integrieren, Baselines definieren und Regressionen detektieren.
  * Monitoring‑Daten (Prometheus/Grafana) sammeln und dokumentieren.
* **Developer‑Onboarding (#163):**

  * Automatisierte Setup‑Skripte (Cross‑Platform) entwickeln, Environment‑Health‑Checks implementieren und Setup‑Validierung in CI/CD integrieren.
  * Troubleshooting‑Guide für Entwickler erstellen.
* **Workflow‑Dispatch für geplante Workflows (#403, #400):**

  * In allen geplanten Workflows `workflow_dispatch` aktivieren, damit sie auch bei Billing‑Limits manuell gestartet werden können.

### Infrastruktur & Produktion

* **Umfangreiche Deployment‑Pipeline (#168):**

  * Produktions‑Deployment‑Pipeline aufbauen, Container‑Registry und Image‑Management implementieren, Rollback‑Prozeduren definieren und Umgebungs‑Konfigurationen erstellen.
  * Sicherheitsscans und Secret‑Rotation mit CI/CD verknüpfen.
* **Environment‑Setup (#123):**

  * `.env.example` um `MODE=paper` und `EXECUTION=dry-run` erweitern, Papier‑Trading‑Runbook erstellen und System mit `make docker-up` sowie `docker-health` validieren.
* **Cluster‑Planung (#121):**

  * M7‑Skelett mit 5–8 Clustern (Data/Feed, Signal, Risk, Execution, PSM, Observability, Reporting, Ops) erstellen. Pro Cluster 3–7 Unteraufgaben mit Akzeptanzkriterien und Abhängigkeiten definieren.

### Governance & Dokumentation

* **Governance‑Migrating & Compliance (#158, #166):**

  * Alle Agenten‑ und Governance‑Dateien aus dem Working‑Repo in die Docs‑Hub verschieben, Governance‑Metadaten im Working‑Repo entfernen und die Ausführungs‑Repo säubern.
  * Systematische Verstöße beheben und Compliance‑Monitoring einrichten.
* **Prompt‑Migration (#118):**

  * Alle `.txt`‑Promptdateien inventarisieren, als `.md` mit YAML‑Frontmatter migrieren und die `DOCS_HUB_INDEX.md` aktualisieren.
  * Ursprüngliche `.txt`‑Dateien mit „DEPRECATED“ markieren.
* **Weekly Status Digest (#120):**

  * Vorlage `weekly_report_TEMPLATE.md` (≤ 1 Seite) und Beispiel `weekly_report_YYYYMMDD.md` im `knowledge/logs/weekly_reports`‑Ordner erstellen.
* **CI/CD‑Dokumentation (#112):**

  * Eine vollständige CI/CD‑Leitfaden‑Dokumentation (CI_PIPELINE_GUIDE.md) und ein Troubleshooting‑Dokument anlegen – alle Stufen, typische Fehler und lokale Setup‑Anleitung.
* **Büro‑Files Review (#119):**

  * Neue Büro‑Files im Docs‑Hub inventarisieren, klassifizieren (OK, OK+Hinweis, Konfliktpotenzial) und Duplikate (z. B. CONSTITUTION.md vs. CDB_CONSTITUTION.md) markieren; Bericht `BUERO_FILES_REVIEW.md` schreiben.

### Monitoring & Reporting

* **Smart Health & Performance Monitoring (#170):**

  * Health‑Monitor, Startup‑Orchestrator und Dev‑Workflow‑Assistant an Alerting‑System und CI/CD‑Trigger anbinden; Performance‑Monitoring in Grafana integrieren.
* **Performance‑Baseline‑Jobs (#221):**

  * CI‑Job für regelmäßige Benchmark‑Runs und Artefakt‑Upload entwerfen; Abhängigkeiten (Hardware‑Konsistenz) berücksichtigen.

### Sonstige Aufgaben

* **Branch‑Triage & Cleanup (#330, #329):**

  * Regelmäßig ungemergte Branches analysieren und nach Kriterien (ALTER, Commits ahead) kategorisieren; DELETE‑Branches entfernen.
  * Alte GitLab‑Branches gemäß #329 löschen.
* **CI‑Billing‑Probleme (#413, #400):**

  * Billing‑Limits prüfen und gegebenenfalls erhöhen bzw. Alternativen (self‑hosted Runner) dokumentieren.
