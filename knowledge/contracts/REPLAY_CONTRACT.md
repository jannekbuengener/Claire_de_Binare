# Replay Contract — stream.fills Schema

**Purpose**: Canonical specification for deterministic replay of paper-trading sessions.

**Source**: `services/execution/models.py:139-177` (`ExecutionResult.to_dict()`)

**Stream**: `stream.fills` (Redis Stream, maxlen=10000)

---

## Stream Entry Format

### Redis Stream Structure

```python
# XREVRANGE stream.fills + - COUNT 1
[
  (
    "1734962388123-0",  # Stream ID (millisecond timestamp + sequence)
    {
      # Field-value pairs (all strings in Redis)
      "type": "order_result",
      "order_id": "e2e-test-1734962388000",
      "status": "FILLED",
      "symbol": "BTC/USDT",
      "side": "BUY",
      "quantity": "0.001",
      "filled_quantity": "0.001",
      "timestamp": "1734962388",
      # Optional fields:
      "price": "45000.5",
      "strategy_id": "mean_reversion_v2",
      "bot_id": "bot-001",
      "client_id": "client-123",
      "error_message": null  # only if status=ERROR
    }
  )
]
```

---

## Required Fields

| Field | Type (in stream) | Type (logical) | Description |
|-------|------------------|----------------|-------------|
| `type` | string | string | Event type discriminator (always "order_result") |
| `order_id` | string | string | Unique order identifier |
| `status` | string | string | Order status (FILLED, REJECTED, ERROR) |
| `symbol` | string | string | Trading pair (e.g., "BTC/USDT") |
| `side` | string | string | Order side (BUY or SELL) |
| `quantity` | string | float | Requested order size |
| `filled_quantity` | string | float | Actual filled size |
| `timestamp` | string | int (Unix) | Execution timestamp (Unix seconds) |

**All values stored as strings in Redis streams** (conversion required for replay).

---

## Optional Fields

| Field | Type (in stream) | Type (logical) | Description |
|-------|------------------|----------------|-------------|
| `price` | string | float | Limit price (if applicable) |
| `strategy_id` | string | string | Strategy that generated order |
| `bot_id` | string | string | Bot instance identifier |
| `client_id` | string | string | Client/session identifier |
| `error_message` | string | string | Error details (if status=ERROR) |

---

## Field Constraints

### `status` Field Mapping

**Source**: `ExecutionResult._schema_status()` (lines 127-137)

| Internal Status | Schema Status (stored) |
|-----------------|------------------------|
| `FILLED` | `FILLED` |
| `REJECTED` | `REJECTED` |
| `ERROR` | `ERROR` |
| `FAILED` | `ERROR` (mapped) |
| `CANCELLED` | `ERROR` (mapped) |
| `PARTIALLY_FILLED` | `FILLED` (mapped) |
| `SUBMITTED` | `ERROR` (mapped) |
| `PENDING` | `ERROR` (mapped) |

**Valid replay statuses**: `FILLED`, `REJECTED`, `ERROR`

### `timestamp` Field

**Format**: Unix integer (seconds since epoch)

**Source**: `ExecutionResult.to_dict()` (lines 141-155)

**Conversion Logic**:
```python
# ISO string → Unix int
if isinstance(timestamp_value, str):
    timestamp_value = int(datetime.fromisoformat(timestamp_value).timestamp())

# Float → Unix int
elif isinstance(timestamp_value, float):
    timestamp_value = int(timestamp_value)

# None → current time
elif timestamp_value is None:
    timestamp_value = int(utcnow().timestamp())
```

**Critical**: Timestamp is stored as **Unix int**, NOT ISO string (validated by E2E test).

### `side` Field

**Valid Values**: `BUY`, `SELL` (uppercase)

**Type**: `Literal["BUY", "SELL"]` in ExecutionResult dataclass

---

## Stream Ordering Guarantee

**Primary Sort Key**: Redis Stream ID (format: `<milliseconds>-<sequence>`)

**Properties**:
- Lexicographically ordered (XRANGE/XREVRANGE respect this)
- Monotonically increasing (no out-of-order entries)
- Unique per entry

**Determinism Guarantee**: Reading stream entries in Stream ID order guarantees deterministic event sequence.

---

## Example Entry (Parsed)

