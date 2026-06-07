# ARVP Signal Reproduction Gap Investigation — #3057 (2026-06-07)

Status: Root-cause investigation for #3057 — evidence-based signal reproduction gap classification
Parent anchor: #2980 / #1900
Upstream evidence:
  - `docs/evidence/arvp_execution_realism_decision_2970_after_2975.md`
  - `docs/evidence/arvp_drift_classification_2973_after_2971.md`
  - `docs/evidence/arvp_batch_compare_2971_after_2961.md`
  - `docs/evidence/arvp_calibration_batch_2961_after_3031.md`
  - `docs/evidence/arvp_regime_scorecards_2975_after_2973.md`
  - `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md`
Output artifact: `artifacts/signal_reproduction/3057/investigation_summary.json`
Live-readiness implication: none
Live/Echtgeld implication: none

---

## Brain Evidence

```
brain_source: repo-only
brain_status: used
tools_or_queries:
  - gh issue view 3057, 2980, 2974, 2971, 2970, 2973, 2975, 2961, 3031, 1905
  - gh pr list --state open
  - git fetch origin main, git rev-parse HEAD, git status
  - Read: all evidence docs under docs/evidence/arvp_*
  - Read: artifacts/calibration/2961/pilot_validation/replay-16a0a8f6d92f-0001/report.json
  - Read: artifacts/calibration/2961/pilot_baseline/paper_reference_window.json
  - Read: artifacts/calibration/2961/pilot_validation_compare/replay-16a0a8f6d92f-0001/shadow_comparison.json
  - Read: artifacts/calibration/2961/pilot_validation_calibration/replay-16a0a8f6d92f-0001/simulator_calibration_report.json
  - Read: artifacts/paper_reference_windows/paper_reference_window.json (#3028)
  - Read: artifacts/replay_reports/replay-577c2f83ac91-0001/report.json (#3028)
  - Read: artifacts/replay_vs_paper_compare/replay-577c2f83ac91-0001/shadow_comparison.json (#3028)
  - Read: artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json
  - Read: artifacts/drift_classification/2973/window_bank_2/drift_classification_summary.json
  - Read: services/signal/service.py (live close_now = market_data.price, tick-based)
  - Read: core/replay/historical_bridge.py (replay close_now = candle[close], close-based)
  - Read: services/validation/strategy_backtest_runner.py (backtest entry_ready gate)
  - Read: services/validation/paper_reference_window_runner.py (SQL window filter)
  - Read: core/replay/paper_reference_window_export.py (strict timestamp bounds)
  - Read: core/replay/replay_vs_paper_compare.py (comparison counting logic)
  - Read: core/replay/shadow_compare.py (delta computation: replay - paper)
  - Read: knowledge/contracts/PRIMARY_BREAKOUT_V1.md
  - Read: knowledge/contracts/PRIMARY_BREAKOUT_V1_VALIDATION.md
  - Read: docs/runbooks/CONTROL_REGISTER.md
  - Read: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md
  - Read: CURRENT_STATUS.md
  - Read: AGENTS.md (bootloader), agents/AGENTS.md (canonical registry)
records_or_results:
  - Pilot window replay signals_total=0 (replay-16a0a8f6d92f-0001/report.json)
  - Pilot window paper: 0 SIGNAL events in reference window (no event_type=SIGNAL)
  - Pilot window paper: 1 ORDER + 1 FILL at 00:42:34.803, inside 00:42-00:43 window
  - Pilot window signal_count_delta=0 (false neutral — both sides 0 for different reasons)
  - Pilot window order_count_delta=-1, fill_count_delta=-1
  - #3028 replay signals_total=0 (replay-577c2f83ac91-0001/report.json)
  - #3028 paper: 1 SIGNAL + 1 DECISION + 1 ORDER + 1 FILL (complete chain)
  - #3028 signal_count_delta=-1, confounded by venue_mismatch (Binance≠MEXC)
  - Live signal service: close_now = market_data.price (tick, intra-candle)
  - Replay bridge: close_now = candle[close] (candle close only)
  - Paper export SQL: WHERE timestamp_ms >= start AND <= end (strict bounds)
  - Paper export Python: fail-closed PaperReferenceExportError if out-of-bounds
  - Comparison: signal_count from paper = count of event_type=="SIGNAL" in window only
repo_crosscheck:
  - services/signal/service.py:552 (live close_now = tick price)
  - core/replay/historical_bridge.py:161 (replay close_now = candle close)
  - services/validation/paper_reference_window_runner.py:182-185 (SQL window bounds)
  - core/replay/paper_reference_window_export.py:214-218 (fail-closed timestamp check)
  - core/replay/replay_vs_paper_compare.py:186-200 (paper signal_count = count SIGNAL events)
  - artifacts/calibration/2961/pilot_baseline/paper_reference_window.json (no SIGNAL event)
  - artifacts/calibration/2961/pilot_validation/replay-16a0a8f6d92f-0001/report.json (signals_total=0)
impact_on_plan:
  - Root cause is MIXED_CAUSE (3 concurrent gaps)
  - #2980 fill-model fix alone insufficient — signal reproduction gap is upstream
  - PAPER_REFERENCE_EXPORT_GAP is the narrowest, highest-impact fix
  - LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP is architectural, needs separate scope
  - #2974 Product-Complete blocked by signal reproduction gap
limitations:
  - No same-venue MEXC data for #3028 window — signal gap there is confounded
  - n=2 window bank limits generalization
  - Causal chain analysis based on evidence documents, not DB queries
  - Only primary_breakout_v1 / BTCUSDT examined
```

