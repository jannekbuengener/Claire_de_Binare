# Message Contracts - CDB Pipeline Interfaces

**Team:** B (Dev-Stream)
**Version:** 1.0
**Date:** 2025-12-29
**Status:** Deliverable

---

## Overview

This document defines the **message schemas** for all Redis Pub/Sub topics and streams in the CDB trading pipeline.

**Scope:**
- `market_data` topic (cdb_ws → cdb_signal)
- `signals` topic + `stream.signals` (cdb_signal → cdb_risk)
- `orders` topic + `stream.orders` (cdb_risk → cdb_execution)

**Contract Stability:**
- ✅ **Required fields** - MUST be present
- ⚠️ **Optional fields** - MAY be present
- 🔴 **Deprecated fields** - Will be removed in future versions

---

## 1. `market_data` Topic

**Producer:** `cdb_ws` (WebSocket Service)
**Consumer:** `cdb_signal` (Signal Engine)
**Transport:** Redis Pub/Sub + Stream (`stream.market_data`)

### Schema (Raw Trade Data - MEXC V3)

```json
{
  "source": "mexc",           // ✅ Required: Data source identifier
  "symbol": "BTCUSDT",        // ✅ Required: Trading pair
  "ts_ms": 1767028490485,     // ✅ Required: Timestamp (milliseconds)
  "price": "87616.18",        // ✅ Required: Trade price (string for precision)
  "qty": "0.00014501",        // ✅ Required: Trade quantity in base asset (BTC)
  "side": "buy",              // ✅ Required: "buy" | "sell"
  "type": "market_data"       // ⚠️ Optional: Event type discriminator
}
```

### Field Mapping Issues

**CRITICAL:** `qty` vs `volume` field mismatch

```python
# Current State (2025-12-29):
# cdb_ws publishes:    { "qty": "0.00014501" }
# cdb_signal expects:  { "volume": 0.0 }  ← Defaults to 0.0 if missing!

# Impact: SIGNAL_MIN_VOLUME check blocks all signals
# Workaround: SIGNAL_MIN_VOLUME="0" (disabled)
# TODO(#154): Fix field mapping in cdb_ws OR MarketData.from_dict()
```

### Required vs Optional

| Field | Status | Default | Notes |
|-------|--------|---------|-------|
| `source` | ✅ Required | - | Always "mexc" for MEXC V3 |
| `symbol` | ✅ Required | - | Trading pair (e.g., "BTCUSDT") |
| `ts_ms` | ✅ Required | - | Millisecond timestamp |
| `price` | ✅ Required | - | String for precision |
| `qty` | ✅ Required | - | Trade quantity (base asset) |
| `side` | ✅ Required | - | "buy" or "sell" |
| `type` | ⚠️ Optional | "market_data" | Event type |
| `pct_change` | ⚠️ Optional | None | Calculated by signal engine if missing |
| `volume` | 🔴 Missing | 0.0 | NOT sent by cdb_ws (should map from `qty`) |

---

## 2. `signals` Topic + `stream.signals`

**Producer:** `cdb_signal` (Signal Engine)
**Consumer:** `cdb_risk` (Risk Manager)
**Transport:** Redis Pub/Sub + Stream (`stream.signals`)

### Schema (Trading Signal)

```json
{
  "type": "signal",                   // ✅ Required: Event type discriminator
  "strategy_id": "paper",             // ✅ Required: Strategy identifier
  "symbol": "BTCUSDT",                // ✅ Required: Trading pair
  "side": "BUY",                      // ✅ Required: "BUY" | "SELL"
  "reason": "Momentum: +0.0076% > 0.005%",  // ✅ Required: Human-readable reason
  "timestamp": 1735494421,            // ✅ Required: Unix timestamp (seconds)
  "price": 87598.03,                  // ✅ Required: Signal price (float)
  "pct_change": 0.0076,               // ✅ Required: Percentage change trigger
  "signal_id": null,                  // ⚠️ Optional: Unique signal ID
  "bot_id": null,                     // ⚠️ Optional: Bot instance ID
  "direction": "",                    // 🔴 Deprecated: Use `side` instead
  "strength": 0.0,                    // 🔴 Deprecated: Not used
  "confidence": null                  // ⚠️ Optional: Signal confidence (0.0-1.0)
}
```

### Redis XADD Compatibility

**CRITICAL:** Redis `XADD` rejects `None` values!

