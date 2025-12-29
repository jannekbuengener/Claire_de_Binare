# WebSocket Service Runbook (D3)

Quick operational guide for cdb_ws service with MEXC V3 Protobuf integration.

## Modes

The service supports two operational modes controlled by the `WS_SOURCE` environment variable:

### STUB Mode (Default)
No external WebSocket connections. Health endpoint only.

```bash
python -u services/ws/service.py
```

**Verification:**
```bash
curl http://127.0.0.1:8000/health
# Expected: {"mode": "stub", "status": "healthy", ...}

curl http://127.0.0.1:8000/metrics
# Expected: All WS metrics at 0/initial values
```

### MEXC Protobuf Mode
Active connection to MEXC Spot V3 WebSocket API for public market data.

```bash
export WS_SOURCE=mexc_pb
export MEXC_SYMBOL=BTCUSDT
export MEXC_INTERVAL=100ms
python -u services/ws/service.py
```

**Windows:**
```powershell
$env:WS_SOURCE="mexc_pb"
$env:MEXC_SYMBOL="BTCUSDT"
$env:MEXC_INTERVAL="100ms"
python -u services/ws/service.py
```

**Verification (within 60 seconds):**
```bash
# Health check
curl http://127.0.0.1:8000/health
# Expected: {"mode": "mexc_pb", "ws_connected": 1, "last_message_age_ms": <small number>}

# Metrics check
curl http://127.0.0.1:8000/metrics | grep -E "(decoded_messages_total|decode_errors_total|ws_connected|last_message_ts_ms)"
# Expected:
#   decoded_messages_total > 0
#   decode_errors_total 0 (or very low)
#   ws_connected 1
#   last_message_ts_ms <recent timestamp>
```

## Configuration

| ENV Variable | Default | Description |
|--------------|---------|-------------|
| `WS_SOURCE` | `stub` | Mode: `stub` or `mexc_pb` |
| `MEXC_SYMBOL` | `BTCUSDT` | Trading pair (uppercase) |
| `MEXC_INTERVAL` | `100ms` | Aggregation interval |
| `WS_PING_INTERVAL` | `20` | Heartbeat interval (seconds) |
| `WS_RECONNECT_MAX` | `10` | Max reconnect backoff (seconds) |

## Troubleshooting

**No messages decoded:**
- Check logs for `[ws] connected` and `subscribe` confirmation
- Verify MEXC API is accessible: `ping wbs-api.mexc.com`

**High decode errors:**
- Check proto files are up-to-date
- Verify `mexc_proto_gen/` contains all 16 pb2 files

**Connection drops:**
- Check logs for reconnect attempts with backoff
- Normal: backoff increases exponentially (1s → 2s → 4s → 10s cap)

**Messages decoded but redis_publish_total = 0:**
- **Issue #342 (RESOLVED 2025-12-29):** Protobuf field name mismatch
- Verify metrics: `decoded_messages_total > 0` AND `redis_publish_total > 0`
- If publish = 0: Check logs for `[redis] published market_data` entries
- Root cause was incorrect field names in `decode_message()`:
  - Must use `publicAggreDeals` (camelCase), not `publicdeals`/`publicDeals`
  - Must use `deals` field, not `dealsList`/`deals_list`
  - Must use `eventType` (camelCase), not `eventtype`

## End-to-End Pipeline Verification

After starting cdb_ws in mexc_pb mode, verify the full trading pipeline:

**1. WebSocket Service (cdb_ws)**
```bash
curl http://127.0.0.1:8000/metrics | grep -E "decoded_messages_total|redis_publish_total"
# Expected:
#   decoded_messages_total > 0
#   redis_publish_total > 0  ← CRITICAL: Must be non-zero
```

**2. Redis Pub/Sub**
```bash
docker exec cdb_redis redis-cli -a $(cat ~/.secrets/.cdb/REDIS_PASSWORD) SUBSCRIBE market_data
# Expected: Continuous stream of JSON messages with MEXC trade data
# Press Ctrl+C to exit
```

**3. Signal Service (cdb_signal)**
```bash
docker logs cdb_signal --tail 20
# Expected: Log entries indicating market data processing
# Note: pct_change errors are a separate issue (not part of WS service)
```

**4. Health Check All Services**
```bash
docker ps --filter "name=cdb_" --format "table {{.Names}}\t{{.Status}}"
# Expected: All services show "Up" with healthy status
```

## Known Issues

### Resolved
- **Issue #342** (2025-12-29): Protobuf field name mismatch causing 0 Redis publishes
  - **Fix:** Commit 1315430
  - **Symptom:** `decoded_messages_total > 0` but `redis_publish_total = 0`
  - **Solution:** Corrected field names to camelCase (`publicAggreDeals`, `eventType`)

### Active
- **cdb_signal pct_change KeyError:** Separate issue in signal processing logic (not WS service)