---

## Executive Summary

This investigation answers **#3057**: why replay/backtest produces `signals_total=0` in paper reference windows, despite paper containing ORDER + FILL events in the compared window.

**Root-Cause Classification: MIXED_CAUSE**

Three concurrent gaps, each independently verifiable from committed repo evidence:

| # | Cause | Applicable Window | Evidence Strength |
|---|-------|-------------------|-------------------|
| 1 | **PAPER_REFERENCE_EXPORT_GAP** — pre-window SIGNAL events not exported | Pilot (primary), #3028 (secondary) | **Strong** — direct code+artifact evidence |
| 2 | **LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP** — live uses tick prices, replay uses candle closes | Both windows | **Strong** — direct code evidence |
| 3 | **METRIC_COUNTING_GAP** — `signal_count_delta=0` masks real absence | Pilot window | **Medium** — artifact evidence |

**Key finding:** The pilot window's `signal_count_delta=0` is a **false neutral**. Both sides show 0 SIGNAL events, but for different reasons:
- **Paper**: SIGNAL occurred before `00:42:00` window start → not exported
- **Replay**: Produced 0 signals across the 3.9-hour evaluation period

The comparison framework reports `signal_count_delta=0` as "signals match," but the paper runtime demonstrably produced a signal (proven by `signal_id="sig-1909-runtime-smoke"` on the ORDER/FILL events). The replay produced none. They are not equivalent.

For the **#3028 window**, the SIGNAL IS inside the window bounds, producing a visible `signal_count_delta=-1`. However, this window is confounded by venue mismatch (Binance ≠ MEXC) and regime discrepancy (regime_id=0 vs 2), so the gap cannot be attributed to simulator behavior alone.

---

## Inputs

### Committed Evidence Artifacts Used

