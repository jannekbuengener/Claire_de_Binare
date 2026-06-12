# CDB Profitability — Regime-Assigned MEXC Replay #3142

**Date:** 2026-06-12
**Parent:** #3032
**Issue:** #3142
**Status:** Complete — regime-assigned derived dataset created, full replay executed

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `git switch -c profitability/3142-regime-assigned-mexc-replay`, `python scripts/profitability/assign_regime_to_mexc_3091.py`, `python -m services.validation.strategy_replay_runner`, Python hashlib sha256, `rg` |
| `records_or_results` | Derived dataset (3496 rows, regime-assigned). Full replay PASS (run_id=replay-ab9333e31c8d-0001). gate_result=FAIL (zero trades, expected). deterministic_replay_ok=True. |
| `repo_crosscheck` | `services/regime/service.py:_derive_regime`, `services/regime/models.py:compute_adx/compute_atr`, `services/candles/service.py:_lookup_regime_id`, `infrastructure/compose/compose.blue.yml` |
| `impact_on_plan` | Derived approach works end-to-end. Regime distribution (99.5% HIGH_VOL_CHAOTIC, 0.5% TREND) is a legitimate finding. |
| `limitations` | No SurrealDB/Context Brain used. Regime labels are estimated, not runtime-derived. ATR threshold 2.0 on raw BTCUSDT prices produces predominantly HIGH_VOL_CHAOTIC. |

## Scope and Non-goals

### In scope
- Create derived file-backed dataset with estimated integer regime_id values.
- Run full primary_breakout_v1 replay against the derived dataset.
- Document method, parameters, regime distribution, replay result.
- Keep original raw MEXC dataset immutable.

### Non-goals
- No runtime, no DB, no Docker, no Redis.
- No core/strategy/runner/provider code changes.
- No Live-Go, no Echtgeld-Go, no LR status change.
- No claim that estimated labels are runtime-derived.

## Original Dataset Integrity

| Property | Value |
|----------|-------|
| SHA-256 | `d79a1c3c81191dcf4418ae0c2b2775a6f354ed0cc6801a6955904871c4077605` |
| Rows | 3,496 |
| regime_id state | All null (0 non-null) |
| Verified | SHA-256 matches dataset_spec.json; all OHLCV fields untouched |

The original raw dataset is **unaltered**. The derived dataset lives in a separate artifact directory.

## Regime-ID Semantics

Canonical mapping from `services/candles/service.py:_lookup_regime_id`:

| regime_id | Regime | Source |
|-----------|--------|--------|
| 0 | TREND | candles/service.py:198-199 |
| 1 | RANGE | candles/service.py:200-201 |
| 2 | HIGH_VOL_CHAOTIC | candles/service.py:202-203 |
| 3 | CRISIS | candles/service.py:204-205 |

Strategy contract (`PRIMARY_BREAKOUT_V1.md`):
- Entry requires `regime_id == TREND`
- No entry when regime is stale, missing, or blocked

## Offline Assignment Method

### Algorithm
Mirrors `services/regime/service.py:_derive_regime` and `services/regime/models.py:compute_adx/compute_atr`:

1. Rolling buffer of up to 70 candles (maxlen = max(adx_period, atr_period) * 5)
2. Compute ADX(14) and ATR(14) from buffer
3. Derive raw regime:
   - `ATR >= 2.0` → HIGH_VOL_CHAOTIC
   - `ADX >= 25.0` → TREND
   - `ADX <= 20.0` → RANGE
   - else → keep current regime
4. Apply confirmation bars (3 consecutive bars of same new regime)
5. Map to integer regime_id per canonical mapping

### Parameters
From `infrastructure/compose/compose.blue.yml`:

| Parameter | Value |
|-----------|-------|
| ADX period | 14 |
| ATR period | 14 |
| ADX trend threshold | 25.0 |
| ADX range threshold | 20.0 |
| ATR high vol threshold | 2.0 |
| Confirmation bars | 3 |
| Buffer maxlen | 70 |

### Regime Distribution

| regime_id | Regime | Count | Percentage |
|-----------|--------|-------|------------|
| 0 | TREND | 16 | 0.5% |
| 2 | HIGH_VOL_CHAOTIC | 3,480 | 99.5% |

**Finding:** The ATR threshold of 2.0 applied to raw BTCUSDT prices (~60,000) results in nearly universal HIGH_VOL_CHAOTIC classification. This is consistent with evidence from prior paper trade analysis (`docs/evidence/arvp_mexc_same_venue_acquisition_3086.md:92` confirms original MEXC paper used `regime_id=2`). This is a legitimate finding of the regime service configuration, not a bug in the assignment script.

First 14 candles (ADX/ATR warmup) default to TREND (regime_id=0). Confirmation bar logic is applied faithfully per `RegimeService._derive_regime` semantics.

### Script
`scripts/profitability/assign_regime_to_mexc_3091.py` — deterministic, no randomness, no external dependencies beyond stdlib.

## Derived Dataset

| Property | Value |
|----------|-------|
| Directory | `artifacts/candles/mexc_strict_window_3091_regime_assigned/` |
| candles.jsonl | 3,496 rows, integer regime_id |
| Rows with null regime_id | 0 |
| Rows with invalid regime_id | 0 |
| All regime_id in {0,1,2,3} | Yes |
| ts_ms sequence | Matches raw dataset exactly |
| OHLCV fields | Unchanged from raw |
| dataset_spec.json | Present |
| regime_assignment_manifest.json | Present (full method, parameters, distribution) |
| Labels marked estimated | Yes (in manifest and dataset_spec) |
| Evidence class | `controlled_lab_evidence` |

