# ARVP-to-Live-Go Roadmap — June 2026

Status: Draft roadmap document
Authority: Repo-backed synthesis; not a live-readiness or Echtgeld authorization
Live-Readiness: **NO-GO** (unchanged)
Echtgeld: **not authorized**
Board Stage: `trade-capable` (orthogonal to LR; does not authorize live capital)

---

## 1. Executive Summary

This roadmap defines a sequential, evidence-gated path from **ARVP product-complete** to **Live-Go readiness** (LR-050). The central insight is:

**ARVP must reach product-complete before Live-Go work meaningfully resumes.**

ARVP exists as a *paper-phase multiplier* — it accelerates evidence generation by replaying historical market data through the real strategy/execution path, comparing against actual paper behavior, and surfacing simulator drift. Right now ARVP infrastructure is landed, but calibration evidence is a single 1-minute pilot window on one symbol. That is not product-complete.

Live-Go (LR-050) is currently **NO-GO** with seven open blockers documented in `LR-050-FINAL-RECONCILE.md`. Three of those blockers (canary values, execution-realism, calibration-informed risk bounds) depend on ARVP evidence to be materially informed; the remaining four (receiver proof, secrets readiness, venue/testnet audit, human approval wording) can be prepared in parallel without ARVP complete. However, Phase A (ARVP product-complete) remains the sequencing prerequisite because calibrated replay-vs-paper evidence is needed before any honest canary-parameter decision can be made — and right now, that evidence does not exist at multi-window scale.

This roadmap sequences work into five phases (A–E), each with explicit gates. ARVP product-complete (Phase A) is the prerequisite for all subsequent phases. No phase authorizes live trades, real-money exposure, or automatic runtime activation.

---

## 2. Current Truth Snapshot

