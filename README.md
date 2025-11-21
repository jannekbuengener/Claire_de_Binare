# Claire de Binaire - Autonomous Crypto Trading Bot

**Status**: ✅ Deployment-Ready (100%)
**Phase**: N1 - Paper Trading Implementation
**Version**: 1.2.0-ci-enhanced

---

## 🎯 Quick Start

### **What is Claire de Binaire?**

An autonomous crypto trading system with multi-layer risk management, currently in **Paper Trading** phase (N1).

**Components:**
- 🔍 Market Data Screener
- 📊 Signal Engine (Momentum Strategy)
- 🛡️ Risk Manager (7-Layer Validation)
- ⚡ Execution Service (Paper Trading)
- 📈 Monitoring (Grafana & Prometheus)

### **Current Status**

- ✅ **122 Tests** (100% Pass Rate)
- ✅ **CI/CD Pipeline** (8 Jobs, ~8min)
- ✅ **Risk Engine** (100% Coverage)
- ✅ **E2E Tests** (18/18 passed)
- ✅ **Security Scanning** (Gitleaks, Bandit, pip-audit)

---

## 📚 Documentation

### **🔴 SINGLE SOURCE OF TRUTH**

**→ [`backoffice/PROJECT_STATUS.md`](backoffice/PROJECT_STATUS.md)** ← **START HERE**

This document contains:
- Current system status (container health, metrics, etc.)
- Active blockers & priorities
- Recent achievements
- Next steps

### **Essential Documents (in order)**

1. **[`CLAUDE.md`](CLAUDE.md)** - KI-Agent-Protokoll (Instructions for Claude)
2. **[`ROADMAP.md`](ROADMAP.md)** - Project roadmap & milestones
3. **[`backoffice/docs/KODEX – Claire de Binare.md`](backoffice/docs/KODEX%20%E2%80%93%20Claire%20de%20Binare.md)** - Project principles
4. **[`backoffice/docs/CI_CD_GUIDE.md`](backoffice/docs/CI_CD_GUIDE.md)** - CI/CD pipeline documentation

### **Architecture & Design**

- **[Architecture](backoffice/docs/architecture/)** - System design documents
  - [`N1_ARCHITEKTUR.md`](backoffice/docs/architecture/N1_ARCHITEKTUR.md) - N1 Phase architecture
  - [`SYSTEM_FLUSSDIAGRAMM.md`](backoffice/docs/architecture/SYSTEM_FLUSSDIAGRAMM.md) - Event flow diagrams

- **[Services](backoffice/docs/services/)** - Service-specific documentation
  - [`SERVICE_DATA_FLOWS.md`](backoffice/docs/services/SERVICE_DATA_FLOWS.md) - Data flow patterns

- **[Decision Log](backoffice/docs/DECISION_LOG.md)** - Architecture Decision Records (ADRs)

### **Testing & Development**

- **[Testing Guide](backoffice/docs/testing/)** - Test documentation
  - [`TESTING_GUIDE.md`](backoffice/docs/testing/TESTING_GUIDE.md) - Complete testing guide
  - [`LOCAL_E2E_TESTS.md`](backoffice/docs/testing/LOCAL_E2E_TESTS.md) - E2E test documentation
  - [`E2E_TEST_COMPLETION_REPORT.md`](backoffice/docs/reports/E2E_PAPER_TEST_REPORT.md) - E2E completion report

- **[Tests README](tests/README.md)** - Quick test reference

### **Operations**

- **[Runbooks](backoffice/docs/runbooks/)** - Operational procedures
  - [`CLAUDE_GORDON_WORKFLOW.md`](backoffice/docs/runbooks/CLAUDE_GORDON_WORKFLOW.md) - Claude → Gordon workflow

- **[Security](backoffice/docs/security/)** - Security documentation
  - [`HARDENING.md`](backoffice/docs/security/HARDENING.md) - Security hardening guide

### **Database**

- **[Database Docs](backoffice/docs/database/)** - Database documentation
  - [`DATABASE_SCHEMA.sql`](backoffice/docs/DATABASE_SCHEMA.sql) - PostgreSQL schema
  - [`DATABASE_READINESS_REPORT.md`](backoffice/docs/database/DATABASE_READINESS_REPORT.md) - DB readiness report
  - [`DATABASE_TRACKING_ANALYSIS.md`](backoffice/docs/database/DATABASE_TRACKING_ANALYSIS.md) - Data tracking analysis

### **Reports & Summaries**

- **[Reports](backoffice/docs/reports/)** - Status reports & summaries
  - [`COMPLETION_SUMMARY.md`](backoffice/docs/reports/COMPLETION_SUMMARY.md) - CI/CD completion summary
  - [`PR_BODY.md`](backoffice/docs/reports/PR_BODY.md) - Pull request template
  - [`SESSION_SUMMARY_2025-11-20.md`](backoffice/docs/reports/SESSION_SUMMARY_2025-11-20.md) - Session summary
  - [`SYSTEM_STATUS_REPORT.md`](backoffice/docs/reports/SYSTEM_STATUS_REPORT.md) - System status

