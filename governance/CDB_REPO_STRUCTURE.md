# CDB Repository Structure (v1)

Date: 2025-12-12  
Status: Target Layout (minimal, governance-first, Kubernetes-ready)

---

## 1. Zielbild (Top-Level)

```text
/ (repo root)
├─ core/
├─ services/
├─ infrastructure/
├─ tests/
├─ governance/
├─ CDB_KNOWLEDGE_HUB.md
├─ .gitignore
├─ docker-compose.yml                (oder compose.yaml)
├─ README.md                         (optional, sehr kurz)
└─ LICENSE                           (OSS, empfohlen)
```

**Prinzip:**  
- **Code & Runtime** im Repo, **Dokumentation extern** (kein `/docs`).  
- **Governance** ist **Single Source of Truth** in `/governance`.  
- **KI schreibt persistent nur** in `CDB_KNOWLEDGE_HUB.md`.

---

## 2. Ordner im Detail

### `/core`
Kernkomponenten und Shared Libraries, die von mehreren Services genutzt werden.

Empfohlenes Minimal-Layout:
```text
core/
├─ domain/            (Events, Models, Schemas, Contracts)
├─ config/            (typed config loader, env mapping)
└─ utils/             (shared helpers)
```

### `/services`
Alle laufenden Komponenten (stateless-by-default).

Beispiel:
```text
services/
├─ market/            (Market ingest)
├─ signal/            (Signal generation)
├─ risk/              (Risk checks, action masking)
├─ execution/         (Order routing)
├─ psm/               (Portfolio/State Manager)
└─ observability/     (optional: log/metric gateways)
```

### `/infrastructure`
IaC, Compose/K8s readiness, deployment scaffolding.

Beispiel:
```text
infrastructure/
├─ compose/           (compose fragments, env templates)
├─ k8s/               (manifests/helm skeleton – später aktiv)
├─ iac/               (Terraform/OpenTofu, optional)
└─ scripts/           (ops scripts, validations)
```

### `/tests`
Tests für Core und Services (Unit/Integration/Replay).

Beispiel:
```text
tests/
├─ unit/
├─ integration/
└─ replay/            (event sourcing replays/backtests)
```

### `/governance`
Alle Regeln/Policies/Agent-Guides an einem Ort (flach, ohne Unterordner).

Beispiel-Dateien:
```text
governance/
├─ CDB_CONSTITUTION.md
├─ CDB_GOVERNANCE.md
├─ CDB_POLICY_STACK_MINI.md
├─ CDB_AGENT_POLICY.md
├─ CDB_INFRA_POLICY.md
├─ CDB_RL_SAFETY_POLICY.md
├─ CDB_TRESOR_POLICY.md
├─ CDB_PSM_POLICY.md
├─ CLAUDE.md
├─ GEMINI.md
├─ COPILOT.md
├─ AGENTS.md
└─ SYSTEM_CONTEXT.md
```

---

## 3. Lokale (nicht versionierte) Arbeitsflächen

Diese Dateien/Ordner sind **lokal** und stehen in `.gitignore`:

```text
.cdb_agent_workspace/
├─ claude.md
├─ gemini.md
├─ copilot.md
└─ codex.md
```

Optional zusätzlich (wenn du magst):
```text
.cdb_local/
└─ secrets/           (vorerst)
```

---

## 4. Kubernetes-Readiness – Designregeln (Kurz)

- Services **stateless-by-default**
- Config nur über **ENV/ConfigMaps/Secrets**
- **health/readiness/liveness** endpoints
- klare Service-Grenzen (risk ≠ execution ≠ psm)
- Observability (logs/metrics/traces) als First-Class

---

## 5. Ein Satz, der alles klärt

**Alles was Regeln sind → `/governance`. Alles was läuft → `/services`. Alles was gemeinsam ist → `/core`. Alles was deployt → `/infrastructure`.**

---
---

# ANHANG: Detaillierter Strukturentwurf (Claude, 2025-12-12)