| Dimension | Status | Source |
|-----------|--------|--------|
| LR overall verdict | **NO-GO** | `LR-AUDIT-STATUS-2026-03-05.md` |
| LR-050 verdict | **NO-GO** / fail-closed | `LR-050-FINAL-RECONCILE.md` §2 |
| Board Stage | `trade-capable` (orthogonal to LR) | `CONTROL_REGISTER.md` |
| ARVP foundation | **Merged** (PR #1808, 2026-04-20) | `arvp_platform.md` §3 |
| ARVP MUST layers | **Implemented** (used by operator entry point) | `arvp_platform.md` §4.2–§4.6 |
| ARVP SHOULD layers | **Not started** (except partial #1901–#1904) | `arvp_platform.md` §4.7–§4.9 |
| ARVP paper reference contract | **Delivered** (#1901, PR #1914) | `arvp_paper_reference_contract.md` |
| ARVP replay-vs-paper comparison | **Delivered** (#1902, PR #1916) | `arvp_platform.md` §4.9 |
| ARVP calibration report | **Delivered** (#1903, PR #1918) | `arvp_platform.md` §4.9 |
| ARVP regime scorecards | **Delivered** (#1904, PR #1920) | `arvp_platform.md` §4.7 |
| ARVP execution realism | **PARKED** (#1905) | `#1900` comment 2026-05-14 |
| Pilot evidence | **1 window** (BTCUSDT, 1-minute, pessimistic drift) | `arvp_calibration_pilot_1932_2026-04-26.md` |
| Calibration batch seed | **1 window** (same pilot, HOLD for additional windows) | `arvp_calibration_batch_2961_2026-06-04.md` |
| LR-050 blockers | 7 open (runtime dry-run, receiver proof, canary values, venue audit, secrets, observability, human approval) | `LR-050-FINAL-RECONCILE.md` §3 |
| P0–P4 | All **DONE** | `LR-AUDIT-STATUS-2026-03-05.md` §B |
| P5 prestart pack | **Committed** (does not authorize live capital) | `reports/p5_canary/2026-04-04/` |

---

## 3. What Is Already DONE

These items are complete, evidenced, and do not need rework:

| Item | Evidence | Close Condition |
|------|----------|-----------------|
| P0 (CI, Contracts, Kill-Switch) | LR-001/002/003 DONE, issues #776/#777/#778 closed | Complete |
| P1 (Risk Engine, State Machine, Negative Payload scope-narrowed) | LR-010/011/012 DONE | Complete |
| P2 (E2E Paper Trading, Replay Framework) | LR-020/021 DONE | Complete |
| P3 (Shadow Mode >24h, Metrics Comparison) | LR-030/031 DONE, soak evidence committed | Complete |
| P4 (72h Soak, DB Failure, Network Chaos) | LR-040/041/042 PASS | Complete |
| P5 prestart pack | Committed under `reports/p5_canary/2026-04-04/` | Documentation only — does not clear LR-050 |
| ARVP foundation (#1801–#1806) | PR #1808 merged | Complete |
| ARVP MUST (#1840–#1845) | Merged, exercised by operator entry point | Complete |
| Paper Reference Contract (#1901) | PR #1914 merged, `arvp_paper_reference_contract.md` canonical | Complete |
| Replay-vs-Paper Comparison (#1902) | PR #1916 merged | Complete |
| Calibration Report (#1903) | PR #1918 merged | Complete |
| Regime Scorecards (#1904) | PR #1920 merged | Complete |
| LR-050 child planning SSOTs (#2526–#2534) | All merged and closed | Planning docs only — no blockers cleared |

---

## 4. What Is Stale / Ledger-Only / Overridden

| Item | Why Stale | Correct Reading |
|------|-----------|-----------------|
| `CURRENT_STATUS.md` | Working repo ledger, not live truth | Per `AGENTS.md`: "Ledger, nicht Live-Wahrheit" |
| `PROJECT_STATUS.md` | Historical snapshot | Per `AGENTS.md`: "nicht der aktuelle Gesamtstatus" |
| `knowledge/CURRENT_STATUS.md` | Historical snapshot | Same |
| P5 prestart GO status (`decision_record.yaml`) | Prestart-only artifact, explicitly does not authorize live capital | `LR-050-FINAL-RECONCILE.md` §4 |
| Board stage `trade-capable` | Orthogonal to LR | Does not authorize live capital |
| `#781` scope | LR-012 closed via scope-narrowing | Candles/signal residuals are non-blocking |
| ARVP #1905 "delivery" claim in #1900 body | Corrected: #1905 is PARKED, evidence-blocked | #1900 control-reconcile comments |
| `LR-050` issue #792 closed state | Closed GitHub issue does not clear gate | `LR-050-FINAL-RECONCILE.md` §2 |

---

## 5. ARVP Product-Complete — Definition of Done

ARVP is "product-complete" when it can serve its stated purpose — **paper-phase multiplier** — with enough evidence to support (but not authorize) Live-Go decisions.

### 5.1 Minimum Product-Complete Criteria

| Criterion | Metric | Current Gap | Issue |
|-----------|--------|-------------|-------|
| Paper Reference Window Bank | At least 2 (target: 3+) comparison-grade windows; window width data-driven (prefer 5+ minutes); BTCUSDT-only acceptable for first canary product path; multi-symbol is an extension, not a blocker for product-complete; market-condition diversity best-effort, repo-backed | Only 1 narrow pilot window (1 minute, BTCUSDT) exists; `HOLD_MISSING_COMPARISON_GRADE_WINDOWS` | #2961 |
| Replay-vs-Paper Batch Compare | Reproducible batch comparison across the window bank with per-window deltas and fingerprints | Batch exists for 1 window; multi-window comparison not evidenced | #2961 |
| Calibration + Drift Classification | Systematic drift classification (optimistic/pessimistic/timing_delta/execution_semantics_gap/missing_data) per window | Classification surface exists; only pessimistic drift demonstrated on 1 narrow window | #1903, #2961 |
| Regime Interpretation | Regime-scorecard output per window with activity/coverage metrics; no regime inference without data | Scorecard surface exists; `unavailable` on pilot (no `regime_segments`) | #1904, #2961 |
| Execution Realism Gap Identification | Ranked, data-driven gap identification from calibration findings; narrow, testable improvement scope | #1905 PARKED; no ranked findings beyond pilot pessimistic drift | #1905 |

### 5.2 Product-Complete Gate

ARVP product-complete is reached when:

1. A Window Bank of at least 2 (target: 3+) comparison-grade `paper_reference_window.v1` entries exists in the repo; window width is data-driven (prefer 5+ minutes); multi-symbol coverage is a stretch goal, not a product-complete blocker
2. A reproducible batch calibration across all bank windows produces per-window deltas and drift classification
3. At least one ranked execution-realism gap is identified from calibration data (not theoretically, but from actual replay-vs-paper deltas)
4. Regime scorecards are populated for at least one window with non-empty `regime_segments`
5. An operator runbook documents how to execute ARVP end-to-end and interpret results

---

## 6. ARVP Workstreams (Phase A)

### Workstream A1: Paper Reference Window Bank

**Goal:** Produce at least 2 (target: 3+) comparison-grade paper reference windows with `correlation_ledger` provenance.

**Contract:** `arvp_paper_reference_contract.md` (v1, #1901)

**Current state:** 1 window (`replay-ae0be21cc75e-0001`, BTCUSDT, 1-minute)

**First step — attempt extraction from existing data (no runtime, no stack start):**
- Use `paper_reference_window_runner.py` with readonly PostgreSQL access against the existing `correlation_ledger`
- The 14-day paper trading period (#1784) may have left comparison-grade windows in the DB already
- If 1+ additional windows are extractable, commit them to `artifacts/paper_reference_windows/` as repo-backed evidence
- This step requires only read-only DB access — no Docker, no stack start, no workflow dispatch

**If existing data is insufficient:**
- Plan a new paper trading execution period under staged/shadow mode
- All windows must satisfy `paper_reference_window.v1` contract requirements
- Window width is data-driven (prefer 5+ minutes); 1h per window is aspirational, not a hard minimum
- Multi-symbol replay requires `historical_bridge.py` adapter expansion (currently primary_breakout_v1/BTCUSDT-only); single-symbol BTCUSDT product-complete is acceptable for canary start

**Blocking issue:** #2961 (HOLD for additional windows)

**Issue anchor:** #2961

### Workstream A2: Replay-vs-Paper Batch Compare

**Goal:** Reproducible batch comparison across all bank windows with per-window deltas and fingerprints.

**Current state:** Surface exists (#1902), single-window comparison evidenced.

**Required next step:**
- Run ARVP replay against each window-bank entry
- Produce `shadow_comparison_summary.md` per window
- Produce a batch aggregation with cross-window delta analysis

**Dependency:** A1 (needs window bank first)

### Workstream A3: Calibration + Drift Classification

**Goal:** Systematic calibration report per window with drift classification.

**Current state:** Surface exists (#1903), one pessimistic classification demonstrated.

**Required next step:**
- For each batch window, classify drift as one of: `simulator_optimistic`, `simulator_pessimistic`, `timing_delta`, `execution_semantics_gap`, `missing_data`
- Produce per-window fingerprints
- Produce batch-level drift summary

**Dependency:** A2 (needs batch comparison first)

### Workstream A4: Regime Interpretation

**Goal:** Regime scorecard per window with meaningful regime segments.

**Current state:** Surface exists (#1904); pilot scorecard `unavailable` (no `regime_segments`).

**Required next step:**
- Longer windows (1h+) will naturally produce regime segments
- Scorecard population should be automatic from window data
- Do not force regime inference where data doesn't support it

**Dependency:** A1 (needs longer windows with regime context)

### Workstream A5: Execution Realism Gap Closure

**Goal:** Ranked, data-driven execution realism improvements identified from calibration.

**Current state:** #1905 PARKED / evidence-blocked.

**Required next step:**
- After A3 produces multi-window calibration with classified drift, the top-ranked gap(s) can be identified
- Scope a narrow, testable improvement (not a generic "add all realism features" bucket)
- Only then unpark #1905

**Dependency:** A3 (needs ranked calibration findings first)

### Workstream A6: Operator Runbook

**Goal:** An operator can execute ARVP end-to-end and interpret results without deep code diving.

**Current state:** No consolidated operator runbook for ARVP exists. The `strategy_replay_runner.py` CLI is the front door, but end-to-end guidance (data preparation → replay → compare → calibrate → interpret) is not documented as a single operational document.

**Required next step:**
- Write `docs/runbooks/ARVP_OPERATOR_RUNBOOK.md` covering: window selection, replay execution, batch comparison, calibration reading, drift classification interpretation

**Dependency:** A1–A3 (needs working pipeline first)

---

## 7. Live-Go Workstreams (Phase B–E)

These workstreams are sequenced AFTER ARVP product-complete. They cannot be honestly started until ARVP provides calibrated replay-vs-paper evidence.

### Workstream B1: LR-050 Blocker Refresh

**Goal:** Re-evaluate the 7 open LR-050 blockers from `LR-050-FINAL-RECONCILE.md` §3 with ARVP evidence in hand.

**Current blockers (from LR-050-FINAL-RECONCILE.md):**

1. Runtime dry-run evidence not executed
2. Operator receiver proof missing
3. Concrete canary values (TBD_BLOCKER_BEFORE_LIVE)
4. Venue/testnet/endpoint semantics externally unverified
5. `MEXC_TESTNET` is not non-send proof
6. Exact human approval absent
7. Secret/permission/IP/account-binding readiness (where not proven)

**Gate:** Phase A complete. ARVP calibration evidence available.

**Issue anchor:** LR-050 parent (#2535 / #792)

### Workstream B2: ARVP Findings → Fixes

**Goal:** Address the highest-ranked execution-realism gaps identified in A5.

**Scope:** Narrow, testable improvements only. Not a general realism overhaul.

**Gate:** A5 completed (ranked gaps identified).

**Issue anchor:** #1905 (unparked after A5)

### Workstream C1: Canary Caps and Symbolset

**Goal:** Define concrete canary parameter set — symbols, notional, loss caps, window.

**Current state:** `TBD_BLOCKER_BEFORE_LIVE` in `LR-050-RISK-LIMITS.md` and `LR-050-CANARY-PLAN.md`.

**Required next step:**
- Use ARVP calibration data to set realistic loss caps
- Define exact symbol set (start small: 1 symbol)
- Define notional limits and time window

**Gate:** Phase B (LR-050 refresh + ARVP-driven parameter input)

**Issue anchor:** #2528, #2532

### Workwork C2: Runtime Prestart Proof

**Goal:** Execute a non-destructive dry-run evidence pack per `LR-050-DRY-RUN-PROOF.md`.

**Current state:** Contract only (`docs_only`); no runtime dry-run executed.

**Required next step:**
- Spin up stack under `DRY_RUN=true`, `MOCK_TRADING=true`
- Collect: envelope, metrics, logs, no real orders
- Commit evidence pack to repo

**Gate:** Phase B (infrastructure unblocked)

**Issue anchor:** #2533

### Workstream C3: Receiver/Operator Receipt

**Goal:** Prove that Alertmanager/receiver actually delivers notifications.

**Current state:** Gate definition exists (`LR-050-OBSERVABILITY-GATES.md`); no delivery proof.

**Required next step:** Execute a live test that an operator can see alerts from the running stack.

**Issue anchor:** #2531

### Workstream C4: Secrets Readiness

**Goal:** Prove that permission scope, IP allowlist, account binding are ready (without values in repo).

**Current state:** Gate matrix `docs_only` (`LR-050-SECRETS-READINESS.md`).

**Required next step:** Operator verification of secrets readiness — outside agent scope.

**Issue anchor:** #2530

### Workstream D1: Kill-Switch / Rollback Proof

**Goal:** Prove kill-switch and rollback under canary-like conditions.

**Current state:** Runbook delivered (`LR-050-KILL-SWITCH-RUNBOOK.md`); not runtime-proven under live-capital scope.

**Required next step:** Drill the runbook against a real stack (staged/shadow mode only).

**Issue anchor:** #2529

### Workstream D2: Venue Audit Verification

**Goal:** External/operator proof that testnet/mainnet URLs and WS feeds match intended canary venue.

**Current state:** Repo inventory only (`LR-050-VENUE-AUDIT.md`).

**Required next step:** Operator verification — outside agent scope.

**Issue anchor:** #2527

### Workstream E1: Final Human-GO Package

**Goal:** Present all closed evidence to the human operator for an explicit live-canary approval decision.

**Current state:** Wording/checklist delivered (`LR-050-HUMAN-APPROVAL.md`); exact human GO text does not exist.

**Required next step:** After ALL gates (C1–D2) are closed with evidence, present the package and wait for explicit human approval.

**Critical rule:** No agent, no PR merge, no automated process may set `ready-for-human-live-approval`. Only explicit human operator text on the designated channel counts.

**Issue anchor:** #2534

---

## 8. Phase Sequence

```
Phase A: ARVP Product-Complete
  A1: Paper Reference Window Bank
  A2: Replay-vs-Paper Batch Compare (depends on A1)
  A3: Calibration + Drift Classification (depends on A2)
  A4: Regime Interpretation (parallel, depends on A1)
  A5: Execution Realism Gap Closure (depends on A3)
  A6: Operator Runbook (depends on A1-A3)
  ────────────────────────────────────────────
  Gate A: ARVP product-complete criteria met
  ────────────────────────────────────────────

Phase B: ARVP Findings → Fixes + LR-050 Blocker Refresh
  B1: Refresh LR-050 blockers with ARVP calibration evidence
  B2: Implement top-ranked execution-realism fix from A5
  ────────────────────────────────────────────────────────
  Gate B: Top execution-realism fix verified; blockers revisited
  ────────────────────────────────────────────────────────

Phase C: LR-050 Technical Closure
  C1: Canary caps and symbolset (ARVP-informed)
  C2: Runtime prestart proof (dry-run evidence pack)
  C3: Receiver/operator receipt
  C4: Secrets readiness (operator verification)
  ────────────────────────────────────────────────
  Gate C: All technical LR-050 blockers closed with evidence
  ────────────────────────────────────────────────

Phase D: Canary Hardening
  D1: Kill-switch / rollback drill under staged conditions
  D2: Venue audit verification (operator-side)
  ────────────────────────────────────────────────
  Gate D: Canary can be safely spun up and shut down
  ────────────────────────────────────────────────

Phase E: Explicit Human Live-Canary Decision
  E1: Present final Human-GO package
  ────────────────────────────────────────────────
  Gate E: Explicit human approval text on designated channel
  ────────────────────────────────────────────────
  Result: LR-050 MAY be upgraded (if all gates met)
```

**No phase may be skipped. No phase authorizes live capital.**

---

## 9. Stop Rules

The following are **absolute stop rules** for any agent working on this roadmap:

1. **No Live-Go** — LR-050 stays NO-GO until Phase E gate is explicitly cleared by human approval
2. **No Real-Money-Go** — No real capital exposure at any phase
3. **No Runtime Start** — No stack start, Docker compose, or service launch without explicit human GO per workstream
4. **No Docker** — No container orchestration without human GO
5. **No workflow_dispatch** — No CI/CD workflow triggers without human GO
6. **No DB/MCP Mutation** — No productive SurrealDB writes, no MCP live mutations
7. **ARVP evidence does not authorize Live-Go** — ARVP outputs are validation evidence only; they feed into LR gates but never bypass them
8. **Board stage `trade-capable` does not authorize live capital** — stage and LR are orthogonal systems

---

## 10. Issue Mapping

| Roadmap Element | Issue Anchor | Role |
|-----------------|-------------|------|
| ARVP north-star meta | #1900 | ARVP product-intent anchor; remains open until product-complete |
| ARVP calibration batch | #2961 | Current batch-window gap; HOLD for additional windows |
| ARVP execution realism | #1905 | PARKED; unpark only after A5 ranked findings |
| ARVP paper reference contract | #1901 | Delivered (PR #1914) |
| ARVP comparison surface | #1902 | Delivered (PR #1916) |
| ARVP calibration surface | #1903 | Delivered (PR #1918) |
| ARVP regime scorecard | #1904 | Delivered (PR #1920) |
| Cockpit/control anchor | #1445 | Operational cockpit epic (dauerhaft offen) |
| Paper phase operational thread | #1784 | 14-day paper phase control thread |
| LR-050 parent | #2535 | Final reconcile; NO-GO verdict |
| LR-050 old issue | #792 | Closed GitHub issue (does not clear gate) |
| LR-050 decision pack | #2526 | Planning SSOT delivered |
| LR-050 venue audit | #2527 | Inventory only; externally unverified |
| LR-050 risk limits | #2528 | Gate structure; canary values TBD_BLOCKER_BEFORE_LIVE |
| LR-050 kill-switch runbook | #2529 | Delivered; not runtime-proven under live scope |
| LR-050 secrets readiness | #2530 | Gate matrix docs_only; operator proof needed |
| LR-050 observability gates | #2531 | Delivered; receiver proof missing |
| LR-050 canary plan | #2532 | Plan only; parameters TBD |
| LR-050 dry-run proof | #2533 | Contract only; no runtime dry-run executed |
| LR-050 human approval | #2534 | Wording/checklist delivered; exact GO text absent |

---

## 11. Recommended Next 5 Issues to Create or Update

### Create

1. **`[ARVP][WINDOW-BANK] Extract comparison-grade paper reference windows from existing correlation_ledger`**
   - Scope: Use `paper_reference_window_runner.py` (readonly Postgres) to extract 2+ additional `paper_reference_window.v1` entries from the existing `correlation_ledger`. No runtime, no Docker, no stack start. If the 14-day paper trading period (#1784) left comparison-grade data, extraction is possible without new runtime. Only if existing data is insufficient: plan a new staged/shadow paper trading period.
   - Parent: #1900, #2961
   - **Note:** This is the critical bottleneck. The first attempt should be readonly extraction — no new runtime until existing data is exhausted. `historical_bridge.py` currently supports only BTCUSDT; multi-symbol replay requires adapter expansion.

2. **`[ARVP][RUNBOOK] Create ARVP operator runbook`**
   - Scope: Document end-to-end ARVP execution (data prep → replay → compare → calibrate → interpret) as a single operational guide
   - Parent: #1900
   - Can be started in parallel with A1 (documentation task, no runtime needed)

### Update

3. **#2961 — Update scope to reference this roadmap and Phase A1**
   - Current: "Run replay-vs-paper calibration batch on real reference windows"
   - Add: Reference to ARVP-to-Live-Go roadmap Phase A1; make window-bank collection an explicit prerequisite

4. **#1905 — Keep PARKED but annotate with roadmap dependency**
   - Add: "Unblock requires Phase A5 — ranked calibration findings from multi-window batch. Do not unpark before A3 is complete."

5. **#2535 — Annotate with roadmap cross-reference**
   - Add: Reference to this roadmap for the Phase B–E sequencing of LR-050 blocker closure

---

## 12. Clear Statement

**ARVP evidence can support Live-Go decisions, but never authorizes Live-Go by itself.**

ARVP outputs are validation evidence. They feed into LR gates through explicit, issue-anchored evidence commits. No calibration report, no scorecard, no drift classification, and no execution-realism improvement authorizes live capital, authorizes a canary, or changes the LR-050 verdict. Only explicit human approval through the designated channel does.

The Board stage `trade-capable` is orthogonal to the LR system and does not authorize live capital.

LR-050 remains **NO-GO**.

---

## Sources

- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — canonical LR status
- `docs/live-readiness/LR-050-FINAL-RECONCILE.md` — LR-050 verdict and blockers
- `docs/live-readiness/GO_NO_GO.md` — phase status table
- `docs/governance/arvp_platform.md` — ARVP module map and productization sequence
- `docs/governance/arvp_paper_reference_contract.md` — paper reference contract (v1)
- `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md` — pilot evidence
- `docs/evidence/arvp_calibration_batch_2961_2026-06-04.md` — batch seed evidence
- `docs/evidence/LR-030.md` — shadow mode evidence
- `CURRENT_STATUS.md` — repo/engineering ledger (not live truth)
- `agents/AGENTS.md` — agent registry and operating rules
- `AGENTS.md` — root pointer and session compass
- `knowledge/governance/CDB_AGENT_POLICY.md` — agent policy (Zone A–D, write gates)