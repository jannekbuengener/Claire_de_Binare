# ARVP Execution-Realism Decision Report — #2970 (2026-06-07)

Status: Decision summary for #2970 — ranked calibration findings reviewed, #1905/#2980 decided
Parent anchor: #1900 / #2973 / #2975
Upstream evidence:
  - `docs/evidence/arvp_drift_classification_2973_after_2971.md` (#2973)
  - `docs/evidence/arvp_regime_scorecards_2975_after_2973.md` (#2975)
  - `docs/evidence/arvp_batch_compare_2971_after_2961.md` (#2971)
  - `docs/evidence/arvp_calibration_batch_2961_after_3031.md` (#2961, #3031)
  - `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md` (#1932)
  - `artifacts/drift_classification/2973/window_bank_2/drift_classification_summary.json`
  - `artifacts/regime_scorecards/2975/window_bank_2/regime_scorecard_summary.json`
Output artifact: `artifacts/execution_realism/2970/decision_summary.json`
Live-readiness implication: none
Live/Echtgeld implication: none

---

## Executive Summary

This report reviews the multi-window calibration evidence (#2961/#2971/#2973/#2975)
and makes the following decisions:

1. **#1905 remains CLOSED** — not reopened. The issue was closed by PR #2949 as a
   side effect against its explicit Non-goals section. No execution-realism delivery
   was made through that PR. The successor is #2980.
2. **#2980 is confirmed as the active implementation path** for the top-ranked
   execution-realism gap (Fill Model / Order Execution Realism).
3. **No new duplicate issue is needed** — #2980 scopes exactly one narrow fix from
   ranked calibration findings, which matches the requirement.
4. **#2970 can close** after this decision report is committed.

The aggregate drift evidence supports a clear Rank-1 gap (fill model), sufficient
certainty from the same-venue pilot window (moderate), but with explicit limitations
on window count (2 of 3+), venue confound (#3028), and regime context (unavailable).

The decision is conservative: the gap is real and actionable, but the implementation
scope is deliberately narrow (#2980: one fix, measured, not a broad realism overhaul).

---

## Inputs

### Upstream Evidence Chain

| Step | Issue | Status | Evidence |
|------|-------|--------|----------|
| Calibration batch | #2961 / #3031 | CLOSED (PR #3052/#3051) | `arvp_calibration_batch_2961_after_3031.md` |
| Window bank extraction | #2969 | CLOSED | 2 comparison-grade windows |
| Batch compare | #2971 | OPEN (HOLD_PARTIAL, 3+ target) | `arvp_batch_compare_2971_after_2961.md` |
| Drift classification | #2973 | CLOSED (PR #3054) | `arvp_drift_classification_2973_after_2971.md` |
| Regime scorecards | #2975 | CLOSED (PR #3055) | `arvp_regime_scorecards_2975_after_2973.md` |
| Pilot evidence | #1932 | CLOSED | `arvp_calibration_pilot_1932_2026-04-26.md` |

### Machine-Readable Artifacts

| Artifact | Fingerprint |
|----------|-------------|
| `artifacts/drift_classification/2973/window_bank_2/drift_classification_summary.json` | JSON schema `arvp_drift_classification_summary.v1` |
| `artifacts/regime_scorecards/2975/window_bank_2/regime_scorecard_summary.json` | JSON schema `arvp_regime_scorecard_summary.v1` |
| `artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json` | JSON schema `arvp_batch_compare_summary.v1` |

---

## Calibration Finding Matrix

### Window Bank

| Property | Pilot Window | #3028 Window |
|----------|-------------|--------------|
| Window ID | paper_1909_1776991354682 | 0c39ac88-... |
| Venue | MEXC (same-venue) | Binance (venue_mismatch=true) |
| same_venue | true | false |
| regime_confounded | false | true (regime_id=0 vs 2) |
| Drift classification | simulator_pessimistic | simulator_pessimistic |
| Certainty | moderate | limited |
| Signal count delta | 0 | -1 |
| Order count delta | -1 | -1 |
| Fill count delta | -1 | -1 |
| Evidence level | proxy | proxy |
| Regime scorecard | unavailable | unavailable |

### Aggregate Drift

| Field | Value |
|-------|-------|
| aggregate_direction | pessimistic |
| aggregate_certainty | limited |
| window_count | 2 |
| same_venue_window_count | 1 (50%) |
| venue_mismatch_window_count | 1 (50%) |
| consistent_direction | yes (both pessimistic) |
| multi_window_coverage | HOLD_MISSING_COMPARISON_GRADE_WINDOWS |

---

## Ranked Execution-Realism Gaps

### Rank 1: Fill Model / Order Execution Realism
- **Evidence:** Both windows show fill_count_delta=-1 (replay produces 0 fills where paper produced 1 fill). Pilot: same-venue MEXC, moderate certainty. #3028: venue-mismatched, limited certainty.
- **Action:** Confirm #2980 as implementation path. Narrow fix targeting the replay fill model or upstream order execution path.
- **Certainty:** moderate (pilot) / limited (#3028)

### Rank 2: Signal Generation / Venue-Regime Sensitivity
- **Evidence:** #3028 shows signal_count_delta=-1 (replay 0 signals vs paper 1 signal). Pilot shows signal_count_delta=0.
- **Limitation:** Venue/regime confounded — Binance prices differ from MEXC, regime_id=0 vs 2. Cannot attribute to simulator alone.
- **Action:** Hold until same-venue MEXC data for #3028 or a third window exists.

### Rank 3: Fill Consistency Pattern
- **Evidence:** Both windows show -1/-1 order/fill delta consistently.
- **Limitation:** n=2; 50% confounded. Suggestive but not statistically significant.
- **Action:** Monitor as additional windows become available.

### Rank 4: Explicit Reject Data
- **Evidence:** No window has explicit reject data. Proxy-only calibration per #1903 contract.
- **Limitation:** Structural gap unrelated to #2970 decision scope.
- **Action:** Not a #2970/#2980 concern. Documented limitation.

---

## #1905 Decision

**Status:** CLOSED (remains closed)

**Closure root cause:** PR #2949 (`fix/2943-correlation-ledger-canonical-order-id`, merged 2026-06-04) referenced #1905 as `Refs` and explicitly stated in its Non-goals section: *"Does not unpark or close #1905 (remains parked)."* Despite this, GitHub closed #1905 as a side effect. No execution-realism delivery was made through PR #2949.

**Labels remain:** `status:parked` + `stage:strategy-validated` — inconsistent with CLOSED state, confirming the accidental nature of the closure.

**Decision:** #1905 stays CLOSED. No reopen. The successor implementation issue is #2980.

**Comment on #1905:** Posted confirming the decision.

---

## #2980 Decision

**Status:** OPEN — confirmed as active implementation path

**Why:** #2980 (`[ARVP][FIX] Implement top-ranked execution-realism fix from calibration`) scopes exactly what the evidence supports:
- One narrow fix selected from ranked calibration findings
- Tests for the fix
- Re-run calibration against same windows to measure delta
- Effect quantified against baseline

**Top-ranked gap for #2980:** Fill Model / Order Execution Realism (Rank 1).

**Recommendation:** #2980 should target the replay fill model path. The pilot window provides the cleanest same-venue signal (order_delta=-1, fill_delta=-1, moderate certainty). The fix should be narrow and measurable — not a broad execution simulator refactor.

**No new duplicate issue needed.** #2980 covers the required scope.

---

## Impact on #2974 (Product-Complete Review)

The #2970 decision makes the following criteria available for #2974:

| Product-Complete Criterion | Status | Source |
|---------------------------|--------|--------|
| Window bank >=2 windows | ✅ met (2 windows) | #2961/#2971 |
| Batch calibration per-window drift | ✅ met (both classified) | #2973 |
| Ranked findings | ✅ met (4 findings) | #2973 |
| Regime scorecards | ✅ met (both unavailable, honest) | #2975 |
| Execution realism gap | ✅ met (Rank 1 identified, #2980 active) | This report |
| Operator runbook (A6) | ❌ not started | #2974 |

**Recommendation:** #2974 can proceed with product-complete review after the Rank-1 implementation (#2980) delivers measurable delta evidence and the operator runbook (A6) exists. The decision framework is now available.

---

## Limitations

1. **2 windows only** — The 3+ comparison-grade target remains unmet. Additional windows would diversify the drift landscape.
2. **Venue mismatch (#3028)** — Binance != MEXC. Half the window bank is confounded.
3. **Regime discrepancy (#3028)** — regime_id=0 vs 2. Regime entry gates behaved differently.
4. **Proxy-only calibration** — No explicit reject data for either window.
5. **Narrow windows** — Both are ~1-2 minutes. Longer windows would produce more robust signals.
6. **Single symbol / single strategy** — BTCUSDT + primary_breakout_v1 only.
7. **Regime scorecards unavailable** — Both windows lack regime_segments.
8. **#1905 closure is accidental** — The closure through PR #2949 does not reflect execution-realism delivery. This is documented but not corrected by reopening.
9. **Ranking is based on n=2 evidence** — A third window could change the gap ranking.

---

## Safety Boundaries

- LR remains **NO-GO**
- No Live-Go / Echtgeld-Go
- No runtime execution beyond already-committed replay/compare/calibration
- No DB mutation
- No strategy/code changes
- No Risk/Execution/Allocation changes
- No Docker or workflow_dispatch actions
- #2980 is the implementation path — not a live-trading authorization
- ARVP evidence is validation, not live approval
- Decision is prioritization, not fix delivery
- #1905 is not reopened — successor is #2980

---

## References

- Issue #2970: https://github.com/jannekbuengener/Claire_de_Binare/issues/2970
- Issue #1905: https://github.com/jannekbuengener/Claire_de_Binare/issues/1905
- Issue #2980: https://github.com/jannekbuengener/Claire_de_Binare/issues/2980
- Issue #2975: https://github.com/jannekbuengener/Claire_de_Binare/issues/2975
- Issue #2973: https://github.com/jannekbuengener/Claire_de_Binare/issues/2973
- Issue #2971: https://github.com/jannekbuengener/Claire_de_Binare/issues/2971
- Issue #2961: https://github.com/jannekbuengener/Claire_de_Binare/issues/2961
- Issue #3031: https://github.com/jannekbuengener/Claire_de_Binare/issues/3031
- PR #3055: https://github.com/jannekbuengener/Claire_de_Binare/pull/3055
- PR #3054: https://github.com/jannekbuengener/Claire_de_Binare/pull/3054
- PR #3053: https://github.com/jannekbuengener/Claire_de_Binare/pull/3053
- PR #3052: https://github.com/jannekbuengener/Claire_de_Binare/pull/3052
- PR #3051: https://github.com/jannekbuengener/Claire_de_Binare/pull/3051
- PR #2949: https://github.com/jannekbuengener/Claire_de_Binare/pull/2949
- PR #1926: https://github.com/jannekbuengener/Claire_de_Binare/pull/1926
- Roadmap: `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
