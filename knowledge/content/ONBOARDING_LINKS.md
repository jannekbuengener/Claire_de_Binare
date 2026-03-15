# CDB Documentation - Consolidated Links

**Team:** B (Dev-Stream)
**Purpose:** Consolidated documentation reference
**Date:** 2025-12-29
**Status:** Deliverable - Onboarding Pointer Pack

---

## 📁 Documentation Hub Structure

```
Claire_de_Binare/
├── CLAUDE.md                    ← Session Lead governance
├── README.md                    ← Project overview (add onboarding section)
├── knowledge/                   ← Knowledge base (canonical docs)
│   ├── SYSTEM.CONTEXT.md       ← Architecture, data flow
│   ├── CURRENT_STATUS.md       ← Latest status, active sprint
│   └── roadmap/
│       └── EXPANDED_ECOSYSTEM_ROADMAP.md  ← Milestones, timeline
├── agents/
│   └── AGENTS.md               ← Multi-agent coordination rules
├── docs/                       ← Technical documentation
│   ├── TEST_HARNESS_V1.md     ← How to run tests (NEW)
│   ├── CONTRACTS.md           ← Message schemas (NEW)
│   ├── PATCHSET_PLAN_345.md   ← Example fix workflow (NEW)
│   ├── ONBOARDING_QUICK_START.md  ← Getting started (NEW)
│   ├── ONBOARDING_LINKS.md    ← This file (NEW)
│   ├── services/              ← Service runbooks
│   ├── architecture/          ← System design
│   ├── governance/            ← Policies, ADRs
│   └── security/              ← Security guidelines
└── tests/                     ← Test suite (228+ tests)
```

---

## 🎯 Quick Navigation

### New Developer? Start Here:
1. `README.md` -> [`CURRENT_STATUS.md`](../CURRENT_STATUS.md) -> [`COMPOSE_LAYERS.md`](../../infrastructure/compose/COMPOSE_LAYERS.md) -> [`QUICK_START.md`](../../infrastructure/docs/QUICK_START.md) (current entry chain)
2. [knowledge/SYSTEM.CONTEXT.md](../SYSTEM.CONTEXT.md) (architecture)
3. [TEST_HARNESS_V1.md](TEST_HARNESS_V1.md) (how to test)

### Working on Code? Check:
1. 📄 [CONTRACTS.md](CONTRACTS.md) (message schemas)
2. 📄 [docs/services/](services/) (service runbooks)
3. 📄 [tests/](../tests/) (test examples)

### Fixing Bugs? See:
1. 📄 [PATCHSET_PLAN_345.md](PATCHSET_PLAN_345.md) (example workflow)
2. 📄 [knowledge/CURRENT_STATUS.md](../knowledge/CURRENT_STATUS.md) (known issues)
3. 📄 [TEST_HARNESS_V1.md](TEST_HARNESS_V1.md) (testing strategy)

---

## 📚 Documentation by Category

### Governance & Process
| Document | Purpose | Location |
|----------|---------|----------|
| CLAUDE.md | Session Lead rules | `/CLAUDE.md` |
| AGENTS.md | Multi-agent coordination | `/agents/AGENTS.md` |
| Roadmap | Milestones, timeline | `/knowledge/roadmap/EXPANDED_ECOSYSTEM_ROADMAP.md` |

### Architecture & Design
| Document | Purpose | Location |
|----------|---------|----------|
| SYSTEM.CONTEXT.md | Architecture overview | `/knowledge/SYSTEM.CONTEXT.md` |
| CONTRACTS.md | Message schemas | `/docs/CONTRACTS.md` |
| Service Runbooks | Per-service operations | `/docs/services/<SERVICE>_RUNBOOK.md` |

### Testing & Quality
| Document | Purpose | Location |
|----------|---------|----------|
| TEST_HARNESS_V1.md | Test execution guide | `/docs/TEST_HARNESS_V1.md` |
| Test Suite | All tests | `/tests/` |
| pytest.ini | Test configuration | `/pytest.ini` |

### Development
| Document | Purpose | Location |
|----------|---------|----------|
| PATCHSET_PLAN_345.md | Example fix workflow | `/docs/PATCHSET_PLAN_345.md` |
| CURRENT_STATUS.md | Latest sprint status | `/knowledge/CURRENT_STATUS.md` |
| requirements-dev.txt | Dev dependencies | `/requirements-dev.txt` |

