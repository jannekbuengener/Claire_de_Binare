# Execution Service

**Port:** 8003
**Version:** 0.1.0
**Status:** ✅ Production-ready

---

## Overview

The Execution Service is responsible for order execution and persistence. It receives approved orders from the Risk Manager, executes them (paper trading or live), and persists results to PostgreSQL.

**Function:**
```
Risk Manager → orders (Redis) → Execution Service → order_results (Redis)
                                         ↓
                                   PostgreSQL (orders + trades)
```

---

## Architecture

### Redis Pub/Sub
- **Subscribe:** `orders` topic (from Risk Manager)
- **Publish:** `order_results` topic (to downstream services)

### Database
- **Tables:** `orders`, `trades`
- **Persistence:** All orders and filled trades stored in PostgreSQL

### Execution Modes
1. **Mock Executor** (`mock_executor.py`): Paper trading with 95% success rate
2. **MEXC Executor** (`mexc_executor.py`): Live trading via MEXC API
3. **Live Executor** (`live_executor.py`): Production live trading
4. **Paper Trading** (`paper_trading.py`): Deterministic paper trading

---

## REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (200 OK if running) |
| `/status` | GET | Service status + statistics + DB stats |
| `/metrics` | GET | Prometheus metrics |
| `/orders` | GET | Last 20 orders from database |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `cdb_redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | (required) | Redis password |
| `POSTGRES_HOST` | `cdb_postgres` | PostgreSQL hostname |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `claire_de_binare` | Database name |
| `POSTGRES_USER` | `claire_user` | Database user |
| `POSTGRES_PASSWORD` | (required) | Database password |
| `TRADING_MODE` | `paper` | Trading mode: `paper`, `live` |
| `DRY_RUN` | `true` | Log-only mode (no real execution) |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Database Schema

### orders table
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255) UNIQUE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- BUY/SELL
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8),
    status VARCHAR(20) NOT NULL,  -- PENDING/FILLED/REJECTED
    created_at TIMESTAMP DEFAULT NOW(),
    filled_at TIMESTAMP,
    reject_reason TEXT
);
```

### trades table
```sql
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    trade_id VARCHAR(255) UNIQUE NOT NULL,
    order_id VARCHAR(255) REFERENCES orders(order_id),
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    fee DECIMAL(20,8) DEFAULT 0,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

---

## Statistics Tracked

- `orders_received` - Total orders received
- `orders_filled` - Successfully executed orders
- `orders_rejected` - Rejected orders
- `start_time` - Service start timestamp

---

## Error Handling

- Try/Except blocks in all critical functions
- Graceful degradation (service continues on DB errors)
- Structured logging with ERROR level for failures
- Graceful shutdown on SIGTERM/SIGINT

---

## Health Check

```bash
curl http://localhost:8003/health
```

**Expected Response:**
```json
{"status": "ok", "service": "execution"}
```

---

## Status Endpoint

```bash
curl http://localhost:8003/status
```

**Expected Response:**
```json
{
  "service": "execution",
  "uptime_seconds": 3600,
  "redis_connected": true,
  "database_connected": true,
  "statistics": {
    "orders_received": 150,
    "orders_filled": 142,
    "orders_rejected": 8
  },
  "database_stats": {
    "total_orders": 150,
    "filled_orders": 142,
    "rejected_orders": 8
  }
}
```

---

## Deployment

### Docker Build
```bash
cd services/execution
docker build -t cdb_execution:latest .
```

### Docker Run (Standalone)
```bash
docker run -d \
  --name cdb_execution \
  --network cdb_network \
  -e REDIS_HOST=cdb_redis \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD=<secret> \
  -e POSTGRES_HOST=cdb_postgres \
  -e POSTGRES_PASSWORD=<secret> \
  -e TRADING_MODE=paper \
  -e DRY_RUN=true \
  -p 8003:8003 \
  cdb_execution:latest
```

### Docker Compose
Service is defined in `infrastructure/compose/dev.yml` and `infrastructure/compose/prod.yml`.

```bash
# Start with dev stack
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d

# Check logs
docker logs cdb_execution -f
```

---

## Testing

### Unit Tests
```bash
pytest tests/unit/test_execution_service.py
```

### E2E Tests
```bash
# Requires full stack running
pytest tests/e2e/test_paper_trading_p0.py -v
```

### Manual Test (Send Order)
```bash
# Publish test order to Redis
docker exec cdb_redis redis-cli -a <password> PUBLISH orders '{
  "order_id": "TEST_001",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "quantity": 0.001,
  "price": 42000.00
}'

# Check order in database
docker exec cdb_postgres psql -U claire_user -d claire_de_binare \
  -c "SELECT * FROM orders WHERE order_id='TEST_001';"
```

---

## Troubleshooting

### Container Crashes on Start

**Check logs:**
```bash
docker logs cdb_execution --tail 50
```

**Common issues:**
- Redis connection failed: Verify `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- PostgreSQL connection failed: Verify `POSTGRES_HOST`, `POSTGRES_PASSWORD`
- Missing dependencies: Rebuild image with `--no-cache`

### Orders Not Processing

**Check Redis subscription:**
```bash
docker exec cdb_redis redis-cli -a <password> PUBSUB CHANNELS
# Should show: orders
```

**Check service logs:**
```bash
docker logs cdb_execution -f
# Look for "Subscribed to orders channel"
```

### Database Persistence Failing

**Check PostgreSQL connection:**
```bash
docker exec cdb_postgres pg_isready -U claire_user -d claire_de_binare
```

**Check table schema:**
```bash
docker exec cdb_postgres psql -U claire_user -d claire_de_binare \
  -c "\d orders"
```

---

## Development

### Code Structure
```
services/execution/
├── service.py          # Main Flask service + Redis subscriber
├── config.py           # Environment configuration
├── models.py           # Pydantic data models
├── mock_executor.py    # Paper trading executor
├── mexc_executor.py    # MEXC live trading executor
├── live_executor.py    # Production live executor
├── paper_trading.py    # Deterministic paper trading
├── database.py         # PostgreSQL persistence layer
├── Dockerfile          # Container definition
└── requirements.txt    # Python dependencies
```

### Dependencies
- Flask 3.0.0 (REST API)
- Redis 5.0.1 (Pub/Sub)
- psycopg2-binary 2.9.9 (PostgreSQL)
- pydantic 2.5.2 (Data validation)

---

## Related Services

- **Risk Manager** (Port 8002): Publishes approved orders to `orders` topic
- **Core Service**: Subscribes to `order_results` topic
- **DB Writer**: Consumes order results for analytics

---

## References

- [Database Schema](../../infrastructure/database/schema.sql)
- [Docker Compose Configuration](../../infrastructure/compose/dev.yml)
- [E2E Test Suite](../../tests/e2e/test_paper_trading_p0.py)

---

**Created:** 2025-12-27
**Last Updated:** 2025-12-27
