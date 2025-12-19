# Database Infrastructure

PostgreSQL schema and migrations for Claire de Binare Trading Bot.

## Directory Structure

```
infrastructure/database/
├── migrations/           # SQL migration scripts
│   ├── 001_initial_schema.sql
│   ├── 002_core_tables.sql
│   ├── 003_paper_trading_schema.sql
│   └── 003_paper_trading_schema_rollback.sql
├── schema/              # Schema documentation
│   └── paper_trading_erd.md
└── README.md            # This file
```

## Migrations

### Migration 003: Paper Trading Schema

**Purpose**: Complete schema for paper trading history, analytics, and performance tracking

**Tables Created**:
- `paper_orders` - All paper trading orders with execution details
- `paper_fills` - Individual fill records for partial fills
- `paper_positions` - Current positions by symbol with P&L
- `paper_pnl_snapshots` - Time-series P&L snapshots (hourly/daily)
- `paper_trading_stats` - Daily aggregate statistics

**Views Created**:
- `v_paper_recent_orders` - Last 24 hours of orders
- `v_paper_active_positions` - Open positions with P&L
- `v_paper_daily_summary` - Daily trading summary by symbol

**Functions Created**:
- `get_paper_total_pnl()` - Get current total P&L
- `get_paper_fill_rate(symbol, days)` - Calculate fill rate for symbol

### Applying Migrations

**Prerequisites**:
- PostgreSQL 15+ running
- Database `claire_de_binare` exists
- User `claire_user` has appropriate permissions

**Apply Migration**:
```bash
# Using docker-compose
docker exec -i cdb_postgres psql -U postgres -d claire_de_binare < infrastructure/database/migrations/003_paper_trading_schema.sql

# Direct psql
psql -h localhost -U postgres -d claire_de_binare -f infrastructure/database/migrations/003_paper_trading_schema.sql
```

**Verify Migration**:
```sql
-- List all paper trading tables
\dt paper_*

-- Check table structure
\d paper_orders

-- Verify views
\dv v_paper_*

-- Test function
SELECT get_paper_total_pnl();
```

**Rollback Migration**:
```bash
# Using docker-compose
docker exec -i cdb_postgres psql -U postgres -d claire_de_binare < infrastructure/database/migrations/003_paper_trading_schema_rollback.sql
```

## Schema Overview

### paper_orders

Stores all paper trading orders with comprehensive execution details.

**Key Fields**:
- `order_id` (PK) - Unique order identifier
- `symbol` - Trading pair (e.g., 'BTCUSDT')
- `side` - BUY or SELL
- `quantity`, `filled_quantity` - Order and fill sizes
- `filled_price` - Average execution price
- `slippage_pct`, `fees_usdt` - Execution costs
- `status` - Order status (PENDING, FILLED, REJECTED, etc.)

**Indexes**:
- `symbol` - Fast symbol lookups
- `created_at DESC` - Time-series queries
- `status` - Status filtering
- Composite indexes for common query patterns

### paper_fills

Individual fill records for orders (especially partial fills).

**Key Fields**:
- `fill_id` (PK) - Unique fill identifier
- `order_id` (FK) - References paper_orders
- `quantity`, `price` - Fill details
- `fees_usdt` - Fee for this fill

**Use Cases**:
- Tracking partial fill sequence
- Detailed execution analysis
- Fee breakdown

### paper_positions

Current and historical positions with P&L tracking.

**Key Fields**:
- `symbol` (PK) - Trading pair
- `quantity` - Position size (+ long, - short)
- `avg_entry_price` - Average entry price
- `unrealized_pnl_usdt`, `realized_pnl_usdt` - P&L breakdown
- `total_pnl_usdt` - Computed total P&L

**Use Cases**:
- Portfolio overview
- P&L tracking
- Position sizing validation

### paper_pnl_snapshots

Time-series P&L snapshots for historical analysis.

**Key Fields**:
- `snapshot_time` - Snapshot timestamp
- `snapshot_type` - HOURLY, DAILY, MANUAL
- `total_pnl_usdt`, `realized_pnl_usdt`, `unrealized_pnl_usdt`
- `win_rate` - Computed win rate
- `symbol_pnl` - JSONB breakdown by symbol

**Use Cases**:
- Performance charts (Grafana)
- Backtesting validation
- Historical analysis

### paper_trading_stats

