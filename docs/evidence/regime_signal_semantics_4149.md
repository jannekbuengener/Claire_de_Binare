# Evidence: Regime/Signal Semantics Correction (#4149)

**Date:** 2026-07-29  
**Parent:** #4147  
**Dependency:** #4148 (CLOSED)  
**Status:** Local validation evidence (Development semantics; not LR-Go)

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_tool_status: absent
context_trust_level: none
records_found: 0
```

## Before / After Semantics

| Surface | Before | After |
|---|---|---|
| High-Vol gate | absolute ATR vs Compose `2.0` | `atr/close` vs `0.001` (`atr_over_close`) |
| `.env.example` | `0.03` (contradictory) | `0.001` + unit docs |
| `pct_change_15m` | tick-to-tick alias | event-time lookback via `SIGNAL_LOOKBACK_MIN` |
| Missing replay regime | `COALESCE(regime_id, 0)` → TREND | `NULL` preserved (no silent TREND) |

## Development-Window Evidence

- Locked Batch-A development window count: **39** (`LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS`).
- Window-bank path `artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m` was **not present** in this Cloud Agent workspace.
- Therefore full 39-window before/after distribution could not be regenerated here.
- Scale-stability and boundary behaviour are covered by deterministic unit/contract tests under `tests/unit/regime` and `tests/unit/signal`.
- Historical calibration reference (not used for PnL selection): `docs/evidence/profitability_btcusdt_regime_calibration_3032.md` (ATR_pct ~0.1% near p75).

### Synthetic relative-scale check (unit)

Identical `atr/close = 0.0015` at close `100` and `60000` both classify `HIGH_VOL_CHAOTIC` under threshold `0.001`.

OOS / Stress / Stage-B windows were **not** opened or used for selection.

## Safety

- LR remains **NO-GO**.
- Risk thresholds (`signal_pct_change_15m_min`, staleness, kill) not loosened.
- No Docker/runtime/DB/MCP mutation in this evidence pack.
