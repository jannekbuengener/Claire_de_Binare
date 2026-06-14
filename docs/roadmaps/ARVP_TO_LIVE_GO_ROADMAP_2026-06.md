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

ARVP exists as a *paper-phase multiplier* — it accelerates evidence generation by replaying historical market data through the real strategy/execution path, comparing against actual paper behavior, and surfacing simulator drift. The original single-window pilot limitation is no longer the only truth: Phase A remains blocked on the natural-paper gate, while the bounded controlled-lab follow-up lane `#3172-#3184` delivered multi-regime attribution and ended with **PARK primary_breakout_v1**. That controlled-lab lane does not clear Product-Complete.

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
| ARVP Product-Complete gate | **BLOCKED** (`#2974` closed) | `arvp_product_complete_review_2974.md` |
| Natural-paper §5.2.4 path | **Still blocked** after Option-E split | `arvp_option_e_waiver_split_decision_3087_3095.md` |
| Controlled-lab evidence lane | **Delivered** (`#3172-#3184`) | `arvp_post_run_005_primary_breakout_v1_decision_3181.md`, `arvp_exit_regime_decay_diagnosis_3183.md` |
| `primary_breakout_v1` status | **PARKED** | `arvp_exit_regime_decay_diagnosis_3183.md` |
| ARVP execution realism | **`#1905` CLOSED/PARKED**; no unpark from this lane | GitHub live `#1905`, `#2970` decision |
| Next active research lane | **Candidate selection/spec only** | `arvp_roadmap_reconcile_after_primary_breakout_park_2985_1900.md` |
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
| Paper Reference Window Bank | At least 2 (target: 3+) comparison-grade windows; window width data-driven (prefer 5+ minutes); BTCUSDT-only acceptable for first canary product path; multi-symbol is an extension, not a blocker for product-complete; market-condition diversity best-effort, repo-backed | 2-window bank exists, but no natural-paper window with non-empty `regime_segments`; 3+ remains a quality target, not a cleared gate | #2974, #3087 |
| Replay-vs-Paper Batch Compare | Reproducible batch comparison across the window bank with per-window deltas and fingerprints | 2-window batch compare is delivered; the remaining gap is gate-clearing natural-paper evidence, not missing batch machinery | #2974 |
| Calibration + Drift Classification | Systematic drift classification (optimistic/pessimistic/timing_delta/execution_semantics_gap/missing_data) per window | 2-window classification is delivered; certainty remains bounded and does not reopen the parked `primary_breakout_v1` lane | #2970, #2974 |
| Regime Interpretation | Regime-scorecard output per window with activity/coverage metrics; no regime inference without data | Natural-paper scorecards remain unavailable on the current bank; later controlled-lab multi-regime attribution does not clear the natural-paper gate | #2974, #3174, #3175, #3179 |
| Execution Realism Gap Identification | Ranked, data-driven gap identification from calibration findings; narrow, testable improvement scope | Ranked gap identification was completed, but `#1905` stayed CLOSED/PARKED and no continuation path was opened from the parked `primary_breakout_v1` lane | #2970, #1905 |

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

**Current state:** 2 comparison-grade windows were delivered for the existing batch path, but no natural-paper window with non-empty `regime_segments` exists.

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

**Blocking issue:** no gate-clearing natural-paper window with non-empty `regime_segments` is currently available.

**Issue anchor:** historical `#2961`; later gate review `#2974`; later split decision `#3087`

### Workstream A2: Replay-vs-Paper Batch Compare

**Goal:** Reproducible batch comparison across all bank windows with per-window deltas and fingerprints.

**Current state:** Surface exists (#1902); 2-window batch comparison was delivered and reviewed.

**Required next step:**
- Run ARVP replay against each window-bank entry
- Produce `shadow_comparison_summary.md` per window
- Produce a batch aggregation with cross-window delta analysis

**Dependency:** A1 (needs window bank first)

### Workstream A3: Calibration + Drift Classification

**Goal:** Systematic calibration report per window with drift classification.

**Current state:** Surface exists (#1903); 2-window drift classification was delivered, with bounded certainty and no rescue path for the later parked `primary_breakout_v1` lane.

**Required next step:**
- For each batch window, classify drift as one of: `simulator_optimistic`, `simulator_pessimistic`, `timing_delta`, `execution_semantics_gap`, `missing_data`
- Produce per-window fingerprints
- Produce batch-level drift summary

**Dependency:** A2 (needs batch comparison first)

### Workstream A4: Regime Interpretation

**Goal:** Regime scorecard per window with meaningful regime segments.

**Current state:** Surface exists (#1904); natural-paper scorecards on the existing bank remain `unavailable`, while the later controlled-lab lane produced multi-regime attribution without clearing the natural-paper gate.

**Required next step:**
- Longer windows (1h+) will naturally produce regime segments
- Scorecard population should be automatic from window data
- Do not force regime inference where data doesn't support it

**Dependency:** A1 (needs longer windows with regime context)

### Workstream A5: Execution Realism Gap Closure

**Goal:** Ranked, data-driven execution realism improvements identified from calibration.

**Current state:** Ranked execution-realism gap identification was completed and documented via `#2970`, while `#1905` remains **CLOSED/PARKED** and `#2980` did not open a legitimate continuation path for the parked `primary_breakout_v1` lane. The later controlled-lab follow-up chain `#3172-#3184` ended with **PARK primary_breakout_v1**.

**Required next step:**
- Do not tune or rescue `primary_breakout_v1` inside this lane.
- Keep `#1905` parked/closed.
- Treat the next honest research move as **candidate selection/specification** from existing repo-backed profitability and candidate evidence.

**Dependency:** A3 (needs ranked calibration findings first)

### Workstream A6: Operator Runbook

**Goal:** An operator can execute ARVP end-to-end and interpret results without deep code diving.

**Current state:** Delivered via `#2972` / PR `#3010`. `docs/runbooks/ARVP_OPERATOR_RUNBOOK.md` exists on `main` and covers the end-to-end ARVP operating order and interpretation path.

**Required next step:**
- Keep the runbook aligned with live control truth and future candidate-selection follow-ups. No new runbook creation work is currently needed in this roadmap slice.

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

**Issue anchor:** no active issue is being advanced from this lane while `primary_breakout_v1` is parked; any future fix lane requires a new bounded issue after candidate selection.

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
| ARVP calibration batch | #2961 | Historical batch anchor; delivered and no longer the active gap issue |
| ARVP execution realism | #1905 | Closed/parked historical anchor; no current reopen path from the parked `primary_breakout_v1` lane |
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

## 11. Reconciled Next Slice

The earlier create/update list for this roadmap is stale. `#2961`, `#2970`, `#2972`, `#2974`, `#3087`, `#3094`, and the bounded controlled-lab lane `#3172-#3184` have already landed or closed.

### Current next action

1. **Create one bounded candidate-selection issue after the `primary_breakout_v1` PARK decision.**
   - Scope: read-only triage of existing repo-backed candidate evidence, shortlist, reject/park reasons, and one recommended next executable slice.
   - Parent: `#1900`
   - Refs: `#2985`, `#3181`, `#3183`
   - Explicitly out of scope: implementation, optimization, runtime changes, Live-Go, Echtgeld-Go, and any `primary_breakout_v1` rescue path.

### Explicitly not next

- No `primary_breakout_v1` parameter tuning or strategy change.
- No `#1905` unpark.
- No Product-Complete claim.
- No LR-050 Phase B-E advancement from this controlled-lab lane.

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
