---
relations:
  role: entrypoint
  domain: documentation
  upstream:
    - REPO_INDEX.md
    - docker-compose.yml
  downstream: []
---
# Claire de Binare

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Welcome to the Claire de Binare repository. This project is a complex system for algorithmic trading, featuring a microservices-based architecture, advanced data analysis, and a sophisticated governance framework.

## Overview

This repository contains all the necessary components to run and develop Claire de Binare, including:

- **Microservices:** A suite of services for handling different aspects of the trading process, such as signal generation, execution, risk management, and data persistence.
- **Infrastructure:** Infrastructure-as-Code (IaC) for setting up the required environment, including database schemas, monitoring dashboards, and deployment configurations.
- **Governance:** A comprehensive set of documents defining the project's constitution, policies, and operational guidelines.
- **Tooling:** A collection of scripts and tools to aid in development, deployment, and maintenance.

## 📊 Projektstatus

### Gesamtfortschritt
```
Issues geschlossen: 200 / 314 (63.7%)
████████████░░░░░░░░ 63.7%
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

### 🔧 Services (8)

| Service | Beschreibung | Status |
|---------|-------------|--------|
| `services/allocation/` | Portfolio Allocation | 🟡 30% |
| `services/db_writer/` | DB Persistenz | ✅ 90% |
| `services/execution/` | Order Execution | ✅ 85% |
| `services/market/` | Market Data | ✅ 95% |
| `services/regime/` | Market Regime Detection | ✅ 70% |
| `services/risk/` | Risk Management | ✅ 80% |
| `services/signal/` | Signal Generation | ✅ 85% |
| `services/ws/` | WebSocket Handler | ✅ 90% |

**Durchschnitt Services: 78%**

### 🧪 Test-Infrastruktur

| Kategorie | Anzahl | Status |
|-----------|--------|--------|
| Test-Dateien | 27 | ✅ |
| Test-Funktionen | 247 | ✅ |
| Unit Tests | ✅ | 75% |
| Integration Tests | 🟡 | 50% |
| E2E Tests | 🟡 | 40% |
| Performance Tests | 🟡 | 30% |
| Chaos Tests | 🔴 | 10% |

### 📈 Monitoring & Observability

| Element | Anzahl | Status |
|---------|--------|--------|
| Grafana Dashboards | 8 | ✅ 60% |
| Prometheus Configs | 2 | ✅ |
| Alert Rules | 1 | 🟡 30% |
| Docker Services | 4 | ✅ |

### 🎯 Milestone-Fortschritt

| Milestone | Beschreibung | Status |
|-----------|-------------|--------|
| **M1** Foundation | Basis-Architektur | ✅ 100% |
| **M2** Trading Core | Signal/Execution | ✅ 95% |
| **M3** Risk Layer | Circuit Breaker | ✅ 90% |
| **M4** Market Data | WebSocket/OHLCV | ✅ 85% |
| **M5** Persistenz | DB Schema | 🟡 60% |
| **M6** ML Prep | Indicators | ✅ 80% |
| **M7** Testnet | Paper Trading | 🟡 55% |
| **M8** Stabilization | E2E Tests | 🟡 40% |
| **M9** Production | Live Trading | 🔴 15% |

### 📊 Zusammenfassung

```
┌─────────────────────────────────────────────┐
│  PROJEKT-REIFE: 65%                         │
│  ███████████████░░░░░░░░░                   │
├─────────────────────────────────────────────┤
│  Code: 1607 Python-Dateien                  │
│  Commits: 140+                              │
│  Issues: 200 closed / 114 open              │
│  Tests: 247 Test-Funktionen                 │
│  Dashboards: 8 Grafana Panels               │
└─────────────────────────────────────────────┘
```

*Stand: 2026-01-05*

---

## Getting Started

To get started with this project, you will need to have Docker and Python installed. The `docker-compose.yml` file in the root directory defines the services required for local development.

For a detailed index of the repository, please refer to the `REPO_INDEX.md` file.