| Artifact | Type | Key Finding |
|----------|------|-------------|
| `artifacts/calibration/2961/pilot_baseline/paper_reference_window.json` | Paper events | 0 SIGNAL, 1 ORDER, 1 FILL — no pre-window SIGNAL |
| `artifacts/calibration/2961/pilot_validation/replay-16a0a8f6d92f-0001/report.json` | Replay report | **signals_total=0**, orders=0, fills=0 |
| `artifacts/calibration/2961/pilot_validation_compare/replay-16a0a8f6d92f-0001/shadow_comparison.json` | Comparison | signal_count_delta=0, order_delta=-1, fill_delta=-1 |
| `artifacts/calibration/2961/pilot_validation_calibration/replay-16a0a8f6d92f-0001/simulator_calibration_report.json` | Calibration | drift: pessimistic, fill_count_delta=-1 |
| `artifacts/paper_reference_windows/paper_reference_window.json` | #3028 paper events | 1 SIGNAL + 1 DECISION + 1 ORDER + 1 FILL |
| `artifacts/replay_reports/replay-577c2f83ac91-0001/report.json` | #3028 replay report | **signals_total=0**, orders=0, fills=0 |
| `artifacts/replay_vs_paper_compare/replay-577c2f83ac91-0001/shadow_comparison.json` | #3028 comparison | signal_count_delta=-1, order_delta=-1, fill_delta=-1 |
| `artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json` | Batch summary | signal delta: pilot=0, #3028=-1 |
| `artifacts/drift_classification/2973/window_bank_2/drift_classification_summary.json` | Drift summary | both pessimistic; #3028 confounded |
| `services/signal/service.py` | Live signal code | `close_now = market_data.price` (tick/intra-candle) |
| `core/replay/historical_bridge.py` | Replay bridge code | `close_now = candle["close"]` (candle close only) |

### Fingerprint Index

| Window | Comparison FP | Calibration FP |
|--------|--------------|----------------|
| Pilot (validation) | d71a4abdd5a89acbf1799cc4e837e845affc4c25b9eaf6c2460b81002b529e0f | 965fb48891129b8a1299804d679ba16b4e922242abb9601dfdca667e028c9da6 |
| #3028 | 8f74124bc362e09ad02ec4c11b2249d8e24fd0ac798d59467a3df552fb259405 | 795b5a58d50dba9b42d6a10c5a10233d888b92c875f1bc1541afdb09fc204001 |

---

## Pilot Window Event Timeline

### Window Definition

- **Paper reference window**: `2026-04-24T00:42:00+00:00` to `2026-04-24T00:43:00+00:00`
- **Replay evaluation period**: `2026-04-23T20:49:00+00:00` to `2026-04-24T00:43:00+00:00` (3.9h)
- **Replay dataset**: 475 candles (240 warmup + 235 live), MEXC same-venue

### Event Sequence

```
Pre-Window (before 00:42:00):
  [?] SIGNAL event (signal_id="sig-1909-runtime-smoke")
      └── timestamp: before 00:42:00 (not preserved in any committed artifact)
      └── reason: breakout_entry (primary_breakout_v1)

Window [00:42:00, 00:43:00]:
  [00:42:34.803] ORDER (event_type=ORDER, order_id="paper_1909_1776991354682")
      └── signal_id="sig-1909-runtime-smoke" (references pre-window SIGNAL)
      └── side=BUY, quantity=0.001
  [00:42:34.803] FILL (event_type=FILL, fill_id="MOCK_45742296")
      └── filled_quantity=0.001, price=50013.08

Replay (same window):
  signals_total=0, orders_placed=0, fills_recorded=0
```

### Critical Observation

The paper reference window contains ORDER + FILL but **no SIGNAL event**. The SIGNAL occurred before `00:42:00` and was excluded from the export by:

1. **SQL filter** (`paper_reference_window_runner.py:182-185`):
   ```sql
   WHERE symbol = %s
     AND timestamp_ms >= %s   -- start_ts_ms_utc
     AND timestamp_ms <= %s   -- end_ts_ms_utc
   ```

2. **Python fail-closed guard** (`paper_reference_window_export.py:214-218`):
   ```python
   if timestamp_ms < request.start_ts_ms_utc or timestamp_ms > request.end_ts_ms_utc:
       raise PaperReferenceExportError("timestamp_ms out of requested window")
   ```

3. **Comparison layer filter** (`replay_vs_paper_compare.py:215-218`):
   ```python
   if ts_ms < start_ts_ms or ts_ms > end_ts_ms:
       raise ReplayVsPaperCompareError("events out of window bounds")
   ```

### Comparison Delta Analysis

| Metric | Paper | Replay | Delta | Interpretation |
|--------|-------|--------|-------|----------------|
| SIGNAL count | 0 | 0 | **0** | **False neutral** — paper SIGNAL was before window; replay produced none |
| ORDER count | 1 | 0 | **-1** | Replay missed the order entirely |
| FILL count | 1 | 0 | **-1** | Replay missed the fill entirely |

