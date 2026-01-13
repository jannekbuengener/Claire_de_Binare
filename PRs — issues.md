PRs — nach Dringlichkeit (was zuerst “wert” ist)  
DRINGLICHKEIT 0 (Security/CI/Hardening, direkt block-reduzierend)

* \#489 hardening: enforce threshold contract (\#487)  
* \#497 ci(docker): advanced docker workflow \+ optimization toolkit (Gordon)  
* \#496 Potential fix: code scanning alert 1528 (permissions) (Draft)  
* \#491 Fix incomplete URL substring sanitization (Draft)  
* \#490 Security: Prevent code injection in emoji-bot workflow (Draft)  
* \#471 Potential fix: code scanning alert 1511 (Code injection)

DRINGLICHKEIT 1 (CI stabilisieren / Runs reduzieren / Hygiene)

* \#476 ci: reduce runs via path filters \+ concurrency (refs \#413)  
* \#504 ci: fix origin/main fetch \+ bump aiohttp to 3.13.3  
* \#508 ci: fix ruff F841 in core/auth  
* \#509 chore(\#470): remove .worktrees\_backup from repo  
* \#481/\#480/\#479/\#478 (ci fixes rund um \#477 worktree backups/ruff/markers/emoji report)  
* \#422 chore(ci): pin GitHub Actions to SHAs

DRINGLICHKEIT 2 (Dependencies / langfristig gut, selten akut)

* \#516/\#511/\#494 dependabot: bump pip group (mehrere Verzeichnisse)  
* \#521 ci: weekly python-compat matrix (3.12/3.13/3.14 informational)  
* \#503 test: scaffold pytest basics

DRINGLICHKEIT 3 (große Draft-Baustellen, erst wenn oben ruhig ist)

* \#495 Complete Kubernetes deployment with GitOps (Draft)  
* \#493 Merge feature/145-smart-pr-auto-labeling… (Draft)  
* \#474/\#473 Potential fix code scanning alerts (Draft)  
* \#472 Remove redundant variable assignment in emoji-bot workflow (Draft)

Nächster Schritt (konkret, ausführbar): Nimm **Dringlichkeit 0** und arbeite strikt in dieser Reihenfolge: **\#414 → \#517 → \#431 → (\#499/\#500 \+ PR \#497/\#489)**. Sobald du mir sagst “go”, mache ich daraus eine **1-Seiten-Exec-Queue** (Top-10, Owner je Agent, klare Exit-Criteria).

CDB\_AGENT\_POLICY

DRINGLICHKEIT 0 — Blockt Betrieb / Produktion (critical / must / P0 / security-hard)

* \#517 Repo scan: Branch protection, secrets path, test failures (priority:critical)

* \#168 \[STABILIZATION-P2\] Production Safety Crisis \- Mock Dependencies Block Real Trading (priority:critical)

* \#162 \[STABILIZATION-MASTER\] Fundamental System Stabilization Program (priority:critical)

* \#160 \[STABILIZATION-P4\] Operational Readiness \- Production Confidence (priority:critical)

* \#159 \[STABILIZATION-P2\] Code Reality Audit \- What Actually Exists? (priority:critical)

* \#157 \[STABILIZATION-P1\] Infrastructure Emergency \- System Broken (priority:critical)

* \#149 \[CODEX\] Service Implementation Status Audit & Completion (priority:critical)

* \#500 Follow-up: Gordon Docker setup — Scout/Trivy/Metrics \+ Dockerfile strategy (prio:must, type:security)

* \#499 Review: Gordon Docker setup \+ CI workflow claims (prio:must, type:security)

* \#492 Follow-up: rerun status \+ blockers (refs \#413 \#26) (prio:must)

* \#470 Follow up on Zero Restart automation (prio:must)

* \#431 🧪 MUST: E2E Smoke Test ≥90% Pass Rate (267/297 Tests) \- Pre-Soak Gate (prio:must)

