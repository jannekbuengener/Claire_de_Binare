# Issue Work Blocks - Praktische Abarbeitungseinheiten

**Erstellt:** 2025-12-29
**Zweck:** 67 Issues in praktische Arbeitsblöcke (2-5 Issues) für effiziente Abarbeitung
**Prinzip:** Thematisch verwandt, gleiche Scope, zusammen testbar

---

## Übersicht: 6 Stränge → 24 Arbeitsblöcke

| Strang | Thema | Blöcke | Issues |
|--------|-------|--------|--------|
| **roter_faden001** | Monitoring & Observability | 1 | 3 |
| **roter_faden002** | Testing & QA | 3 | 10 |
| **roter_faden003** | Governance & Automation | 5 | 15 |
| **roter_faden004** | Security & Compliance | 2 | 7 |
| **roter_faden005** | Strategy & ML | 5 | 16 |
| **roter_faden006** | Infrastructure & Features | 8 | 16 |
| **TOTAL** | | **24** | **67** |

---

# 🔴 ROTER_FADEN001: Monitoring & Observability (3 Issues)

## Block M1: Monitoring Foundation (3 Issues) ⚡ QUICK WIN
**Scope:** Metrics Export + Dashboards
**Effort:** 2-3 Tage
**Zusammenhang:** #341 ist Blocker für #210+#203

**Issues:**
- **#341** (P1 BUG): cdb_ws Metrics Export broken - Prometheus scraping fehlschlägt
- **#210**: Comprehensive Monitoring & Observability Infrastructure
- **#203**: Trading Performance Analytics Dashboard

**Warum zusammen?**
- #341 muss ZUERST (ohne Metrics keine Dashboards)
- #210 baut Monitoring-Infrastruktur auf
- #203 nutzt dann die funktionierende Infrastruktur

**Deliverable:** Vollständiges Monitoring-Setup + Dashboard

**Files berührt:**
- `services/ws/service.py` (Metrics Export fix)
- `infrastructure/monitoring/prometheus.yml` (Scrape Config)
- `infrastructure/monitoring/grafana/dashboards/` (neue Dashboards)

---

# 🟠 ROTER_FADEN002: Testing & QA (10 Issues → 3 Blöcke)

## Block T1: E2E Pipeline Fix (CRITICAL BLOCKER) ⚡ SOFORT
**Scope:** order_results Pipeline + Test Harness Bug
**Effort:** 1 Tag
**Zusammenhang:** Blockt ALLE E2E Tests

**Issues:**
- **#224** (P1): order_results not published (DRY_RUN + DB schema mismatch)
- **#229**: Test harness cursor scope bug (local workaround exists)

**Warum zusammen?**
- #224 blockt E2E Pipeline (keine OrderResults = keine Tests)
- #229 macht Tests flaky (cursor bug)
- Beide sind Quick Fixes, müssen VOR weiteren Tests behoben werden

**Deliverable:** Stabile E2E Test Infrastruktur

**Files berührt:**
- `services/execution/service.py` (order_results publishing fix)
- `tests/e2e/harness.py` (cursor scope fix)
- `infrastructure/docker-compose/dev.yml` (DRY_RUN Config)

---

## Block T2: Testnet Foundation (2 Issues)
**Scope:** Replay-fähige E2E Tests + Complete Test Infrastructure
**Effort:** 3-4 Tage
**Zusammenhang:** Basis für Production-ready Testing

**Issues:**
- **#319** (M5/M7): Testnet & Persistence - Replay-fähige E2E Tests
- **#149**: Complete Test Infrastructure Implementation

**Warum zusammen?**
- #319 schafft Replay-Fähigkeit (Testnet Setup)
- #149 vervollständigt Test-Infrastruktur (Coverage, Harness, CI Integration)
- Beide bauen Test-Foundation für M5/M7

**Deliverable:** Production-ready Test Framework

**Files berührt:**
- `tests/e2e/testnet/` (neue Testnet-Infrastruktur)
- `tests/conftest.py` (Fixtures für Replay)
- `.github/workflows/tests.yml` (CI Integration)

---