**Status:** Entwurf zur Prüfung durch Gemini-G
**Autor:** Claude (Session Lead)
**Zweck:** Vollständige Tier-Migration (T1/T2/T3 → moderne Struktur) mit Governance-Verankerung

---

## A. Governance-Verankerung (Kanonische Quellen)

### Primäre Governance-Dokumente

1. **CDB_CONSTITUTION.md** (v1.0.0)
   - Höchste Instanz
   - Systemziel: Deterministisch, event-getrieben, reproduzierbar
   - Souveränität: Self-Custody, Tresor-Zone
   - Dezentralisierung: Event-Sourcing, austauschbare Runtime
   - Transparenz: Append-only Logs, Replay-fähig
   - Resilienz: Stateless Services, idempotent

2. **CDB_GOVERNANCE.md** (v1.0.0)
   - Rollenmodell: User, Session Lead, Peer-Modelle
   - Zonenmodell: Core, Governance, Knowledge, Workspace, Tresor
   - Arbeitsmodi: Analysis (Default), Delivery (explizite Freigabe)
   - Dev-Freeze: CI blockiert bei KI-Ausfall

3. **CDB_AGENT_POLICY.md** (v1.0.0)
   - Write-Gates: KI schreibt NUR in `CDB_KNOWLEDGE_HUB.md` + `.cdb_agent_workspace/*`
   - Verbotene Pfade: `/core`, `/services`, `/infrastructure`, `/tests`, `/governance`
   - Enforcement: Branch Protection, CODEOWNERS, CI-Gates, Secrets-Scan

4. **CDB_INFRA_POLICY.md** (v1.0.0)
   - IaC + GitOps verpflichtend
   - Git = Single Source of Truth
   - K8s-Readiness: Stateless, ENV-Config, Health-Endpoints
   - Event-Bus: Redis (temp) → NATS JetStream/Kafka (persistent)

5. **CDB_PSM_POLICY.md** (v1.0.0)
   - Portfolio & State Manager = Single Source of Truth für Finanzdaten
   - Event-Sourcing Kern: Append-only, Idempotent, Replay-fähig
   - Snapshots + Events = vollständiger State

---

## B. Historische Tier-Struktur (Bestandsaufnahme aus CDB_REPO_INDEX.md)

### T1 (Essential Core) - 64 Dateien
**Services:**
- execution_service/ (7 Dateien)
- risk_manager/ (6 Dateien)
- signal_engine/ (6 Dateien)
- db_writer/ (3 Dateien)
- cdb_paper_runner/ (2 Dateien)

**Infrastructure:**
- docker-compose.yml, Dockerfile, Makefile, prometheus.yml
- DATABASE_SCHEMA.sql, migrations/
- grafana/dashboards/ + provisioning/

**Tests:**
- pytest.ini, tests/unit/ (execution_service, risk_manager, signal_engine - alle leer)

**Config:**
- .env.example, .gitignore, .dockerignore, requirements.txt, requirements-dev.txt

**CI/CD:**
- .github/workflows/ci.yaml

### T2 (Productive Tools & DevOps) - 4 Dateien
- .github/PULL_REQUEST_TEMPLATE.md
- .github/ISSUE_TEMPLATE/ (bug_report.md, feature_request.md)
- services/execution_simulator.py

### T3 (Research/Legacy/Experimental) - 15 Dateien
- backoffice/automation/, backoffice/scripts/, backoffice/services/portfolio_manager/
- scripts/ (link_check.py, provenance_hash.py, security_audit.sh, migration/)
- services/cdb_paper_runner/ (email_alerter.py, service.py - alternative Impl)
- tests/ (mexc_top5_ws.py, test_smoke_repo.py.skip)

---

## C. Detaillierte Zielstruktur (Erweitert)

### Top-Level Tree-View (Vollständig)

