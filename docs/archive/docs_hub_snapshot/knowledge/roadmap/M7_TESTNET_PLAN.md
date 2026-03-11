# M7 TESTNET PLAN

**Version:** 2.0
**Date:** 2025-12-27
**Status:** Active Refinement (v1 was placeholder from 2025-12-19)
**Scope:** Testnet (Paper Trading) Infrastructure Implementation
**Milestone:** M7 - Testnet
**Epic:** #91 Paper Trading Test Infrastructure

---

## Executive Summary

**Mission:** Complete test infrastructure for Paper Trading to validate system behavior without real capital risk.

**Timeline:** 4-6 weeks (depending on M6 completion and resource availability)
**Critical Path:** M6 (Docker Baseline) ✅ → M7 (Testnet) 🔄 → M8 (Security) → M9 (Release)
**Resource Need:** 1-2 developers, infra access, testnet API keys

**Success Criteria:**
- ✅ 5 P0 E2E tests passing consistently
- ✅ Performance baselines documented (latency, throughput, resource usage)
- ✅ Paper trading validated over 14-day automated run
- ✅ Event-store integration functional
- ✅ Monitoring dashboards operational (Grafana)

---

## Epic #91 Breakdown

**Epic:** Paper Trading Test Infrastructure
**Consolidates:** 10 issues (#46-#50, #52-#56)
**Labels:** `type:feature`, `milestone:m7`, `scope:core`, `prio:should`

### Issue Inventory

| # | Issue | Type | Est. | Priority |
|---|-------|------|------|----------|
| #46 | Deep Research: Paper Trading Implementation Analysis | Research | 3d | P1 (Blocker) |
| #47 | Implement E2E Paper Trading Scenario Tests | Test | 5d | P0 (Critical) |
| #48 | Performance Baseline Measurements | Test | 2d | P1 |
| #49 | Resilience Tests: Service Recovery & Fault Injection | Test | 3d | P1 |
| #50 | Event-Store Integration | Feature | 5d | P0 (Critical) |
| #52 | Security Tests: Penetration Testing & Hardening | Test | 3d | P2 (M8 prep) |
| #53 | Monitoring Integration: Grafana Dashboards & Alerting | Infra | 3d | P1 |
| #54 | CLI Tools Testing: query_analytics.py & Management Scripts | Test | 2d | P2 |
| #55 | Documentation Gaps: Complete Missing Architecture Docs | Docs | 3d | P2 |
| #56 | Automated Test Data Generation: Realistic Market Scenarios | Tooling | 3d | P1 |
| **Total** | | | **32d** | |

**Additional M7 Issues (Outside Epic #91):**
- #92 TBD (check GitHub)
- #93 TBD
- #94 TBD

---

## Weekly Sprint Breakdown

### Week 1: Foundation & Research (Issues #46, #56, #47 start)

**Goal:** Establish research baseline, test data infrastructure, begin E2E scaffolding

**Tasks:**
- **#46 Deep Research (3d):** Analyze existing paper trading implementation
  - Review `services/execution/paper_trading.py` (506 lines)
  - Review `tools/paper_trading/service.py` (469 lines)
  - Document findings in `docs/testing/PAPER_TRADING_IMPLEMENTATION_ANALYSIS.md`
  - Identify gaps, risks, and optimization opportunities

- **#56 Automated Test Data Generation (3d):** Build realistic market scenario generator
  - Create `tools/test_data_generator/` module
  - Implement OHLCV generator with volatility models
  - Generate 14-day MEXC testnet data (BTC/USDT, ETH/USDT)
  - Validate against real market distributions

- **#47 E2E Tests - Scaffolding (2d):** Setup test framework
  - Create `tests/e2e/test_paper_trading_p0.py` (if not exists - check first!)
  - Define P0 test cases: happy path, signal-to-execution, error handling
  - Setup fixtures for Redis, Postgres, mock MEXC testnet

**Deliverables:**
- ✅ Research report (PAPER_TRADING_IMPLEMENTATION_ANALYSIS.md)
- ✅ Test data generator (realistic OHLCV data)
- ✅ E2E test scaffolding (tests runnable but not all passing)

**Resource Needs:**
- 1 developer (full-time)
- MEXC testnet API access
- Docker + local dev environment

**Risks:**
- Research uncovers major gaps requiring rework (→ extend Week 1 by 2d)
- Test data quality insufficient (→ iterate on volatility models)

---

### Week 2: E2E Tests + Performance (Issues #47 complete, #48, #53 start)

**Goal:** Complete P0 E2E tests, establish performance baselines, begin monitoring setup

**Tasks:**
- **#47 E2E Tests - Implementation (3d):** Complete all P0 tests
  - TC_P0_001: Happy path market-to-trade
  - TC_P0_002: Signal-to-execution flow
  - TC_P0_003: Error handling (invalid signals, connection failures)
  - TC_P0_004: Multi-signal concurrent execution
  - TC_P0_005: State persistence (Redis + Postgres)
  - All tests must pass consistently (3 consecutive runs)

- **#48 Performance Baselines (2d):** Measure and document baseline metrics
  - Latency: signal receipt → order execution (<500ms target)
  - Throughput: signals/second (target: 10+ concurrent)
  - Resource usage: CPU, memory, network per service
  - Document in `docs/testing/PERFORMANCE_BASELINES.md`
  - Establish SLO targets for M9

- **#53 Monitoring - Setup (2d start, continues W3):** Deploy Grafana dashboards
  - Setup Prometheus scraping (if not already configured)
  - Import/create dashboards: Paper Trading Overview, Signal Processing, Order Execution
  - Configure alerting rules (paper_runner health, Redis down, Postgres slow query)

**Deliverables:**
- ✅ 5 P0 E2E tests passing (100% pass rate over 3 runs)
- ✅ Performance baseline report (PERFORMANCE_BASELINES.md)
- ✅ Grafana dashboards deployed (observability functional)

**Resource Needs:**
- 1 developer (full-time)
- Grafana instance (staging or local)
- Prometheus (if not already running)

**Risks:**
- E2E tests flaky due to timing issues (→ add retries, fix race conditions)
- Performance targets not met (→ optimization sprint needed, may slip M7)
- Monitoring setup blocked by infra access (→ escalate to infra team)

**Blockers:**
- Grafana instance provisioning (ACTION: request staging Grafana if not available)

---

### Week 3: Resilience + Event-Store Integration (Issues #49, #50, #53 complete)

**Goal:** Validate system resilience under failure, integrate event-store, finish monitoring

**Tasks:**
- **#49 Resilience Tests (3d):** Fault injection and recovery testing
  - Chaos tests: kill Redis mid-trade, restart Postgres, network partition
  - Service recovery: validate paper_runner restarts gracefully
  - Data consistency: verify no lost trades after failures
  - Circuit breaker validation (if implemented)
  - Document in `docs/testing/RESILIENCE_TEST_REPORT.md`

- **#50 Event-Store Integration (5d - CRITICAL PATH):** Connect event sourcing
  - **RISK:** This is the biggest M7 blocker if event-store not ready
  - Tasks:
    - Review event-store schema (Postgres `events` table or dedicated store)
    - Implement event publishing from paper trading service
    - Validate event replay capabilities
    - Add event-based E2E test (replay 14-day paper trading from events)
  - **Dependency:** M5 persistence layer must be functional
  - **Mitigation:** If event-store not ready, mock interface and defer full integration to M8

- **#53 Monitoring - Complete (1d):** Finalize dashboards & alerting
  - Validate all dashboards showing live data
  - Test alert routing (Slack, email, PagerDuty)
  - Document in `docs/runbooks/MONITORING_SETUP.md`

**Deliverables:**
- ✅ Resilience test suite passing (all recovery scenarios validated)
- ✅ Event-store integration complete OR mocked with clear migration plan
- ✅ Monitoring fully operational (dashboards + alerts)

**Resource Needs:**
- 1 developer (full-time)
- Event-store access (Postgres or dedicated store)
- Alert routing credentials (Slack webhook, email SMTP)

**Risks:**
- **CRITICAL:** Event-store not ready → Blocks M7 completion
  - Mitigation: Use mock interface, defer to M8, document assumptions
- Chaos tests reveal critical bugs → Extend Week 3 by 2d for fixes
- Alert spam → Tune thresholds, may require Week 4 iteration

**Blockers:**
- Event-store readiness (ACTION: verify M5 status, escalate if blocked)

---

### Week 4: Security Prep + CLI Tools + Docs (Issues #52, #54, #55)

**Goal:** Complete M7 closure tasks, prepare for M8 security audit

**Tasks:**
- **#52 Security Tests - Planning (3d - partial):** M8 prep work
  - **Note:** Full penetration testing is M8 scope, this is preparatory
  - Tasks:
    - Document attack surface (paper trading API, Redis, Postgres, Grafana)
    - Run automated security scanners (e.g., OWASP ZAP on health endpoints)
    - Review secret management (are API keys properly rotated?)
    - Create `docs/security/M7_SECURITY_AUDIT_PREP.md`
  - **Output:** Security checklist for M8 team, no blocking issues

- **#54 CLI Tools Testing (2d):** Validate management scripts
  - Test `query_analytics.py` (if exists) against paper trading logs
  - Validate `make paper-trading-start/stop/logs` targets
  - Test `tools/paper_trading/service.py` health endpoint
  - Document in `docs/runbooks/CLI_TOOLS_GUIDE.md`

- **#55 Documentation Gaps (3d):** Close missing architecture docs
  - Audit `docs/architecture/` for missing diagrams/explanations
  - Create/update:
    - `docs/architecture/PAPER_TRADING_FLOW.md` (signal → trade flow)
    - `docs/architecture/EVENT_STORE_DESIGN.md` (if event-store integrated)
    - `docs/architecture/SERVICE_DEPENDENCIES.md` (update with M7 changes)
  - Ensure all diagrams are up-to-date

**Deliverables:**
- ✅ Security audit prep complete (checklist for M8, no P0 issues)
- ✅ CLI tools validated and documented
- ✅ Architecture docs gap analysis complete, critical docs updated

**Resource Needs:**
- 1 developer (full-time or 0.5 FTE if tasks parallelized)
- Security scanning tools (OWASP ZAP, Bandit for Python)
- Diagram tools (Mermaid, draw.io)

**Risks:**
- Security scans reveal P0 vulnerabilities → Extends M7, blocks M8
  - Mitigation: Fix P0s immediately, defer P1/P2 to M8
- Documentation gaps larger than expected → Prioritize critical paths only
- CLI tools broken → Quick fixes or escalate if systemic issues

---

## Week 5-6: Buffer & Final Validation (Contingency)

**Goal:** Buffer weeks for slippage, final validation, and M8 prep

**Scenarios:**
- **If on schedule:** Use Week 5 for:
  - Final 14-day paper trading automated run (validation test)
  - M8 preparation (security hardening, penetration test scheduling)
  - Knowledge transfer (document lessons learned)

- **If behind schedule:**
  - Week 5: Complete slipped tasks from W1-W4
  - Week 6: Final validation + catch-up

- **If ahead of schedule:**
  - Early M8 start (security audit, penetration test booking)
  - Optimize performance (if baselines not met, iterate)

**Deliverables (if used):**
- ✅ 14-day paper trading run successful (zero P0 errors)
- ✅ M8 kickoff document ready (security roadmap finalized)
- ✅ M7 retrospective completed (lessons learned logged)

---

## Dependencies & Blockers

### Hard Dependencies (Must Complete Before M7 Close)
- ✅ **M6 Complete:** Docker baseline stable (assumed complete per M7 readiness)
- 🔄 **M5 Progress:** Event-store integration functional (BLOCKER if not ready)
- ⚠️ **MEXC Testnet Access:** API keys provisioned (VERIFY: Are keys active?)
- ⚠️ **Grafana Instance:** Staging or dev Grafana available (ACTION: Provision if missing)

### Soft Dependencies (Can Work Around)
- M3 Risk Layer complete (Nice-to-have, not blocking)
- Production Grafana (can use staging/local for M7)

### Known Blockers (As of 2025-12-27)
1. **Event-Store Readiness:** If M5 not complete, event-store integration (#50) blocked
   - **Mitigation:** Mock interface, defer to M8
2. **Grafana Provisioning:** If no staging instance, monitoring (#53) delayed
   - **Mitigation:** Use local Grafana, migrate to staging in M8
3. **Security Lead Assignment:** M8 prep (#52) requires security expert
   - **Mitigation:** Preliminary work can be done by M7 team, full audit in M8

---

## Resource Allocation

### People
- **Primary:** 1 full-time developer (entire M7 duration)
- **Support:** 0.5 FTE infra engineer (Week 2-3 for monitoring setup)
- **Escalation:** Tech lead available for blockers (on-call basis)

### Tools & Infrastructure
- **Compute:** Local Docker + staging environment
- **Services:** Redis, Postgres, Grafana, Prometheus
- **APIs:** MEXC testnet (ensure keys active)
- **Security:** OWASP ZAP, Bandit (Python static analysis)

### Budget (if applicable)
- **MEXC Testnet:** Free (no cost)
- **Grafana Cloud:** $0 (use self-hosted)
- **Compute:** Existing staging infra (no additional cost)
- **Pentest (M8 prep):** $0 in M7 (budget reserved for M8)

**Estimated Total:** $0 (assuming existing infra reused)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Event-store not ready (M5 dependency) | MEDIUM | HIGH | Mock interface, defer full integration to M8 |
| E2E tests flaky/failing | MEDIUM | HIGH | Add retries, fix race conditions, extend W2 by 2d |
| Performance targets not met | LOW | MEDIUM | Optimization sprint (may slip M7 by 1 week) |
| Grafana access blocked | LOW | LOW | Use local Grafana, migrate to staging later |
| Security scans find P0 bugs | LOW | MEDIUM | Fix immediately, defer P1/P2 to M8 |
| Documentation gaps larger than expected | LOW | LOW | Prioritize critical paths only |
| Developer unavailability | LOW | HIGH | Cross-train backup, maintain handoff docs |

**Overall Risk:** MEDIUM (event-store dependency is main concern)

---

## Success Metrics (M7 Completion Criteria)

### Must-Have (Blockers for M7 Close)
- [ ] 5 P0 E2E tests passing (100% pass rate over 3 runs)
- [ ] Performance baselines documented (latency, throughput, resources)
- [ ] Paper trading validated (14-day automated run OR manual validation)
- [ ] Monitoring operational (Grafana dashboards + alerting)
- [ ] No P0 security issues found (security prep checklist complete)

### Should-Have (Defer if Time-Constrained)
- [ ] Event-store integration complete (can mock and defer to M8)
- [ ] Resilience tests passing (all chaos scenarios)
- [ ] CLI tools tested and documented
- [ ] Architecture docs gap closed

### Nice-to-Have (M8 Scope if Not Done)
- [ ] Security penetration test (M8 primary scope)
- [ ] Performance optimization (if baselines not met, iterate in M8)
- [ ] Full 14-day paper trading run (can do partial validation)

---

## Handoff to M8 (Security)

### M8 Inputs from M7
- Security audit prep checklist (`docs/security/M7_SECURITY_AUDIT_PREP.md`)
- Performance baselines (for M8 load testing validation)
- Event-store integration status (complete OR mocked with migration plan)
- Monitoring setup (M8 adds security-specific dashboards)

### M8 Blockers Identified in M7
- Security Lead assignment (ACTION: Assign before M8 start)
- Penetration test booking (ACTION: Schedule 2 weeks into M8)

---

## Timeline Summary

| Week | Focus | Deliverables | Risk |
|------|-------|--------------|------|
| W1 | Research + Test Data + E2E Scaffold | Research report, test data, E2E scaffolding | LOW |
| W2 | E2E Complete + Performance + Monitoring | 5 P0 tests passing, baselines, Grafana | MEDIUM |
| W3 | Resilience + Event-Store + Monitoring | Chaos tests, event-store integration | HIGH (event-store dependency) |
| W4 | Security Prep + CLI + Docs | Security checklist, CLI guide, arch docs | LOW |
| W5-W6 | Buffer + Final Validation | 14-day run, M8 prep, retrospective | MEDIUM (catch-up buffer) |

**Expected Duration:** 4 weeks (optimistic) to 6 weeks (with buffer)
**Critical Path:** Week 3 (event-store integration)

---

## References

- Epic #91: https://github.com/jannekbuengener/Claire_de_Binare/issues/91
- MILESTONES.md: `.github/MILESTONES.md` (Working Repo)
- M8_SECURITY_PLAN.md: `knowledge/roadmap/M8_SECURITY_PLAN.md` (Docs Hub)
- M9_RELEASE_PLAN.md: `knowledge/roadmap/M9_RELEASE_PLAN.md` (Docs Hub)
- PAPER_TRADING_TEST_REQUIREMENTS.md: `docs/testing/PAPER_TRADING_TEST_REQUIREMENTS.md` (if exists)

---

**Plan Status:** ✅ REFINED (v2.0)
**Last Updated:** 2025-12-27
**Next Review:** Start of Week 1 (M7 kickoff)
**Owner:** Claude (Session Lead) per Issue #107

---

_M7 Testnet Plan refined for Issue #107_
_Epic #91 breakdown complete | Weekly sprints defined | Resource needs identified_