## Block T3: Security Testing + E2E Guard Cases (3 Issues)
**Scope:** Penetration Tests + Guard Test Cases
**Effort:** 5-7 Tage
**Zusammenhang:** Security + E2E Validation

**Issues:**
- **#99** (M8): Security: Penetration Test - Web Application
- **#100** (M8): Security: Penetration Test - Infrastructure
- **#230**: E2E Guard-Cases (TC-P0-003 drawdown + TC-P0-004 circuit breaker)

**Warum zusammen?**
- #99+#100 sind Penetration Tests (können parallel laufen)
- #230 testet Guards in E2E (Drawdown, Circuit Breaker)
- Alle sind M8 Milestone (Security + Safety)

**Deliverable:** Security Audit + Guard Test Suite

**Files berührt:**
- `docs/security/pentest_report_web.md` (neue Audit Reports)
- `docs/security/pentest_report_infra.md`
- `tests/e2e/test_guards.py` (neue Guard Tests)

---

## Block T4: Live Trading Validation (3 Issues) 📌 M9
**Scope:** Real MEXC Executor + 72-Hour Validation + Production Safety
**Effort:** 8-12 Tage
**Zusammenhang:** M9 Live Trading Pipeline

**Issues:**
- **#171** (M9 CRITICAL): Phase 1: Real MEXC Executor Implementation
- **#172** (M9 CRITICAL): Phase 2: Real 72-Hour Trading Validation System
- **#154**: Massive TODO/Unimplemented Code Audit - Production Risk

**Warum zusammen?**
- #171 implementiert Real Executor (kein Mock mehr)
- #172 validiert mit 72-Stunden-Testlauf
- #154 Audit muss VOR Live Trading (TODO-Cleanup)

**Deliverable:** Live Trading Ready (M9)

**Files berührt:**
- `services/execution/mexc_executor.py` (Real Executor statt Mock)
- `tests/live/validation_72h.py` (neue 72h Tests)
- Alle `*.py` mit TODOs (Audit + Cleanup)

---

## Block T5: Test Infrastructure Optimization (2 Issues)
**Scope:** Sophisticated Testing Infrastructure aktivieren
**Effort:** 2-3 Tage
**Zusammenhang:** Bestehende Infra besser nutzen

**Issues:**
- **#162**: Sophisticated Testing Infrastructure Exists But Unused
- **#149**: Complete Test Infrastructure Implementation (falls nicht in Block T2 erledigt)

**Warum zusammen?**
- #162 aktiviert vorhandene aber ungenutzte Test-Tools
- #149 vervollständigt Setup

**Deliverable:** Voll ausgelastete Test-Infrastruktur

**Files berührt:**
- `tests/` (aktivieren ungenutzter Fixtures/Utilities)
- `Makefile` (neue Test-Targets)

---

# 🟡 ROTER_FADEN003: Governance & Automation (15 Issues → 5 Blöcke)

## Block G1: Canonical Policy Enforcement (CRITICAL) ⚡ SOFORT
**Scope:** Agent Files + Canonical Violations beheben
**Effort:** 2-3 Tage
**Zusammenhang:** M1 Blocker, Governance Violations

**Issues:**
- **#165** (M1 CRITICAL): Critical Canonical Policy Violations - Agent Files in Wrong Repository
- **#166** (M1 HIGH): Systematic Canonical Policy Violations Throughout Working Repository
- **#167** (M1 HIGH): Missing Agent Roles Directory Structure - Canonical Location Incomplete

**Warum zusammen?**
- Alle 3 sind Governance-Violations (Canonical Policy)
- #165 ist CRITICAL (Agent Files falsch platziert)
- #166, #167 sind systematische Strukturprobleme
- Müssen zusammen behoben werden (komplette Restructure)

**Deliverable:** Canonical-konformes Repository

**Files berührt:**
- `.claude/agents/` (Agent Files verschieben)
- `knowledge/governance/` (Canonical Docs)
- Alle falsch platzierten Agent-Files (move zu richtigen Locations)

---

## Block G2: Code Reality Audit + Governance Enforcement (2 Issues)
**Scope:** Was existiert wirklich? + Governance Fix
**Effort:** 3-4 Tage
**Zusammenhang:** M1 Stabilization