```
claire-de-binare_v2.0/
│
├── core/                           # Shared Libraries & Domain Logic
│   ├── domain/                     # Events, Models, Schemas, Contracts
│   ├── config/                     # Typed config loader, env mapping
│   └── utils/                      # Shared helpers
│
├── services/                       # Stateless Runtime Services
│   ├── market/                     # Market data ingest
│   ├── signal/                     # Signal generation (RL-based)
│   ├── risk/                       # Risk checks, action masking
│   ├── execution/                  # Order routing
│   ├── psm/                        # Portfolio & State Manager
│   ├── db_writer/                  # Database persistence
│   └── observability/              # (optional) Log/Metric gateways
│
├── infrastructure/                 # IaC, Deployment, Ops
│   ├── compose/                    # docker-compose fragments + env templates
│   ├── k8s/                        # K8s manifests / Helm (später aktiv)
│   ├── iac/                        # Terraform/OpenTofu (optional)
│   ├── monitoring/                 # Prometheus, Grafana provisioning
│   │   ├── prometheus.yml
│   │   └── grafana/
│   │       ├── dashboards/
│   │       └── provisioning/
│   ├── database/                   # Schema, migrations
│   │   ├── schema.sql
│   │   └── migrations/
│   └── scripts/                    # Ops scripts, validations
│
├── tests/                          # Tests (Unit/Integration/Replay)
│   ├── unit/                       # Service-spezifische Unit-Tests
│   │   ├── execution/
│   │   ├── risk/
│   │   ├── signal/
│   │   ├── psm/
│   │   └── db_writer/
│   ├── integration/                # Cross-Service Integration-Tests
│   └── replay/                     # Event-Sourcing Replay-Tests
│
├── governance/                     # Canonical Policies (FLAT, READ-ONLY für KI)
│   ├── CDB_CONSTITUTION.md
│   ├── CDB_GOVERNANCE.md
│   ├── CDB_AGENT_POLICY.md
│   ├── CDB_INFRA_POLICY.md
│   ├── CDB_RL_SAFETY_POLICY.md
│   ├── CDB_TRESOR_POLICY.md
│   ├── CDB_PSM_POLICY.md
│   ├── CDB_POLICY_STACK_MINI.md
│   ├── NEXUS.MEMORY.md
│   ├── CDB_KNOWLEDGE_HUB.md
│   ├── CLAUDE.md                   # Session Lead Policy
│   ├── GEMINI.md
│   ├── COPILOT.md
│   └── (weitere Policies)
│
├── .github/                        # CI/CD, Templates
│   ├── workflows/
│   │   └── ci.yaml
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── CODEOWNERS
│
├── scripts/                        # Top-Level Operational Scripts
│   └── validate_write_zones.sh    # CI Write-Zone Enforcement
│
├── .cdb_agent_workspace/           # KI Local Workspace (GITIGNORED)
│   └── (lokale Scratch-Dateien)
│
├── CDB_KNOWLEDGE_HUB.md            # Einzige KI-beschreibbare Datei im Repo
├── CDB_REPO_STRUCTURE.md           # Diese Strukturdefinition
├── CDB_REPO_INDEX.md               # File Inventory + Tier-Validation
├── CLAUDE.md                       # Developer Guide für Claude Code
├── README.md                       # (optional, sehr kurz)
├── LICENSE                         # OSS License (Apache 2.0 empfohlen)
├── .gitignore
├── .dockerignore
├── docker-compose.yml              # Haupt-Compose-Datei
├── Makefile                        # Build-Automation
├── pytest.ini                      # Test-Framework Config
└── .env.example                    # ENV Template
```

---

## D. Detaillierte Ordnerdefinitionen

### 1. `/core/` (Shared Libraries & Domain Logic)

**Zweck:**
- Shared Code, der von mehreren Services genutzt wird
- Domain-Modelle, Events, Schemas, Verträge
- Konfigurationslogik, Utilities

**Governance-Bezug:**
- CDB_GOVERNANCE.md: "Core-Zone" (KI read-only, PR-basierte Änderungen)
- CDB_AGENT_POLICY.md: CODEOWNERS-Pflicht, mind. 2 Reviewer
- CDB_PSM_POLICY.md: Event-Schemas leben hier

