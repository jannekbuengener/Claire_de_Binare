# Market State Input Contract V1

**Version**: V1
**Owner**: BLUE (Signal/Market Data Services)
**Consumer**: Risk Service (`cdb_risk`)
**Status**: Active
**Created**: 2026-02-14

## Purpose

`market_state` is the BLUE-owned input contract that provides market context data to the Risk Service (`cdb_risk`) for trade decisions. Risk does not compute any derived values - it validates inputs and blocks deterministically when required fields are missing or invalid.

## Ownership Model

| Component | Owner | Responsibility |
|-----------|-------|----------------|
| `market_state` production | BLUE | Compute and deliver all required fields |
| `market_state` validation | Risk Service | Validate presence, block if missing (fail-closed) |
| Return calculations | BLUE | `return_1m`, `return_5m`, `price_change_5m` |
| Regime classification | BLUE | `regime_id` |

## Required Fields (V1)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `return_1m` | `float` | percentage points | 1-minute price return: `((close_now - close_1m_ago) / close_1m_ago) * 100` |
| `return_5m` | `float` | percentage points | 5-minute price return: `((close_now - close_5m_ago) / close_5m_ago) * 100` |
| `price_change_5m` | `float` | percentage points | Absolute 5-minute price change (for volatility check) |

## Required Fields for Data Freshness (V1)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `ts_ms` | `int` | milliseconds | Timestamp of market state snapshot (used for RC_003 staleness check) |
| `last_tick_ts_ms` | `int` | milliseconds | Timestamp of most recent trade tick (used for RC_004 data silence check) |

### last_tick_ts_ms Semantics

- **Source**: Updated on each processed trade event (trade `ts_ms`)
- **Monotonic Guard**: Only updates if `new_ts_ms > prev_ts_ms` (protects against out-of-order trades)
- **NOT updated**: On candle window close, sweep, or timer events
- **Fail-closed**: If missing/None → RC_004 BLOCK (data_silence_s cannot be computed)

## Optional Fields (V1)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `regime_id` | `int` | enum | Market regime: 0=trending, 1=ranging, 2=volatile, 3=crisis |
| `symbol` | `string` | - | Trading pair (e.g., "BTCUSDT") |

## Calculation Semantics

### return_1m
```
return_1m = (current_close - close_1_minute_ago) / close_1_minute_ago
return_1m_pct = return_1m * 100
```
- **Range**: Typically -5.0 to +5.0 (±5%)
- **Safety threshold**: `return_1m > -2.0` (RC_002 blocks if ≤ -2.0)

### return_5m
```
return_5m = (current_close - close_5_minutes_ago) / close_5_minutes_ago
return_5m_pct = return_5m * 100
```
- **Range**: Typically -10.0 to +10.0 (±10%)
- **Safety threshold**: `return_5m > -5.0` (RC_002 blocks if ≤ -5.0)

### price_change_5m
```
price_change_5m = abs((current_close - close_5_minutes_ago) / close_5_minutes_ago)
price_change_5m_pct = price_change_5m * 100
```
- **Range**: 0.0 to ~10.0 (0-10%)
- **Safety threshold**: `abs(price_change_5m) <= 10.0` (RC_002 blocks if > 10.0)

## Invariants

1. **Risk does not compute returns**: Risk Service receives pre-computed values; it never accesses candle history.

2. **Fail-closed on missing required fields**:
   - `return_1m`, `return_5m`, `price_change_5m` is `None` → `BLOCK` with `RC_002`
   - `last_tick_ts_ms` is `None` → `BLOCK` with `RC_004` (data_silence_s cannot be computed)

3. **No silent defaults**: Risk never substitutes default values (e.g., 0.0) for missing data.

4. **No fallback calculation**: If BLUE fails to deliver, Risk blocks - there is no "best effort" path.

5. **Monotonic timestamps**: `last_tick_ts_ms` only increases (protects against replay/out-of-order data).

## Enforcement

**Code Reference**: `services/risk/service.py:252-259`

```python
# 1) Safety/Anomaly
if return_1m is None or return_5m is None or price_change_5m is None:
    return DECISION_BLOCK, RC_002, evidence
if (
    return_1m <= DECISION_THRESHOLDS["return_1m_min"]
    or return_5m <= DECISION_THRESHOLDS["return_5m_min"]
    or abs(price_change_5m) > DECISION_THRESHOLDS["price_change_5m_abs_max"]
):
    return DECISION_BLOCK, RC_002, evidence
```

## Example Payload

```json
{
  "market_state": {
    "return_1m": -0.23,
    "return_5m": 0.12,
    "price_change_5m": 0.35,
    "ts_ms": 1771074848286,
    "last_tick_ts_ms": 1771074848100,
    "regime_id": 0,
    "symbol": "BTCUSDT"
  }
}
```

## Versioning

| Version | Status | Changes |
|---------|--------|---------|
| V1 | Active | Initial contract with 3 required fields |
| V2 | Planned | May add `vwap_deviation`, `order_book_imbalance` |

Extensions to V2 will be additive - V1 fields remain required.

## Runtime Evidence

This contract was formalized based on runtime validation findings:

- **Report**: `P1_RUNTIME_DOD_REPORT.md` (P1-01 FAIL: RC_002 blocks 100%)
- **Evidence Bundle**: `runtime_evidence_bundle_P1.json`
- **Root Cause**: `market_state` fields were `None` → immediate RC_002 block

---

*Related: [Governance README](README.md) | [Reason Codes](../../services/risk/reason_codes.py)*
