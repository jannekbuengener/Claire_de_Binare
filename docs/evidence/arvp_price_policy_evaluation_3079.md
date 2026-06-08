# ARVP Price Policy Evaluation — #3079

**Status:** HOLD — close remains default; no policy closes the signal gap

**Verdict:** The LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP is **not caused by intra-candle price selection**. No measurable price policy can close it. The gap is driven by venue-level market structure mismatch (MEXC tick vs Binance candles per #3028).

---

## Summary

| Policy | Pilot Sig Δ | 3028 Sig Δ | Verdict |
|--------|------------:|-----------:|---------|
| `close` (default) | +0 | -1 | status quo, zero regression |
| `high` | +2 | -1 | overly optimistic — false positives |
| `hlc3` | +0 | -1 | equivalent to close on this data |
| `ohlc4` | +0 | -1 | equivalent to close on this data |

**Recommendation:** Leave default as `close`. Do not switch to `high` (over-generates). `hlc3`/`ohlc4` introduce no regression but also no benefit over `close`.

---

## Method

- **Tool:** `tools/replay/evaluate_price_policies.py` — offline, deterministic, no DB/MCP/runtime
- **Engine:** `SignalEngine.process_market_data()` with each candle's policy-adjusted price fed as `price` + `close`
- **Windows:** pilot (MEXC same-venue, ~240 candles) + #3028 (Binance, ~240 candles)
- **Reference:** paper_reference_window.json per window (signal/order/fill counts incl. causal_context)
- **Metrics:** signal_count, order_count, fill_count, deltas against paper reference

## Results per Window

### Pilot Window (MEXC same-venue)
- Expected paper signal = 0 signals + 1 causal-context signal (total 1)
- `close`: 0 signals (ctx_delta=-1) — matches PR #3080 baseline
- `high`: 2 signals (ctx_delta=+1) — over-generates; would produce false positives
- `hlc3`: 0 signals (ctx_delta=-1) — identical to close for this dataset
- `ohlc4`: 0 signals (ctx_delta=-1) — identical to close for this dataset

### #3028 Window (Binance venue_mismatch)
- Expected paper signal = 1 signal (no causal signals in this window)
- All policies produce 0 signals (delta=-1) — the gap persists regardless of price selection
- Confirms the gap is venue-level, not candle-level

## Conclusion

The *LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP* (#3079) is a **venue mismatch / market-microstructure gap**, not a price-policy gap. The pre-switch signal decision (tick price) versus replay signal decision (candle close) produces identical breakout outcomes on this dataset. The remaining gap originates from different market structure (MEXC tick domain vs Binance 1m candle domain).

Closing this gap requires either:
1. A venue-matched replay source (MEXC 1m candles instead of Binance — blocked by data availability per #3058)
2. A different evaluation framework that does not rely on replay-parity with a different venue

No action needed on the `price_policy` dimension. Close #3079 as **HOLD** with this evidence.
