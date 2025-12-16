# Agent Task Recommendations — Multi-Agent Workload Distribution

**Date:** 2025-12-16  
**Created by:** Copilot (CDB_GITHUB_MANAGER)  
**Purpose:** Task recommendations for Claude, Gemini, Codex, and Copilot  
**Status:** 🎯 **READY FOR ASSIGNMENT**

---

## Overview

Nach GitHub Cleanup (Copilot) und Docs Hub Audit sind **folgende Aufgaben** für die anderen Agenten entstanden.

**Principles:**
- Tasks aligned with agent charters
- Clear scope & acceptance criteria
- No overlap between agents
- MUST/SHOULD/NICE prioritization

---

## CLAUDE — Session Lead (Orchestration)

**Role:** Strategic planning, coordination, session management  
**Strengths:** Big picture, decision prep, cross-agent coordination

### Task 1: M7-M9 Roadmap Refinement 🎯 **HIGH PRIORITY**

**Goal:** Refine Milestone roadmap (M7 Testnet, M8 Security, M9 Release) with detailed timeline & resource allocation.

**Scope:**
- Review `.github/MILESTONES.md` (Working Repo)
- Break down M7 Epic #91 into weekly sprints
- Identify M8 blockers (Security Lead assignment, Penetration Test booking)
- Define M9 acceptance criteria (production deployment checklist)

**Deliverables:**
- `docs/roadmap/M7_TESTNET_PLAN.md` (Docs Hub)
- `docs/roadmap/M8_SECURITY_PLAN.md` (refined from SECURITY_ROADMAP.md)
- `docs/roadmap/M9_RELEASE_PLAN.md` (new)
- Updated `knowledge/CDB_KNOWLEDGE_HUB.md` (decisions logged)

**Acceptance:**
- ✅ M7-M9 timeline with week-by-week breakdown
- ✅ Resource needs identified (people, tools, budget)
- ✅ Critical path validated (M6 → M7 → M8 → M9)
- ✅ Blockers explicitly named & mitigation plans

**Estimated Effort:** 2-3 sessions  
**Priority:** **MUST** (M7 execution imminent)

---

### Task 2: Docs Hub Consolidation Review 🔍

**Goal:** Review new files from Büro (16 files pushed today) and consolidate with existing structure.

