# Batch-A Established Strategy Funnel Contract v1

**Status:** Slice 2a shared contract surface (#4031)  
**Parent control:** #4029  
**Candidate lock:** #4030 (`BATCH_A_LOCKED`)  
**Live-Readiness:** NO-GO  
**ranking_ready:** false  

## Purpose

Batch A is the locked ten-candidate development funnel for established strategy
screening. Slice **2a** delivers the shared machine-readable contract, development
window selector, Binance window-bank dataset adapter, and strategy registry
metadata. Strategy signal logic and Stage-A campaign execution remain out of
scope until slices **2b–2d** and WP3 (#4032).

## Canonical artifacts

| Artifact | Path |
|---|---|
| Batch manifest | `docs/contracts/batch_a_funnel_manifest.v1.json` |
| JSON Schema | `docs/contracts/batch_a_funnel_manifest.v1.schema.json` |
| Strategy registry | `core/replay/batch_a_strategy_registry.py` |
| Development selector | `tools/market_data/development_window_selector.py` |
| Dataset adapter | `core/replay/binance_window_bank_adapter.py` |
| Stage-A scenario scaffold | `tests/fixtures/arvp/batch_a_scenario_matrix_v1.json` |

## Locked candidates (10)

All parameters are frozen from #4030. No optimization or post-hoc changes.

| strategy_id | Status | Slice |
|---|---|---|
| `breakout_volatility_filter_v1` | implementation_pending | 2b |
| `volatility_breakout_v1` | implementation_pending | 2b |
| `bollinger_squeeze_breakout_v1` | implementation_pending | 2b |
| `atr_expansion_v1` | implementation_pending | 2b |
| `ema_trend_follow_v1` | implementation_pending | 2c |
| `ma_crossover_v1` | implementation_pending | 2c |
| `opening_range_breakout_v1` | implementation_pending | 2c |
| `roc_breakout_confirm_v1` | **implemented** | 2d |
| `range_mean_reversion_v1` | **implemented** (reuse) | 2d |
| `momentum_capture_v1` | **implemented** (reuse) | 2d |

Excluded from Batch A: #3990 three (`primary_breakout_v1`, `donchian_breakout_v1`,
`breakout_trend_filter_v1`) and `trend_regime_gated_ma_cross_v1`.

## Development selection (39 monthly windows)

- **Venue:** Binance spot BTCUSDT 1m
- **Purpose:** `development` only
- **Overlap class:** `monthly` only (quarterly/yearly excluded)
- **Count:** 39 non-overlapping windows
- **Selection SHA-256 (WP1 lock):** `3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52`

Selector API:

```python
from tools.market_data.development_window_selector import (
    load_window_bank_manifest,
    select_batch_a_development_windows,
)

manifest = load_window_bank_manifest()
selection = select_batch_a_development_windows(manifest)
assert selection.window_count == 39
assert selection.selection_sha256 == "3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52"
```

## Dataset adapter API

Read-only loader for replay runners (RMR/Momentum and later slices):

```python
from core.replay.binance_window_bank_adapter import load_binance_window_dataset

dataset = load_binance_window_dataset("binance_1m_month_2021_01", warmup_candles=240)
candles = dataset.candles  # ordered OHLCV + optional regime_id
```

Regime enrichment is passed through when present in source candles; the adapter
does not compute regime labels.

## Implementation-pending semantics

Only `range_mean_reversion_v1` and `momentum_capture_v1` are marked
`implemented` with adapter IDs. All ten Batch-A runners are now executable via
`strategy_replay_runner` dispatch (slice 2d).

## Non-goals (slice 2a)

- No new strategy signal logic
- No Stage-A screening campaign (#4032)
- No parameter search or promotion
- No runtime BLUE/RED or workflow changes
- No ranking_ready change

## Safety

- LR **NO-GO**
- Binance evidence ≠ MEXC production confirmation
- Technical implementation readiness ≠ economic PASS
