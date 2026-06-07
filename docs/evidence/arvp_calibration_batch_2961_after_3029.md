# ARVP Calibration Batch — 2-Window Bank (2026-06-06)

Status: Repo-backed calibration report for `#2961` — 2-window batch calibration evidence
Parent anchor: `#1900`
Pilot source: `#1932`
New window source: `#3028` (merged as `af01c76c`)
Docs reconciled per: `#3029` (merged as `ed6613625`)
Live-readiness implication: none
Live/Echtgeld implication: none

## Context

This document records the results of the first ARVP calibration batch execution
against the existing 2-window bank. Per the `#2961` prompt contract and operator
GO on 2026-06-06:

- **Pilot window** (`paper_1909_1776991354682`): baseline artifacts reused and
  validated with a fresh replay against current code (`ed6613625`)
- **New window** (`0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab`, #3028): replay was
  attempted but is **HOLD** due to insufficient candle data at the window's
  timestamp range (2026-06-06 00:28–00:30 UTC) in the `candles_1m` table

## Window Set

### Window 1: Pilot — `paper_1909_1776991354682`

| Property | Baseline (replay-8049a7afc831-0001) | Validation (replay-16a0a8f6d92f-0001) |
|----------|--------------------------------------|--------------------------------------|
| Code commit | `1e16e677` | `ed6613625` (current HEAD) |
| Candle source | DB (`dataset_source=db`) | File (DB-exported, gap-free) |
| Dataset fingerprint | `3280894a4eef92604ea7175629c612097fd1f8a2dc04bab6a2258d26216bfb41` | `25ae0aa84735dc2d1654877aa48baf5c2eb1479616ac56a34b8aaf4ca5eb39ce` |
| Comparison fingerprint | `4a895743104d126fe789430b44f69d59017c0b3acd5f5f2a62520e9ef9d92a79` | `d71a4abdd5a89acbf1799cc4e837e845affc4c25b9eaf6c2460b81002b529e0f` |
| Calibration fingerprint | `5fc1ec6c6657ece5561a46805c59a0bf52bf4d171ace3a5b16ceaeeee74d764e` | `965fb48891129b8a1299804d679ba16b4e922242abb9601dfdca667e028c9da6` |
| Order count delta | -1 | -1 |
| Fill count delta | -1 | -1 |
| Signal count delta | 0 | 0 |
| Inferred unfilled delta | 0 | 0 |
| Drift classification | pessimistic | pessimistic |
| Status | aligned | aligned |

The validation replay confirmed **identical deltas and drift classification**.
Both runs show the simulator missed one paper order+fill (pessimistic drift).

### Window 2: New — `0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab`

**Status: HOLD_REPLAY_DATASET_MISSING**

| Property | Value |
|----------|-------|
| Paper window start (UTC) | 2026-06-06 00:28:12 |
| Paper window end (UTC) | 2026-06-06 00:30:12 |
| Events | SIGNAL + DECISION + ORDER(paper_) + FILL (4 events) |
| Candle data required | ~242 continuous 1m candles (240 warmup + 2 live) |
| Candles available in DB | 163 in wider window, sparse (6-min intervals, gaps) |
| Warmup range start needed | ~1780691280000 (continuous for 240 min from live start) |
| Candle continuity in needed range | BROKEN — gap at 1780705440000→1780705620000, sparse throughout |

**Root cause**: The candles service (`cdb_candles`) was not running continuously
during the period when the #3028 paper window was produced. The `candles_1m`
table has intermittent candles (6-minute and 3-minute gaps) around this
timestamp range. The replay runner's strict cadence validation
(`_validate_candle_series` in `dataset_provider.py:71-115`) requires exact 60s
intervals between all consecutive candles.

**No existing candle file** in `artifacts/backtests/` covers timestamps beyond
2026-04-19 (latest: `1776211140000`). The new window falls on 2026-06-06
(`1780705692551+`), which is outside the range of any previously backfilled
candle dataset.

## Calibration Results

### Pilot Window

```
Drift classification: pessimistic
  fill_count_delta:   -1 (pessimistic, proxy)
  inferred_unfilled:   0  (neutral, proxy)
Paper orders/fills:   1 / 1
Replay orders/fills:  0 / 0
```

The simulator missed one real paper opportunity in the 1-minute window.
Classified as **pessimistic** drift (replay underperforms paper).
Classification is consistent across baseline and fresh validation (code
commit difference did not alter the delta).

### New Window

The replay for the new window could not be executed due to data insufficiency.
Compare + calibration are therefore blocked for this window.

## Comparison Fingerprints (Per Window)

| Window | Comparison FP | Calibration FP |
|--------|--------------|----------------|
| Pilot (baseline) | `4a895743104d126fe789430b44f69d59017c0b3acd5f5f2a62520e9ef9d92a79` | `5fc1ec6c6657ece5561a46805c59a0bf52bf4d171ace3a5b16ceaeeee74d764e` |
| Pilot (validation) | `d71a4abdd5a89acbf1799cc4e837e845affc4c25b9eaf6c2460b81002b529e0f` | `965fb48891129b8a1299804d679ba16b4e922242abb9601dfdca667e028c9da6` |
| New window (#3028) | N/A (HOLD) | N/A (HOLD) |

## Mismatch Classification

| Delta | Value | Classification | Evidence Level |
|-------|-------|---------------|----------------|
| order_count_delta | -1 | pessimistic | proxy (no explicit reject data) |
| fill_count_delta | -1 | pessimistic | proxy (fill counts may mask reject reasons) |
| inferred_unfilled_count_delta | 0 | neutral | proxy (derived from orders - fills) |
| signal_count_delta | 0 | N/A | direct (exact match) |

## Timelines and Clock-Data

- Pilot window start: 2026-04-24T00:42:00Z — end: 2026-04-24T00:43:00Z
- New window start: 2026-06-06T00:28:12Z — end: 2026-06-06T00:30:12Z
- Both windows use `utcnow` / `timestamp_ms` anchors; no timezone ambiguity.
- Replay window_start reflects warmup origin, not paper window origin. This
  is expected — the compare logic uses the paper window bounds for alignment.

## Runtime Safety Preflight

| Check | Result |
|-------|--------|
| LR status | NO-GO — confirmed |
| Live-Go | No |
| Echtgeld-Go | No |
| MOCK_TRADING | true (confirmed via `docker exec cdb_execution printenv MOCK_TRADING`) |
| DB user for replay | `claire_user` (superuser-like, PASS_WITH_LIMITS: SELECT-only, no mutation, no secrets) |
| cdb_readonly role | Exists but not used by replay runner (uses `POSTGRES_USER` env) |
| Docker stack | Running, healthy, all services up |
| No exchange orders | Confirmed — MOCK_TRADING=true, no live credentials used |
| No secrets in outputs | All env redacted, no DSN/password exposed |

## Artifact Inventory

```
artifacts/calibration/2961/
  pilot_baseline/
    paper_reference_window.json        — paper reference v1
    replay_report.json                 — replay report (original, replay-8049a7afc831-0001)
    shadow_comparison.json             — baseline shadow comparison
    shadow_comparison_summary.md
    simulator_calibration_report.json  — baseline calibration report
    simulator_calibration_summary.md
    operator_summary.json
  pilot_validation/
    replay-16a0a8f6d92f-0001/         — fresh replay (current code)
      report.json, manifest.json, config.resolved.json, operator_summary.json,
      env_redacted.txt, audit.log
  pilot_validation_compare/
    replay-16a0a8f6d92f-0001/
      shadow_comparison.json           — validation shadow comparison
      shadow_comparison_summary.md
  pilot_validation_calibration/
    replay-16a0a8f6d92f-0001/
      simulator_calibration_report.json — validation calibration report
      simulator_calibration_summary.md
```

## Honest Limits

- `batch_seed_count=2` (pilot + #3028 reference window)
- `calibration_executed_count=1` (pilot only; #3028 replayed not run)
- `multi_window_coverage=HOLD_MISSING_COMPARISON_GRADE_WINDOWS` (target 3+)
- `new_window_replay=HOLD_REPLAY_DATASET_MISSING` (sparse candle data)
- `regime_scorecard=unavailable` (no regime segments in comparison input)
- `explicit_reject_evidence=unavailable` (no `fill_rate_delta` in any calibration report)
- No live-readiness or capital approval implication introduced
- No runtime, paper execution, or stimulus publish occurred

## Next Steps

1. **Replay for new window #3028** requires backfilled candle data. Options:
   - Backfill `candles_1m` for the 2026-06-06 window from Binance/Exchange
   - Run the `cdb_candles` service long enough to accumulate continuous 1m data
   - If backfill is not possible, document that the #3028 window is comparison-proof
     only (paper events show the expected chain was produced) but not
     replay-calibratable
2. **3+ window coverage (#2971)** still requires an additional comparison-grade
   paper reference window with its own candle data
3. **Calibration report** for the new window can be produced once replay is
   feasible
4. **Regime scorecards** remain out of scope for both windows

## Guardrails

- LR remains **NO-GO**
- No Live-Go / Echtgeld-Go implication
- No runtime execution beyond replay/compare/calibration
- No stimulus publish
- No DB mutation
- No strategy code changes
- No exporter contract changes

## Status

`#2961` calibration batch executed on 2-window bank. Pilot fully calibrated
(pessimistic drift, confirmed). New window on HOLD due to candle data gap.

Closing decision: #2961 acceptance criteria are **partially met**:
- ✅ at least 2 concrete paper reference windows selected (pilot + #3028)
- ✅ replay-vs-paper compare reproducible for pilot window
- ✅ per-window deltas and fingerprints documented
- ✅ mismatches classified explicitly (pessimistic drift)
- ✅ no live-readiness or capital approval implication
- ❌ calibration for #3028 window not possible (HOLD_REPLAY_DATASET_MISSING)
- ❌ batch comparison across all windows not complete (1 of 2 windows)

---

## Post-#3031 Status Update (2026-06-07)

**#3031 resolved the candle data gap.** PR #3051 (merged ca9a17a4) backfilled 244
continuous 1m BTCUSDT candles from Binance Spot API for the #3028 window.

**Calibration for #3028 window is now completed.** See the updated evidence document:
[`docs/evidence/arvp_calibration_batch_2961_after_3031.md`](arvp_calibration_batch_2961_after_3031.md)

**Critical caveat:** The Binance dataset is `venue_mismatch=true` — not same-venue
MEXC evidence. The #3028 calibration is a functional pipeline validation, not pure
simulator evidence. See the new document for full classification and limitations.

**Updated status:** #2961 acceptance criteria are now fully met (with explicit
venue/regime limitations documented). The 2-window calibration batch is complete.
