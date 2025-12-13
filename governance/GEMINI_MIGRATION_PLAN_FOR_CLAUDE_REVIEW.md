# Migrationsplan zur technischen Validierung durch Claude

**Erstellt von:** Gemini (Senior Repository Architect & Governance Planner)
**Datum:** 2025-12-12
**Zweck:** Dieses Dokument enthält den vollständigen, von Gemini erstellten Migrationsplan und dient als direkte Eingabe für eine technische Validierung durch die Claude-Persona.

---

### 1. Zusammenfassung: Ist-Zustand vs. Ziel-Struktur & Risiken

*   **Ist-Zustand:** Das Repository besteht aus einer leeren Ziel-Struktur (`/core`, `/services` etc.) und einer Sammlung von Governance-Dokumenten. Der eigentliche Anwendungs-Code existiert derzeit nur als *logisches Inventar* in `CDB_REPO_INDEX.md`, aufgeteilt in Tiers (T1/T2/T3).
*   **Ziel-Struktur:** Das in den Briefings definierte Ziel-Schema ist logisch, klar und entspricht modernen Best Practices (IaC, Service-Trennung, K8s-Readiness). Es behebt die Mängel der historisch gewachsenen Struktur.
*   **Kritische Inkonsistenz/Risiko:** Die größte Herausforderung ist, dass die Quell-Dateien für die Migration (`t1/`, `t2/`, `t3/`) im aktuellen `HEAD` nicht physisch vorhanden sind. Der ausführende Migrations-Agent (`Codex`) muss instruiert werden, diese Dateien aus einem früheren Git-Commit oder einem bereitgestellten Archiv zu beziehen. Mein Migrationsplan wird diese logischen `SourcePath`-Angaben verwenden, da sie die "historische Wahrheit" darstellen.

### 2. Vollständiger Migrationsplan

Dieser Plan ist die Single Source of Truth für den Migrations-Agenten. Er listet alle bekannten Dateien aus dem `CDB_REPO_INDEX.md` sowie die aktuell im `HEAD` vorhandenen Projekt- und Governance-Dateien auf.

**Tabelle 1: Governance- & Root-Dateien**

| ID | SourcePath | TargetPath | Action | Tier | Owner/Domain | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| MIG-G001 | `CDB_REPO_STRUCTURE.md` | `governance/CDB_REPO_STRUCTURE.md` | MOVE | - | governance | Zentralisiert Repo-Meta-Dokumentation. |
| MIG-G002 | `CDB_REPO_INDEX.md` | `governance/CDB_REPO_INDEX.md` | MOVE | - | governance | Zentralisiert Repo-Meta-Dokumentation. |
| MIG-G003 | `CDB_REPO_MIGRATION_BRIEF.md` | `governance/archive/CDB_REPO_MIGRATION_BRIEF.md` | MOVE | - | governance | Als historisches Briefing archivieren. |
| MIG-G004 | `PROMPT.txt` | `governance/archive/PROMPT.txt` | MOVE | - | governance | Als historisches Briefing archivieren. |
| MIG-G005 | `governance/` | `governance/` | HOLD | - | governance | Bestehende Governance-Dateien bleiben. |
| MIG-G006 | `.github/CODEOWNERS` | `.github/CODEOWNERS` | HOLD | - | devops | Bleibt, muss aber nach Migration aktualisiert werden. |
| MIG-G007 | `.github/pull_request_template.md` | `.github/PULL_REQUEST_TEMPLATE.md` | HOLD | T2 | devops | Umbenennung zu `.github/PULL_REQUEST_TEMPLATE.md` empfohlen. |
| MIG-G008 | `.gitignore` | `.gitignore` | HOLD | T1 | root | Inhalt muss ggf. nach Migration angepasst werden. |
| MIG-G009 | `nul` | `(none)` | DROP | - | - | Leere Datei, wird nicht benötigt. |
| MIG-G010 | `.claude/` | `.claude/` | HOLD | - | agent-config | Agenten-Konfiguration, ist `gitignored`. |

**Tabelle 2: Tier 1 Migration (Essential Core)**

