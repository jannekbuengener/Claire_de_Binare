# Spec — `hh_hl_continuation_v1` (#4372 Slice 1)

**Contract version:** `cdb.batch_b.hh_hl_continuation_v1.spec.1`  
**strategy_id:** `hh_hl_continuation_v1`  
**Family:** trend_following  
**Owner-GO:** `GO_BATCH_B_IMPLEMENTATION_DUAL` comment `5196985942` (`jannekbuengener`)  
**Bound main SHA:** `279b7100df899276a92386ee83161734811e9e7c`  
**Lock:** `docs/contracts/batch_b_funnel_manifest.v1.json`  
**LR:** NO-GO · `execution_authorized=false` · `campaign_authorized=false`

## Hypothesis

Enter long continuation only after a confirmed rising swing-high and swing-low
structure (Higher High + Higher Low). Invalidate when a confirmed swing low
breaks the prior higher-low structure.

## Dedupe boundary

Price-structure continuation only — not moving-average trend following and not
channel / Donchian breakout.

## Required data

Closed 1m OHLC candles with strictly increasing `ts_ms` (60_000 ms cadence):
`open`, `high`, `low`, `close`. Symbol default `BTCUSDT`.

## Parameters (frozen, minimal)

| Parameter | Default | Range | Rationale |
|---|---:|---|---|
| `swing_left_bars` | 2 | fixed | Bars left of pivot that must be strictly dominated |
| `swing_right_bars` | 2 | fixed | Confirmation lag (bars right of pivot that must close first) |
| `min_minutes_between_entries` | 60 | fixed | Signal dedupe / cooldown |
| `trade_side_mode` | `long_only` | fixed | Slice scope |

No sweeps, no optimization, no result-driven selection.

## Candle / timestamp semantics

1. Candles are closed 1m bars ordered by `ts_ms`.
2. Decision at index `t` may use only candles `0..t` inclusive.
3. Minimum history before any pivot can confirm:
   `swing_left_bars + swing_right_bars` bars before the confirmation index.

## Swing definitions

### Swing High (pivot at index `p`)

Confirmed at confirmation index `c = p + swing_right_bars` when:

- `p >= swing_left_bars`
- `c` is a closed bar (decision index `>= c`)
- `high[p] > high[j]` for all `j` in
  `[p - swing_left_bars, p - 1] ∪ [p + 1, p + swing_right_bars]`

Equal highs never form a swing high (strict inequality).

### Swing Low (pivot at index `p`)

Confirmed at `c = p + swing_right_bars` when analogous strict inequality holds
on `low`.

### Pivot naming vs use

- Pivot **time** is the historical bar `p`.
- Pivot may be **used** only from confirmation bar `c` onward.
- Later candles must not rewrite earlier decisions (prefix invariance).

## Structure / entry

After each new confirmation at `t`:

- Maintain confirmed swing highs / lows in confirmation order.
- Entry requires ≥2 confirmed swing highs and ≥2 confirmed swing lows.
- Higher High: last swing-high price > prior swing-high price.
- Higher Low: last swing-low price > prior swing-low price.
- Long entry on bar `t` when HH+HL first holds, cooldown allows, and flat.

## Invalidation / exit

While long, exit on the confirmation bar of a new swing low whose price is
strictly below the previous confirmed swing-low price (structural HL failure).

### Single-run closeout

If still long at the final candle, close at that candle’s `close` with reason
`series_end_closeout`.

## Signal dedupe

- At most one entry per confirmation event / bar.
- `min_minutes_between_entries` cooldown between entries.

## Fail-closed

Reject / no-trade report on: empty series; missing OHLC; NaN/Inf; non-positive
prices; `high < low`; `high < open|close` or `low > open|close`; duplicate or
non-increasing `ts_ms`; non-1m cadence; wrong symbol.

## No-lookahead contract

Prefix invariance: decisions on prefix `N` equal the first `N` decisions of
prefix `N+M`.

## Replay-only boundary / non-goals

Replay research only. No paper/live/echtgeld, Stage B, OOS, stress, campaign,
promotion, merge, productive signal publish, risk/execution changes.

## Allowed claims

- Spec is deterministic and reviewable.
- Adapter is executable in single-run replay.
- Registry reaches the runner.

## Forbidden claims

- Profitability, promotability, Stage-A pass, campaign authorization.