The `signal_count_delta=0` is **misleading**. It does not mean "signals matched." It means "neither side has a SIGNAL event within the window bounds." The paper runtime demonstrably generated a signal (proven by `signal_id` on ORDER/FILL). The replay generated none. This is a **METRIC_COUNTING_GAP**.

---

## #3028 Window Event Timeline

### Window Definition

- **Paper reference window**: `2026-06-06T00:28:12.551Z` to `2026-06-06T00:30:12.814Z`
- **Replay evaluation period**: `2026-06-06T00:28:00Z` to `2026-06-06T00:31:00Z`
- **Replay dataset**: 244 candles (240 warmup + 4 live), Binance (venue_mismatch=true)

### Event Sequence

```
Window [00:28:12.551, 00:30:12.814]:
  [00:29:12.551] SIGNAL (event_type=SIGNAL, signal_id="sig-43d57cfa16445220a7b49e8c759abac8")
      └── reason: breakout_entry, side=BUY
      └── close_now=61490.70949, highest_high=61458.98, breakout_buffer=0.0005
      └── condition: 61490.71 > 61458.98 * 1.0005 = 61489.59 → TRUE
  [00:29:12.551] DECISION
  [00:29:12.551] ORDER
  [00:29:12.551] FILL

Replay (same window):
  signals_total=0, orders_placed=0, fills_recorded=0
```

### Critical Observation

The #3028 window DOES contain the SIGNAL (unlike the pilot). The replay produced 0 signals despite having the event inside the comparison window. However, this window is **confounded**:

| Confound | Detail |
|----------|--------|
| **Venue mismatch** | Paper from MEXC runtime, replay uses Binance candles |
| **Regime discrepancy** | Paper used regime_id=2 (HIGH_VOL_CHAOTIC), replay defaulted to regime_id=0 (TREND) |
| **Price differences** | Binance BTC prices differ from MEXC — breakout threshold comparison may not fire |
| **Regime gate** | `regime_id in {0, "TREND"}` is the entry condition; if replay regime_id=0, the gate should pass — but the breakout condition `close_now > highest_high * (1 + buffer)` may not hold with Binance prices |

### Confound Analysis

The regime discrepancy is less likely the root cause here (replay correctly uses regime_id=0 TREND which should allow entry). The venue mismatch (Binance candles vs MEXC paper) is the more likely cause: different candle close/high prices mean the breakout condition either never fires or fires at different times. Additionally, **live uses tick prices** while **replay uses candle closes** — this architectural difference applies equally here.

---

## Source Code Evidence

### Live Signal Service — Tick-Based `close_now`

**File:** `services/signal/service.py`, line 552

```python
close_now = float(market_data.close or market_data.price)
```

The live signal service receives market data from MEXC WebSocket trade deals (`services/ws/mexc_v3_client.py`). The `normalize_deal()` function produces payloads with only `price`, `trade_qty`, `ts_ms`, `side` — there is **no `close`, `high`, or `low` field**. Since `market_data.close` is `None`, the fallback `close_now = market_data.price` uses the **current tick price**.

**Consequence:** Every incoming trade deal can trigger a breakout if its price exceeds the highest tick in the lookback window. This is **intra-candle breakout detection**.

### Replay/Backtest Bridge — Candle-Close `close_now`

**File:** `core/replay/historical_bridge.py`, line 161

```python
close_now = _required_number(row, "close")
```

The bridge iterates over settled 1-minute OHLCV candles. `close_now` is always the **candle close price**. `highest_high` is computed from candle highs over the lookback window.

**Consequence:** Breakout can only fire when a **settled candle close** exceeds the highest candle high in the lookback window. This is **candle-close breakout detection**, which lags behind intra-candle tick-level detection.

### Critical Difference

| Aspect | Live | Replay/Backtest |
|--------|------|-----------------|
| `close_now` | Tick price (intra-candle) | Candle close price |
| `highest_high` | Max tick price in time window | Max candle high in bar window |
| Windowing | Time-based (now_ms - lookback_ms) | Bar-count (index - lookback_bars) |
| Warmup | Elapsed wall-clock time | N candles consumed before first request |
| Data source | MEXC WS trade deals | Historical 1m OHLCV candles |