```python
# Problem (2025-12-29):
# signal.to_dict() contained None values → Redis XADD failed

# Solution: Filter None values before publishing
{k: v for k, v in signal.to_dict().items() if v is not None}

# Implementation: services/signal/models.py:36-54
```

### Required vs Optional

| Field | Status | Default | Notes |
|-------|--------|---------|-------|
| `type` | ✅ Required | "signal" | Always "signal" |
| `strategy_id` | ✅ Required | - | Must be set in config |
| `symbol` | ✅ Required | - | Trading pair |
| `side` | ✅ Required | - | "BUY" or "SELL" |
| `reason` | ✅ Required | - | Explanation for signal |
| `timestamp` | ✅ Required | - | Unix timestamp (seconds) |
| `price` | ✅ Required | - | Price at signal generation |
| `pct_change` | ✅ Required | - | Percentage change trigger |
| `signal_id` | ⚠️ Optional | None | UUID (if generated) |
| `bot_id` | ⚠️ Optional | None | Multi-bot setups |
| `confidence` | ⚠️ Optional | None | Signal quality metric |
| `direction` | 🔴 Deprecated | "" | Legacy field, use `side` |
| `strength` | 🔴 Deprecated | 0.0 | Not used in current logic |

---

## 3. `orders` Topic (Future Scope)

**Producer:** `cdb_risk` (Risk Manager)
**Consumer:** `cdb_execution` (Execution Service)
**Transport:** Redis Pub/Sub + Stream (`stream.orders`)

### Schema (Placeholder - Not Yet Implemented)

```json
{
  "type": "order",
  "order_id": "uuid-here",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "quantity": 0.001,
  "order_type": "MARKET",
  "timestamp": 1735494500,
  "signal_id": "original-signal-id",
  "risk_approval": true
}
```

**Status:** Out of scope for v1 - To be defined by Team A (Infra-Stream)

---

## Contract Validation Rules

### Publisher Responsibilities

1. **All Required fields MUST be present**
2. **Types MUST match schema** (string vs float vs int)
3. **None values MUST be filtered** before Redis XADD
4. **Timestamps MUST be consistent** (ms for market_data, seconds for signals)

### Consumer Responsibilities

1. **Handle missing Optional fields** gracefully (use defaults)
2. **Validate Required fields** before processing
3. **Ignore unknown fields** for forward compatibility
4. **Log schema violations** (don't crash)

---

## Known Issues & TODOs

### Issue #1: `qty` → `volume` Field Mapping
**Impact:** HIGH
**Workaround:** `SIGNAL_MIN_VOLUME="0"` (disabled volume check)
**TODO(#154):**
- Option A: Rename `qty` → `volume` in cdb_ws publisher
- Option B: Map `qty` → `volume` in MarketData.from_dict()
- Option C: Use `qty` everywhere (rename volume checks)

**Recommendation:** Option B (backwards compatible)

### Issue #2: `pct_change` Calculation Location
**Impact:** MEDIUM
**Status:** ✅ RESOLVED (Issue #345)
**Solution:** PriceBuffer in cdb_signal calculates stateful pct_change if missing

### Issue #3: Signal `direction` vs `side` Redundancy
**Impact:** LOW
**Status:** Deprecated
**TODO(#154):** Remove `direction` field in v2.0 (breaking change)

---

## Schema Evolution Policy

### Adding New Fields
- ✅ **Allowed:** Add Optional fields (consumers ignore unknown fields)
- ⚠️ **Review:** Add Required fields (needs consumer update)

### Removing Fields
- ✅ **Allowed:** Remove Optional fields (mark as Deprecated first)
- 🔴 **Forbidden:** Remove Required fields (breaking change, needs migration)

### Changing Types
- 🔴 **Forbidden:** Change type of Required field (breaking change)
- ⚠️ **Review:** Change type of Optional field (needs consumer compatibility check)

---

## JSON Examples (Real Payloads)

### market_data (from Redis SUBSCRIBE)
```json
{"source": "mexc", "symbol": "BTCUSDT", "ts_ms": 1767028490485, "price": "87616.18", "qty": "0.00014501", "side": "buy"}
```

### signals (from Redis XREAD stream.signals)
```json
{"type": "signal", "strategy_id": "paper", "symbol": "BTCUSDT", "side": "BUY", "reason": "Momentum: +0.0076% > 0.005%", "timestamp": 1735494421, "price": 87598.03, "pct_change": 0.0076}
```

---

**Deliverable:** Contracts.md ✅
**Handover:** See HANDOVERS_TO_TEAM_A.md for required infrastructure support
