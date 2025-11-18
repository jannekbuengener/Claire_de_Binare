# Claire de Binare – Cleanroom Repository

**Kanonisches Repository** für das Claire de Binare autonome Trading-System.

**Status**: ✅ Cleanroom Baseline etabliert (2025-11-16)
**Current Phase**: N1 - Paper-Test Vorbereitung

---

## 🚀 Quick Start / Onboarding

**Neu hier?** Start here:
- 📖 **[Onboarding & Repository Navigation](backoffice/docs/CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md)** – Comprehensive guide for new contributors and AI agents
- 📐 **[KODEX – Project Principles](backoffice/docs/KODEX%20–%20Claire%20de%20Binare.md)** – Architecture philosophy
- 🏗️ **[N1 Architecture](backoffice/docs/architecture/N1_ARCHITEKTUR.md)** – Current system design (Paper-Test phase)
- 📊 **[Project Status](backoffice/PROJECT_STATUS.md)** – Current phase and work items

---

## Strukturüberblick

**Active Code & Documentation**:
- `backoffice/` – **Single Source of Truth** for all code and documentation
  - `backoffice/docs/` – Canonical documentation (KODEX, ADRs, architecture, services)
  - `backoffice/services/` – Service implementations (signal_engine, risk_manager, execution_service)
  - `backoffice/templates/` – Reusable templates (.env, infrastructure)
- `scripts/` – Utility scripts (migration templates, tooling)
- `tests/` – Test code (unit & integration)

**Historical Reference**:
- `archive/` – Historical artifacts (read-only, do not modify)
  - `archive/backoffice_original/` – Pre-migration backup
  - `archive/docs_original/` – Old documentation versions
  - `archive/sandbox_backups/` – Historical sandbox environment

---

## Current Phase: N1 - Paper-Test

The system is in **N1 phase** (simulated trading environment):
- ✅ Market Data Interface (MDI) – simulated price feeds
- ✅ Signal Engine – strategy signal generation
- ✅ Risk Manager – 6-layer risk validation
- ✅ Execution Service – simulated order execution
- ✅ Portfolio Tracker – position and PnL tracking
- ✅ Monitoring – Prometheus & Grafana

**NOT in N1**: Live broker API, real capital deployment

See [N1_ARCHITEKTUR.md](backoffice/docs/architecture/N1_ARCHITEKTUR.md) for details.

---

## Nächste Schritte

1. **For New Contributors**: Read [CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md](backoffice/docs/CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md)
2. **For Development**: Check [PROJECT_STATUS.md](backoffice/PROJECT_STATUS.md) for current work items
3. **For Architecture**: Review [STRUCTURE_CLEANUP_PLAN.md](backoffice/docs/architecture/STRUCTURE_CLEANUP_PLAN.md) for planned refactoring

### Evaluation schnell starten

- Abhängigkeiten installieren: `python -m pip install -r requirements.txt`
- Demo-Evaluation ausführen: `python scripts/evaluate.py --config evaluation/config.yaml`
  (Optionale Traces im Console-Exporter; OTLP-Endpunkt in `evaluation/config.yaml` konfigurierbar.)

Weitere Details und Ablaufbeschreibungen finden sich im Runbook-Index (`docs/runbooks/INDEX.md`).
