Welcome to the Claire de Binare repository. This project is a complex system for algorithmic trading, featuring a microservices-based architecture, advanced data analysis, and a sophisticated governance framework.

---
## 🚦 Live Readiness (Operational Gate)

**Status:** ✅ **LIVE-READY**  
**Gate:** PASSED (LR-001 → LR-007 vollständig abgeschlossen)

- **Completion:** ★★★★★ **100 %**
- **Tasks:** 7 / 7 DONE · 0 BLOCKED
- **Validator:** `python scripts/lr004_completion_guard.py --check` → **PASS**
- **Last verified:** 2026-02-10 15:50 CET
- **Commit:** `27d2f4b9cda518821ae855009db68793cd9656cf`

**Interpretation (bindend):**  
Das System ist **betriebsfähig**, **governance-konform**, **fail-closed**, **recovery-fähig** und kann im Shadow / Live-Betrieb laufen.  
Es gibt **keine offenen Blocker** für den operativen Einsatz.

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

- **Live Readiness:** NO-GO (Post-Migration, BLUE+RED canonical runtime)
- **Systemstatus:** Runtime migriert auf BLUE+RED; base.yml + dev.yml sind CI/Legacy-only
- **Offene Issues:** betreffen Ausbau, nicht Betrieb

---

## Overview

This repository contains all the necessary components to run and develop Claire de Binare, including:

- **Microservices:** A suite of services for handling different aspects of the trading process, such as signal generation, execution, risk management, and data persistence.
- **Infrastructure:** Infrastructure-as-Code (IaC) for setting up the required environment, including database schemas, monitoring dashboards, and deployment configurations.
- **Governance:** A comprehensive set of documents defining the project's constitution, policies, and operational guidelines.
- **Tooling:** A collection of scripts and tools to aid in development, deployment, and maintenance.

## Tooling & Helper Scripts (Cheat Sheet)

| Script | Zweck | Hinweis zur Nutzung |
| --- | --- | --- |
| `scripts/lr004_completion_guard.py` | Validiert deterministisch den Abschluss von LR-001 bis LR-007 und sichert das Live-Readiness-Gate ab. | Wird manuell zum Reporten eingesetzt und läuft automatisiert als Gate-Check. |
| `scripts/lr003_contract_drift_guard.py` | Überwacht Contract-Drift-Indikatoren und schlägt Alarm bei Abweichungen. | Teil der Live-Readiness-Toolchain; bei Verdacht auf Drift einsetzen. |
| `scripts/manage_secrets.ps1` | Erstellt, rotiert und validiert Produktions-Geheimnisse mit restriktiven Berechtigungen. | Ops-only: Use the secrets rotator/init tooling to generate/rotate/validate secrets; do not hardcode paths in docs—if unsure, run the validate/rotate command and follow its output. |
| `scripts/setup_testnet.ps1` | Führt die MEXC-Testnet-Vorbereitung inklusive Credential-Validierung durch. | Sicherer Test-Setup-Flow; keine Änderungen am Live-Stack. |
| `scripts/smart_health_check.py` | Fragt Health-Endpunkte lokaler Services ab und liefert Diagnose-Summary. | Read-only-Diagnose: nur GET-Requests gegen /health ausführen. |
| `scripts/activate_live_data.ps1` | Schaltet das System auf Live Data (echte APIs und echtes Kapital) um und startet die Container neu. | Ops-only und mit höchster Vorsicht: echtes Geld, reale Märkte. |

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

# Windows (PowerShell):
# .\infrastructure\scripts\init-secrets.ps1

# 4. Validate environment (Linux/Mac)
./infrastructure/scripts/validate-environment.sh

# 5. Start the stack (canonical BLUE+RED runtime)
docker network create cdb_network 2>/dev/null || true
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d

# Legacy (CI/test only):
# docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d

# 6. Verify health
make docker-health

# 7. Access Grafana
# http://localhost:3000 (admin / see GRAFANA_PASSWORD in secrets)
```

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
2. **Secret errors**: Run `./infrastructure/scripts/init-secrets.sh` (or `.ps1` on Windows)
3. **Port conflicts**: Check for services using ports 6379, 5432, 3000, 9090, 8000
4. **Permission denied**: Fix secrets permissions: `chmod 700 ~/Documents/.secrets/.cdb && chmod 600 ~/Documents/.secrets/.cdb/*`

See **[DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)** for detailed troubleshooting.

### Documentation

- **Setup Guide**: [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) - Comprehensive onboarding
- **Service Status**: [PROJECT_STATUS.md](PROJECT_STATUS.md) - Service implementation audit
- **Governance**: [Governance Audit](governance-audit-2026-01-15.md) - Governance compliance
- **Agent Registry**: [agents/AGENTS.md](agents/AGENTS.md) - Local agent entrypoint
- **Policies**: `knowledge/governance/` - Canonical governance and policy documents