Daily aggregate statistics.

**Key Fields**:
- `stat_date` (Unique) - Date
- `total_orders`, `filled_orders`, `rejected_orders` - Order counts
- `fill_rate` - Computed fill rate
- `avg_slippage_pct`, `avg_fee_pct` - Average metrics
- `daily_pnl_usdt`, `cumulative_pnl_usdt` - P&L

**Use Cases**:
- Daily reports
- Trend analysis
- Performance dashboards

## Common Queries

### Daily Summary
```sql
SELECT * FROM v_paper_daily_summary
WHERE trade_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY trade_date DESC, symbol;
```

### Active Positions
```sql
SELECT * FROM v_paper_active_positions
ORDER BY total_pnl_usdt DESC;
```

### Fill Rate by Symbol
```sql
SELECT
    symbol,
    get_paper_fill_rate(symbol, 7) as fill_rate_7d,
    get_paper_fill_rate(symbol, 30) as fill_rate_30d
FROM (SELECT DISTINCT symbol FROM paper_orders) symbols
ORDER BY fill_rate_7d DESC;
```

### Performance Over Time
```sql
SELECT
    snapshot_time::DATE as date,
    total_pnl_usdt,
    win_rate,
    total_trades
FROM paper_pnl_snapshots
WHERE snapshot_type = 'DAILY'
  AND snapshot_time >= NOW() - INTERVAL '30 days'
ORDER BY snapshot_time;
```

### Slippage Analysis
```sql
SELECT
    symbol,
    AVG(slippage_pct) as avg_slippage,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY slippage_pct) as median_slippage,
    MAX(slippage_pct) as max_slippage
FROM paper_orders
WHERE status = 'FILLED'
  AND filled_at >= NOW() - INTERVAL '7 days'
GROUP BY symbol
ORDER BY avg_slippage DESC;
```

## Integration

### From Python (psycopg2)

```python
import psycopg2

# Insert order
cursor.execute("""
    INSERT INTO paper_orders (
        order_id, symbol, side, order_type, quantity, price, status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
""", (order_id, symbol, side, order_type, quantity, price, status))

# Update order status
cursor.execute("""
    UPDATE paper_orders
    SET status = %s, filled_at = NOW(), filled_quantity = %s, filled_price = %s
    WHERE order_id = %s
""", (status, filled_qty, filled_price, order_id))

# Get total P&L
cursor.execute("SELECT get_paper_total_pnl()")
total_pnl = cursor.fetchone()[0]
```

## Maintenance

### Cleanup Old Data

```sql
-- Delete orders older than 90 days
DELETE FROM paper_orders WHERE created_at < NOW() - INTERVAL '90 days';

-- Delete old snapshots
DELETE FROM paper_pnl_snapshots WHERE snapshot_time < NOW() - INTERVAL '180 days';
```

### Reindex

```sql
REINDEX TABLE paper_orders;
REINDEX TABLE paper_pnl_snapshots;
```

### Vacuum

```sql
VACUUM ANALYZE paper_orders;
VACUUM ANALYZE paper_positions;
```

## Backup

```bash
# Backup paper trading data only
pg_dump -h localhost -U postgres -d claire_de_binare -t 'paper_*' > paper_trading_backup.sql

# Restore
psql -h localhost -U postgres -d claire_de_binare < paper_trading_backup.sql
```

## Performance Tuning

**Recommended PostgreSQL Settings** (for trading workload):
```sql
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
```

**Table Statistics**:
```sql
-- Update statistics for better query planning
ANALYZE paper_orders;
ANALYZE paper_positions;
```

## Monitoring

**Check table sizes**:
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 'paper_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Check index usage**:
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND tablename LIKE 'paper_%'
ORDER BY idx_scan DESC;
```

## Troubleshooting

**Migration Fails**:
1. Check PostgreSQL logs: `docker logs cdb_postgres`
2. Verify user permissions: `\du` in psql
3. Check existing tables: `\dt`
4. Rollback and retry

**Slow Queries**:
1. Check query plan: `EXPLAIN ANALYZE <query>`
2. Verify indexes exist: `\d paper_orders`
3. Update statistics: `ANALYZE paper_orders`

**Disk Space**:
1. Check table sizes (see Monitoring section)
2. Clean old data (see Maintenance section)
3. Vacuum tables: `VACUUM FULL paper_orders`
