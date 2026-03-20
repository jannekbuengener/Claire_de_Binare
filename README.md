Welcome to the Claire de Binare repository. This project is a complex system for algorithmic trading, featuring a microservices-based architecture, advanced data analysis, and a sophisticated governance framework.

---
## 🚦 Live Readiness (Operational Gate)

**Status:** ❌ **NO-GO**<br>
**Canonical source:** `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`

- **Scope basis:** `ROADMAP.yaml` + `LR-001..LR-007-STATE.yaml` + aktuelle GitHub-LR-Issues
- **Last reconciliation:** 2026-03-15
- **Roadmap status:** `P0` DONE, `P1` bis `P5` nicht abgeschlossen
- **Human gate:** Keine Echtgeld-Freigabe ohne vollstaendige Evidenz und explizite menschliche Freigabe

**Einordnung:**<br>
`CURRENT_STATUS.md` beschreibt den aktuellen Repo-/Main-/Testzustand.<br>
`PROJECT_STATUS.md` ist ein historischer Implementierungs-Snapshot und kein operativer Go/No-Go-Status.<br>
`knowledge/CURRENT_STATUS.md` ist nur ein historischer Knowledge-Snapshot und keine aktuelle Repo-/Ops-Quelle.

---

## 🧭 Post-Live Development (nicht gate-relevant)

**Ausbaugrad:** **~72 %**  
*(Backlog, Optimierungen, Erweiterungen – kein Einfluss auf Live-Betrieb)*
Diese Kennzahl beschreibt **Weiterentwicklung nach Erreichen der Live Readiness**, z. B.:

- Performance-Optimierungen  
- Zusätzliche Tests (Chaos / Perf)  
- Komfort-Features  
- ML-Vorbereitung & Experimente  
- Dokumentations-Verdichtung

**Wichtig:**  
Dieser Fortschritt ist **optional, iterativ und nicht zeitkritisch**.  
Er ist **kein Maß für Betriebsreife** und **kein Release-Gate**.

---

### Kurzfassung (fuer Leser mit wenig Zeit)

- **Live Readiness:** NO-GO (siehe `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`)
- **Systemstatus:** Runtime migriert auf BLUE+RED; base.yml + dev.yml sind CI/Legacy-only
- **Repo-/Teststatus:** siehe `CURRENT_STATUS.md`
- **Historischer Implementierungsstand:** siehe `PROJECT_STATUS.md` (historischer Snapshot)

---

## Overview

This repository contains all the necessary components to run and develop Claire de Binare, including:

- **Microservices:** A suite of services for handling different aspects of the trading process, such as signal generation, execution, risk management, and data persistence.
- **Infrastructure:** Infrastructure-as-Code (IaC) for setting up the required environment, including database schemas, monitoring dashboards, and deployment configurations.
- **Governance:** A comprehensive set of documents defining the project's constitution, policies, and operational guidelines.
- **Tooling:** A collection of scripts and tools to aid in development, deployment, and maintenance.

## PowerShell Toolchain

Der autoritative repo-weite PowerShell-Index liegt in [`tools/README.md`](tools/README.md).

Dort ist die Discovery in `Canonical v1 Front Door`, `Canonical v1 Scripts`, `Secondary` und `Legacy/Stale` konsolidiert.

Bevorzugter Windows/PowerShell-v1-Einstiegspunkt:

```powershell
.\tools\cdb.ps1 secrets init
.\tools\cdb.ps1 runtime up
.\tools\cdb.ps1 stack verify
.\tools\cdb.ps1 service logs -ServiceName cdb_risk -Lines 100
.\tools\cdb.ps1 runtime smoke
```

Der Dispatcher ist bewusst duenn und ruft nur den fixierten v1-Korridor auf: `init-secrets.ps1`, `setup_blue_red.ps1`, `verify_stack.ps1`, `cdb-service-logs.ps1` und `smoke_test.ps1`.

`Makefile` bleibt die operative Front Door fuer haeufige Ablaufe wie `make docker-up`, `make docker-health` und `make docker-down`, ist aber nicht selbst Teil der PowerShell-v1-Toolchain.

## Docker CI Lab Baseline

Kanonische 431B-Linie:

```bash
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/test.yml up --abort-on-container-exit
```

Rollentrennung:
- `base.yml + test.yml` = kanonische Docker-CI-Lab-Baseline fuer isolierte Test-/E2E-Labs
- `base.yml + dev.yml` = sekundaerer Dev-/Kompatibilitaetspfad; einige aeltere Workflows nutzen ihn noch
- `compose.blue.yml + compose.red.yml` = lokale Operator-Runtime, nicht die CI-Lab-Baseline

## Security Simulation Source of Truth

Kanonische 431C-Linie:

- `scripts/drills/` plus `tests/chaos/` = repo-native Source of Truth fuer deterministische Drill-/Chaos-Ausfuehrung und Gate-Tests
- `tools/test_pack/` = sekundaerer experimenteller/importierter Bestand; nicht die repo-weite Default-Linie
- `infrastructure/scripts/security_audit.sh` = Legacy-/Stale-Helper mit alten Repo-Annahmen; nur Referenz, nicht Harness-Canon

## 📊 Projektstatus

### Gesamtfortschritt
```
Issues geschlossen: 202 / 300 (67.3%)
███████████████░░░░░ 67.3%
```

### 🏗️ Architektur-Komponenten

| Komponente | Status | Fortschritt |
|------------|--------|-------------|
| **Core Modules** (6) | ✅ | 95% |
| `core/clients/` - MEXC API Client | ✅ | 100% |
| `core/config/` - Konfiguration | ✅ | 100% |
| `core/domain/` - Domain Models | ✅ | 100% |
| `core/indicators/` - Technische Indikatoren | ✅ | 100% |
| `core/safety/` - Circuit Breaker | ✅ | 100% |
| `core/utils/` - Rate Limiter | ✅ | 100% |

### 🔧 Services (9)

| Service | Beschreibung | Status |
|---------|-------------|--------|
| `services/allocation/` | Portfolio Allocation | 🟡 30% |
| `services/db_writer/` | DB Persistenz | ✅ 90% |
| `services/execution/` | Order Execution | ✅ 85% |
| `services/market/` | Market Data | ✅ 95% |
| `services/paper_trading/` | Paper Trading Runner | ✅ 75% |
| `services/regime/` | Market Regime Detection | ✅ 70% |
| `services/risk/` | Risk Management | ✅ 80% |
| `services/signal/` | Signal Generation | ✅ 85% |
| `services/ws/` | WebSocket Handler | ✅ 90% |

**Durchschnitt Services: 80%**

### 🧪 Test-Infrastruktur

| Kategorie | Anzahl | Status |
|-----------|--------|--------|
| Test-Dateien | 27 | ✅ |
| Test-Funktionen | 254 | ✅ |
| Unit Tests | ✅ | 75% |
| Integration Tests | 🟡 | 50% |
| E2E Tests | 🟢 | 50% |
| Performance Tests | 🟡 | 30% |
| Chaos Tests | 🔴 | 10% |

### 📈 Monitoring & Observability

| Element | Anzahl | Status |
|---------|--------|--------|
| Grafana Dashboards | 8 | ✅ 70% |
| Prometheus Configs | 2 | ✅ |
| Alert Rules | 1 | 🟡 40% |
| Docker Services | 9 | ✅ |
| Health Checks | 9 | ✅ |

### 🎯 Milestone-Fortschritt

| Milestone | Beschreibung | Status |
|-----------|-------------|--------|
| **M1** Foundation | Basis-Architektur | ✅ 100% |
| **M2** Trading Core | Signal/Execution | ✅ 95% |
| **M3** Risk Layer | Circuit Breaker | ✅ 90% |
| **M4** Market Data | WebSocket/OHLCV | ✅ 85% |
| **M5** Persistenz | DB Schema | 🟡 65% |
| **M6** ML Prep | Indicators | ✅ 80% |
| **M7** Testnet | Paper Trading | 🟢 70% |
| **M8** Stabilization | E2E Tests | 🟢 60% |
| **M9** Production | Live Trading | 🟡 30% |

### 📊 Zusammenfassung