| ID | SourcePath | TargetPath | Action | Tier | Owner/Domain | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| MIG-T1-001 | `t1/.dockerignore` | `.dockerignore` | MOVE | T1 | root | Globale Docker-Ignore-Datei. |
| MIG-T1-002 | `t1/.env.example` | `.env.example` | MOVE | T1 | root | Globale Konfigurationsvorlage. |
| MIG-T1-003 | `t1/docker-compose.yml` | `docker-compose.yml` | MOVE | T1 | root | Haupt-Compose-Datei. |
| MIG-T1-004 | `t1/Makefile` | `Makefile` | MOVE | T1 | root | Haupt-Makefile. |
| MIG-T1-005 | `t1/pytest.ini` | `pytest.ini` | MOVE | T1 | root | Globale Test-Konfiguration. |
| MIG-T1-006 | `t1/requirements.txt` | `(none)` | DROP | T1 | root | Veraltet, Dependencies sind service-spezifisch. |
| MIG-T1-007 | `t1/requirements-dev.txt`| `(none)` | DROP | T1 | root | Veraltet, Dev-Dependencies sind service-spezifisch. |
| MIG-T1-008 | `t1/DATABASE_SCHEMA.sql` | `infrastructure/database/schema.sql` | MOVE | T1 | infra-db | Zentrales DB-Schema. |
| MIG-T1-009 | `t1/migrations/` | `infrastructure/database/migrations/` | MOVE | T1 | infra-db | DB-Migrationen. |
| MIG-T1-010 | `t1/prometheus.yml` | `infrastructure/monitoring/prometheus.yml` | MOVE | T1 | infra-mon | Prometheus-Konfiguration. |
| MIG-T1-011 | `t1/grafana/` | `infrastructure/monitoring/grafana/` | MOVE | T1 | infra-mon | Grafana-Dashboards und Provisioning. |
| MIG-T1-012 | `t1/run-tests.ps1` | `infrastructure/scripts/run-tests.ps1` | MOVE | T1 | devops | Test-Ausführungsskript. |
| MIG-T1-013 | `t1/.github/workflows/ci.yaml` | `.github/workflows/ci.yaml` | MOVE | T1 | devops | CI-Workflow. |
| MIG-T1-014 | `t1/Dockerfile` | `(none)` | DROP | T1 | root | Veraltet, Dockerfiles sind service-spezifisch. |
| MIG-T1-015 | `t1/cdb_paper_runner/` | `services/market/` | MOVE | T1 | service-market| Umbenennung `cdb_paper_runner` zu `market`. |
| MIG-T1-016 | `t1/db_writer/` | `services/db_writer/` | MOVE | T1 | service-db | Service bleibt bestehen. |
| MIG-T1-017 | `t1/execution_service/`| `services/execution/` | MOVE | T1 | service-exec | Umbenennung `execution_service` zu `execution`. |
| MIG-T1-018 | `t1/risk_manager/` | `services/risk/` | MOVE | T1 | service-risk | Service bleibt bestehen. |
| MIG-T1-019 | `t1/signal_engine/` | `services/signal/` | MOVE | T1 | service-signal| Service bleibt bestehen. |
| MIG-T1-020 | `t1/tests/unit/` | `tests/unit/` | MOVE | T1 | tests | Leere Unit-Test-Ordner. |
| MIG-T1-021 | `t1/tests/README.md` | `tests/README.md` | MOVE | T1 | tests | Doku für Tests. |

**Tabelle 3: Tier 2 & 3 Migration (Tools, Legacy, Research)**