## Replay Result

### Command
```
python -m services.validation.strategy_replay_runner \
  --dataset-source file \
  --input-candles artifacts/candles/mexc_strict_window_3091_regime_assigned/candles.jsonl \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --adapter-id primary_breakout_runner_v1
```

### Result

| Metric | Value |
|--------|-------|
| Exit code | 0 |
| run_id | `replay-ab9333e31c8d-0001` |
| execution_provenance_id | `bt-c2230b20effa4aeb` |
| deterministic_replay_ok | True |
| gate_result | FAIL |
| failed_criteria | `min_closed_trades_total`, `min_profit_factor` |
| signals_total | 0 |
| buy_signals_total | 0 |
| sell_signals_total | 0 |
| closed_trades_total | 0 |
| data_integrity_ok | True |

### Interpretation
The replay ran successfully with deterministic integrity, but produced zero trades because 99.5% of the dataset is classified as HIGH_VOL_CHAOTIC (regime_id=2), which is a blocked regime per the primary_breakout_v1 strategy contract (`entry requires regime_id == TREND`).

The 16 TREND-assigned candles (first 14 warmup + rare transitions) constitute only 0.5% of the window and likely never align with a breakout condition.

## Evidence Classification

| Dimension | Status |
|-----------|--------|
| Dataset quality | `strict_campaign_grade` (inherited from raw) |
| Regime labels | Estimated (`controlled_lab_evidence`) |
| Replay execution | PASS (deterministic, no runtime) |
| Replay gate | FAIL (zero trades) |
| Strategy evidence | Blocked (HIGH_VOL_CHAOTIC prevents entry) |
| Overall | `controlled_lab_evidence` — no natural paper evidence chain |

## Decision for #3142

The objective is met:
- Derived regime-assigned dataset exists and is file-backed
- Full replay runs against `primary_breakout_v1` without code changes
- Original raw MEXC dataset is unchanged
- All regime labels are explicitly documented as estimated/controlled_lab_evidence
- No runtime, DB, Docker, or live-go was involved

The regime distribution (99.5% HIGH_VOL_CHAOTIC) is a legitimate finding. The ATR threshold of 2.0 on raw BTCUSDT prices (~60,000) drives this outcome. This is consistent with existing evidence (`docs/evidence/arvp_mexc_same_venue_acquisition_3086.md:92`).

## Limitations

1. Regime labels are estimated via offline ADX/ATR heuristic, not runtime-derived. They match what the live regime service would produce with identical parameters, but no runtime verification was performed.
2. The ATR threshold of 2.0 produces near-universal HIGH_VOL_CHAOTIC on BTCUSDT at ~60,000. This is a faithful mirroring of the committed regime service configuration, not a script artifact.
3. The strategy produced zero trades. This is consistent with the strategy contract (TREND required, HIGH_VOL_CHAOTIC blocked) and the regime distribution.
4. Evidence class remains `controlled_lab_evidence`. No `natural_paper_evidence` chain exists.
5. No profitability metrics were produced (0 trades = 0 return, 0 drawdown).
6. First 14 candles default to TREND regardless of actual price action (ADX/ATR require period+1 candles).

## Follow-ups

| Priority | Title | Rationale |
|----------|-------|-----------|
| Medium | [PROFITABILITY] Regime parameter calibration for BTCUSDT MEXC | ATR threshold 2.0 may need recalibration for BTCUSDT price scale; current config produces near-universal HIGH_VOL_CHAOTIC |
| Low | [PROFITABILITY] Generalize regime assignment to arbitrary datasets | Current script is MEXC-3091-specific; generalize for reuse across datasets |
| Low | [PROFITABILITY] Natural-paper regime-derived dataset | When regime service runs live during a paper campaign, capture runtime-derived regime_id for natural_paper_evidence |

## Produced Artifacts

| File | Path | Type |
|------|------|------|
| Generator Script | `scripts/profitability/assign_regime_to_mexc_3091.py` | Python |
| Derived Candles | `artifacts/candles/mexc_strict_window_3091_regime_assigned/candles.jsonl` | JSONL |
| Dataset Spec | `artifacts/candles/mexc_strict_window_3091_regime_assigned/dataset_spec.json` | JSON |
| Regime Manifest | `artifacts/candles/mexc_strict_window_3091_regime_assigned/regime_assignment_manifest.json` | JSON |
| Evidence Doc | `docs/evidence/profitability_regime_assigned_replay_3142.md` | Markdown (this file) |
| Replay Report | `artifacts/replay_reports/replay-ab9333e31c8d-0001/report.json` | JSON (generated) |

## Safety Boundaries

- LR remains NO-GO.
- Board `trade-capable` stage does not authorize live capital.
- No Live-Go, no Echtgeld-Go.
- No runtime, no DB, no Docker, no Redis.
- No core/strategy/runner/provider code changes.
- Regime labels are estimated, not runtime-derived.
- Evidence class is `controlled_lab_evidence`.
- Original raw dataset is unmodified.
- No silent synthetic metadata.

## Ref Issues

- #3142 — This issue
- #3032 — Parent: Profitability Engine
- #3141 — First Evidence Packet (MEXC 3091)
- #3091 — MEXC future capture (dataset source)
- #3086 — MEXC same-venue data acquisition