### **Issue Tracking**

- **[`backoffice/docs/ISSUES_BACKLOG.md`](backoffice/docs/ISSUES_BACKLOG.md)** - Active issues & priorities

---

## 🚀 Quick Commands

### **Setup**

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Copy environment template
cp .env.example .env
# → Edit .env with your settings
```

### **Testing**

```bash
# CI Tests (fast, with mocks)
pytest -v -m "not e2e and not local_only"

# E2E Tests (requires Docker)
docker compose up -d
pytest -v -m e2e

# Local Tests (performance, stress)
pytest -v -m local_only

# With Coverage
pytest --cov=services --cov-report=html
```

### **Docker**

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# Health checks
curl http://localhost:8001/health  # Signal Engine
curl http://localhost:8002/health  # Risk Manager
curl http://localhost:8003/health  # Execution Service
```

### **Development**

```bash
# Lint & Format
ruff check .
black --check .

# Type checking
mypy services/

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

---

## 📊 Project Structure

```
Claire_de_Binare_Cleanroom/
├── CLAUDE.md                    ← KI-Agent instructions
├── README.md                    ← This file
├── ROADMAP.md                   ← Project roadmap
├── MILESTONES_README.md         ← GitHub milestones
│
├── backoffice/                  ← Documentation hub
│   ├── PROJECT_STATUS.md        ← 🔴 SINGLE SOURCE OF TRUTH
│   └── docs/
│       ├── architecture/        ← System design
│       ├── services/            ← Service docs
│       ├── testing/             ← Test documentation
│       ├── runbooks/            ← Operational procedures
│       ├── security/            ← Security docs
│       ├── database/            ← Database docs
│       ├── reports/             ← Status reports
│       ├── analysis/            ← Code analysis
│       ├── DECISION_LOG.md      ← ADRs
│       ├── KODEX.md             ← Project principles
│       └── ISSUES_BACKLOG.md    ← Active issues
│
├── services/                    ← Python microservices
│   ├── cdb_ws/                  ← WebSocket screener
│   ├── cdb_core/                ← Signal engine
│   ├── cdb_risk/                ← Risk manager
│   └── cdb_execution/           ← Execution service
│
├── tests/                       ← Test suite
│   ├── e2e/                     ← End-to-end tests
│   ├── integration/             ← Integration tests
│   ├── local/                   ← Local-only tests
│   └── conftest.py              ← Test fixtures
│
├── .github/                     ← GitHub config
│   ├── workflows/               ← CI/CD pipelines
│   └── README.md                ← CI/CD quick reference
│
└── docker-compose.yml           ← Container orchestration
```

---

## 🛡️ Security

- ✅ **Secret Scanning** (Gitleaks) - Blocks commits with secrets
- ✅ **Code Security** (Bandit) - SAST for Python
- ✅ **Dependency Audit** (pip-audit) - CVE scanning
- ✅ **Pre-commit Hooks** - Automated quality checks
- ✅ **ENV Validation** - Environment variable checking

See [`backoffice/docs/security/HARDENING.md`](backoffice/docs/security/HARDENING.md) for details.

---

## 📈 Metrics

### **Code Quality**
- **Test Coverage**: 100%
- **Test Count**: 122 (90 Unit, 14 Integration, 18 E2E)
- **CI Runtime**: ~8 minutes
- **Linting**: 0 issues

### **CI/CD Pipeline**
- **Jobs**: 8 (Lint, Format, Type, Test, Security×3, Docs)
- **Python Versions**: 3.11, 3.12
- **Security Scans**: Gitleaks, Bandit, pip-audit
- **Coverage Reports**: HTML + XML (30 days retention)

---

## 🤝 Team

- **Jannek** - Project Lead
- **Claude** - Architecture & Development
- **Gordon** - Docker & System Operations

---

## 📞 Support

### **Issues & Bugs**
- Check [`backoffice/docs/ISSUES_BACKLOG.md`](backoffice/docs/ISSUES_BACKLOG.md)
- Review [`backoffice/PROJECT_STATUS.md`](backoffice/PROJECT_STATUS.md)

### **Questions**
- Architecture: See [`backoffice/docs/DECISION_LOG.md`](backoffice/docs/DECISION_LOG.md)
- Testing: See [`backoffice/docs/testing/TESTING_GUIDE.md`](backoffice/docs/testing/TESTING_GUIDE.md)
- CI/CD: See [`backoffice/docs/CI_CD_GUIDE.md`](backoffice/docs/CI_CD_GUIDE.md)

---

**Last Updated**: 2025-11-21
**License**: Proprietary
**Project**: Claire de Binaire - Autonomous Crypto Trading Bot