**Issues:**
- **#157** (M1 CRITICAL): Code Reality Audit - What Actually Exists?
- **#158** (M1 CRITICAL): Governance Enforcement - Fix All Violations

**Warum zusammen?**
- #157 findet heraus, was wirklich implementiert ist
- #158 behebt dann alle gefundenen Violations
- Beide sind M1 Stabilization-Priority

**Deliverable:** Sauberes, Governance-konformes Codebase

**Files berührt:**
- Alle Services (Audit)
- `docs/governance/violations_report.md` (Audit Report)
- Fixes in allen verletzten Files

---

## Block G3: Issue Lifecycle Automation (3 Issues) ⚡ QUICK WIN
**Scope:** State Machine + PR Auto-Labeling + Pipeline Output Clarity
**Effort:** 2-3 Tage
**Zusammenhang:** Workflow Automation

**Issues:**
- **#337**: Issue Lifecycle State Machine - Labels & Transitions
- **#145**: Smart PR Auto-Labeling System
- **#335**: Pipeline Output Clarity - Idee ≠ Entscheidung

**Warum zusammen?**
- #337 schafft State Machine (Foundation)
- #145 auto-labelt PRs (nutzt Labels von #337)
- #335 klärt Pipeline-Output (bessere Ideen-Review)

**Deliverable:** Automatisierte Issue/PR Workflows

**Files berührt:**
- `.github/workflows/issue-lifecycle.yml` (State Machine)
- `.github/workflows/pr-auto-label.yml` (PR Labeling)

---

## Block G4: Review Automation + Devil's Advocate (2 Issues)
**Scope:** Auto-Assign Reviews + Skepticism Mode
**Effort:** 2-3 Tage
**Zusammenhang:** Qualitätssicherung durch Automation

**Issues:**
- **#336**: Pipeline-to-Review Bridge - Auto-Assign & SLA Tracking
- **#338**: Devil's Advocate Mode - Built-in Skepticism

**Warum zusammen?**
- #336 automatisiert Review-Assignments (SLA Tracking)
- #338 fügt Skepticism Layer hinzu (Devil's Advocate)
- Beide verbessern Review-Qualität

**Deliverable:** Intelligentes Review-System

**Files berührt:**
- `.github/workflows/review-bridge.yml` (Auto-Assign)

---

## Block G5: Governance Meta + Productivity Tools (4 Issues)
**Scope:** Governance Audit + Development Dashboard + Issue Tracking
**Effort:** 3-5 Tage
**Zusammenhang:** Meta-Governance + Developer Experience

**Issues:**
- **#328** (MUST): META: Governance Audit Q1 2026 - Repo-Hygiene & Compliance
- **#321**: Establish weekly Governance Review process
- **#169**: Issue Management & Progress Tracking Enhancement
- **#170**: Smart Development Dashboard & Workflow Automation

**Warum zusammen?**
- #328 ist Governance Meta-Audit (übergreifend)
- #321 etabliert Weekly Review (Prozess)
- #169, #170 sind Developer Productivity Tools
- Alle verbessern Governance + DX

**Deliverable:** Governance Framework + Productivity Suite

**Files berührt:**
- `docs/governance/audit_q1_2026.md` (Audit Report)
- `.github/workflows/weekly-governance-review.yml` (Weekly Review)
- `tools/issue-tracker-dashboard/` (neue Tools)

---

## Block G6: CI/CD Consistency (1 Issue) ⚡ QUICK WIN
**Scope:** GitHub Actions vs GitLab CI Cleanup
**Effort:** 1 Tag
**Zusammenhang:** CI/CD Hygiene

**Issues:**
- **#155** (MEDIUM): Dual CI/CD Pipeline Inconsistency - GitHub Actions vs GitLab CI

**Warum solo?**
- Standalone Issue (CI/CD Cleanup)
- Quick Win (1 Tag)

**Deliverable:** Single Source CI/CD (nur GitHub Actions)

**Files berührt:**
- `.gitlab-ci.yml` (deprecate/delete)
- `.github/workflows/` (konsolidieren)

---

# 🔴 ROTER_FADEN004: Security & Compliance (7 Issues → 2 Blöcke)

