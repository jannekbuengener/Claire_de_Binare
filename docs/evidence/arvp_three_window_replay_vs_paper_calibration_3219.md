# ARVP 3-Window Replay-vs-Paper Calibration — #3219

Status Class: Scoped evidence / A2/A3/A4 readiness assessment
Issue: #3219
Parent: #1900
Control Refs: #2985, #3217, #3218, #2977, #2971, #2973, #2975
Live-Readiness: NO-GO
Echtgeld: not authorized

---

## 1. Brain Evidence Block

```
brain_source: repo-only
brain_status: used
tools_or_queries:
  - read: canonical read-order per AGENTS.md
  - read: docs/evidence/arvp_guarded_natural_paper_window_execution_3217.md
  - read: docs/evidence/arvp_batch_compare_2971_after_2961.md
  - read: docs/evidence/arvp_regime_scorecards_2975_after_2973.md
  - read: docs/evidence/arvp_window_bank_inventory_3212.md
  - read: core/replay/replay_vs_paper_compare.py
  - read: core/replay/simulator_calibration_report.py
  - read: core/replay/arvp_regime_scorecards.py
  - read: core/replay/shadow_compare.py
  - execute: load_paper_reference_window() on all 3 artifact paths
  - bash: git status, gh issue/pr checks, artifact inventory
records_or_results:
  - HEAD == origin/main == d2ba9b8b
  - #3219 OPEN; #3217 CLOSED; #3218 MERGED; #2971 OPEN; #2973 DONE; #2975 DONE
  - 3-window bank inventoried: pilot (docs-backed), #3028 (machine-readable), June 6 1h (machine-readable)
  - Both machine-readable artifacts (3028, June6 1h): load_paper_reference_window() OK
  - Pilot 1m: no committed machine-readable artifact (docs-backed only)
  - June 6 1h: no replay_report.v1 exists → no comparison/calibration/regime possible
  - Existing replay reports: pilot (replay-16a0a8f6d92f-0001), #3028 (replay-577c2f83ac91-0001)
  - Existing compare artifacts: both windows have shadow_comparison.json
  - Existing calibration artifacts: both windows have simulator_calibration_report
  - Existing regime scorecards: both windows status=unavailable (no regime_segments)
  - No runtime/Docker/DB started
repo_crosscheck:
  - arvp_batch_compare_2971_after_2961.md (2-window batch)
  - arvp_regime_scorecards_2975_after_2973.md (regime evidence)
  - arvp_window_bank_inventory_3212.md (prior bank)
  - arvp_guarded_natural_paper_window_execution_3217.md (new window)
  - core/replay/replay_vs_paper_compare.py (tooling)
  - core/replay/simulator_calibration_report.py (tooling)
  - core/replay/arvp_regime_scorecards.py (tooling)
impact_on_plan:
  - 3-window bank assessed: A2 WARN, A3 WARN, A4 FAIL
  - June 6 1h cannot be compared without replay engine execution (requires Docker)
  - regime_segments unavailable for ALL windows — no regime scorecard can be populated
  - Decision: THREE_WINDOW_BATCH_COMPARE_PARTIAL_REGIME_UNAVAILABLE
limitations:
  - No replay report exists for June 6 1h window — replay_input gap, not tooling gap
  - No runtime/Docker/DB was used — replay execution is outside this scope
  - Pilot 1m window has no committed machine-readable artifact (docs-backed only)
  - No Product-Complete claim
```

---

## 2. Bootloader / Read-Order

Canonical read-order executed per `agents/AGENTS.md`:

1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md`
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `knowledge/CDB_KNOWLEDGE_HUB.md`
6. `docs/meta/WORKING_REPO_CANON.md`
7. `CURRENT_STATUS.md`
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
9. `docs/runbooks/CONTROL_REGISTER.md`
10. `agents/OPEN_CODE_AGENTS.md`

Verified boundaries:

- `CURRENT_STATUS.md` treated as ledger, not live truth.
- LR SSOT remains `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` (NO-GO).
- Board stage `trade-capable` is not Live-Go.
- No secret values printed, committed, or inspected.

---

## 3. Live-Lage

| Item | Status |
|---|---|
| Branch at session start | `main` |
| HEAD / origin/main | `d2ba9b8b` / equal |
| Working tree | clean (except untracked `.opencode/plans/`, `docs/decisions/`) |
| #3219 | OPEN |
| #3217 | CLOSED |
| #3218 | MERGED |
| #2971 | OPEN |
| #2973 | DONE |
| #2975 | DONE |
| #2985 | OPEN |
| #1900 | OPEN |
| #2977 | OPEN / BLOCKED |
| Open PRs | Dependabot-only (4) |
| LR verdict | NO-GO |
| Board stage | `trade-capable` (not Live-Go) |

No live-truth conflict found.

---

## 4. #3219 Scope

Per issue body and acceptance criteria, this slice:

1. Inventories the 3-window bank.
2. Identifies existing compare/calibration/regime tooling.
3. Verifies whether the new June 6 1h artifact is consumable by existing tooling.
4. Assesses A2/A3/A4 readiness on the 3-window bank.
5. Reports regime_segments status for every window.
6. Produces an exact final decision status.

**Not in scope:** replay execution, Docker/Compose, runtime, DB mutation, secrets, new extraction, new strategy.

---

## 5. 3-Window Bank Inventory

| # | Window ID | Width | Data span | Chains | Artifact | Tooling consumable | Replay report exists |
|---|---|---|---|---|---|---|---|
| 1 | Pilot (paper_1909) | 1 min | ~0s | 1 | docs-backed only (no committed JSON artifact) | — | ✅ replay-16a0a8f6d92f-0001 |
| 2 | #3028 (0c39ac88) | 2 min | ~0s | 1 | `artifacts/paper_reference_windows/paper_reference_window.json` | ✅ | ✅ replay-577c2f83ac91-0001 |
| 3 | June 6 1h | 60 min | 52.6 min | 4 | `artifacts/paper_reference_windows/paper_reference_window_june6_1h.json` | ✅ (paper-side) | ❌ |

### 5.1 Pilot 1m

- Docs-backed only: no committed machine-readable `paper_reference_window.v1` artifact exists in the repo.
- Previous evidence: `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md`, batch compare #2971.
- Replay report exists: `replay-16a0a8f6d92f-0001`.
- Compare/calibration/regime artifacts exist under `artifacts/calibration/2961/` and `artifacts/regime_scorecards/2975/`.

### 5.2 #3028 2m

- Machine-readable artifact committed via PR #3028: `artifacts/paper_reference_windows/paper_reference_window.json`.
- Replay report exists: `replay-577c2f83ac91-0001`.
- Compare/calibration/regime artifacts exist under `artifacts/replay_vs_paper_compare/`, `artifacts/calibration/2961/`, and `artifacts/regime_scorecards/2975/`.

### 5.3 June 6 1h

- Machine-readable artifact committed via PR #3218: `artifacts/paper_reference_windows/paper_reference_window_june6_1h.json`.
- Verified consumable by `load_paper_reference_window()`: PASS (4 SIGNAL, 4 DECISION, 2 ORDER, 1 FILL; strategy_id=primary_breakout_v1, symbol=BTCUSDT).
- **No replay_report.v1 exists** for this window's time period (2026-06-05T23:30:00Z to 2026-06-06T00:30:00Z).
- Without a replay report, the `replay_vs_paper_compare.py` tooling cannot produce a comparison; the downstream calibration and regime chain is therefore blocked.

---

## 6. Tooling Inventory

### 6.1 Tooling Chain

| Step | Tool | Input(s) | Output(s) | Status for June 6 1h |
|---|---|---|---|---|
| 1 | Replay engine (Docker) | Candle dataset | `replay_report.v1` | ❌ Blocked (requires Docker/runtime) |
| 2 | `replay_vs_paper_compare.py` | replay_report.v1 + paper_reference_window.v1 | `shadow_comparison.json` + `shadow_comparison_summary.md` | ❌ Blocked (missing replay input) |
| 3 | `simulator_calibration_report.py` | shadow_comparison.json | `simulator_calibration_report.json` + `simulator_calibration_summary.md` | ❌ Blocked (missing comparison input) |
| 4 | `arvp_regime_scorecards.py` | shadow_comparison.json | `arvp_regime_scorecard.json` + `arvp_regime_scorecard_summary.md` | ❌ Blocked (missing comparison input) |

### 6.2 Existing Tooling Verification

Both machine-readable artifacts (#3028 and June 6 1h) were loaded through `load_paper_reference_window()` from `core/replay/replay_vs_paper_compare.py`:

| Artifact | Result | Signals | Orders | Fills | Causal signals |
|---|---|---|---|---|---|
| `paper_reference_window.json` (#3028) | ✅ PASS | 1 | 1 | 1 | 0 |
| `paper_reference_window_june6_1h.json` (June 6) | ✅ PASS | 4 | 2 | 1 | 0 |

The paper-side tooling correctly consumes both artifacts. The pilot window has no committed machine-readable artifact (docs-backed only), so `load_paper_reference_window()` cannot be run.

---

## 7. Replay-vs-Paper Batch Compare Result (A2)

### 7.1 Existing 2-Window Compare (from #2971)

The 2-window batch compare was executed and delivered in #2971 / `docs/evidence/arvp_batch_compare_2971_after_2961.md`:

| Window | Status | Drift | Certainty | Comparison FP |
|---|---|---|---|---|
| Pilot | aligned | pessimistic | moderate | `d71a4abdd5a89acbf1799cc4e837e845affc4c25b9eaf6c2460b81002b529e0f` |
| #3028 | aligned | pessimistic | limited (venue confounded) | `8f74124bc362e09ad02ec4c11b2249d8e24fd0ac798d59467a3df552fb259405` |

Artifacts exist at `artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json`.

### 7.2 June 6 1h Status

**Not comparable.** The replay_report.v1 required for the comparison toolchain does not exist. Generating a replay report would require:

1. Preparing a BTCUSDT candle dataset for the window period (2026-06-05T23:30 to 2026-06-06T00:30).
2. Running the replay engine (Docker-based) against that dataset.
3. This is outside the scope of #3219 (no runtime/Docker/DB).

### 7.3 A2 Assessment

| Window | Compare available | Status |
|---|---|---|
| Pilot 1m | ✅ (existing) | PASS |
| #3028 2m | ✅ (existing) | PASS |
| June 6 1h | ❌ (missing replay input) | BLOCKED |

**A2: WARN** — 2 of 3 windows have complete compare artifacts. The 3rd window is blocked by missing replay inputs, not by tooling incompatibility.

---

## 8. Calibration / Drift Classification Result (A3)

### 8.1 Existing 2-Window Calibration (from #2971/#2973)

| Window | Status | Drift | Calibration FP |
|---|---|---|---|
| Pilot | aligned | pessimistic | `965fb48891129b8a1299804d679ba16b4e922242abb9601dfdca667e028c9da6` |
| #3028 | aligned | pessimistic (confounded) | `795b5a58d50dba9b42d6a10c5a10233d888b92c875f1bc1541afdb09fc204001` |

Both windows classify as pessimistic: the replay simulator underperforms compared to paper trading. The #3028 calibration is confounded by venue mismatch (Binance != MEXC).

### 8.2 June 6 1h Status

**Not calibratable.** The comparison input (shadow_comparison.json) that the calibration tooling consumes does not exist because the replay report does not exist.

### 8.3 A3 Assessment

| Window | Calibration available | Status |
|---|---|---|
| Pilot 1m | ✅ (existing) | PASS |
| #3028 2m | ✅ (existing) | PASS |
| June 6 1h | ❌ (missing comparison input) | BLOCKED |

**A3: WARN** — 2 of 3 windows have complete calibration evidence. The 3rd window is blocked. Drift classification remains pessimistic for both comparable windows.

---

## 9. Regime Scorecard / regime_segments Result (A4)

### 9.1 Existing 2-Window Regime Status (from #2975)

Both windows produce `status=unavailable` regime scorecards:

| Window | Status | Scorecard FP | Notes |
|---|---|---|---|
| Pilot | unavailable | `43e57fb78982c091dde9a147a71a69ee06676991cbe37cf719d0d8e4e5f61a15` | comparison input has no regime_segments |
| #3028 | unavailable | `e49de1d8524c3ca66c40db8f8001ecead5b31867883032af93984110612bf0a9` | comparison input has no regime_segments |

`regime_segments` are not present in any comparison input because:

1. The replay reports do not contain step-level regime_id data.
2. The replay engine does not emit `regime_segments` into its report output for these window periods.
3. The regime scorecard tooling correctly reports `unavailable` when regime data is missing.

### 9.2 June 6 1h Regime Status

**Not assessable.** The comparison input required by the regime scorecard tooling does not exist. Even if it did, the existing evidence (pilot, #3028) strongly suggests that `regime_segments` would remain `unavailable` because:

1. The replay engine does not emit step-level regime data for this strategy/symbol pair.
2. Longer windows (60 min) are necessary but not sufficient for regime_segments.

### 9.3 A4 Assessment

| Window | regime_segments available | Scorecard status |
|---|---|---|
| Pilot 1m | ❌ | unavailable |
| #3028 2m | ❌ | unavailable |
| June 6 1h | ❌ not assessable | unavailable (inferred) |

**A4: FAIL** — No window in the 3-window bank has populated `regime_segments`. The regime scorecard tooling correctly reports `unavailable` for all windows where it can be run. Regime_segments cannot be inferred; they must be generated by the replay engine with step-level regime data.

---

## 10. A2/A3/A4 Readiness

| Workstream | Status | Basis |
|---|---|---|
| A2 Replay-vs-Paper Batch Compare | **WARN** | 2 of 3 windows complete (pilot, #3028). June 6 1h blocked by missing replay input. |
| A3 Calibration + Drift Classification | **WARN** | Same as A2. Drift consistently pessimistic. #3028 venue-confounded. |
| A4 Regime Interpretation | **FAIL** | No regime_segments available for any window. All scorecards unavailable. |

---

## 11. Decision

**Decision: THREE_WINDOW_BATCH_COMPARE_PARTIAL_REGIME_UNAVAILABLE**

Rationale:

1. **A2/A3 are partially executable.** The existing 2-window batch compare, calibration, and drift classification artifacts are complete and reproducible. The June 6 1h window adds a 3rd consumable paper artifact but cannot be compared without replay engine execution.

2. **The gap is bounded.** The June 6 1h paper artifact is technically consumable (verified via `load_paper_reference_window()`). The sole blocker is the missing replay_report.v1 — a prerequisite input that requires Docker-based replay execution.

3. **regime_segments remain unavailable for ALL windows.** No window in the 3-window bank has populated regime_segments. A4 readiness is FAIL and cannot be resolved by tooling alone — it requires the replay engine to emit step-level regime data.

4. **No Product-Complete claim.** A4 is FAIL. This issue is evidence/calibration only.

This is not:
- A Product-Complete claim
- A Live-Go / Echtgeld-Go step
- A new candidate-family opening
- A strategy rescue path

---

## 12. Required Follow-up

1. **Replay execution for June 6 1h window** — Running the replay engine against a candle dataset covering 2026-06-05T23:30 to 2026-06-06T00:30 would unblock the compare/calibration chain. This requires Docker/runtime (Human-GO gated per roadmap).

2. **MEXC candle backfill for #3028** — The #3028 calibration is confounded by Binance venue mismatch. A MEXC candle backfill for the same period would enable pure same-venue comparison.

3. **Replay engine regime output** — For regime_segments to be populated, the replay engine must emit step-level regime_id data. This is a platform enhancement, not a calibration task.

4. **Fourth window** — Even with June 6 1h compared, the 3-window batch would be partial (1 of 3 windows is venue-mismatched). A fourth comparison-grade window (same-venue MEXC, >=5min) would strengthen the bank.

---

## 13. Stop Rules / Safety

| Rule | Status |
|---|---|
| No Live-Go | Enforced — LR remains NO-GO |
| No Real-Money-Go | Enforced |
| No Runtime/Docker/Compose | Enforced |
| No DB mutation | Enforced |
| No workflow_dispatch | Enforced |
| No secrets exposed | Enforced |
| No Product-Complete claim | Enforced |
| No Candidate #4 | Enforced |
| No PB1/RMR/Momentum rescue | Enforced |

---

## 14. Restunsicherheiten

1. The June 6 1h window cannot be compared without replay engine execution. The full A2/A3/A4 chain for the 3rd window remains blocked.
2. Even with a replay report, regime_segments may remain unavailable if the replay engine does not emit step-level regime data for this period.
3. The pilot window has no committed machine-readable artifact; its comparison/calibration chain is docs-backed but not reproducible from a committed `paper_reference_window.v1` artifact.
4. The #3028 calibration is venue-confounded (Binance != MEXC). The pessimistic drift for this window cannot be cleanly attributed to simulator behavior.
5. regime_segments inference was strictly avoided. No claim about regime behavior is made from unavailable status.

---

## 15. Status

`THREE_WINDOW_BATCH_COMPARE_PARTIAL_REGIME_UNAVAILABLE`

A2: WARN (2 of 3 windows comparable)
A3: WARN (2 of 3 windows calibratable)
A4: FAIL (all windows: regime_segments unavailable)