| ID | SourcePath | TargetPath | Action | Tier | Owner/Domain | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| MIG-T2-001 | `t2/.github/` | `.github/` | MOVE | T2 | devops | Templates für Issues und PRs. |
| MIG-T2-002 | `t2/services/execution_simulator.py` | `tests/integration/execution_simulator.py` | MOVE | T2 | tests | Klares Test-Tool, kein Prod-Service. |
| MIG-T3-001 | `t3/backoffice/` | `archive/backoffice/` | HOLD | T3 | ops-legacy | Veraltete Ops-Skripte, als Referenz halten. |
| MIG-T3-002 | `t3/scripts/` | `archive/scripts/` | HOLD | T3 | dev-tools | Veraltete Dev-Tools, als Referenz halten. |
| MIG-T3-003 | `t3/scripts/security_audit.sh` | `infrastructure/scripts/security_audit.sh` | MOVE | T3 | infra-sec | Nützliches Skript, wird übernommen. |
| MIG-T3-004 | `t3/services/cdb_paper_runner/` | `(none)` | DROP | T3 | service-market| Duplikat/Alternative zu T1-Version. |
| MIG-T3-005 | `t3/backoffice/services/portfolio_manager/`|`(none)`| DROP | T3 | service-psm | Veraltet, wird durch neuen PSM-Service ersetzt. |
| MIG-T3-006 | `t3/tests/` | `archive/tests-experimental/` | HOLD | T3 | research | Experimentelle Tests, nicht für CI. |
| MIG-T3-007 | `scripts/validate_write_zones.sh` | `infrastructure/scripts/validate_write_zones.sh` | MOVE | - | devops | CI-Skript, gehört zur Infrastruktur. |

### 3. Vorschläge für Governance-Dokumente

**3.1. Vorschlag für `CDB_REPO_STRUCTURE.md`**

```markdown
# CDB Repository Structure (v2.0)
Date: 2025-12-12
Status: Final Target Layout

## 1. Top-Level-Struktur

Dieses Schema ist die Single Source of Truth für die Organisation des Repositories.

/ (repo root)
├── core/
├── services/
├── infrastructure/
├── tests/
├── governance/
├── .github/
├── .cdb_agent_workspace/ (gitignored)
├── CDB_KNOWLEDGE_HUB.md
├── .gitignore
├── .dockerignore
├── docker-compose.yml
├── Makefile
├── README.md
└── LICENSE

## 2. Ordner-Definitionen

*   **/core/**: Geteilte Bibliotheken und Domänenlogik (Events, Models). Stabil und selten geändert.
*   **/services/**: Alle laufenden Applikations-Komponenten. Jeder Ordner ist ein stateless, containerisierter Microservice.
*   **/infrastructure/**: Infrastructure as Code (IaC). Enthält alles für Deployment, Monitoring, Datenbank-Schemata und CI/CD-Skripte.
*   **/tests/**: Alle Tests (Unit, Integration, Replay). Die Struktur spiegelt die `/services`-Struktur wider.
*   **/governance/**: Das Gehirn des Projekts. Alle Policies, Agenten-Guides und Meta-Dokumente wie dieses hier. **SINGLE SOURCE OF TRUTH**.
*   **/.github/**: GitHub-spezifische Konfigurationen wie CI-Workflows und PR-Templates.
*   **/CDB_KNOWLEDGE_HUB.md**: Der einzige Ort, an dem KI-Agenten persistent in das Repository schreiben. Dient als Logbuch und Wissensspeicher.
```

**3.2. Vorschlag für `CDB_REPO_INDEX.md`**

Dieses Dokument sollte nach der Migration den **finalen Zustand** widerspiegeln, nicht den historischen.

```markdown
# CDB Repository Index (v2.0)
Date: 2025-12-12
Status: Post-Migration

Dieses Dokument listet den finalen Ort aller relevanten Dateien nach der Restrukturierung auf.

## / (root)
- .dockerignore
- .env.example
- .gitignore
- docker-compose.yml
- Makefile
- pytest.ini
- README.md
- LICENSE
- CDB_KNOWLEDGE_HUB.md

## /core
- /core/domain/
- /core/config/
- /core/utils/

## /services
- /services/market/
- /services/signal/
- /services/risk/
- /services/execution/
- /services/db_writer/
- /services/psm/ (Ziel, noch leer)

## /infrastructure
- /infrastructure/database/
- /infrastructure/monitoring/
- /infrastructure/compose/
- /infrastructure/k8s/
- /infrastructure/scripts/

## /tests
- /tests/unit/
- /tests/integration/
- /tests/replay/
- /tests/README.md

## /governance
- (Liste aller .md Dateien)
```

### 4. Optionale Hinweise & Unsicherheiten