## Block S1: Production Safety (CRITICAL) ⚡ SOFORT
**Scope:** Mock Dependencies blocken Production + Operational Readiness
**Effort:** 3-5 Tage
**Zusammenhang:** M1 Production Blocker

**Issues:**
- **#164** (M1 CRITICAL): Production Safety Crisis - Mock Dependencies Block Real Trading
- **#159** (M1 CRITICAL): Operational Readiness - Production Confidence
- **#168** (MEDIUM): Production Deployment Readiness - Critical Infrastructure Gaps

**Warum zusammen?**
- #164 ist Production Blocker (Mock statt Real Executor)
- #159 ist Operational Readiness (Monitoring, Alerts, Runbooks)
- #168 sind Infra-Gaps (Missing Production Config)
- Alle 3 müssen für Production-Launch behoben sein

**Deliverable:** Production-Ready System

**Files berührt:**
- `services/execution/service.py` (Real Executor aktivieren)
- `infrastructure/production/` (Production Config)
- `docs/runbooks/` (Operational Runbooks)

---

## Block S2: Security Audit + Tresor + Release Process (4 Issues) 📌 M8/M9
**Scope:** Pentest + Tresor-Zone + Release 1.0 Process
**Effort:** 7-10 Tage
**Zusammenhang:** M8/M9 Security + Release

**Issues:**
- **#326** (M8 CRITICAL): Implement Tresor-Zone (Keys, Limits, Governance separation)
- **#325** (M8 CRITICAL): Penetration Testing & Compliance (M8)
- **#327** (M9 CRITICAL): Release 1.0 Process & Incident Response
- **#173** (M9 HIGH): Phase 3: Production Safety Systems for Real Money Trading

**Warum zusammen?**
- #326 muss ZUERST (Tresor-Zone für sichere Secrets)
- #325 ist Pentest (findet Vulnerabilities)
- #327 ist Release Process (inkl. Security Fixes von #325)
- #173 sind Production Safety Systems (Guards, Limits)
- Dependencies: #326 → #325 → #327 + #173

**Deliverable:** Security-Certified Release 1.0

**Files berührt:**
- `infrastructure/secrets/tresor/` (neue Tresor-Zone)
- `docs/security/pentest_m8_report.md` (Pentest Report)
- `docs/release/v1.0_release_process.md` (Release Runbook)
- `services/risk/production_guards.py` (Production Safety)

---

# 🟢 ROTER_FADEN005: Strategy & ML (16 Issues → 5 Blöcke)

## Block ML1: ML Foundation Phase 1-4 (5 Issues) 📌 M9 ML Epic
**Scope:** Kompletter ML Stack von Data Pipeline bis MLOps
**Effort:** 15-20 Tage (Großprojekt)
**Zusammenhang:** epic:ml-foundation (Sequential Pipeline)

**Issues:**
- **#192** (HIGH): ML Phase 1: Enhanced Data Pipeline & Feature Engineering
- **#193** (HIGH): ML Phase 2: Model Development Infrastructure & Training Pipeline
- **#194** (HIGH): ML Phase 3: Advanced ML Strategies & Multi-Asset Intelligence
- **#195** (M9 HIGH): ML Phase 4: Production MLOps & Intelligent Trading Orchestration
- **#196** (HIGH): IMMEDIATE: Upgrade Python Dependencies for ML Foundation

**Warum zusammen?**
- Sequential Pipeline: #196 (Deps) → #192 (Data) → #193 (Training) → #194 (Strategies) → #195 (MLOps)
- Alle Teil des epic:ml-foundation
- #196 MUSS ZUERST (Python Deps upgraden)

**Deliverable:** Production ML Trading System