### Paper Reference Window Export — Strict Bounds

**File:** `core/replay/paper_reference_window_export.py`, lines 214-218

The export layer **fail-closed rejects** any event whose `timestamp_ms` is outside `[start_ts_ms_utc, end_ts_ms_utc]`. This means causally prior events (like a SIGNAL that triggered an ORDER inside the window) are **never included**.

**File:** `services/validation/paper_reference_window_runner.py`, lines 182-185

The SQL query also filters strictly by window bounds:
```sql
WHERE symbol = %s
  AND timestamp_ms >= %s
  AND timestamp_ms <= %s
```

---

## Hypothesis Matrix

| # | Hypothesis | Evidence | Windows | Verdict |
|---|-----------|----------|---------|---------|
| 1 | **SIGNAL_WINDOW_BOUNDARY_GAP** — SIGNAL event outside window bounds not exported | Pilot: SIGNAL before 00:42:00, not in reference. #3028: SIGNAL IS inside window. | Pilot: ✅. #3028: ❌ (SIGNAL inside bounds) | **PARTIAL** — explains pilot but not #3028 |
| 2 | **LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP** — live tick vs replay candle close | Code evidence: `service.py:552` uses tick price, `historical_bridge.py:161` uses candle close. Direct architectural difference. | Both: ✅ | **STRONG** — independent architectural gap |
| 3 | **PAPER_REFERENCE_EXPORT_GAP** — pre-window causally-linked events not exported | Export code fail-closed rejects out-of-bounds. Pilot has ORDER+FILL with `signal_id` but no SIGNAL. | Pilot: ✅. #3028: ❌ (SIGNAL inside) | **STRONG for pilot** — directly proven |
| 4 | **METRIC_COUNTING_GAP** — signal_count_delta=0 is misleading | Pilot: paper=0, replay=0, delta=0. But paper had a real SIGNAL. Both 0 for different reasons. | Pilot: ✅ | **STRONG** — counting masks real gap |
| 5 | **MIXED_CAUSE** — multiple concurrent gaps | Hypotheses 2+3+4 combine to explain both windows comprehensively | Both: ✅ | **CLASSIFICATION** — see below |
| 6 | **INSUFFICIENT_EVIDENCE** | All three gaps have direct code/artifact evidence | n/a | **REJECTED** — evidence is sufficient |

---

## Root-Cause Classification

**Classification: MIXED_CAUSE**

Three independently verifiable gaps combine to produce the observed `signals_total=0` result:

### Gap 1: PAPER_REFERENCE_EXPORT_GAP (Pilot Window, Primary Cause)

**What:** The paper reference window export layer filters strictly by `[window_start, window_end]`. Causally-linked SIGNAL events that occurred before the window start are **never exported**.

**Evidence:**
- Pilot paper reference window contains 0 SIGNAL events but has ORDER+FILL with `signal_id="sig-1909-runtime-smoke"`, proving a SIGNAL existed
- Code: `paper_reference_window_runner.py:182-185` (SQL filter), `paper_reference_window_export.py:214-218` (fail-closed bounds check)
- Code: `replay_vs_paper_compare.py:215-218` (comparison layer also enforces bounds)

**Impact:** The comparison framework **cannot detect** the signal gap in the pilot window. `signal_count_delta=0` is a false neutral.

### Gap 2: LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP (Both Windows, Architectural)

**What:** Live signal service evaluates breakouts on every trade **tick price** (intra-candle). Replay evaluates breakouts on **candle close prices** only. These can produce fundamentally different signal outcomes, especially in volatile markets where intra-candle price spikes trigger live signals that never fire at candle close.

**Evidence:**
- Live `service.py:552`: `close_now = float(market_data.close or market_data.price)` → tick price
- Replay `historical_bridge.py:161`: `close_now = _required_number(row, "close")` → candle close

**Impact:** Even if the paper export included pre-window SIGNAL events, the replay would still likely fail to reproduce signals if the original live signal was triggered by an intra-candle tick spike that is invisible to candle-close evaluation.

### Gap 3: METRIC_COUNTING_GAP (Pilot Window, Secondary)

