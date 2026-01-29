# Cash-First Paper Trading Metrics (BTCUSDT)

What was measured
- Paper trading order_results for BTCUSDT
- Equity curve, trades, win/loss, max drawdown

How it was produced
- Parsed existing paper trading event log: logs/events/events_20260128.jsonl
- Used order_results events only (no new session run)
- Start equity: 1,000 (fictive)

Result
- Period (UTC): 2026-01-28T00:00:05Z → 2026-01-28T15:29:20Z
- Total trades: 2,927
- Win / Loss: 723 / 700 (win rate 50.81%)
- Max drawdown: 0.1731%
- Start equity: 1,000.00
- End equity: 999.9171 (net PnL -0.0829)

Definition of Done
- If the system started with 1,000, it would be 999.9171 at the end of this window.

Files
- metrics.json
- equity_curve.csv

Shortcut used
- Used existing paper trading logs instead of re-running the system.
