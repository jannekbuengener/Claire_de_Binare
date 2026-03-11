# Issue Bundling Analysis - 30 Issues Systematisch Gebündelt

**Erstellt:** 2025-12-29
**Scope:** 30 offene Issues (#200-#345)
**Zweck:** Thematische Bündelung für koordinierte PR-Strategie
**Status:** KEINE IMPLEMENTATION - NUR ORGANISATION

---

## Executive Summary

**30 Issues analysiert** → **10 thematische Bündel** → **6 PR-Stränge**

**Kritische Dependencies:**
- Monitoring (#341) blockt Analytics (#203, #211, #205)
- Governance (#328, #337) blockt Automation (#336, #338)
- Testing Framework (#319, #229) blockt E2E Tests (#230)
- Security (#325, #326) blockt Production Readiness (#327)

**Empfohlene Execution Order:**
1. **Foundation** (Testing + Monitoring) → unblocks everything
2. **Governance** (Automation + Process) → enables coordination
3. **Security** (Pentesting + Tresor) → production readiness
4. **Features** (Signal, Strategy, ML) → value delivery
5. **Infrastructure** (K8s, Event Bus) → scalability
6. **Docs** (README, Governance) → operational readiness

---

## Thematische Bündel (10 Cluster)

### 🔴 BÜNDEL 1: MONITORING & OBSERVABILITY (CRITICAL - BLOCKER)

**Issues:**
- #341 (P1): fix(monitoring) - cdb_ws Metrics Export broken
- #210: CODEX Comprehensive Monitoring & Observability Infrastructure
- #203: GEMINI Trading Performance Analytics Dashboard
- #211: GEMINI Multi-Asset Portfolio Management (Monitoring Aspect)

**Zusammenhang:**
- #341 ist BLOCKER → ohne cdb_ws Metrics keine vollständigen Dashboards
- #210 ist Foundation → etabliert Monitoring-Pattern für alle Services
- #203, #211 sind Consumers → brauchen funktionierende Metrics

**Dependencies:**
- #341 blockt #203, #211 (ohne Metrics keine Analytics)
- #210 ist parallel zu #341 (Infrastructure Setup)

**PR-Strategie:**
```
PR #1: Monitoring Foundation
  - Fix #341 (cdb_ws Metrics Export)
  - Implement #210 (Observability Infrastructure)

PR #2: Analytics Dashboards (AFTER PR #1 merged)
  - #203 (Performance Analytics)
  - #211 (Portfolio Monitoring)
```

**Estimated Effort:** 3-5 Tage (PR #1: 2 Tage, PR #2: 2-3 Tage)
**Priority:** CRITICAL (P0) - blockt alles andere

---

### 🟠 BÜNDEL 2: TESTING & QA INFRASTRUCTURE (CRITICAL - FOUNDATION)

**Issues:**
- #319 (M5/M7): Testnet & Persistence - Replay-fähige E2E Tests
- #229: Test harness cursor scope bug (local workaround exists)
- #230: E2E Guard-Cases (TC-P0-003 drawdown + TC-P0-004 circuit breaker)
- #224: P1 order_results not published (DRY_RUN + DB schema mismatch)

**Zusammenhang:**
- #319 ist Foundation → ohne replay-fähige Tests kein deterministisches Testing
- #229 ist Bug-Fix → muss VOR #230 behoben werden (sonst flaky tests)
- #230 ist Feature → braucht stabile Test Harness (#229)
- #224 ist Blocker für E2E → order_results Pipeline muss funktionieren

**Dependencies:**
```
#224 (order_results) → MUSS ZUERST (blockt alle E2E Tests)
  ↓
#229 (cursor bug) → FIX BEFORE E2E
  ↓
#319 (Testnet Foundation) → enables replay
  ↓
#230 (E2E Guard Cases) → runs on stable harness
```

**PR-Strategie:**
```
PR #3: E2E Pipeline Fix (HIGHEST PRIORITY)
  - Fix #224 (order_results publishing)
  - Fix #229 (cursor scope bug)

PR #4: Testnet Foundation (AFTER PR #3)
  - Implement #319 (Replay-fähige E2E Tests)

PR #5: Guard Test Cases (AFTER PR #4)
  - Implement #230 (Drawdown + Circuit Breaker Tests)
```

**Estimated Effort:** 4-6 Tage (PR #3: 1 Tag, PR #4: 2-3 Tage, PR #5: 1-2 Tage)
**Priority:** CRITICAL (P0) - Foundation für alle Tests

---

### 🟡 BÜNDEL 3: AUTOMATION & GOVERNANCE (HIGH PRIORITY)

**Issues:**
- #337: [AUTOMATION] Issue Lifecycle State Machine
- #328: 🔍 META Governance Audit Q1 2026
- #321: Establish weekly Governance Review process

**Zusammenhang:**
- #337 (State Machine) ist Foundation → ohne States keine Automation
- #336 (Review Bridge) braucht #337 (states für assignment)
- #335 (Output Clarity) ist parallel → verbessert Pipeline-Verständnis
- #338 (Devil's Advocate) braucht #336 (review process)
- #328 (Governance Audit) ist übergeordnet → prüft alles
- #321 (Weekly Review) ist Prozess → nutzt #337 states

**Dependencies:**
```
#337 (State Machine) → Foundation
  ↓
#336 (Review Bridge) + #335 (Output Clarity) → parallel
  ↓
#338 (Devil's Advocate) + #321 (Weekly Review) → nutzen Infrastruktur
  ↓
#328 (Governance Audit) → prüft alles
```

**PR-Strategie:**
```
PR #6: Governance Foundation (Phase 1)
  - Implement #337 (State Machine Labels + Transitions)
  - Implement #335 (Pipeline Output Clarity)

PR #7: Automation Layer (Phase 2, AFTER PR #6)
  - Implement #336 (Auto-Assign + SLA Tracking)
  - Implement #321 (Weekly Review Process)

PR #8: Advanced Pipeline Features (Phase 3, AFTER PR #7)
  - Implement #338 (Devil's Advocate Mode)

PR #9: Governance Audit (AFTER all others)
  - Execute #328 (Audit Q1 2026)
```

**Estimated Effort:** 5-7 Tage (PR #6: 1 Tag, PR #7: 2 Tage, PR #8: 2 Tage, PR #9: 2-3 Tage)
**Priority:** HIGH (P1) - enables coordinated work

---

### 🔴 BÜNDEL 4: SECURITY & COMPLIANCE (CRITICAL - PRODUCTION BLOCKER)

**Issues:**
- #325 (M8): Penetration Testing & Compliance
- #326: Tresor-Zone (Keys, Limits, Governance separated)
- #327 (M9): Release 1.0 Process & Incident Response

**Zusammenhang:**
- #326 (Tresor) MUSS VOR #325 (Pentest) → sonst keine sichere Key-Verwaltung
- #325 (Pentest) findet Vulnerabilities → fixes gehen in #327 (Release Process)
- #327 (Release) braucht #325 (Security Sign-Off) für Production

**Dependencies:**
```
#326 (Tresor-Zone) → Foundation
  ↓
#325 (Pentest) → identifies issues
  ↓
#327 (Release 1.0) → includes security fixes
```

**PR-Strategie:**
```
PR #10: Tresor-Zone (FIRST)
  - Implement #326 (Secrets Separation + Key Management)

PR #11: Security Audit (AFTER PR #10, NO CODE PR - AUDIT ONLY)
  - Execute #325 (Penetration Testing)
  - Document findings
  - Create follow-up issues for fixes

PR #12: Release 1.0 Preparation (AFTER fixes from #325)
  - Implement #327 (Release Process + Incident Response)
  - Verify all security findings resolved
```

**Estimated Effort:** 7-10 Tage (PR #10: 2-3 Tage, PR #11: 3-5 Tage, PR #12: 2 Tage)
**Priority:** CRITICAL (P0) - blockt Production Launch

---

### 🟢 BÜNDEL 5: SIGNAL SERVICE & DATA PIPELINE (FEATURE)

**Issues:**
- #345: feat(signal) - Implement stateful pct_change calculation

**Zusammenhang:**
- Standalone Feature, keine Dependencies
- Ergänzt Issue #342 (MEXC protobuf) + Commit c06ae5c (pct_change optional)

**Dependencies:**
- None (unblocked)

**PR-Strategie:**
```
PR #13: Stateful pct_change
  - Implement #345 (Price History Tracker + Calculation)
  - Tests: Unit + Integration + E2E
```

**Estimated Effort:** 1-2 Tage
**Priority:** MEDIUM (P2) - Pipeline stable, Signals currently not generated

---

### 🟢 BÜNDEL 6: STRATEGY & ML RESEARCH (FEATURE - M8/M9)

**Issues:**
- #333 (M8): [SPEC] Minimum Viable Decision Engine for CDB v1.0
- #332: [DECISION] Is advanced control theory needed for M8/M9?
- #334 (M10+): [RESEARCH] BSDE/HJB Framework Selection (DEFERRED)
- #215: E1-E4 Integration (Regime & Allocation Services)
- #205: GEMINI Adaptive Strategy Selector
- #207: GEMINI Backtesting Framework
- #200: ML Deep Research Topics

**Zusammenhang:**
- #332 (Decision) MUSS ZUERST → entscheidet Scope für M8/M9
- #333 (Minimum Viable) folgt aus #332 → implementiert gewählten Ansatz
- #334 (BSDE/HJB) ist DEFERRED M10+ → nicht in v1.0 Scope
- #215 (E1-E4) braucht #333 (Decision Engine als Basis)
- #205 (Strategy Selector) + #207 (Backtesting) sind Features on top of #333
- #200 (ML Research) ist Meta → koordiniert alle ML Topics

**Dependencies:**
```
#332 (Decision: Control Theory?) → BLOCKER
  ↓
#333 (Minimum Viable Engine) → Implementation
  ↓
#215 (E1-E4 Integration) + #205 (Strategy Selector) + #207 (Backtesting) → parallel features
  ↓
#200 (ML Research Coordination) → Meta-Issue

#334 (BSDE/HJB) → DEFERRED M10+, nicht in diesem Sprint
```

**PR-Strategie:**
```
PR #14: Strategy Decision (NO CODE - DECISION ONLY)
  - Resolve #332 (Advanced Control Theory Decision)
  - Document decision rationale

PR #15: Minimum Viable Decision Engine (AFTER PR #14)
  - Implement #333 (MVP Engine based on #332 decision)

PR #16: Strategy Features (AFTER PR #15, can be parallel PRs)
  - #215 (E1-E4 Integration)
  - #205 (Strategy Selector)
  - #207 (Backtesting Framework)

PR #17: ML Research Coordination (AFTER all others)
  - Close #200 (Meta-Issue)

DEFERRED: #334 → M10+ Roadmap
```

**Estimated Effort:** 10-15 Tage (PR #14: 1 Tag, PR #15: 4-5 Tage, PR #16: 5-7 Tage, PR #17: 1 Tag)
**Priority:** MEDIUM (P2) - M8/M9 Milestone, not v1.0 blocker

---

### 🔵 BÜNDEL 7: INFRASTRUCTURE & SCALABILITY (NICE TO HAVE)

**Issues:**
- #323: Event-Driven Backbone (JetStream/Kafka)
- #322: Kubernetes-Readiness & GitOps (FluxCD)
- #330: Triage 82 unmerged branches (Cleanup)

**Zusammenhang:**
- #323 (Event Bus) ist Foundation → ersetzt Redis Pub/Sub
- #322 (K8s) braucht #323 (Event Bus als Production-Ready Backbone)
- #330 (Branch Cleanup) ist unabhängig → Hygiene

**Dependencies:**
```
#323 (Event-Driven Backbone) → Foundation
  ↓
#322 (K8s-Readiness) → nutzt Event Bus

#330 (Branch Cleanup) → parallel, unabhängig
```

**PR-Strategie:**
```
PR #18: Event-Driven Backbone (BIG CHANGE)
  - Implement #323 (JetStream/Kafka Migration)
  - Migrate all Pub/Sub to Event Bus

PR #19: K8s Readiness (AFTER PR #18)
  - Implement #322 (Helm Charts + FluxCD)

PR #20: Branch Cleanup (parallel, independent)
  - Execute #330 (Triage 82 branches)
  - Delete stale branches
  - Document kept branches
```

**Estimated Effort:** 8-12 Tage (PR #18: 5-7 Tage, PR #19: 3-4 Tage, PR #20: 1 Tag)
**Priority:** LOW (P3) - Nice to have, not v1.0 blocker

---

### 🔵 BÜNDEL 8: DATABASE & SCHEMA (FEATURE)

**Issues:**
- #206: CODEX Database Schema Migrations & Optimization

**Zusammenhang:**
- Standalone Feature
- Relates to #224 (order_results schema mismatch) → should be fixed together

**Dependencies:**
- Optional: Combine with #224 (schema fix)

**PR-Strategie:**
```
PR #21: Database Schema Management
  - Implement #206 (Migration Framework + Optimization)
  - Include fix for #224 (order_results schema) if not already done
```

**Estimated Effort:** 2-3 Tage
**Priority:** MEDIUM (P2) - Schema consistency important

---

### 🔵 BÜNDEL 9: DOCS & INTERNATIONALIZATION (NICE TO HAVE)

**Issues:**
- #320: Internationalize README (English summary)

**Zusammenhang:**
- Standalone Task
- No Dependencies

**PR-Strategie:**
```
PR #22: Internationalize README
  - Add English summary to README.md
  - Keep German as primary language
```

**Estimated Effort:** 0.5 Tage
**Priority:** LOW (P3) - Nice to have

---

### 🟣 BÜNDEL 10: PORTFOLIO MANAGEMENT (FEATURE - M8/M9)

**Issues:**
- #211: GEMINI Multi-Asset Portfolio Management

**Zusammenhang:**
- Relates to #333 (Decision Engine) → Portfolio Manager uses Decision Engine
- Relates to #341 (Monitoring) → Portfolio Metrics need working Metrics Export

**Dependencies:**
```
#341 (Metrics Export) → Foundation
#333 (Decision Engine) → Integration Point
  ↓
#211 (Portfolio Management) → Feature
```

**PR-Strategie:**
```
PR #23: Portfolio Management (AFTER #333 + #341)
  - Implement #211 (Multi-Asset Portfolio Manager)
  - Integrate with Decision Engine (#333)
  - Dashboard (needs #341 fixed)
```

**Estimated Effort:** 3-5 Tage
**Priority:** MEDIUM (P2) - M8/M9 Milestone

---

## Dependency Graph (Critical Path)

```
┌─────────────────────────────────────────────────────────────┐
│                     CRITICAL PATH                            │
└─────────────────────────────────────────────────────────────┘

PHASE 1: FOUNDATION (PARALLEL) ← START HERE
├─ #224 + #229 (Testing Pipeline Fix) → 1d
├─ #341 + #210 (Monitoring Fix) → 2d
└─ #326 (Tresor-Zone) → 2-3d

         ↓

PHASE 2: INFRASTRUCTURE (SEQUENTIAL)
├─ #319 (Testnet Foundation) → 2-3d [AFTER #224+#229]
├─ #203 + #211 (Analytics Dashboards) → 2-3d [AFTER #341+#210]
└─ #325 (Penetration Testing) → 3-5d [AFTER #326]

         ↓

PHASE 3: AUTOMATION & GOVERNANCE (PARALLEL)
├─ #337 + #335 (Governance Foundation) → 1d
├─ #230 (E2E Guard Tests) → 1-2d [AFTER #319]
└─ #327 (Release 1.0 Process) → 2d [AFTER #325]

         ↓

PHASE 4: FEATURES (PARALLEL)
├─ #336 + #321 (Automation Layer) → 2d [AFTER #337]
├─ #332 + #333 (Decision Engine) → 5-6d
├─ #345 (pct_change) → 1-2d [INDEPENDENT]
└─ #206 (Database Schema) → 2-3d [INDEPENDENT]

         ↓

PHASE 5: ADVANCED FEATURES (PARALLEL)
├─ #338 (Devil's Advocate) → 2d [AFTER #336]
├─ #215 + #205 + #207 (Strategy Features) → 5-7d [AFTER #333]
└─ #211 (Portfolio Management) → 3-5d [AFTER #333+#341]

         ↓

PHASE 6: GOVERNANCE & CLEANUP (SEQUENTIAL)
├─ #328 (Governance Audit) → 2-3d [AFTER ALL]
├─ #330 (Branch Cleanup) → 1d [PARALLEL]
└─ #320 (README i18n) → 0.5d [PARALLEL]

         ↓

DEFERRED M10+:
├─ #334 (BSDE/HJB Research)
├─ #323 (Event Bus Migration) [MAJOR REFACTOR]
└─ #322 (K8s-Readiness)
```

---

## PR-Stränge (6 Themen-Stränge)

### 🔴 STRANG A: MONITORING & OBSERVABILITY
**PRs:** #1, #2
**Issues:** #341, #210, #203, #211
**Timeline:** Week 1-2 (3-5 Tage)
**Blocker Status:** Blockt Analytics & Portfolio Features

### 🟠 STRANG B: TESTING & QA
**PRs:** #3, #4, #5
**Issues:** #224, #229, #319, #230
**Timeline:** Week 1-2 (4-6 Tage)
**Blocker Status:** Blockt alle E2E Tests

### 🟡 STRANG C: AUTOMATION & GOVERNANCE
**PRs:** #6, #7, #8, #9
**Issues:** #337, #335, #336, #321, #338, #328
**Timeline:** Week 2-4 (5-7 Tage)
**Blocker Status:** Enables coordination, not a blocker

### 🔴 STRANG D: SECURITY & COMPLIANCE
**PRs:** #10, #11, #12
**Issues:** #326, #325, #327
**Timeline:** Week 1-3 (7-10 Tage)
**Blocker Status:** Blockt Production Launch

### 🟢 STRANG E: STRATEGY & ML
**PRs:** #14, #15, #16, #17
**Issues:** #332, #333, #215, #205, #207, #200
**Timeline:** Week 3-6 (10-15 Tage)
**Blocker Status:** M8/M9 Milestone, nicht v1.0 blocker

### 🔵 STRANG F: INFRASTRUCTURE & FEATURES
**PRs:** #13, #21, #22, #23
**Issues:** #345, #206, #320, #211
**Timeline:** Week 2-5 (7-11 Tage)
**Blocker Status:** Independent features, can be parallel

---

## Empfohlene Execution Order (6 Wochen)

### Week 1: FOUNDATION (CRITICAL)
**Parallel Start:**
- STRANG A (Monitoring): PR #1 (#341 + #210) → 2 Tage
- STRANG B (Testing): PR #3 (#224 + #229) → 1 Tag
- STRANG D (Security): PR #10 (#326 Tresor) → 2-3 Tage

**Outcome:** Monitoring + Testing + Secrets Management operational

---

### Week 2: INFRASTRUCTURE (SEQUENTIAL after Week 1)
**Sequential:**
- STRANG A (Monitoring): PR #2 (#203 + #211 Dashboards) → 2-3 Tage [AFTER PR #1]
- STRANG B (Testing): PR #4 (#319 Testnet) → 2-3 Tage [AFTER PR #3]
- STRANG D (Security): PR #11 (#325 Pentest) → 3-5 Tage [AFTER PR #10]

**Parallel (independent):**
- STRANG C (Governance): PR #6 (#337 + #335) → 1 Tag
- STRANG F (Features): PR #13 (#345 pct_change) → 1-2 Tage

**Outcome:** Full Monitoring, Testnet, Security Audit started

---

### Week 3: AUTOMATION & SECURITY CLOSURE
**Sequential:**
- STRANG B (Testing): PR #5 (#230 E2E Guards) → 1-2 Tage [AFTER PR #4]
- STRANG D (Security): PR #12 (#327 Release Process) → 2 Tage [AFTER PR #11]
- STRANG C (Governance): PR #7 (#336 + #321) → 2 Tage [AFTER PR #6]

**Parallel (independent):**
- STRANG E (Strategy): PR #14 (#332 Decision) → 1 Tag
- STRANG F (Features): PR #21 (#206 Database Schema) → 2-3 Tage

**Outcome:** Security closed, Automation operational, Strategy decision made

---

### Week 4: FEATURES & STRATEGY
**Sequential:**
- STRANG E (Strategy): PR #15 (#333 Decision Engine) → 4-5 Tage [AFTER PR #14]
- STRANG C (Governance): PR #8 (#338 Devil's Advocate) → 2 Tage [AFTER PR #7]

**Parallel (independent):**
- STRANG F (Features): PR #22 (#320 README i18n) → 0.5 Tage
- STRANG F (Cleanup): PR #20 (#330 Branch Cleanup) → 1 Tag

**Outcome:** Decision Engine MVP, Advanced Pipeline Features

---

### Week 5: STRATEGY FEATURES & PORTFOLIO
**Sequential:**
- STRANG E (Strategy): PR #16 (#215 + #205 + #207) → 5-7 Tage [AFTER PR #15]
- STRANG F (Portfolio): PR #23 (#211 Portfolio Management) → 3-5 Tage [AFTER PR #15 + PR #2]

**Outcome:** Strategy Features complete, Portfolio Management operational

---

### Week 6: GOVERNANCE AUDIT & CLOSE
**Sequential:**
- STRANG E (Strategy): PR #17 (#200 ML Research Meta) → 1 Tag [AFTER PR #16]
- STRANG C (Governance): PR #9 (#328 Governance Audit) → 2-3 Tage [AFTER ALL]

**Outcome:** Governance Audit complete, All issues resolved or deferred

---

## DEFERRED Issues (M10+)

**Not in 6-Week Sprint:**
- #334: BSDE/HJB Framework Selection → Deferred to M10+ (Research)
- #323: Event-Driven Backbone (JetStream/Kafka) → Major refactor, not v1.0 blocker
- #322: Kubernetes-Readiness & GitOps → Nice to have, not v1.0 blocker

**Rationale:** Focus on v1.0 Paper Trading MVP, defer scalability improvements.

---

## Summary Statistics

**Total Issues:** 30
**Thematische Bündel:** 10
**PR-Stränge:** 6
**Geplante PRs:** 23
**Deferred Issues:** 3 (M10+)

**Timeline:**
- **Critical Path:** 6 Wochen (optimistisch)
- **Realistic Timeline:** 8 Wochen (mit Buffer)

**Effort Distribution:**
- **Foundation (Week 1-2):** 12-16 Tage (CRITICAL)
- **Features (Week 3-5):** 20-30 Tage (MEDIUM)
- **Governance (Week 6):** 3-4 Tage (CLOSURE)

**Blocker Issues (MUST FIX FIRST):**
1. #224 + #229 (Testing Pipeline) → 1 Tag
2. #341 + #210 (Monitoring) → 2 Tage
3. #326 (Tresor-Zone) → 2-3 Tage
4. #325 (Pentest) → 3-5 Tage

**Quick Wins (Week 1):**
- #345 (pct_change) → 1-2 Tage
- #337 + #335 (Governance Labels) → 1 Tag
- #320 (README i18n) → 0.5 Tage

---

## Nächste Schritte (KEINE IMPLEMENTATION)

1. **User-Approval:** Jannek muss Bündelung + Execution Order absegnen
2. **Label-Cleanup:** Issues mit thematischen Labels versehen (bundle:A, bundle:B, etc.)
3. **Milestone-Zuordnung:** Issues zu Milestones zuordnen (M5, M8, M9, M10+)
4. **PR-Template:** Template für gebündelte PRs erstellen
5. **Tracking-Board:** GitHub Project Board mit 6 Strängen aufsetzen

**Output:** Diese Analyse, KEINE IMPLEMENTATION.

---

**Erstellt von:** Claude (Orchestrator-Modus)
**Status:** READY FOR REVIEW
**Next:** User-Approval für Execution Order