**Files berührt:**
- `requirements.txt` (Python Deps upgrade #196)
- `services/data/feature_engineering.py` (Phase 1)
- `ml/training_pipeline/` (Phase 2)
- `ml/strategies/` (Phase 3)
- `ml/mlops/` (Phase 4)

---

## Block ML2: ML Research & Workspace (3 Issues)
**Scope:** Research Topics + Jupyter Integration + Master Roadmap
**Effort:** 3-5 Tage
**Zusammenhang:** ML Foundation Support

**Issues:**
- **#197** (HIGH DOCS): ML FOUNDATION MASTER ROADMAP
- **#198** (HIGH): ML Development Workspace & Jupyter Integration
- **#199** (HIGH): ML Deep Research Topics für Trading AI

**Warum zusammen?**
- #197 ist Meta-Roadmap (koordiniert ML-Arbeit)
- #198 schafft Workspace (Jupyter für Research)
- #199 sind Research Topics (nutzen Workspace #198)

**Deliverable:** ML Research Environment + Roadmap

**Files berührt:**
- `docs/ml/ML_FOUNDATION_MASTER_ROADMAP.md`
- `ml/notebooks/` (Jupyter Setup)
- `docs/ml/research_topics.md`

---

## Block ML3: Strategy Decision + Minimum Viable Engine (2 Issues) 📌 M8
**Scope:** Control Theory Decision + MVP Decision Engine
**Effort:** 5-7 Tage
**Zusammenhang:** M8 Strategy Foundation

**Issues:**
- **#332** (M8 MUST DECISION): Is advanced control theory needed for M8/M9?
- **#333** (M8 MUST SPEC): Minimum Viable Decision Engine for CDB v1.0

**Warum zusammen?**
- #332 ist Decision (BSDE/HJB vs. simpler approach)
- #333 implementiert dann MVP basierend auf #332 Decision
- Dependency: #332 → #333

**Deliverable:** Decision Engine MVP (v1.0)

**Files berührt:**
- `docs/decisions/control_theory_m8.md` (Decision #332)
- `services/decision_engine/mvp.py` (MVP Implementation #333)

---

## Block ML4: Advanced Strategy Features (4 Issues)
**Scope:** Adaptive Selector + Backtesting + Multi-Asset + E1-E4 Integration
**Effort:** 8-12 Tage
**Zusammenhang:** Strategy Layer on top of Decision Engine

**Issues:**
- **#205** (M7 HIGH): Adaptive Strategy Selector - Market Regime Detection
- **#207** (M5/M7 HIGH): Backtesting Framework - Strategy Validation
- **#211** (M3/M5/M7): Multi-Asset Portfolio Management
- **#215**: E1-E4 Integration (Regime & Allocation Services)

**Warum zusammen?**
- #205 ist Strategy Selector (wählt Strategie basierend auf Regime)
- #207 ist Backtesting (validiert Strategies)
- #211 ist Portfolio Manager (Multi-Asset Allocation)
- #215 integriert E1-E4 Services (Regime, Allocation)
- Alle bauen auf Decision Engine auf (#333)

**Deliverable:** Advanced Strategy Suite

**Files berührt:**
- `services/strategy/adaptive_selector.py`
- `tools/backtesting/framework.py`
- `services/portfolio/multi_asset.py`
- `services/regime/`, `services/allocation/` (E1-E4)

---

## Block ML5: AI Market Prediction + Meta Research (3 Issues)
**Scope:** AI Prediction Engine + ML Research Meta
**Effort:** 5-8 Tage
**Zusammenhang:** Advanced ML Features

**Issues:**
- **#191**: AI-Powered Market Prediction Engine
- **#200** (HIGH DOCS): ML Deep Research Topics - Systematische Aufarbeitung
- **#147** (HIGH): Intelligent Deep Research Synthesis System

**Warum zusammen?**
- #191 ist AI Prediction (Feature)
- #200 ist ML Research Meta (koordiniert Research)
- #147 ist Deep Research Synthesis (AI-Powered Research Tool)

**Deliverable:** AI-Powered Prediction + Research Tools

**Files berührt:**
- `ml/prediction/ai_engine.py`
- `docs/ml/deep_research_topics.md`
- `tools/research/synthesis_system.py`

---

# 🔵 ROTER_FADEN006: Infrastructure & Features (16 Issues → 8 Blöcke)

## Block I1: Stabilization Master Program (CRITICAL) ⚡ SOFORT
**Scope:** System Stabilization + Service Audit + Environment Setup
**Effort:** 5-7 Tage
**Zusammenhang:** M1 Foundation

**Issues:**
- **#160** (M1 CRITICAL): STABILIZATION-MASTER - Fundamental System Stabilization Program
- **#156** (M1 CRITICAL): Infrastructure Emergency - System Broken
- **#148** (CRITICAL BUG): Service Implementation Status Audit & Completion
- **#163** (M1 HIGH BUG): Complete Environment Setup Breakdown - Developer Onboarding Impossible

**Warum zusammen?**
- #160 ist Meta-Program (koordiniert Stabilization)
- #156, #148, #163 sind konkrete Stabilization Tasks
- Alle M1 Foundation

**Deliverable:** Stable System + Onboarding-fähig

**Files berührt:**
- Alle Services (Audit + Fixes)
- `docs/onboarding/setup_guide.md`
- `infrastructure/docker-compose/`

---

## Block I2: Signal Service Feature (1 Issue) ⚡ QUICK WIN
**Scope:** Stateful pct_change Calculation
**Effort:** 1-2 Tage
**Zusammenhang:** Signal Service Enhancement

**Issues:**
- **#345**: Implement stateful pct_change calculation

**Warum solo?**
- Standalone Feature (Signal Service)
- Quick Win (1-2 Tage)

**Deliverable:** pct_change Stateful Calculation

**Files berührt:**
- `services/signal/price_buffer.py` (neu)
- `services/signal/service.py` (Integration)

---

## Block I3: Database & Schema (1 Issue)
**Scope:** Database Migrations & Optimization
**Effort:** 2-3 Tage
**Zusammenhang:** Database Layer

**Issues:**
- **#206** (M1/M5/M9 HIGH): Database Schema Migrations & Optimization

**Warum solo?**
- Standalone Feature (Database)
- Touches ALL services (schema changes)

**Deliverable:** Production-ready Schema Management

**Files berührt:**
- `infrastructure/database/migrations/` (Alembic Migrations)
- `services/*/models.py` (Schema Updates)

---

## Block I4: Event-Driven Backbone Migration (2 Issues) 📌 MAJOR REFACTOR
**Scope:** Redis → JetStream/Kafka + K8s-Readiness
**Effort:** 10-15 Tage (MAJOR)
**Zusammenhang:** Scalability Infrastructure

**Issues:**
- **#323**: Event-Driven Backbone - Migrate to JetStream/Kafka
- **#322**: Kubernetes-Readiness & GitOps (FluxCD)

**Warum zusammen?**
- #323 ist Event Bus Migration (Redis → JetStream/Kafka)
- #322 macht K8s-ready (braucht Event Bus #323)
- Dependency: #323 → #322

**Deliverable:** Production-Scale Infrastructure

**Files berührt:**
- Alle Services (Event Bus Migration)
- `infrastructure/k8s/` (Helm Charts, FluxCD)

---

## Block I5: Cross-Repo Consistency + README i18n (2 Issues) ⚡ QUICK WIN
**Scope:** Repo Hygiene + Internationalization
**Effort:** 1-2 Tage
**Zusammenhang:** Documentation & Consistency

**Issues:**
- **#151** (MEDIUM): Cross-Repo Consistency Gap Analysis & Synchronization
- **#320** (NICE DOCS): Internationalize README (English summary)

**Warum zusammen?**
- #151 analysiert Cross-Repo Drift
- #320 macht README international (English Summary)
- Beide sind Docs/Hygiene

**Deliverable:** Konsistente Repos + International README

**Files berührt:**
- `README.md` (English Summary)
- `docs/cross_repo_analysis.md` (Consistency Report)

---

## Block I6: Branch Cleanup (1 Issue) ⚡ QUICK WIN
**Scope:** 82 unmerged branches triagieren
**Effort:** 1 Tag
**Zusammenhang:** Repository Hygiene

**Issues:**
- **#330** (MEDIUM CLEANUP): Triage 82 unmerged branches

**Warum solo?**
- Standalone Cleanup Task
- Quick Win (1 Tag)

**Deliverable:** Sauberer Branch-Tree

**Files berührt:**
- Git Branches (delete/merge/document)

---

## Block I7: Advanced Infrastructure Features (2 Issues)
**Scope:** Ultra-Low Latency Engine + Advanced Order Types
**Effort:** 8-12 Tage
**Zusammenhang:** Performance & Features

**Issues:**
- **#189**: Ultra-Low Latency Trading Engine
- **#190**: Advanced Order Types Implementation

**Warum zusammen?**
- #189 ist Latency Optimization
- #190 sind Advanced Order Types (nutzen Low-Latency Engine)
- Beide sind Performance-Features

**Deliverable:** High-Performance Trading Engine

**Files berührt:**
- `services/execution/low_latency_engine.py`
- `services/execution/order_types.py`

---

## Block I8: BSDE/HJB Research (1 Issue) 📌 DEFERRED M10+
**Scope:** Advanced Control Theory Research
**Effort:** N/A (Deferred)
**Zusammenhang:** M10+ Research

**Issues:**
- **#334** (NICE M10+): BSDE/HJB Framework Selection (Deferred M10+)

**Warum solo?**
- Deferred to M10+
- Not in v1.0 Scope

**Deliverable:** Research Report (M10+)

**Files berührt:**
- `docs/research/bsde_hjb_selection.md` (M10+)

---

# 📊 Summary: 24 Arbeitsblöcke

## Nach Effort sortiert (Quick Wins → Große Projekte)

### ⚡ QUICK WINS (< 2 Tage)
1. **Block T1** (Testing): E2E Pipeline Fix → 1 Tag (CRITICAL!)
2. **Block G6** (Governance): CI/CD Consistency → 1 Tag
3. **Block I2** (Infrastructure): pct_change Feature → 1-2 Tage
4. **Block I5** (Infrastructure): Cross-Repo + README → 1-2 Tage
5. **Block I6** (Infrastructure): Branch Cleanup → 1 Tag

**Total Quick Wins:** 5 Blöcke, 5-7 Tage

---

### 🟡 MEDIUM BLOCKS (2-5 Tage)
6. **Block M1** (Monitoring): Monitoring Foundation → 2-3 Tage
7. **Block G1** (Governance): Canonical Policy Fix → 2-3 Tage
8. **Block G2** (Governance): Code Reality Audit → 3-4 Tage
9. **Block G3** (Governance): Issue Lifecycle Automation → 2-3 Tage
10. **Block G4** (Governance): Review Automation → 2-3 Tage
11. **Block T2** (Testing): Testnet Foundation → 3-4 Tage
12. **Block S1** (Security): Production Safety → 3-5 Tage
13. **Block I3** (Infrastructure): Database Migrations → 2-3 Tage
14. **Block ML2** (Strategy): ML Research + Workspace → 3-5 Tage

**Total Medium:** 9 Blöcke, 23-34 Tage

---

### 🔴 LARGE BLOCKS (5-15 Tage)
15. **Block G5** (Governance): Governance Meta → 3-5 Tage
16. **Block T3** (Testing): Security Testing + Guards → 5-7 Tage
17. **Block I1** (Infrastructure): Stabilization Master → 5-7 Tage
18. **Block ML3** (Strategy): Decision Engine MVP → 5-7 Tage
19. **Block ML5** (Strategy): AI Prediction + Research → 5-8 Tage
20. **Block S2** (Security): Security Audit + Tresor → 7-10 Tage
21. **Block ML4** (Strategy): Advanced Strategy Features → 8-12 Tage
22. **Block I7** (Infrastructure): Low Latency + Order Types → 8-12 Tage
23. **Block T4** (Testing): Live Trading Validation → 8-12 Tage

**Total Large:** 9 Blöcke, 54-80 Tage

---

### 🟣 MAJOR PROJECTS (15+ Tage)
24. **Block I4** (Infrastructure): Event Bus + K8s → 10-15 Tage
25. **Block ML1** (Strategy): ML Foundation Phase 1-4 → 15-20 Tage

**Total Major:** 2 Blöcke, 25-35 Tage

---

## Empfohlene Execution Order (nach Dependencies)

### 🚨 PHASE 1: CRITICAL BLOCKERS (Woche 1-2)
**Parallel Start:**
1. **Block T1** (E2E Pipeline Fix) → 1 Tag ⚡ SOFORT
2. **Block M1** (Monitoring Foundation) → 2-3 Tage
3. **Block S1** (Production Safety) → 3-5 Tage
4. **Block G1** (Canonical Policy) → 2-3 Tage

**Outcome:** System funktionsfähig, E2E testbar, Production-ready

---

### 🏗️ PHASE 2: FOUNDATION (Woche 2-4)
**Sequential:**
5. **Block I1** (Stabilization Master) → 5-7 Tage [NACH Phase 1]
6. **Block G2** (Code Reality Audit) → 3-4 Tage [NACH I1]
7. **Block T2** (Testnet Foundation) → 3-4 Tage [NACH T1]

**Parallel:**
8. **Block I2** (pct_change) → 1-2 Tage
9. **Block G6** (CI/CD) → 1 Tag
10. **Block I6** (Branch Cleanup) → 1 Tag

**Outcome:** Stabile Foundation, Test-Infrastructure

---

### 🔐 PHASE 3: SECURITY & COMPLIANCE (Woche 4-6)
**Sequential:**
11. **Block S2** (Security Audit + Tresor) → 7-10 Tage [NACH Phase 2]
12. **Block T3** (Security Testing) → 5-7 Tage [NACH S2]

**Outcome:** Security-Certified

---

### ⚙️ PHASE 4: AUTOMATION & GOVERNANCE (Woche 5-8)
**Parallel:**
13. **Block G3** (Issue Lifecycle) → 2-3 Tage
14. **Block G4** (Review Automation) → 2-3 Tage
15. **Block G5** (Governance Meta) → 3-5 Tage

**Outcome:** Automatisierte Workflows

---

### 🧠 PHASE 5: STRATEGY & ML (Woche 6-12)
**Sequential:**
16. **Block ML3** (Decision Engine MVP) → 5-7 Tage
17. **Block ML1** (ML Foundation 1-4) → 15-20 Tage [NACH ML3]
18. **Block ML4** (Advanced Strategies) → 8-12 Tage [NACH ML1]

**Parallel:**
19. **Block ML2** (ML Research) → 3-5 Tage
20. **Block ML5** (AI Prediction) → 5-8 Tage

**Outcome:** ML Trading System

---

### 🚀 PHASE 6: INFRASTRUCTURE & FEATURES (Woche 8-14)
**Parallel:**
21. **Block I3** (Database) → 2-3 Tage
22. **Block I5** (Cross-Repo + README) → 1-2 Tage
23. **Block I7** (Low Latency) → 8-12 Tage

**Sequential:**
24. **Block I4** (Event Bus + K8s) → 10-15 Tage [MAJOR REFACTOR]

**Outcome:** Production-Scale Infrastructure

---

### 🎯 PHASE 7: LIVE TRADING (Woche 12-16)
**Sequential:**
25. **Block T4** (Live Trading Validation) → 8-12 Tage [FINAL]

**Outcome:** Live Trading Ready (M9)

---

## Kritischer Pfad (MUST-Sequence)

```
Block T1 (E2E Fix) → 1 Tag ⚡ START HERE
  ↓
Block M1 (Monitoring) → 2-3 Tage
  ↓
Block S1 (Production Safety) → 3-5 Tage
  ↓
Block I1 (Stabilization) → 5-7 Tage
  ↓
Block G2 (Code Audit) → 3-4 Tage
  ↓
Block T2 (Testnet) → 3-4 Tage
  ↓
Block S2 (Security Audit) → 7-10 Tage
  ↓
Block T3 (Security Testing) → 5-7 Tage
  ↓
Block ML3 (Decision Engine) → 5-7 Tage
  ↓
Block ML1 (ML Foundation) → 15-20 Tage
  ↓
Block T4 (Live Trading) → 8-12 Tage
  ↓
PRODUCTION LAUNCH ✅
```

**Kritischer Pfad Total:** ~65-85 Tage (13-17 Wochen)

---

## Nächste Schritte

1. **User-Approval:** Jannek entscheidet Execution Order
2. **Block-Assignment:** Pro Block einen Owner (Claude/Codex/Gemini)
3. **Tracking:** GitHub Project Board mit 24 Spalten (1 pro Block)
4. **Start:** Block T1 (E2E Pipeline Fix) → 1 Tag ⚡

---

**Erstellt von:** Claude
**Status:** READY FOR EXECUTION
**Next:** User wählt ersten Block zum Starten