```
┌─────────────────────────────────────────────┐
│  PROJEKT-REIFE: 72%                         │
│  █████████████████░░░░░░                    │
├─────────────────────────────────────────────┤
│  Code: 3566 Python-Dateien                  │
│  Commits: 261 (2025)                        │
│  Issues: 202 closed / 98 open               │
│  Tests: 79 Test-Dateien                     │
│  Branches: 99 remote                        │
│  Services: 9 healthy                        │
│  Security: 4 Vulnerabilities behoben        │
│  CI/CD: ci + policy-gate (required)          │
└─────────────────────────────────────────────┘
```

*Stand: 2026-01-07 (GitHub Live Data)*

---

## Getting Started

**New Developer?** See **[DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)** for comprehensive setup instructions.

### Quick Setup (5 minutes)

**Prerequisites**: Docker, Python 3.12+, Git

```bash
# 1. Clone repository
git clone https://github.com/jannekbuengener/Claire_de_Binare.git
cd Claire_de_Binare

# 2. Setup environment
cp .env.example .env

# 3. Initialize secrets (Linux/Mac)
./infrastructure/scripts/init-secrets.sh

# Windows (PowerShell, canonical v1 front door):
# .\tools\cdb.ps1 secrets init

# 4. Validate environment (Linux/Mac)
./infrastructure/scripts/validate-environment.sh

# 5. Start the stack (canonical BLUE+RED runtime)
docker network create cdb_network 2>/dev/null || true
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d

# Windows (PowerShell, canonical v1 front door):
# .\tools\cdb.ps1 runtime up

# Secondary dev/compatibility path (not the 431B CI-lab baseline):
# docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d

# 6. Verify health
make docker-health

# PowerShell v1 front door:
# .\tools\cdb.ps1 stack verify

# Focused BLUE core-path smoke:
# .\tools\cdb.ps1 runtime smoke

# 7. Access Grafana
# http://localhost:3000 (admin / see GRAFANA_PASSWORD in secrets)
```

Repo-weite PowerShell-Discovery: [`tools/README.md`](tools/README.md). `bootstrap_local.ps1` und `bootstrap_local.sh` bleiben Secondary Convenience Wrapper und sind nicht der kanonische Windows/PowerShell-v1-Einstieg.

## Navigation (MCP)

Für schnelle Orientierung im Working Repo: [`mcp_navpack_working_repo/`][navpack]

- Einstieg/Lesereihenfolge: [`ENTRYPOINTS.yaml`](mcp_navpack_working_repo/ENTRYPOINTS.yaml)
- Such-/Read-Presets: [`QUERIES.snippets.yaml`](mcp_navpack_working_repo/QUERIES.snippets.yaml)
- Repo-Map: [`REPO.map.json`](mcp_navpack_working_repo/REPO.map.json)
- Cheat-Sheet: [`CHEATSHEET.md`](mcp_navpack_working_repo/CHEATSHEET.md)

Die lokale Canon-Matrix fuer aktive Doku liegt im Working Repo: [`docs/meta/WORKING_REPO_CANON.md`][working_repo_canon]

[navpack]: mcp_navpack_working_repo/
[working_repo_canon]: docs/meta/WORKING_REPO_CANON.md


### Troubleshooting

If you encounter issues:

1. **Missing .env**: Run `cp .env.example .env`
2. **Secret errors**: Run `./infrastructure/scripts/init-secrets.sh` on Linux/Mac or `.\tools\cdb.ps1 secrets init` on Windows
3. **Port conflicts**: Check for services using ports 6379, 5432, 3000, 9090, 8000
4. **Permission denied**: Fix secrets permissions: `chmod 700 ~/Documents/.secrets/.cdb && chmod 600 ~/Documents/.secrets/.cdb/*`

See **[DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)** for detailed troubleshooting.

### Documentation

- **Setup Guide**: [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) - Comprehensive onboarding
- **Service Status**: [PROJECT_STATUS.md](PROJECT_STATUS.md) - Service implementation audit
- **Governance**: [Governance Audit](governance-audit-2026-01-15.md) - Historical governance audit snapshot
- **Agent Registry**: [agents/AGENTS.md](agents/AGENTS.md) - Local agent entrypoint
- **Policies**: `knowledge/governance/` - Canonical governance and policy documents
