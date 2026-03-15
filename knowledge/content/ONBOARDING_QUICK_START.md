# CDB Onboarding - Quick Start

**Team:** B (Dev-Stream)
**Version:** 1.0
**Date:** 2025-12-29
**Status:** Deliverable - Onboarding Pointer Pack

---

## 🎯 Essential Reading (30 min)

### 1. README + Current Entry Chain (5 min)
📍 **Start:** `README.md` then [`CURRENT_STATUS.md`](../CURRENT_STATUS.md), [`COMPOSE_LAYERS.md`](../../infrastructure/compose/COMPOSE_LAYERS.md), [`QUICK_START.md`](../../infrastructure/docs/QUICK_START.md)
**What:** Project overview, current runtime model, canonical compose layers, getting started

### 2. System Context (5 min)
📍 **Location:** `knowledge/SYSTEM.CONTEXT.md`
**What:** Architecture, components, data flow

### 3. Current Status (3 min)
📍 **Location:** `knowledge/CURRENT_STATUS.md`
**What:** Latest sprint, resolved issues, active work

### 4. Roadmap (10 min)
📍 **Location:** `knowledge/roadmap/EXPANDED_ECOSYSTEM_ROADMAP.md`
**What:** Milestones, timelines, epic structure

### 5. CLAUDE.md (Session Lead Rules) (7 min)
📍 **Location:** `CLAUDE.md`
**What:** Governance, session workflow, tool usage rules

---

## 🔧 Developer Setup (20 min)

### Prerequisites
- Docker Desktop installed
- Git configured
- Python 3.11+ with venv

### Quick Setup
```powershell
# 1. Clone repo
git clone https://github.com/jannekbuengener/Claire_de_Binare.git
cd Claire_de_Binare

# 2. Setup venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dev dependencies
pip install -r requirements-dev.txt

# 4. Setup secrets (see SECRETS.md)
# Copy .cdb_local.secrets/ to C:/Users/<you>/Documents/.secrets/.cdb/

# 5. Start Docker stack (canonical BLUE+RED runtime)
docker network create cdb_network 2>$null
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d

# 6. Verify stack
docker ps --filter "name=cdb_"

# 7. Run smoke tests
.venv/Scripts/python.exe -m pytest tests/unit/test_models.py -v
```

---

## 📚 Key Documentation

### Architecture & Design
- `docs/architecture/` - System design documents
- `docs/services/` - Service-specific runbooks
- `docs/workflows/` - Process documentation

### Governance & Policy
- `docs/governance/` - Decision records, policies
- `docs/security/` - Security guidelines, threat models

### Testing & Quality
- 📄 `docs/TEST_HARNESS_V1.md` - How to run tests ✅
- 📄 `docs/CONTRACTS.md` - Message schemas ✅
- `tests/` - Test suite (228+ tests)

### Development
- 📄 `docs/PATCHSET_PLAN_345.md` - Example fix workflow ✅
- `.github/workflows/` - CI/CD pipelines
- `infrastructure/` - Docker, compose, monitoring config

---

## 🔍 Finding Things

### "I need to understand the signal generation flow"
1. Start: `knowledge/SYSTEM.CONTEXT.md` (data flow diagram)
2. Code: `services/signal/service.py` (SignalEngine class)
3. Contract: `docs/CONTRACTS.md` (message schemas)
4. Tests: `tests/unit/signal/test_service.py`

### "I need to debug why my service won't start"
1. Logs: `docker logs cdb_<service>`
2. Runbook: `docs/services/<SERVICE>_RUNBOOK.md`
3. Health: `curl http://localhost:<port>/health`
4. Metrics: `curl http://localhost:<port>/metrics`

### "I need to add a new test"
1. Guide: `docs/TEST_HARNESS_V1.md`
2. Fixtures: `tests/conftest.py`, `tests/fixtures/`
3. Examples: `tests/unit/test_models.py`
4. Run: `.venv/Scripts/python.exe -m pytest <your_test.py> -v`

### "I need to understand how secrets work"
1. Architecture: `knowledge/SYSTEM.CONTEXT.md` (secrets section)
2. Config: canonical BLUE+RED compose files (`infrastructure/compose/compose.blue.yml`)
3. Local setup: `.cdb_local.secrets/` directory structure

---

## 🚨 Common Pitfalls

### ❌ "pytest: command not found"
**Solution:** Use venv python: `.venv/Scripts/python.exe -m pytest`

### ❌ "Services won't start - connection refused"
**Solution:** Check Docker stack: `docker-compose up -d`

### ❌ "Tests fail with 'No module named X'"
**Solution:** Install deps: `pip install -r requirements-dev.txt`

### ❌ "I committed secrets to git!"
**Solution:** See `docs/security/SECRET_LEAK_RESPONSE.md` (TODO: create)

---

## 🤝 Getting Help

### Documentation Issues
- Check `knowledge/CURRENT_STATUS.md` for latest updates
- Review relevant runbook in `docs/services/`
- Search GitHub issues for keywords

### Code Questions
- Read service's `service.py` (main entry point)
- Check `tests/unit/<service>/` for examples
- Review `docs/CONTRACTS.md` for data schemas

### Process Questions
- Read `CLAUDE.md` for session workflow
- Check `agents/AGENTS.md` for agent coordination
- Review recent commits for examples

---

## 📖 Deep Dives (When You Have Time)

### Week 1: Core Concepts
- [ ] Read full `knowledge/SYSTEM.CONTEXT.md`
- [ ] Explore `services/` directory structure
- [ ] Run full unit test suite
- [ ] Review recent PR commits

### Week 2: Pipeline Understanding
- [ ] Trace a trade through the full pipeline (ws → signal → risk → execution)
- [ ] Read all service runbooks
- [ ] Understand Redis Pub/Sub + Streams architecture
- [ ] Review `docs/CONTRACTS.md` schemas

### Week 3: Testing & Quality
- [ ] Run E2E test suite
- [ ] Add a new unit test
- [ ] Fix a failing test
- [ ] Review coverage report

### Week 4: Contribution
- [ ] Pick a "good first issue" from GitHub
- [ ] Create a feature branch
- [ ] Implement + test
- [ ] Submit PR with test coverage

---

## 🔗 External Resources

### Docker & Compose
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Docker Compose V2](https://docs.docker.com/compose/)

### Python & Testing
- [pytest Documentation](https://docs.pytest.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

### Redis
- [Redis Pub/Sub](https://redis.io/docs/manual/pubsub/)
- [Redis Streams](https://redis.io/docs/data-types/streams/)

### MEXC API
- [MEXC V3 WebSocket](https://mexcdevelop.github.io/apidocs/spot_v3_en/#websocket-market-streams)

---

**Deliverable:** Onboarding Pointer Pack (1/2) ✅
**Next:** ONBOARDING_LINKS.md (consolidated reference)