* \#464 GAP-006: Audit Trail & Hash-Chain Export (prio:must, priority:P0)

* \#462 GAP-004: Emergency Stop with Sub-30s SLA (prio:must, priority:P0)

* \#460 GAP-002: Defined DB/Redis Failure Modes (prio:must, priority:P0)

* \#458 GOV-003: External Review Sign-off (AI Audit Report) (prio:must, priority:P0, type:security)

* \#457 GOV-002: Least Privilege & Separation of Duties (prio:must, priority:P0)

* \#456 GOV-001: Hardware-MFA for Critical Access (prio:must, priority:P0, type:security)

* \#451 T5c: Unannounced Operator Drill (Issue G2) (prio:must, priority:P0)

* \#449 T5a: 72h Soak Test (Zero Restarts) (prio:must, priority:P0)

* \#448 M4: Disk Space Guard (prio:must, priority:P0)

* \#330 🔍 META: Governance Audit Q1 2026 \- Repo-Hygiene & Compliance (prio:must)

* \#328 audit: Release 1.0 Process & Incident Response (M9) (prio:must)

* \#327 audit: Implement Tresor-Zone (Keys, Limits, Governance separation) (prio:must, type:security)

* \#326 audit: Penetration Testing & Compliance (M8) (prio:must, type:security)

* \#323 audit: Kubernetes-Readiness & GitOps (FluxCD) (prio:must, type:security)

* \#145 Security: Penetration Test \- Infrastructure (prio:must, status:blocked)

* \#100 Security: Penetration Test \- Web Application (prio:must, status:blocked)

DRINGLICHKEIT 1 — High (sollte als Nächstes, reduziert Risiko/Chaos stark)

* \#498 SCOPE \- merge open branches to main (review) (prio:should)

* \#477 \[CLEANUP\] Exclude .worktrees\_backup from Dependabot \+ gitignore (prio:should)

* \#413 \[P1\]\[roter\_faden005\] Enforce PR-only on main (Branch Protection) (priority:high)

* \#414 CI blocked by billing/limits (Actions runs failing) (priority:high)

* \#346 \[PIPELINE\] Devil's Advocate Mode \- Built-in Skepticism & Stress Testing (prio:should)

* \#338 \[AUTOMATION\] Issue Lifecycle State Machine \- Labels & Transitions (prio:should)

* \#337 \[AUTOMATION\] Pipeline-to-Review Bridge \- Auto-Assign & SLA Tracking (prio:should)

* \#336 \[PIPELINE\] Discussion Pipeline Output Clarity \- Idee ≠ Entscheidung (prio:should)

* \#320 audit: Testnet & Persistence \- Replay-fähige E2E Tests (M5/M7) (prio:should)

* \#325 audit: Event-Driven Backbone \- Migrate to JetStream/Kafka (prio:should)

* \#322 audit: Establish weekly Governance Review process (prio:should)

* \#224 E1–E4 Integration: Regime & Allocation Services, strategy\_id Pipeline, Risk-Off Enforcement (prio:should)

* \#206 🧠 Adaptive Strategy Selector \- Market Regime Detection (priority:high)

DRINGLICHKEIT 2 — Medium (wertvoll, aber nicht akuter Blocker)

* \#432 Agent PowerShell Toolchain: CLI/Bootstrap \+ Docker CI Lab \+ Security Simulation Harness (priority:medium)

* \#427 Raise coverage threshold (70% → 80%) (priority:medium)

* \#332 \[CLEANUP\] Triage 82 unmerged branches (priority:medium)

* \#215 🧠 Multi-Asset Portfolio Management \- Dynamic Allocation & Risk Balancing (priority:medium)

* \#205 🧠 Trading Performance Analytics Dashboard (priority:medium)

* \#173 \[PRODUCTIVITY\] Smart Development Dashboard & Workflow Automation (priority:medium)