*   **Abhängigkeit zu Git History:** Der Plan setzt voraus, dass der Migrations-Agent (`Codex`) Zugriff auf die Git-Historie hat, um die `t1/`, `t2/`, `t3/` Inhalte abzurufen. Dies muss im Skript berücksichtigt werden.
*   **Service-interne Struktur:** Der Plan migriert Service-Ordner als Ganzes (z.B. `t1/risk_manager/` nach `services/risk/`). Eine detailliertere Refaktorierung *innerhalb* der Services (z.B. Aufteilung von `models.py` in `/core/domain`) ist ein nachgelagerter Schritt und nicht Teil dieser strukturellen Migration.
*   **`requirements.txt` Konsolidierung:** Ich habe die Root-`requirements.txt`-Dateien als `DROP` markiert. Die Annahme ist, dass jeder Service seine eigenen Dependencies in seinem Verzeichnis verwalten wird. Dies muss im Build-Prozess (Makefile, Dockerfiles) berücksichtigt werden.

---
## APPLIED_T1_MIGRATIONS

### MOVED
- `git mv t1/.dockerignore .dockerignore`
- `git mv t1/.env.example .env.example`
- `git mv t1/docker-compose.yml docker-compose.yml`
- `git mv t1/Makefile Makefile`
- `git mv t1/pytest.ini pytest.ini`
- `git mv t1/DATABASE_SCHEMA.sql infrastructure/database/schema.sql`
- `git mv t1/migrations/ infrastructure/database/migrations/`
- `git mv t1/prometheus.yml infrastructure/monitoring/prometheus.yml`
- `git mv t1/grafana/ infrastructure/monitoring/grafana/`
- `git mv t1/run-tests.ps1 infrastructure/scripts/run-tests.ps1`
- `git mv t1/.github/workflows/ci.yaml .github/workflows/ci.yaml`
- `git mv t1/tests/README.md tests/README.md`
- `git mv t1/cdb_paper_runner/Dockerfile services/market/`
- `git mv t1/cdb_paper_runner/requirements.txt services/market/`
- `git mv t1/db_writer/db_writer services/db_writer/`
- `git mv t1/db_writer/Dockerfile services/db_writer/`
- `git mv t1/execution_service/Dockerfile services/execution/`
- `git mv t1/execution_service/execution_service/config.py services/execution/`
- `git mv t1/execution_service/execution_service/database.py services/execution/`
- `git mv t1/execution_service/execution_service/EXECUTION_SERVICE_STATUS.md services/execution/`
- `git mv t1/execution_service/execution_service/mock_executor.py services/execution/`
- `git mv t1/execution_service/execution_service/models.py services/execution/`
- `git mv t1/execution_service/execution_service/requirements.txt services/execution/`
- `git mv t1/execution_service/execution_service/service.py services/execution/`
- `git mv t1/execution_service/execution_service/__init__.py services/execution/`
- `git mv t1/risk_manager/Dockerfile services/risk/`
- `git mv t1/risk_manager/risk_manager/config.py services/risk/`
- `git mv t1/risk_manager/risk_manager/models.py services/risk/`
- `git mv t1/risk_manager/risk_manager/README.md services/risk/`
- `git mv t1/risk_manager/risk_manager/requirements.txt services/risk/`
- `git mv t1/risk_manager/risk_manager/service.py services/risk/`
- `git mv t1/risk_manager/risk_manager/__init__.py services/risk/`
- `git mv t1/signal_engine/Dockerfile services/signal/`
- `git mv t1/signal_engine/signal_engine/config.py services/signal/`
- `git mv t1/signal_engine/signal_engine/models.py services/signal/`
- `git mv t1/signal_engine/signal_engine/models.py.backup services/signal/`
- `git mv t1/signal_engine/signal_engine/README.md services/signal/`
- `git mv t1/signal_engine/signal_engine/requirements.txt services/signal/`
- `git mv t1/signal_engine/signal_engine/service.py services/signal/`
- `git mv t1/signal_engine/signal_engine/__init__.py services/signal/`
- `git mv t1/tests/unit/test_smoke_repo.py.skip tests/unit/`
- `git mv t1/systemcheck.py infrastructure/scripts/systemcheck.py`

### DROPPED / ARCHIVED
- `git rm -f t1/requirements.txt`
- `git rm -f t1/requirements-dev.txt`
- `git rm -f t1/Dockerfile`
- `git rm -f t1/.gitignore`
- `git rm -f t1/cdb_paper_runner.Dockerfile`
- `git rm -f t1/mexc_top5_ws.py`