### Infrastructure
| Document | Purpose | Location |
|----------|---------|----------|
| Compose Layers | Canonical runtime topology | `/infrastructure/compose/COMPOSE_LAYERS.md` |
| BLUE+RED Runtime | Canonical compose (operator/runtime) | `/infrastructure/compose/compose.blue.yml` + `compose.red.yml` |
| Legacy Compose | CI/test and explicit debug only | `/infrastructure/compose/base.yml` + `dev.yml` |
| Monitoring Config | Prometheus/Grafana | `/infrastructure/monitoring/` |

---

## 🔗 Legacy Archive (Local)

### Docs Hub Snapshot
📍 **Location:** `docs/archive/docs_hub_snapshot/`

**Contents:**
- historical strategic planning documents
- legacy research and review artifacts
- old session-log style material
- prior navpacks, templates, and migration evidence

**Rule:** The working repo now contains the productive canon. The snapshot is for
historical lookup only.

---

## 📖 Service-Specific Runbooks

| Service | Runbook | Key Topics |
|---------|---------|------------|
| WebSocket (cdb_ws) | [WS_SERVICE_RUNBOOK.md](services/WS_SERVICE_RUNBOOK.md) | MEXC V3 API, trade decoding, Redis publishing |
| Signal Engine (cdb_signal) | TBD | Signal generation, PriceBuffer, thresholds |
| Risk Manager (cdb_risk) | TBD | Portfolio checks, circuit breakers, allocation |
| Execution (cdb_execution) | TBD | Order routing, API calls, confirmations |
| DB Writer (cdb_db_writer) | TBD | Event persistence, batch writes |

**Status:** Only WS_SERVICE_RUNBOOK.md exists (2025-12-29)
**TODO:** Create runbooks for other services

---

## 🧪 Test Documentation

### Test Categories
| Category | Location | Purpose | Docker Required? |
|----------|----------|---------|------------------|
| Unit | `tests/unit/` | Isolated component tests | No |
| E2E | `tests/e2e/` | Full pipeline tests | Yes |
| Integration | `tests/integration/` | Multi-service tests | Partial |
| Chaos | `tests/chaos/` | Resilience tests | Yes |
| Performance | `tests/performance/` | Latency/throughput | Yes |

### Test Execution Guide
📄 **Primary Reference:** [TEST_HARNESS_V1.md](TEST_HARNESS_V1.md)

---

## 🎯 Working Group Specific Links

### Team A (Infra-Stream)
- Infrastructure configs: `/infrastructure/`
- Monitoring: `/infrastructure/monitoring/`
- Secrets architecture: `/knowledge/SYSTEM.CONTEXT.md` (secrets section)
- **Handovers from Team B:** [HANDOVERS_TO_TEAM_A.md](HANDOVERS_TO_TEAM_A.md)

### Team B (Dev-Stream)
- Test Harness: [TEST_HARNESS_V1.md](TEST_HARNESS_V1.md)
- Contracts: [CONTRACTS.md](CONTRACTS.md)
- Patchset Plan: [PATCHSET_PLAN_345.md](PATCHSET_PLAN_345.md)
- Onboarding: [ONBOARDING_QUICK_START.md](ONBOARDING_QUICK_START.md)

---

## 🔄 Document Maintenance

### Update Frequency
- `CURRENT_STATUS.md`: After every session
- `TEST_HARNESS_V1.md`: When test infrastructure changes
- `CONTRACTS.md`: When message schemas change
- Service Runbooks: When service behavior changes

### Ownership
- **Canonical Docs** (knowledge/): Session Lead + Orchestrator
- **Technical Docs** (docs/): Relevant Team (A or B)
- **Service Runbooks** (docs/services/): Service owner

---

## 📝 TODO: Missing Documentation

### High Priority
- [ ] Create runbooks for remaining services (signal, risk, execution, db_writer)
- [ ] Add README.md onboarding section (link to ONBOARDING_QUICK_START.md)
- [ ] Create SECRET_LEAK_RESPONSE.md (security incident response)

### Medium Priority
- [ ] Expand CONTRACTS.md with `orders` schema
- [ ] Add CI/CD documentation (GitHub Actions guide)
- [ ] Create TROUBLESHOOTING.md (common issues + solutions)

### Low Priority
- [ ] Add Grafana dashboard documentation
- [ ] Create performance tuning guide
- [ ] Add observability best practices

---

**Deliverable:** Onboarding Pointer Pack (2/2) ✅
**Status:** Complete - Ready for Team A handover
