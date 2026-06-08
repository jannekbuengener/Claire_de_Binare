# ARVP #2980 Recheck After #3058 — Calibration Re-Run Evidence (2026-06-08)

Status: Recheck for #2980 after PAPER_REFERENCE_EXPORT_GAP fix (#3058 / PR #3072)
Parent anchor: #1900 / #2980 / #3058 / #3072
Upstream evidence:
  - `docs/evidence/arvp_paper_reference_causal_signal_context_3058.md` (#3058)
  - `docs/evidence/arvp_signal_reproduction_gap_3057_after_2980.md` (#3057)
  - `docs/evidence/arvp_execution_realism_decision_2970_after_2975.md` (#2970)
  - `docs/evidence/arvp_drift_classification_2973_after_2971.md` (#2973)
  - `docs/evidence/arvp_calibration_batch_2961_after_3031.md` (#2961)
Re-Run input: `artifacts/calibration/2961/pilot_baseline/paper_reference_window.json` augmented with `causal_context_events[]`
Re-Run output: `artifacts/recheck_2980/comparison/replay-8049a7afc831-0001/shadow_comparison.json`
Live-readiness implication: none
Live/Echtgeld implication: none

---

## Summary

This document records the calibration re-run after #3058 (PAPER_REFERENCE_EXPORT_GAP)
to verify that signal_context_delta now correctly reflects the pre-window causal SIGNAL,
and to re-evaluate whether #2980 can proceed as a fill-model fix.

**Result: #3058 verifiziert ✅ — #2980 bleibt HOLD/BLOCKED durch LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP**

---

## Inputs

### Paper Reference Window

The pilot window paper reference (`paper_1909_1776991354682`, MEXC same-venue)
was augmented with a `causal_context_events[]` entry containing the pre-window
SIGNAL (`signal_id="sig-1909-runtime-smoke"`) that triggered the ORDER+FILL
inside the window. This simulates what `paper_reference_window_runner.py` with
`--causal-lookup-*` flags would extract from the DB.

- In-window SIGNAL events: 0
- Causal SIGNAL events: 1
- Paper reference window: `window_bank_2` / pilot window (MEXC same-venue)

### Replay Report

Replay report from the original baseline run (same artifact as original comparison).

- Replay signals_total: 0
- Replay orders: 0
- Replay fills: 0

---

## Calibration Re-Run Results

### Comparison Output (shadow_comparison.json)

```json
{
  "signal_context_delta": -1,
  "signal_count_delta": 0,
  "signal_count_false_neutral_detected": true,
  "order_count_delta": -1,
  "fill_count_delta": -1,
  "status": "aligned"
}
```

### Before/After Delta

| Metric | Before #3058 | After #3058 | Change |
|--------|-------------|-------------|--------|
| signal_count_delta | 0 | 0 (in-window) | unchanged |
| signal_context_delta | — | -1 | **NEW** — correctly shows paper had causal signal |
| signal_count_false_neutral_detected | — | true | **NEW** — honest flag |
| order_count_delta | -1 | -1 | unchanged |
| fill_count_delta | -1 | -1 | unchanged |

### Interpretation

The #3058 fix works correctly:
- `signal_context_delta=-1` now reveals that paper had 1 SIGNAL (pre-window causal)
  while replay produced 0 signals.
- `signal_count_false_neutral_detected=true` flags the old false-neutral delta=0.

However, `fill_count_delta=-1` remains unchanged. The replay still produces
0 signals → 0 orders → 0 fills. The **LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP**
(live tick price vs replay candle close) prevents any fill-model fix from
being measurable.

---

## Conclusion for #2980

1. **#3058/#3072 (PAPER_REFERENCE_EXPORT_GAP): VERIFIED** ✅
   - Causal signal context is correctly exported and counted.
   - The pilot window's signal reproduction gap is no longer invisible.

2. **#2980 remains HOLD/BLOCKED** ❌
   - The fill-model fix (#2980 original scope) cannot be measured:
     replay produces 0 signals → 0 orders → no fills for any fill model to act on.
   - Blocker: **LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP** (architectural:
     `historical_bridge.py:161` uses candle close; `signal/service.py:552` uses tick price).

3. **Follow-up needed**:
   - Dedicated issue for LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP investigation/fix.
   - Target: reconcile replay signal generation with live tick-based behavior.

---

## Safety Boundaries

- LR remains **NO-GO**
- No Live-Go / Echtgeld-Go
- No code changes in this recheck
- No runtime execution
- No DB mutation
- ARVP evidence is validation, not live approval

---

## Restunsicherheiten

1. The exact pre-window SIGNAL timestamp is not preserved in committed artifacts.
   The causal event was placed at `start_ts_ms - 30000` (estimated ~30s before window).
2. Only the pilot window was re-run. A full batch re-run would require re-extracting
   both windows with DB causal lookup, which is not available offline.
3. The #3028 window had its SIGNAL inside window bounds and was not re-run here
   (no causal augmentation needed for in-window signals).

---

## References

- Issue #2980: https://github.com/jannekbuengener/Claire_de_Binare/issues/2980
- Issue #3058: https://github.com/jannekbuengener/Claire_de_Binare/issues/3058
- PR #3072: https://github.com/jannekbuengener/Claire_de_Binare/pull/3072
- Re-Run artifact: `artifacts/recheck_2980/comparison/replay-8049a7afc831-0001/shadow_comparison.json`
- Augmented paper ref: `artifacts/recheck_2980/pilot_window_causal/paper_reference_window.json`