**Context:**
- Büro pushed: `governance/CONSTITUTION.md`, `governance/CONTRIBUTION_RULES.md`, `docs/INDEX.md`, `knowledge/index.yaml`, etc.
- Existing structure: `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `DOCS_HUB_INDEX.md`

**Scope:**
- Compare new vs existing governance files
- Identify duplicates or conflicts
- Decide canonical versions
- Update cross-references

**Deliverables:**
- `knowledge/reviews/DOCS_HUB_CONSOLIDATION_REVIEW.md`
- Recommendation: Keep / Merge / Deprecate for each duplicate
- Updated `DOCS_HUB_INDEX.md` if structure changes

**Acceptance:**
- ✅ All duplicates resolved
- ✅ Clear canonical structure
- ✅ No conflicting references

**Estimated Effort:** 1-2 sessions  
**Priority:** **SHOULD** (affects agent navigation)

---

### Task 3: Epic #91 Breakdown & Sprint Planning 🗓️

**Goal:** Convert Epic #91 (Paper Trading Test Infrastructure) into actionable sprint plan.

**Scope:**
- Review sub-issues #92-#96
- Add missing sub-issues (Event-Store Integration, CLI Tools Testing, Documentation Gaps)
- Assign to sprints (Week 1-4)
- Define sprint goals & acceptance

**Deliverables:**
- `knowledge/tasklists/M7_SPRINT_PLAN.md` (new folder created by Copilot)
- Sprint 1: Research (#92)
- Sprint 2: E2E Tests (#94)
- Sprint 3: Performance (#93)
- Sprint 4: Resilience + Monitoring (#95, #96)

**Acceptance:**
- ✅ 4 sprints defined
- ✅ Each sprint has clear goal + acceptance
- ✅ Dependencies mapped (Sprint 2 needs Sprint 1 artifacts)

**Estimated Effort:** 1 session  
**Priority:** **SHOULD** (enables M7 execution)

---

### Task 4: Session Handoff Protocol 📋

**Goal:** Formalize session handoff process between agents.

**Problem:**
- Sessions often end without clear next agent
- Knowledge transfer inconsistent
- Blockers not explicitly handed off

**Scope:**
- Define handoff checklist (status, decisions, blockers, next agent)
- Create handoff template
- Update `knowledge/SHARED.WORKING.MEMORY.md` usage rules

**Deliverables:**
- `governance/SESSION_HANDOFF_PROTOCOL.md` (Docs Hub)
- Template: `docs/templates/session-handoff-template.md`

**Acceptance:**
- ✅ Checklist covers all handoff scenarios
- ✅ Template usable by all agents
- ✅ Integrated with CDB_KNOWLEDGE_HUB.md workflow

**Estimated Effort:** 1 session  
**Priority:** **NICE** (quality of life)

---

## GEMINI — Audit & Review (Governance Compliance)

**Role:** Governance compliance, consistency checks, risk assessment  
**Strengths:** Policy alignment, structural validation, independent review

### Task 1: Docs Hub Governance Alignment Audit 🔍 **HIGH PRIORITY**

**Goal:** Full governance compliance check after Büro merge (16 new files).

**Scope:**
- Audit new files against `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md`
- Check for conflicts with existing policies
- Validate YAML frontmatter consistency
- Review new workflows (translate-issues.yml)

**Deliverables:**
- `knowledge/reviews/GOVERNANCE_ALIGNMENT_AUDIT_20251216.md`
- **MUST** findings: Blocking issues
- **SHOULD** findings: Recommended fixes
- **NICE** findings: Optional improvements

**Acceptance:**
- ✅ All new files audited
- ✅ Conflicts identified & categorized
- ✅ Recommendations actionable

**Estimated Effort:** 1-2 sessions  
**Priority:** **MUST** (governance integrity)

---

### Task 2: Security Roadmap Risk Assessment 🔒

**Goal:** Independent risk assessment of M8 Security Roadmap (10 issues #97-#106).

**Scope:**
- Review `SECURITY_ROADMAP.md`
- Assess completeness (OWASP Top 10 coverage)
- Identify missing security controls
- Evaluate timeline feasibility (Q2 2026)

**Deliverables:**
- `knowledge/reviews/M8_SECURITY_RISK_ASSESSMENT.md`
- Risk register (Likelihood × Impact)
- **MUST** items: Critical gaps
- **SHOULD** items: Recommended additions

**Acceptance:**
- ✅ All 10 security issues reviewed
- ✅ Gaps identified (e.g., DDoS protection, WAF, etc.)
- ✅ Timeline realistic or flagged

**Estimated Effort:** 1 session  
**Priority:** **MUST** (M8 gate-keeping)

---

### Task 3: Kanban Metrics Validation 📊

**Goal:** Validate Kanban metrics defined in `KANBAN_STRUCTURE.md`.

**Scope:**
- Review metrics: Lead Time, Cycle Time, Throughput, WIP Ratio
- Validate against industry best practices
- Check feasibility with GitHub tooling
- Recommend adjustments

**Deliverables:**
- `knowledge/reviews/KANBAN_METRICS_VALIDATION.md`
- **MUST**: Metric definitions clear & measurable
- **SHOULD**: Baseline targets realistic
- **NICE**: Automation recommendations

**Acceptance:**
- ✅ All 5 metrics validated
- ✅ Targets adjusted if needed
- ✅ Measurement approach documented

**Estimated Effort:** 0.5 session  
**Priority:** **SHOULD** (operational excellence)

---

### Task 4: Working Repo ↔ Docs Hub Consistency Check 🔗

**Goal:** Ensure Working Repo references to Docs Hub are correct.

**Scope:**
- Check all `.md` files in Working Repo for Docs Hub references
- Validate submodule config (if used)
- Check MILESTONES.md, SECURITY_ROADMAP.md, KANBAN_STRUCTURE.md references
- Identify outdated links

**Deliverables:**
- `knowledge/reviews/REPO_CROSS_REFERENCE_AUDIT.md`
- **MUST**: Broken references
- **SHOULD**: Outdated references
- **NICE**: Missing references

**Acceptance:**
- ✅ 0 broken links
- ✅ All canonical refs point to Docs Hub
- ✅ Working Repo has no Canon content

**Estimated Effort:** 1 session  
**Priority:** **SHOULD** (agent navigation)

---

## CODEX — Execution (Deterministic Implementation)

**Role:** Code implementation, technical execution, deterministic tasks  
**Strengths:** Surgical code changes, test implementation, script automation

### Task 1: Fix PR #87 — Dependabot Security Updates 🔧 **CRITICAL**

**Goal:** Resolve CI failures in PR #87 (requests + cryptography updates).

**Scope:**
- Analyze CI failures (Linting, Formatting, Type Checking, Tests, Secret Scanning)
- Fix code compatibility with new dependency APIs
- Ensure all CI checks pass

**Input Required:**
- PR #87 diff
- CI log analysis
- Dependency changelog (requests 2.31.0 → 2.32.4, cryptography 42.0.4 → 44.0.1)

**Deliverables:**
- Fixed code (commits to PR #87)
- CI green
- No breaking changes in core services

**Acceptance:**
- ✅ All 8 CI stages pass
- ✅ No type errors
- ✅ No security regressions
- ✅ Tests pass (Python 3.11 + 3.12)

**Estimated Effort:** 1-2 sessions  
**Priority:** **MUST** (security CVE unpatched)

---

### Task 2: Implement Bug Fix #43 — query_analytics.py Crash 🐛

**Goal:** Fix crash at line 222 in `query_analytics.py`.

**Scope:**
- Debug `services/cdb_analytics/query_analytics.py`
- Identify root cause (line 222)
- Implement fix
- Add test case to prevent regression

**Input Required:**
- Issue #43 description
- Reproduction steps
- Stack trace

**Deliverables:**
- Fixed `query_analytics.py`
- New test: `tests/unit/test_query_analytics_line222_fix.py`
- PR with fix

**Acceptance:**
- ✅ No crash at line 222
- ✅ Test covers failure scenario
- ✅ No breaking changes

**Estimated Effort:** 1 session  
**Priority:** **SHOULD** (M5 blocker)

---

### Task 3: Implement E2E Test Suite (M7) 🧪

**Goal:** Implement 5 P0 E2E test scenarios from Issue #94.

**Scope:**
- TC-P0-001: Happy Path (market_data → trade)
- TC-P0-002: Risk Blockierung (Position Limit)
- TC-P0-003: Daily Drawdown Stop
- TC-P0-004: Circuit Breaker Trigger
- TC-P0-005: Data Persistence Check

**Input Required:**
- Issue #94 acceptance criteria
- `docs/testing/PAPER_TRADING_TEST_REQUIREMENTS.md`
- Docker Compose stack running

**Deliverables:**
- `tests/e2e/test_paper_trading_p0.py`
- 5 test functions
- Deterministic (no flaky)
- pytest.ini configured for e2e marker

**Acceptance:**
- ✅ All 5 tests pass
- ✅ Tests run with `pytest -m e2e`
- ✅ No external dependencies (mocked)

**Estimated Effort:** 2-3 sessions  
**Priority:** **MUST** (M7 gate)

---

### Task 4: Migrate Deprecated .txt Prompts to .md (Docs Hub) 📄

**Goal:** Migrate 4 deprecated `.txt` prompt files to `.md` format.

**Scope:**
- Files:
  ```
  agents/prompts/PROMPT_CODEX.txt
  agents/prompts/Prompt CLAUDE - Durchsetzbarkeit.txt
  agents/prompts/Prompt Gemini - Konsistenz.txt
  agents/prompts/Prompt Gemini - Strukturierung.txt
  ```
- Convert to Markdown
- Add YAML frontmatter
- Move to `agents/prompts/*.md`
- Delete .txt after validation

**Deliverables:**
- 4 new `.md` files
- Deleted 4 `.txt` files
- Verified content complete

**Acceptance:**
- ✅ All content migrated
- ✅ Frontmatter consistent
- ✅ No information loss

**Estimated Effort:** 0.5 session  
**Priority:** **NICE** (housekeeping)

---

### Task 5: Implement Performance Baseline Tests (#93) ⚡

**Goal:** Measure baseline performance metrics for Paper Trading.

**Scope:**
- Latency tests (market_data → signal, signal → risk, order → execution)
- Throughput tests (events/sec, signals/sec, orders/sec)
- Document baselines

**Input Required:**
- Issue #93 metrics definitions
- Docker Compose stack running

**Deliverables:**
- `tests/performance/test_baseline_measurements.py`
- `docs/testing/PERFORMANCE_BASELINES.md` (results)
- CI integration (optional, manual run ok)

**Acceptance:**
- ✅ All metrics measured
- ✅ Baselines documented
- ✅ Tests reproducible

**Estimated Effort:** 1-2 sessions  
**Priority:** **SHOULD** (M7 requirement)

---

## COPILOT — GitHub Manager (Automation & Maintenance)

**Role:** GitHub hygiene, automation, CI/CD, issue management  
**Strengths:** Workflow automation, label management, reporting

### Task 1: Implement Branch Protection Rules ⚙️

**Goal:** Configure branch protection for `main` (Working Repo).

**Limitation:** Requires GitHub Pro or Public Repo (currently not available).

**Workaround Options:**
1. Manual PR review enforcement (document policy)
2. GitHub Actions workflow (block direct push)
3. Request repo upgrade

**Scope:**
- Document branch protection policy
- Implement enforcement via GitHub Actions
- Test with dummy PR

**Deliverables:**
- `.github/workflows/branch-protection.yml` (if possible)
- `docs/ci-cd/BRANCH_PROTECTION_POLICY.md`

**Acceptance:**
- ✅ Direct push to main blocked (or policy documented)
- ✅ CI required before merge

**Estimated Effort:** 1 session  
**Priority:** **NICE** (quality gate)

---

### Task 2: GitHub Projects Board Setup 📋

**Goal:** Create GitHub Project for visual Kanban board.

**Scope:**
- Create project "CDB - Master Roadmap"
- Configure 5 columns (Backlog, Ready, In Progress, Review, Done)
- Link to milestones M1-M9
- Configure automation (label → column move)

**Deliverables:**
- GitHub Project created
- All 17 issues assigned to board
- Automation rules active

**Acceptance:**
- ✅ Board reflects KANBAN_STRUCTURE.md
- ✅ Issues auto-move on label change
- ✅ Milestones visible

**Estimated Effort:** 1 session  
**Priority:** **SHOULD** (visual management)

---

### Task 3: Stale Bot Configuration Tuning 🤖

**Goal:** Tune Stale Bot config based on actual usage.

**Scope:**
- Review `.github/workflows/stale.yml`
- Adjust timings (90d too long?)
- Add exemptions (milestone:m7, milestone:m8)
- Test with dry-run

**Deliverables:**
- Updated `stale.yml`
- Dry-run report

**Acceptance:**
- ✅ Stale Bot runs without false positives
- ✅ Critical issues exempt
- ✅ PR/Issue close timings optimal

**Estimated Effort:** 0.5 session  
**Priority:** **NICE** (automation tuning)

---

### Task 4: CI/CD Pipeline Documentation 📚

**Goal:** Document complete CI/CD pipeline for new contributors.

**Scope:**
- Document `.github/workflows/ci.yaml` (8 stages)
- Document all checks (Ruff, Black, mypy, Pytest, Bandit, pip-audit, Gitleaks)
- Create troubleshooting guide
- Document local pre-commit hooks

**Deliverables:**
- `docs/ci-cd/CI_PIPELINE_GUIDE.md`
- `docs/ci-cd/TROUBLESHOOTING.md`

**Acceptance:**
- ✅ All 8 CI stages documented
- ✅ Common failures + fixes documented
- ✅ Local setup instructions clear

**Estimated Effort:** 1 session  
**Priority:** **SHOULD** (onboarding)

---

### Task 5: Dependabot Configuration Optimization 🔧

**Goal:** Optimize Dependabot config for smarter updates.

**Scope:**
- Review `.github/dependabot.yml` (if exists)
- Configure grouping (e.g., group minor updates)
- Configure auto-merge for low-risk updates
- Schedule (weekly vs daily)

**Deliverables:**
- `.github/dependabot.yml` (optimized)
- Documentation in `docs/ci-cd/DEPENDABOT_POLICY.md`

**Acceptance:**
- ✅ Updates grouped intelligently
- ✅ Auto-merge for patch updates
- ✅ No spam PRs

**Estimated Effort:** 0.5 session  
**Priority:** **NICE** (automation quality)

---

## Cross-Agent Coordination Tasks

### Task: Security Penetration Test Coordination 🔐

**Agents:** Claude (lead), Gemini (audit), Copilot (logistics)

**Goal:** Book and coordinate external Penetration Test (M8 Phase 4).

**Steps:**
1. **Claude:** Define scope (Web App + Infrastructure)
2. **Claude:** Create RFP (Request for Proposal)
3. **Copilot:** Research firms, collect quotes
4. **Claude:** Select firm, schedule test
5. **Gemini:** Review final report, prioritize findings

**Deliverables:**
- `docs/security/PENTEST_RFP.md`
- `docs/security/PENTEST_REPORT.md` (post-test)
- Issues created for all findings

**Estimated Effort:** 3-4 sessions (spread over weeks)  
**Priority:** **MUST** (M8 blocker)

---

### Task: M7 → M8 Gate Review 🚪

**Agents:** Claude (orchestrate), Gemini (audit), Codex (fix), Copilot (report)

**Goal:** Formal gate review before M8 execution.

**Criteria:**
- ✅ All M7 issues closed
- ✅ E2E tests passing
- ✅ Performance baselines met
- ✅ No P0/P1 bugs
- ✅ Documentation complete

**Process:**
1. **Copilot:** Generate gate report (issue status, metrics)
2. **Codex:** Fix any blocking issues
3. **Gemini:** Audit compliance (tests, docs, governance)
4. **Claude:** Decision (Pass / Conditional Pass / Fail)

**Deliverables:**
- `knowledge/reviews/M7_GATE_REVIEW.md`
- Go/No-Go decision

**Estimated Effort:** 2 sessions  
**Priority:** **MUST** (M7 → M8 transition)

---

## Task Priority Matrix

| Agent | Task | Priority | Effort | Blocker For |
|-------|------|----------|--------|-------------|
| **CLAUDE** | M7-M9 Roadmap Refinement | MUST | 2-3 | M7 execution |
| **CLAUDE** | Docs Hub Consolidation Review | SHOULD | 1-2 | Agent nav |
| **CLAUDE** | Epic #91 Sprint Planning | SHOULD | 1 | M7 execution |
| **CLAUDE** | Session Handoff Protocol | NICE | 1 | QoL |
| **GEMINI** | Docs Hub Governance Audit | MUST | 1-2 | Governance |
| **GEMINI** | M8 Security Risk Assessment | MUST | 1 | M8 gate |
| **GEMINI** | Kanban Metrics Validation | SHOULD | 0.5 | Ops |
| **GEMINI** | Repo Cross-Reference Audit | SHOULD | 1 | Navigation |
| **CODEX** | Fix PR #87 (Dependabot) | MUST | 1-2 | Security CVE |
| **CODEX** | Fix Bug #43 (query_analytics) | SHOULD | 1 | M5 |
| **CODEX** | E2E Test Suite (M7) | MUST | 2-3 | M7 gate |
| **CODEX** | Migrate .txt Prompts | NICE | 0.5 | Housekeeping |
| **CODEX** | Performance Baselines | SHOULD | 1-2 | M7 |
| **COPILOT** | Branch Protection | NICE | 1 | Quality gate |
| **COPILOT** | GitHub Projects Board | SHOULD | 1 | Visual mgmt |
| **COPILOT** | Stale Bot Tuning | NICE | 0.5 | Automation |
| **COPILOT** | CI/CD Documentation | SHOULD | 1 | Onboarding |
| **COPILOT** | Dependabot Optimization | NICE | 0.5 | Automation |

---

## Recommended Execution Order

### Phase 1: Critical Path (Week 1-2)
1. **CODEX:** Fix PR #87 (security CVE blocking)
2. **GEMINI:** Docs Hub Governance Audit (new files validation)
3. **CLAUDE:** M7-M9 Roadmap Refinement (execution planning)

### Phase 2: M7 Preparation (Week 3-4)
4. **CLAUDE:** Epic #91 Sprint Planning (M7 breakdown)
5. **CODEX:** E2E Test Suite implementation (M7 gate)
6. **GEMINI:** M8 Security Risk Assessment (early feedback)

### Phase 3: Quality & Automation (Week 5-6)
7. **COPILOT:** GitHub Projects Board (visual management)
8. **CODEX:** Fix Bug #43 (M5 blocker)
9. **CODEX:** Performance Baselines (M7 requirement)

### Phase 4: Documentation & Polish (Week 7-8)
10. **CLAUDE:** Docs Hub Consolidation Review
11. **COPILOT:** CI/CD Documentation
12. **GEMINI:** Repo Cross-Reference Audit

### Phase 5: Nice-to-Have (Ongoing)
13. **CODEX:** Migrate .txt prompts
14. **COPILOT:** Branch Protection
15. **COPILOT:** Stale Bot Tuning
16. **COPILOT:** Dependabot Optimization

---

## Success Metrics

**By Week 4:**
- ✅ PR #87 merged (security updates)
- ✅ M7 roadmap complete (sprint plan ready)
- ✅ E2E tests implemented (5 P0 scenarios)
- ✅ Docs Hub governance audit complete

**By Week 8:**
- ✅ All MUST tasks complete
- ✅ M7 ready for execution
- ✅ M8 security roadmap validated
- ✅ GitHub Projects board operational

**By M7 Gate:**
- ✅ All M7 tests passing
- ✅ Performance baselines met
- ✅ Documentation complete
- ✅ Gate review passed

---

## Notes

**Agent Coordination:**
- Claude orchestrates all tasks
- Gemini audits before/after critical changes
- Codex executes only on clear orders
- Copilot handles GitHub automation

**Handoffs:**
- Use `knowledge/SHARED.WORKING.MEMORY.md` for session notes
- Update `knowledge/CDB_KNOWLEDGE_HUB.md` for decisions
- Tag blockers explicitly for next agent

**Escalation:**
- User approval required for: governance changes, architecture decisions, external contracts
- Claude approval required for: scope changes, priority shifts, resource allocation

---

**Status:** 🎯 **READY FOR ASSIGNMENT**  
**Next Step:** Claude reviews & assigns tasks to agents

**Created:** 2025-12-16 @ 16:00 UTC  
**By:** Copilot (CDB_GITHUB_MANAGER)