**Erlaubte Inhalte:**
- `/core/domain/` - Event-Definitionen, Models, Contracts
- `/core/config/` - Typed Config Loader, ENV-Mapping
- `/core/utils/` - Shared Helpers (z.B. Logging, Serialization)

**Tier-Mapping:**
- T1: Keine direkten Dateien bisher
- Konsolidierung: Event-Modelle aus `execution_service/models.py`, `risk_manager/models.py`, `signal_engine/models.py` → `/core/domain/`

**NICHT erlaubt:**
- Service-spezifische Business-Logik
- Runtime-Dependencies
- Stateful Components

---

### 2. `/services/` (Stateless Runtime Services)

**Zweck:**
- Alle laufenden Komponenten des Systems
- Jeder Service ist stateless, K8s-ready, ENV-konfiguriert

**Governance-Bezug:**
- CDB_INFRA_POLICY.md: Stateless, Health-Endpoints, ENV-only Config
- CDB_CONSTITUTION.md: Event-driven Pipeline
- CDB_PSM_POLICY.md: PSM ist Single Source of Truth

**Erlaubte Inhalte:**
- `/services/market/` - Market Data Ingest
- `/services/signal/` - Signal Engine (RL-Policy)
- `/services/risk/` - Risk Manager (Action Masking)
- `/services/execution/` - Execution Service (Order Routing)
- `/services/psm/` - Portfolio & State Manager
- `/services/db_writer/` - Database Writer
- `/services/observability/` - (optional) Metric/Log Gateways

**Tier-Mapping:**
- **T1 → `/services/`:**
  - `execution_service/` → `/services/execution/`
  - `risk_manager/` → `/services/risk/`
  - `signal_engine/` → `/services/signal/`
  - `db_writer/` → `/services/db_writer/`
  - `cdb_paper_runner/` → `/services/paper_runner/` (oder `/services/market/`)

- **T2:**
  - `execution_simulator.py` → `/tests/integration/execution_simulator.py` (Test-Tool)

- **T3 (NICHT migrieren):**
  - `backoffice/services/portfolio_manager/` → DROP (Legacy/Alternative)
  - `services/cdb_paper_runner/service.py` → DROP (Duplicate)

**Service-Struktur (Standard):**
```
services/<service_name>/
├── <service_name>/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── service.py
│   └── requirements.txt
├── Dockerfile
└── README.md
```

---

### 3. `/infrastructure/` (IaC, Deployment, Ops)

**Zweck:**
- Infrastructure as Code
- Deployment-Konfigurationen
- Monitoring-Setup
- Database-Schema & Migrationen
- Operational Scripts

**Governance-Bezug:**
- CDB_INFRA_POLICY.md: IaC + GitOps verpflichtend, Git = SoT
- CDB_AGENT_POLICY.md: CI-Checks für Write-Zones, Secrets-Scan
- CDB_GOVERNANCE.md: Dev-Freeze bei KI-Ausfall

**Erlaubte Inhalte:**
- `/infrastructure/compose/` - docker-compose Fragmente, ENV-Templates
- `/infrastructure/k8s/` - Kubernetes Manifests, Helm Charts (Tier-2+)
- `/infrastructure/iac/` - Terraform/OpenTofu (optional)
- `/infrastructure/monitoring/` - Prometheus, Grafana
- `/infrastructure/database/` - Schema, Migrations
- `/infrastructure/scripts/` - Ops Scripts

**Tier-Mapping:**
- **T1 → `/infrastructure/`:**
  - `prometheus.yml` → `/infrastructure/monitoring/prometheus.yml`
  - `grafana/` → `/infrastructure/monitoring/grafana/`
  - `DATABASE_SCHEMA.sql` → `/infrastructure/database/schema.sql`
  - `migrations/` → `/infrastructure/database/migrations/`

- **T3 (Selektiv):**
  - `scripts/security_audit.sh` → `/infrastructure/scripts/security_audit.sh` (MIGRATE)
  - `backoffice/scripts/backup_postgres.ps1` → `/infrastructure/scripts/` (OPTIONAL)
  - `backoffice/scripts/daily_check.py` → `/infrastructure/scripts/` (OPTIONAL)

