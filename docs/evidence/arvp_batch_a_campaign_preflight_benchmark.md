# ARVP Batch-A Stage-A Campaign Preflight Benchmark (A4)

**Date:** 2026-07-13  
**Issue:** [#4032](https://github.com/jannekbuengener/Claire_de_Binare/issues/4032)  
**Source SHA:** `d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a` (gate merge #4058)  
**Plan:** `arvp-funnel-v1.1-2026-07-13` — GO amendment **A4**  
**LR:** NO-GO | **`ranking_ready`:** `false`

---

## Scope

Conservative preflight before the locked Stage-A matrix (390 coordinator jobs / 780 scenario runs: 10 strategies × 39 development windows × 2 scenarios).

| Constraint | Value |
|------------|-------|
| Max parallel workers (benchmark) | 2 |
| Scenarios | `baseline`, `pessimistic_execution` |
| Sample windows | 3 locked development months |
| Runner families | 4 (2 regime-enriched + 2 non-regime) |

---

## Sample matrix (12 jobs)

| Family | Strategy | Adapter | Regime |
|--------|----------|---------|--------|
| Regime / reuse | `momentum_capture_v1` | `momentum_capture_runner_v1` | yes |
| Regime / reuse | `range_mean_reversion_v1` | `range_mean_reversion_runner_v1` | yes |
| Breakout | `breakout_volatility_filter_v1` | `batch_a_shadow_runner_v1` | no |
| Trend | `ema_trend_follow_v1` | `batch_a_shadow_runner_v1` | no |

**Windows:** `binance_1m_month_2017_10`, `binance_1m_month_2017_11`, `binance_1m_month_2018_03`

---

## Timing (live, 2026-07-13)

| Metric | Value |
|--------|-------|
| Jobs total | 12 |
| Jobs PASS | 12 |
| Jobs FAIL | 0 |
| Wall clock (2 workers) | 21.37 s |
| Median job time | 3.252 s |
| **p95 job time** | **3.677 s** |
| Max job time | 3.755 s |

---

## Artifacts

| Metric | Value |
|--------|-------|
| Total artifact bytes (12 jobs) | 82,211 |
| Median bytes / job | ~6,850 |
| **Extrapolated Stage-A artifacts (390 jobs)** | **~2.6 MB** (scenario bundles only; excludes queue/metrics JSON) |

---

## Disk headroom

| Metric | Value |
|--------|-------|
| Free disk before benchmark | 65.64 GB |
| Free disk after benchmark | 65.64 GB |
| Campaign `min_free_disk_gb` gate | 5.0 GB |
| Headroom vs extrapolated artifacts | >> adequate |

---

## Campaign duration estimate (conservative)

| Mode | Estimate |
|------|----------|
| Sequential coordinator (1 job/cycle) | 390 × 3.677 s p95 ≈ **24 min** replay wall |
| 2-worker sample benchmark throughput | ~12 min equivalent replay wall |
| Full matrix scenario runs | **780** (`baseline` + `pessimistic_execution` per job) |

---

## RAM

Process RSS sampling unavailable in the benchmark shell (`psutil` not installed). Replay jobs are short-lived subprocesses; coordinator remains single-process. **No RAM blocker observed** for the 12-job sample at 2-worker concurrency.

---

## Boundaries

- Binance `historical_cross_venue_research` / controlled-lab window bank only
- No live capital, no promotion, LR **NO-GO**
- Preflight does not assert survivor counts or gate outcomes

---

## Raw summary

Machine-readable run summary (local, not versioned): `artifacts/evidence/batch_a_preflight_tmp/summary.json`