```python
{
  "stream_id": "1734962388123-0",  # Metadata (not in payload)
  "payload": {
    "type": "order_result",
    "order_id": "e2e-test-1734962388000",
    "status": "FILLED",
    "symbol": "BTC/USDT",
    "side": "BUY",
    "quantity": 0.001,  # Converted from string "0.001"
    "filled_quantity": 0.001,
    "timestamp": 1734962388,  # Converted from string "1734962388"
    "price": 45000.5,  # Optional, converted from string
    "strategy_id": "mean_reversion_v2"  # Optional
  }
}
```

---

## Type Conversion for Replay

**Redis → Python**:
```python
def parse_stream_entry(entry_id: str, entry_data: dict) -> dict:
    """Convert Redis stream entry to typed replay event."""
    return {
        "stream_id": entry_id,
        "type": entry_data["type"],
        "order_id": entry_data["order_id"],
        "status": entry_data["status"],
        "symbol": entry_data["symbol"],
        "side": entry_data["side"],
        "quantity": float(entry_data["quantity"]),
        "filled_quantity": float(entry_data["filled_quantity"]),
        "timestamp": int(entry_data["timestamp"]),
        # Optional fields (use .get() to handle absence)
        "price": float(entry_data["price"]) if "price" in entry_data else None,
        "strategy_id": entry_data.get("strategy_id"),
        "bot_id": entry_data.get("bot_id"),
        "client_id": entry_data.get("client_id"),
        "error_message": entry_data.get("error_message"),
    }
```

---

## Verification Commands

### 1. Check Stream Exists
```powershell
docker exec cdb_redis redis-cli EXISTS stream.fills
# Expected: 1 (exists)
```

### 2. Get Stream Length
```powershell
docker exec cdb_redis redis-cli XLEN stream.fills
# Expected: > 0 if any orders executed
```

### 3. Read Latest 3 Entries
```powershell
docker exec cdb_redis redis-cli XREVRANGE stream.fills + - COUNT 3
```

### 4. Read Specific Range
```powershell
docker exec cdb_redis redis-cli XRANGE stream.fills 1734962388000-0 1734962389000-0
```

### 5. Validate Field Types (Python)
```python
import redis
r = redis.Redis(host="localhost", port=6379, password="...", decode_responses=True)
entries = r.xrevrange("stream.fills", count=1)
entry_id, entry_data = entries[0]

# All values should be strings in Redis
assert all(isinstance(v, str) for v in entry_data.values()), "Non-string value found"

# Timestamp should be parseable as int
assert int(entry_data["timestamp"]) > 1700000000, "Timestamp not Unix int"
```

---

## Replay Determinism Requirements

For replay to be deterministic, the following must hold:

1. **Input Determinism**: Same stream entries (by ID range) always produce same output
2. **Timestamp Injection**: No use of `datetime.now()` during replay - use `event["timestamp"]`
3. **Seed Control**: If randomness is used, seed must be fixed (`CDB_REPLAY_SEED`)
4. **No External Calls**: No live exchange API calls, no database reads (except stream)
5. **Stable Ordering**: Process events in Stream ID order (XRANGE guarantees this)

---

## Related Files

**Producer**:
- `services/execution/service.py:171` - XADD to stream.fills
- `services/execution/models.py:139-177` - ExecutionResult.to_dict()
- `services/execution/config.py:74` - STREAM_ORDER_RESULTS config

**Consumer (E2E Test)**:
- `tests/e2e/test_paper_trading_p0.py:219-280` - test_stream_persistence

**Config**:
- `STREAM_ORDER_RESULTS` - Defaults to "stream.fills"
- Stream maxlen: 10000 (oldest entries auto-trimmed)

---

## Schema Version

**Version**: 1.0 (2025-12-25)

**Changes from previous versions**: N/A (initial version)

**Backward Compatibility**: N/A (initial version)

---

## Future Considerations

**Not Implemented (Out of Scope for MVP)**:
- Schema versioning in stream entries (type field discriminator only)
- Multi-event types in stream (currently only "order_result")
- Compression or compaction strategies
- Sharding across multiple streams

**When to Revisit**:
- If stream grows beyond 10000 entries per session
- If replay performance becomes bottleneck
- If multiple event types need replay (signals, regime changes)
