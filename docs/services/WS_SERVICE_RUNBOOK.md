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
