## **10er Block 1 (Quick Wins \+ Phase-0 Shipability Base)**

Ziel: “Jetzt sofort spürbarer Fortschritt” (Branch Protection \+ Determinism \+ Alertmanager) und direkt danach CI/E2E/Contracts sauber.

1. **\#353** \[P1\] Enforce PR-only on main (Branch Protection)

2. **\#354** \[P0\] Deterministic E2E Test Path (local \+ CI)

3. **\#352** \[P0\] Enable Alertmanager (alert routing \+ test alert)

4. **\#355** \[P0\] CI/CD back to green (Actions \+ Guards)

5. **\#356** \[P0\] Canonical Message Contracts (market\_data, signals)

6. **\#349** \[P2\] Standardize Redis payload sanitization (no None in XADD)

7. **\#341** fix(monitoring): cdb\_ws Metrics Export broken (Prometheus scrape fails)

8. **\#347** \[P1\] Logging Policy dev vs prod (cost/noise control)

9. **\#348** \[P2\] Align network naming (docs vs compose reality)

10. **\#346** EPIC: Phase 0 – Shipability Base (als Steuerboard updaten)

Warum das zusammenpasst: Das ist ein kompletter “Gate-and-Proof”-Loop: Regeln (PR-only), deterministische Tests, Alerting aktiv, CI grün, Contracts stabil, Redis sauber, Metrics/Logging/Netzwerk konsistent, Epic als Dashboard.

---

## **10er Block 2 (Automation & Governance Workflows)**

Ziel: Issue-Lifecycle \+ Review-Brücke \+ “Decision hygiene” damit dein System nicht wieder verwildert.

1. **\#338** \[AUTOMATION\] Devil’s Advocate Mode

2. **\#337** \[AUTOMATION\] Issue Lifecycle State Machine (Labels & Transitions)

3. **\#336** \[AUTOMATION\] Pipeline-to-Review Bridge (Auto-Assign & SLA)

4. **\#335** \[PIPELINE\] Discussion Pipeline Output Clarity (Idee ≠ Entscheidung)

5. **\#330** 🔍 META: Governance Audit Q1 2026

6. **\#321** audit: Establish weekly Governance Review process

7. **\#147** \[AUTOMATION\] Smart PR Auto-Labeling

8. **\#170** \[SMART-AUTOMATION\] Issue Management & Progress Tracking

9. **\#171** \[PRODUCTIVITY\] Smart Development Dashboard & Workflow Automation

10. **\#159** \[STABILIZATION-P3\] Governance Enforcement – Fix All Violations

(Die Blöcke 2 und 3 greifen ineinander, aber hier bleibt der Fokus: Workflows \+ Regeln.)

---

## **10er Block 3 (Repo-Hygiene \+ Stabilization Kern)**

Ziel: “Repo wieder wartbar”, weniger Chaos, schnelleres Arbeiten, weniger Seiteneffekte.

1. **\#162** \[STABILIZATION-MASTER\] Fundamental System Stabilization Program

2. **\#158** \[STABILIZATION-P2\] Code Reality Audit – What actually exists?

3. **\#166** \[GOVERNANCE\] Agent Files in wrong repository (critical)

4. **\#167** \[GOVERNANCE\] Systematic canonical policy violations

5. **\#168** \[GOVERNANCE\] Missing Agent Roles directory structure

6. **\#330** \[CLEANUP\] Triage 82 unmerged branches

7. **\#164** \[DEVOPS\] Environment setup breakdown (Onboarding impossible)

8. **\#156** \[DEVOPS\] Dual CI/CD inconsistency (GitHub Actions vs GitLab CI)

9. **\#155** \[QUALITY\] Massive TODO/Unimplemented code audit

10. **\#151** \[ANALYSIS\] Cross-Repo Consistency Gap Analysis & Sync

---

## **10er Block 4 (Testing & Trading Core Guards)**

Ziel: Risk/Guard-Cases, Testharness, “Trading engine kann nicht aus Versehen Mist bauen”.

1. **\#230** E2E Guard-Cases: drawdown guard \+ circuit breaker

2. **\#229** Test harness cursor scope bug in `_count_rows`

3. **\#224** P1: order\_results not published (DRY\_RUN \+ DB schema mismatch \+ missing stream)

4. **\#172** Phase 2: Real 72-Hour Trading Validation System

5. **\#160** \[STABILIZATION-P4\] Operational Readiness – Production Confidence

6. **\#165** \[STABILIZATION-P2\] Production Safety Crisis – Mock deps block real trading

7. **\#171** Phase 1: Real MEXC Executor – Replace MockExecutor

8. **\#173** Phase 3: Production Safety Systems (real money)

9. **\#169** \[OPERATIONAL\] Production Deployment Readiness – Infra gaps

10. **\#328** audit: Release 1.0 Process & Incident Response (M9)

---

## **10er Block 5 (Security & Compliance Track)**

Ziel: Tresor/Keys, PenTest, Compliance, Security-by-default für M8/M9.

1. **\#327** audit: Implement Tresor-Zone (keys/limits/separation)

2. **\#326** audit: Penetration Testing & Compliance (M8)

3. **\#145** Security: Penetration Test – Infrastructure

4. **\#99** Security: Penetration Test – Web Application

5. **\#328** audit: Release 1.0 Process & Incident Response (M9)

6. **\#169** \[OPERATIONAL\] Production Deployment Readiness – Infra gaps

7. **\#160** Operational Readiness – Production Confidence

8. **\#173** Production Safety Systems for Real Money Trading

9. **\#325** Event-Driven Backbone – migrate to JetStream/Kafka

10. **\#323** Kubernetes-Readiness & GitOps (FluxCD)

---

## **10er Block 6 (ML / Strategy Research als eigener Zug)**

Ziel: Forschung ohne den Shipping-Track zu stören.

1. **\#203** ML Deep Research Topics – Systematische Aufarbeitung

2. **\#200** ML Deep Research Topics für Trading AI

3. **\#198** ML Foundation Master Roadmap

4. **\#199** ML Development Workspace & Jupyter

5. **\#197** Upgrade Python Dependencies for ML Foundation

6. **\#193** ML Foundation Phase 1

7. **\#194** ML Foundation Phase 2

8. **\#195** ML Foundation Phase 3

9. **\#196** ML Foundation Phase 4

10. **\#333** \[DECISION\] advanced control theory needed for M8/M9?