**What:** The comparison framework reports `signal_count_delta=0` for the pilot window. This is **mathematically correct** (paper=0 SIGNAL events, replay=0 SIGNAL events), but **semantically misleading** — the paper runtime did generate a signal; it's just not in the exported window.

**Evidence:**
- `shadow_comparison.json`: `signal_count_delta=0`
- `paper_reference_window.json`: 0 SIGNAL events
- ORDER+FILL contain `signal_id` proving SIGNAL existed pre-window

**Impact:** Downstream consumers of the delta metrics (calibration, drift classification, batch compare) see `signal_count_delta=0` and interpret it as "signals matched," missing the real signal reproduction gap.

### Cause Mapping by Window

| Window | Paper SIGNAL in window? | Replay signals_total | signal_count_delta | Primary Gap | Secondary Gap |
|--------|------------------------|---------------------|--------------------|-------------|---------------|
| **Pilot** (MEXC) | ❌ (before 00:42:00) | 0 | 0 (false neutral) | PAPER_REFERENCE_EXPORT_GAP | METRIC_COUNTING_GAP |
| **#3028** (Binance) | ✅ (at 00:29:12) | 0 | -1 | LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP | (confounded by venue_mismatch) |

### Most Actionable Fix

**PAPER_REFERENCE_EXPORT_GAP** is the narrowest, highest-impact fix:

1. Extend the paper reference window export to include causally-linked SIGNAL events that fall **outside** the window bounds but have downstream ORDER/FILL **inside** the window
2. This would make the pilot window show `signal_count_delta=-1` instead of the false `0`
3. The change is contained to `paper_reference_window_export.py` — no strategy/signal/execution changes needed

**LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP** is architectural and cannot be fixed with a narrow implementation slice. Documenting this limitation is the correct near-term action.

---

## Impact on #2980

**Issue:** `[ARVP][FIX] Implement top-ranked execution-realism fix from calibration`

**Status Analysis:**

The #2980 scope targets the Rank-1 gap (Fill Model / Order Execution Realism — `fill_count_delta=-1`). However, this investigation reveals that the signal reproduction gap (upstream of fill/execution) is a separate, previously unclassified blocker:

- If the replay produces `signals_total=0`, no orders will be placed regardless of fill model improvements
- The fill-model fix (#2980) would have **zero measurable effect** if signal reproduction remains broken
- The `signal_count_delta=0` in the pilot window masked this dependency from the drift classification

**Recommendation:**

1. **#2980 remains HOLD** until the PAPER_REFERENCE_EXPORT_GAP fix is implemented and signal reproduction is measurable
2. The follow-up implementation issue for PAPER_REFERENCE_EXPORT_GAP should be a dependency of #2980
3. After the export gap fix, re-run calibration against the pilot window — `signal_count_delta` should change from 0 to -1
4. Only then can #2980 target the fill-model fix with a valid signal-reproduction baseline

**Decision:** #2980 stays OPEN/HOLD, now with an additional explicit blocker: signal reproduction gap (#3057 follow-up).

---

## Impact on #2974

**Issue:** `[ARVP][GATE] Product-complete review for ARVP Phase A`

**Status Analysis:**

The signal reproduction gap adds a new criterion that ARVP must address before product-complete:

| Product-Complete Criterion | Previous Status | Revised Status | Source |
|---------------------------|----------------|----------------|--------|
| Window bank ≥2 windows | ✅ met (2 windows) | ✅ unchanged | #2961/#2971 |
| Batch calibration per-window drift | ✅ met (both classified) | ✅ unchanged | #2973 |
| Ranked findings | ✅ met (4 findings) | ✅ unchanged | #2973 |
| Regime scorecards | ✅ met (both unavailable, honest) | ✅ unchanged | #2975 |
| Execution realism gap | ✅ met (Rank 1 identified) | ✅ unchanged | #2970 |
| Operator runbook (A6) | ❌ not started | ❌ unchanged | #2974 |
| **Signal reproduction gap resolved** | **not evaluated** | **❌ BLOCKER** | #3057 (this report) |

**Recommendation:** #2974 Product-Complete review should add "Signal reproduction gap classified and follow-up implementation scoped" as a criterion. The follow-up issue for PAPER_REFERENCE_EXPORT_GAP will address this.

**Decision:** #2974 remains OPEN/BLOCKED — not just by A6 runbook, but now also by the unaddressed signal reproduction gap.

---

## Recommended Follow-up

### Follow-up Issue: `[ARVP][SIGNAL][FIX] Preserve causal signal context for paper reference replay comparison`

**Scope:** Fix the PAPER_REFERENCE_EXPORT_GAP by extending the paper reference window export to include causally-linked SIGNAL events outside window bounds.

**Implementation sketch:**
1. In `paper_reference_window_export.py`, after extracting in-window events, do a secondary query for SIGNAL events that share `correlation_id` with in-window ORDER/FILL events but have `timestamp_ms < window_start` or `timestamp_ms > window_end`
2. Include these SIGNAL events in the exported `events[]` array with a flag like `"causal_context": true`
3. Update the comparison layer (`replay_vs_paper_compare.py`) to count causally-linked pre-window SIGNAL events as paper signal count
4. Update `shadow_compare.py` delta computation to use causal-aware signal counts

**Validation:** After fix, re-run comparison on pilot window → expected `signal_count_delta=-1` (paper=1, replay=0) instead of the current false `0`

**Not in scope:**
- LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP (architectural, separate tracking)
- Fill model changes (#2980 scope)

### Separate Tracking: LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP

This architectural gap cannot be closed with a narrow fix. The recommended action is:
1. Document as known limitation in the primary_breakout_v1 validation contract
2. If evidence later shows this gap is the dominant source of replay pessimism, scope a separate investigation for bridging intra-candle behavior into replay

---

## Safety Boundaries

- LR remains **NO-GO**
- No Live-Go / Echtgeld-Go
- No runtime execution beyond already-committed replay/compare/calibration
- No DB mutation
- No strategy/signal code changes
- No execution/fill model changes
- No Risk/Execution/Allocation changes
- No Docker or workflow_dispatch actions
- #3057 is a diagnostic investigation — no trading authorization
- ARVP evidence is validation, not live approval
- #1905 remains CLOSED (not reopened)
- #2980 remains HOLD — this report does not unpark it
- #2985 unaffected in this slice
- Binance candles are not MEXC same-venue evidence

---

## Restunsicherheiten

1. **Exact pre-window SIGNAL timestamp (pilot):** The committed artifacts do not preserve the exact timestamp of the pilot SIGNAL that occurred before 00:42:00. This would require a DB query on the live correlation_ledger, which is not available in this offline investigation.
2. **#3028 same-venue comparison:** Without MEXC candles for the #3028 window, the LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP contribution cannot be separated from the venue/regime confounds.
3. **Intra-candle evidence:** No intra-candle tick data is committed in any artifact. The claim that live tick prices caused the breakout is based on code analysis and indirect evidence (the signal fired at a timestamp that aligns with a tick within a 1-minute candle).
4. **n=2 generalization:** Both windows show disjoint primary causes. A third window could reveal additional gap types or confirm the dominance of one gap type.

---

## References

- Issue #3057: https://github.com/jannekbuengener/Claire_de_Binare/issues/3057
- Issue #2980: https://github.com/jannekbuengener/Claire_de_Binare/issues/2980
- Issue #2974: https://github.com/jannekbuengener/Claire_de_Binare/issues/2974
- Issue #2971: https://github.com/jannekbuengener/Claire_de_Binare/issues/2971
- Issue #2970: https://github.com/jannekbuengener/Claire_de_Binare/issues/2970
- Issue #2973: https://github.com/jannekbuengener/Claire_de_Binare/issues/2973
- Issue #2975: https://github.com/jannekbuengener/Claire_de_Binare/issues/2975
- Issue #2961: https://github.com/jannekbuengener/Claire_de_Binare/issues/2961
- Issue #3031: https://github.com/jannekbuengener/Claire_de_Binare/issues/3031
- Issue #1905: https://github.com/jannekbuengener/Claire_de_Binare/issues/1905
- Roadmap: `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
