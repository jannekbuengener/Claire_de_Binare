# primary_breakout_v1

**Status:** canonical v1 strategy spec  
**Primary issue:** `#1578`  
**Strategy decision source:** `#1574`

## Identity

- `strategy_id = primary_breakout_v1`
- `symbol = BTCUSDT`
- `trade_side_mode = long_only`
- candle basis: existing `1m` candles only

## Core rule set

`primary_breakout_v1` is a regime-filtered channel-breakout strategy.

It may emit a `BUY` signal only when all of these are true:

1. `regime_id == TREND`
2. no active shutdown, kill-switch, or risk block is present
3. no entry cooldown from `min_minutes_between_entries` is active
4. `close_now > highest_high(entry_lookback_minutes) * (1 + breakout_buffer)`

It may emit a `SELL` signal when:

- `close_now < lowest_low(exit_lookback_minutes)`

Exits remain allowed even when new entries are blocked, so an existing position
can leave the market cleanly.

## No-trade zones

No new entry is allowed when any of these is true:

- `regime_id != TREND`
- market state or regime is stale
- market state or regime is missing
- risk, allocation, or kill-switch blocks trading
- entry cooldown is active

This v1 spec is fail-closed: if the required regime or market-state context is
not present and trustworthy, the strategy does not open a new position.

## Canonical v1 defaults

- `entry_lookback_minutes = 240`
- `exit_lookback_minutes = 120`
- `breakout_buffer = 0.0005`
- `min_minutes_between_entries = 60`
- `trade_side_mode = long_only`

These defaults mirror the canonical v1 parameter surface from `#1577`. If the
runtime config surface is not yet landed on local `main`, this issue-level
default set remains the repo-backed source for the strategy spec.

## Operator summary

- `BUY`: only when BTCUSDT is in `TREND`, the cooldown is clear, no core guard
  blocks the path, and price breaks above the configured entry channel with the
  breakout buffer.
- `SELL`: when price falls below the configured exit channel.
- `DO NOTHING`: when regime is not `TREND`, when regime or market state is
  stale or missing, when cooldown is active, or when core guardrails block new
  entries.

Operator meaning:

- this strategy is supposed to trade rarely and only in trend conditions
- it is allowed to stay inactive for long periods outside trend regimes
- v1 does not short and does not rotate across symbols

## Strategy vs core boundary

The strategy is responsible for:

- deterministic `BUY` / `SELL` signal generation
- breakout-entry logic
- channel-exit logic
- strategy-local metadata that explains why a signal was produced

The core remains responsible for:

- risk
- allocation
- kill-switch and shutdown enforcement
- run-mode policy
- `decision_contract_v1`
- execution approval and routing
- canonical publish / evidence / persistence

This boundary matches the docking intent in `#190`: strategy logic may become
adapter-owned later, but it must not bypass core safety or policy.

## Explicit v1 limits

Not part of `primary_breakout_v1`:

- no short side
- no multi-asset scope
- no adaptive parameter logic
- no mean-reversion hybrid
- no hidden extra indicators or scoring layers

## Adjacent anchors

- `#1575`: unit and scale drift must stay explicit; this spec does not overrule
  that contract risk
- `#1576`: technical adapter implementation should mirror this rule set exactly
- `#1573`: paper and shadow operationalization should use this operator view
- `#190`: adapter docking must preserve the strategy-versus-core boundary
- `#207`: backtest and validation should evaluate this exact v1 spec, not a
  wider variant