* \#156 \[DEVOPS\] Dual CI/CD Pipeline Inconsistency \- GitHub Actions vs GitLab CI (priority:medium)

* \#155 \[ANALYSIS\] Cross-Repo Consistency Gap Analysis & Synchronization (priority:medium)

* \#163 \[PERFORMANCE\] Sophisticated Testing Infrastructure Exists But Unused (priority:medium)

* \#169 \[OPERATIONAL\] Production Deployment Readiness \- Critical Infrastructure Gaps (priority:medium)

DRINGLICHKEIT 3 — Nice/Backlog/P2 (kann warten)

* \#520 Tech debt: DB driver modernisieren für Python 3.13/3.14 (psycopg2 binary mismatch) (prio:nice/should)

* \#501 Stand up isolated cdb\_autoclaude stack (prio:should/nice)

* \#467 M3: Time Drift / NTP Guard (priority:P0, aber prio:nice/should → nach den echten Blockern)

* \#466 M2: Kill-Switch Priority (Latency \< 1s) (priority:P0, prio:nice/should)

* \#465 M1: Application Reject Circuit Breaker (Consecutive 4xx) (priority:P0, prio:nice/should)

* \#463 GAP-005: Change Freeze Enforcement (priority:P0, prio:nice/should)

* \#461 GAP-003: Safe Degradation & HALT Fallback (priority:P0, prio:nice/should)

* \#459 GAP-001: SOT Proof (Deterministic Replay) (priority:P0, prio:nice/should)

* \#455 P4: Resource Exhaustion Deep Tests (priority:P2)

* \#454 P3: Safe Mode Alert Non-Blocking (priority:P2)

* \#453 P2: Stale Price Advanced Detection (priority:P2)

* \#452 (in deinem Dump abgeschnitten)

* \#450 T5b: Market Chaos Drill (priority:P0, prio:nice/should)

* \#447 Codex MCP Alignment: remove MCP\_DOCKER, use central MCP config

* \#319 E2E Guard-Cases: TC-P0-003 drawdown guard \+ TC-P0-004 circuit breaker (prio:must/should, aber priority:low)

* \#230 Test harness: cursor scope bug in \_count\_rows (prio:must, priority:low)

* \#229 P1: order\_results not published (prio:should/nice)

* \#210 Backtesting Framework (prio:should/nice, priority:high)

* \#207 Database Schema Migrations & Optimization (prio:should/nice, priority:high)

* \#203 ML Deep Research Topics \- Systematische Aufarbeitung (priority:high)

* \#200 ML Deep Research Topics für Trading AI (priority:high)

* \#199 ML Development Workspace & Jupyter Integration (priority:high)

* \#198 ML FOUNDATION MASTER ROADMAP (prio:must, priority:high)

* \#197 IMMEDIATE: Upgrade Python Dependencies for ML Foundation (priority:high)

* \#196/195/194/193 ML Foundation Phasen (priority:high)

* \#192 Ultra-Low Latency Trading Engine

* \#191 AI-Powered Market Prediction Engine

* \#189 Advanced Order Types Implementation

* \#190 (in deinem Dump nur als Header sichtbar)

* \#170 \[SMART-AUTOMATION\] Issue Management & Progress Tracking Enhancement (priority:high)

* \#148 \[AI-RESEARCH\] Intelligent Deep Research Synthesis System (priority:high)

* \#147 \[AUTOMATION\] Implement Smart PR Auto-Labeling System (priority:medium)

* \#321 audit: Internationalize README (prio:nice)

* \#335 \[RESEARCH\] BSDE/HJB Framework Selection (prio:nice)

* \#334 \[SPEC\] Minimum Viable Decision Engine for CDB v1.0 (prio:must)

* \#333 \[DECISION\] Is advanced control theory needed for M8/M9? (prio:must)

* \#353 EPIC: Phase 0 – Shipability Base (Contracts, E2E, Alerting, CI Green)