---

### 4. `/tests/` (Tests: Unit/Integration/Replay)

**Zweck:**
- Alle Tests (Unit, Integration, Replay)
- Event-Sourcing Replay-Tests sind PFLICHT (CDB_PSM_POLICY.md)

**Governance-Bezug:**
- CDB_PSM_POLICY.md: Replay-Tests Pflicht, Hash-Vergleiche
- CDB_INFRA_POLICY.md: CI blockiert Merge ohne grüne Tests
- CDB_AGENT_POLICY.md: Tests müssen grün sein vor Merge

**Erlaubte Inhalte:**
- `/tests/unit/` - Unit-Tests pro Service
- `/tests/integration/` - Cross-Service Integration-Tests
- `/tests/replay/` - Event-Sourcing Replay-Tests

**Tier-Mapping:**
- **T1 → `/tests/`:**
  - `tests/unit/execution_service/` → `/tests/unit/execution/`
  - `tests/unit/risk_manager/` → `/tests/unit/risk/`
  - `tests/unit/signal_engine/` → `/tests/unit/signal/`

- **T3 (NICHT migrieren):**
  - `tests/mexc_top5_ws.py` → DROP (experimentell)
  - `tests/test_smoke_repo.py.skip` → DROP (geskippt)

---

### 5. `/governance/` (Canonical Policies - FLAT, READ-ONLY für KI)

**Zweck:**
- Constitutional Layer des Systems
- Alle Policies an einem Ort (FLAT, keine Unterordner)

**Governance-Bezug:**
- CDB_CONSTITUTION.md: Höchste Instanz
- CDB_GOVERNANCE.md: Governance-Zone, read-only für KI
- CDB_AGENT_POLICY.md: Mind. 2 Reviewer für Änderungen

**Tier-Mapping:**
- Bereits vollständig vorhanden
- `governance/CLAUDE.md` ist korrekt platziert

---

## E. Tier-Migration Matrix (Vollständig)

| Alte Position (T1/T2/T3) | Neue Position | Status | Begründung |
|--------------------------|---------------|--------|------------|
| **T1: Services** | | | |
| `execution_service/` | `/services/execution/` | MIGRATE | Core Service |
| `risk_manager/` | `/services/risk/` | MIGRATE | Core Service |
| `signal_engine/` | `/services/signal/` | MIGRATE | Core Service |
| `db_writer/` | `/services/db_writer/` | MIGRATE | Core Service |
| `cdb_paper_runner/` | `/services/paper_runner/` | MIGRATE | Core Service |
| **T1: Infrastructure** | | | |
| `docker-compose.yml` | Root | MIGRATE | Konvention |
| `Dockerfile` | Service-spezifisch | MIGRATE | Clean Separation |
| `Makefile` | Root | MIGRATE | Build Automation |
| `prometheus.yml` | `/infrastructure/monitoring/` | MIGRATE | Observability |
| `grafana/` | `/infrastructure/monitoring/grafana/` | MIGRATE | Observability |
| `DATABASE_SCHEMA.sql` | `/infrastructure/database/schema.sql` | MIGRATE | Schema |
| `migrations/` | `/infrastructure/database/migrations/` | MIGRATE | Migrations |
| **T1: Tests** | | | |
| `tests/unit/` | `/tests/unit/` | MIGRATE | Testing |
| `pytest.ini` | Root | MIGRATE | Test Config |
| **T1: Config** | | | |
| `.env.example` | Root | MIGRATE | Config Template |
| `.gitignore` | Root | MIGRATE | Git Config |
| `.dockerignore` | Root | MIGRATE | Docker Config |
| `requirements.txt` | Service-spezifisch | MIGRATE | Dependencies |
| **T1: CI/CD** | | | |
| `.github/workflows/ci.yaml` | `.github/workflows/` | MIGRATE | CI Pipeline |
| **T2: DevOps** | | | |
| `.github/PULL_REQUEST_TEMPLATE.md` | `.github/` | MIGRATE | PR Template |
| `.github/ISSUE_TEMPLATE/` | `.github/ISSUE_TEMPLATE/` | MIGRATE | Issue Templates |
| `services/execution_simulator.py` | `/tests/integration/` | MIGRATE | Test Tool |
| **T3: Ops (selektiv)** | | | |
| `scripts/security_audit.sh` | `/infrastructure/scripts/` | MIGRATE | Security |
| `backoffice/scripts/backup_postgres.ps1` | `/infrastructure/scripts/` | OPTIONAL | Ops |
| `backoffice/scripts/daily_check.py` | `/infrastructure/scripts/` | OPTIONAL | Ops |
| **T3: Legacy/Research** | | | |
| `backoffice/services/portfolio_manager/` | - | DROP | Legacy |
| `services/cdb_paper_runner/` (alt) | - | DROP | Duplicate |
| `scripts/migration/` | - | DROP | Einmalig |
| `tests/mexc_top5_ws.py` | - | DROP | Experimentell |

