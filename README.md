Welcome to the Claire de Binare repository. This project is a complex system for algorithmic trading, featuring a microservices-based architecture, advanced data analysis, and a sophisticated governance framework.

## Live Readiness Status

- **Stars:** ★★★★★ (5/5)
- **Percent complete:** 100% (7/7 LR tasks done, 0 blocked)
- **Tasks:** DONE 7 / BLOCKED 0
- **Blocker code:** n/a (no blocked tasks; LR-007 finalized under RC_001 for infrastructure readiness)
- **Last verified:** 2026-02-10 15:32 CET — commit `27d2f4b9cda518821ae855009db68793cd9656cf`
- **Audit report:** `docs/live-readiness/LR-README-AUDIT.md`

## Overview

This repository contains all the necessary components to run and develop Claire de Binare, including:

- **Microservices:** A suite of services for handling different aspects of the trading process, such as signal generation, execution, risk management, and data persistence.
- **Infrastructure:** Infrastructure-as-Code (IaC) for setting up the required environment, including database schemas, monitoring dashboards, and deployment configurations.
- **Governance:** A comprehensive set of documents defining the project's constitution, policies, and operational guidelines.
- **Tooling:** A collection of scripts and tools to aid in development, deployment, and maintenance.

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
│  CI/CD: Grün mit Concurrency                │
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

# 5. Start the stack
docker compose -f infrastructure/compose/dev.yml up -d

# 6. Verify health
docker compose -f infrastructure/compose/dev.yml ps

# 7. Access Grafana
# http://localhost:3000 (admin / see GRAFANA_PASSWORD in secrets)
```

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
- **Policies**: `governance/` - Project governance and policies# Trigger E2E for PR 806