---

## F. Offene Fragen für Gemini-G Review

### 1. docker-compose.yml Platzierung
**Frage:** Root-Level oder `/infrastructure/compose/`?
**Empfehlung Claude:** Root (Konvention), Fragmente in `/infrastructure/compose/`

### 2. requirements.txt Platzierung
**Frage:** Root-Level oder Service-spezifisch?
**Empfehlung Claude:** Service-spezifisch (K8s-Ready, isolierte Dependencies)

### 3. Dockerfile Platzierung
**Frage:** Root, Infrastructure, oder Service-spezifisch?
**Empfehlung Claude:** Service-spezifisch (Clean Separation)

### 4. T3 Ops-Scripts Migration
**Frage:** Welche Backoffice-Scripts migrieren?
**Empfehlung Claude:** `security_audit.sh` JA, Rest OPTIONAL (User-Entscheidung)

### 5. execution_simulator.py Platzierung
**Frage:** Service oder Test?
**Empfehlung Claude:** `/tests/integration/` (Test-Tool, kein Production-Service)

---

## G. Implementierungs-Leitplanken

### Governance-First Prinzipien
1. **Struktur vor Inhalt** - Verzeichnisse anlegen, dann füllen
2. **Explizit > Implizit** - Jede Entscheidung dokumentiert
3. **Leer und korrekt > Voll und falsch**
4. **Governance ist Primärsystem** - Struktur aus Governance ableitbar

### K8s-Readiness Anforderungen
1. **Stateless Services** - Kein lokaler State
2. **ENV-only Config** - Keine Hardcoded Pfade
3. **Health Endpoints** - `/health`, `/ready`, `/live`
4. **Service Isolation** - Eigenständig deploybar

### Event-Sourcing Anforderungen
1. **Append-only Events** - In `/core/domain/`
2. **Replay-Tests** - In `/tests/replay/`
3. **Schema Versioning** - SemVer für Events

---

## H. Erfolgs-Kriterien

✅ **Governance-Konformität:**
- Alle Pfade entsprechen Zonenmodell
- Write-Gates technisch durchsetzbar
- CI-Gates funktionsfähig

✅ **K8s-Readiness:**
- Services stateless
- ENV-basierte Konfiguration
- Health-Endpoints vorhanden

✅ **Event-Sourcing:**
- Events in `/core/domain/`
- Replay-Tests in `/tests/replay/`
- Schema-Versionierung dokumentiert

✅ **Tier-Migration:**
- Alle T1 Essential Core migriert
- T2 DevOps integriert
- T3 Legacy explizit ausgeklammert

✅ **Auditierbarkeit:**
- Jede Datei hat klare Zuständigkeit
- Migration nachvollziehbar
- Struktur aus Governance ableitbar

---

**ENDE ANHANG - Bitte Gemini-G um Konsistenzprüfung, Redundanzen, Brüche und Verbesserungsvorschläge bitten.**
