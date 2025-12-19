# Paper Trading Schema - Entity Relationship Diagram

## Overview

Complete database schema for paper trading history, analytics, and performance tracking.

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         PAPER_ORDERS                            │
├─────────────────────────────────────────────────────────────────┤
│ PK │ order_id          VARCHAR(50)                              │
│    │ client_id         VARCHAR(50)                              │
│    │ symbol            VARCHAR(20)    NOT NULL                  │
│    │ side              VARCHAR(4)     CHECK (BUY/SELL)          │
│    │ order_type        VARCHAR(20)    DEFAULT 'MARKET'          │
│    │ quantity          DECIMAL(18,8)  NOT NULL                  │
│    │ price             DECIMAL(18,8)                            │
│    │ filled_quantity   DECIMAL(18,8)  DEFAULT 0                 │
│    │ filled_price      DECIMAL(18,8)                            │
│    │ status            VARCHAR(20)    NOT NULL                  │
│    │ slippage_pct      DECIMAL(10,6)                            │
│    │ fees_usdt         DECIMAL(18,8)  DEFAULT 0                 │
│    │ fee_type          VARCHAR(10)                              │
│    │ created_at        TIMESTAMP      DEFAULT NOW()             │
│    │ submitted_at      TIMESTAMP                                │
│    │ filled_at         TIMESTAMP                                │
│    │ updated_at        TIMESTAMP      DEFAULT NOW()             │
│    │ rejection_reason  TEXT                                     │
│    │ error_message     TEXT                                     │
│    │ metadata          JSONB                                    │
│    │ fill_ratio        DECIMAL(5,4)   COMPUTED                  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ 1
                           │
                           │ N
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                          PAPER_FILLS                            │
├─────────────────────────────────────────────────────────────────┤
│ PK │ fill_id           VARCHAR(50)                              │
│ FK │ order_id          VARCHAR(50)    → paper_orders.order_id   │
│    │ symbol            VARCHAR(20)    NOT NULL                  │
│    │ quantity          DECIMAL(18,8)  NOT NULL                  │
│    │ price             DECIMAL(18,8)  NOT NULL                  │
│    │ fees_usdt         DECIMAL(18,8)  DEFAULT 0                 │
│    │ fee_type          VARCHAR(10)                              │
│    │ filled_at         TIMESTAMP      DEFAULT NOW()             │
│    │ metadata          JSONB                                    │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                       PAPER_POSITIONS                           │
├─────────────────────────────────────────────────────────────────┤
│ PK │ symbol            VARCHAR(20)                              │
│    │ quantity          DECIMAL(18,8)  NOT NULL                  │
│    │ avg_entry_price   DECIMAL(18,8)  NOT NULL                  │
│    │ current_price     DECIMAL(18,8)                            │
│    │ unrealized_pnl    DECIMAL(18,8)  DEFAULT 0                 │
│    │ realized_pnl      DECIMAL(18,8)  DEFAULT 0                 │
│    │ total_pnl         DECIMAL(18,8)  COMPUTED                  │
│    │ cost_basis_usdt   DECIMAL(18,8)  NOT NULL                  │
│    │ market_value_usdt DECIMAL(18,8)                            │
│    │ entry_trades      INT            DEFAULT 0                 │
│    │ exit_trades       INT            DEFAULT 0                 │
│    │ opened_at         TIMESTAMP      NOT NULL                  │
│    │ updated_at        TIMESTAMP      DEFAULT NOW()             │
│    │ closed_at         TIMESTAMP                                │
│    │ metadata          JSONB                                    │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                     PAPER_PNL_SNAPSHOTS                         │
├─────────────────────────────────────────────────────────────────┤
│ PK │ snapshot_id       SERIAL                                   │
│    │ snapshot_time     TIMESTAMP      NOT NULL                  │
│    │ snapshot_type     VARCHAR(10)    CHECK (HOURLY/DAILY/...)  │
│    │ total_pnl_usdt    DECIMAL(18,8)  NOT NULL                  │
│    │ realized_pnl      DECIMAL(18,8)  NOT NULL                  │
│    │ unrealized_pnl    DECIMAL(18,8)  NOT NULL                  │
│    │ balance_usdt      DECIMAL(18,8)                            │
│    │ equity_usdt       DECIMAL(18,8)                            │
│    │ margin_used_usdt  DECIMAL(18,8)  DEFAULT 0                 │
│    │ total_trades      INT            DEFAULT 0                 │
│    │ winning_trades    INT            DEFAULT 0                 │
│    │ losing_trades     INT            DEFAULT 0                 │
│    │ win_rate          DECIMAL(5,4)   COMPUTED                  │
│    │ total_volume_usdt DECIMAL(18,8)  DEFAULT 0                 │
│    │ total_fees_usdt   DECIMAL(18,8)  DEFAULT 0                 │
│    │ symbol_pnl        JSONB                                    │
│    │ metadata          JSONB                                    │
│    │ UNIQUE(snapshot_time, snapshot_type)                       │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                     PAPER_TRADING_STATS                         │
├─────────────────────────────────────────────────────────────────┤
│ PK │ stat_id           SERIAL                                   │
│    │ stat_date         DATE           NOT NULL   UNIQUE         │
│    │ total_orders      INT            DEFAULT 0                 │
│    │ filled_orders     INT            DEFAULT 0                 │
│    │ partial_fills     INT            DEFAULT 0                 │
│    │ rejected_orders   INT            DEFAULT 0                 │
│    │ cancelled_orders  INT            DEFAULT 0                 │
│    │ fill_rate         DECIMAL(5,4)   COMPUTED                  │
│    │ avg_slippage_pct  DECIMAL(10,6)                            │
│    │ avg_fee_pct       DECIMAL(10,6)                            │
│    │ avg_latency_ms    DECIMAL(10,2)                            │
│    │ total_volume_usdt DECIMAL(18,8)  DEFAULT 0                 │
│    │ total_fees_usdt   DECIMAL(18,8)  DEFAULT 0                 │
│    │ daily_pnl_usdt    DECIMAL(18,8)  DEFAULT 0                 │
│    │ cumulative_pnl    DECIMAL(18,8)  DEFAULT 0                 │
│    │ updated_at        TIMESTAMP      DEFAULT NOW()             │
└─────────────────────────────────────────────────────────────────┘
```

## Relationships

### paper_orders → paper_fills (1:N)
- One order can have multiple fills (partial fill scenario)
- `paper_fills.order_id` references `paper_orders.order_id`
- CASCADE delete: If order is deleted, all its fills are deleted

## Views

### v_paper_recent_orders
**Purpose**: Quick access to last 24 hours of orders
**Source**: `paper_orders` WHERE created_at >= NOW() - INTERVAL '24 hours'

### v_paper_active_positions
**Purpose**: Current open positions only
**Source**: `paper_positions` WHERE closed_at IS NULL

### v_paper_daily_summary
**Purpose**: Daily trading summary by symbol
**Source**: Aggregates from `paper_orders` grouped by DATE(created_at) and symbol

## Functions

### get_paper_total_pnl() → DECIMAL
**Purpose**: Get current total P&L across all positions
**Returns**: Sum of total_pnl_usdt from all active positions

### get_paper_fill_rate(symbol, days) → DECIMAL
**Purpose**: Calculate fill rate for a specific symbol over N days
**Parameters**:
- `symbol`: Trading pair (e.g., 'BTCUSDT')
- `days`: Number of days to analyze (default: 7)
**Returns**: Fill rate as decimal (0.0 to 1.0)

## Indexes

### paper_orders
- `idx_paper_orders_symbol` - ON (symbol)
- `idx_paper_orders_created_at` - ON (created_at DESC)
- `idx_paper_orders_filled_at` - ON (filled_at DESC) WHERE filled_at IS NOT NULL
- `idx_paper_orders_status` - ON (status)
- `idx_paper_orders_client_id` - ON (client_id) WHERE client_id IS NOT NULL
- `idx_paper_orders_symbol_status` - ON (symbol, status)
- `idx_paper_orders_symbol_created` - ON (symbol, created_at DESC)

### paper_fills
- `idx_paper_fills_order_id` - ON (order_id)
- `idx_paper_fills_symbol` - ON (symbol)
- `idx_paper_fills_filled_at` - ON (filled_at DESC)

### paper_positions
- `idx_paper_positions_pnl` - ON (total_pnl_usdt DESC)
- `idx_paper_positions_updated` - ON (updated_at DESC)
- `idx_paper_positions_open` - ON (closed_at) WHERE closed_at IS NULL

### paper_pnl_snapshots
- `idx_paper_pnl_time` - ON (snapshot_time DESC)
- `idx_paper_pnl_type_time` - ON (snapshot_type, snapshot_time DESC)

### paper_trading_stats
- `idx_paper_stats_date` - ON (stat_date DESC)

## Data Flow

```
┌──────────────┐
│  Enhanced    │
│ MockExecutor │
│   (v2.0)     │
└──────┬───────┘
       │
       │ ExecutionResult
       │
       ▼
┌──────────────┐
│   Execution  │──────────► INSERT INTO paper_orders
│   Service    │
└──────┬───────┘
       │
       │ (if partial fill)
       │
       ▼
  INSERT INTO paper_fills
       │
       │
       ▼
┌──────────────┐
│  Position    │──────────► UPDATE paper_positions
│  Tracker     │
└──────┬───────┘
       │
       │ (hourly/daily)
       │
       ▼
  INSERT INTO paper_pnl_snapshots
       │
       │
       ▼
  INSERT INTO paper_trading_stats (daily rollup)
```

## Storage Estimates

**Assumptions**:
- 1000 orders/day
- 10% partial fills (100 additional fill records/day)
- 10 active positions
- 24 hourly + 1 daily snapshot = 25 snapshots/day

**Daily Storage**:
- `paper_orders`: 1000 rows × ~500 bytes = ~500 KB/day
- `paper_fills`: 100 rows × ~200 bytes = ~20 KB/day
- `paper_positions`: 10 rows × ~300 bytes = ~3 KB (total, not daily)
- `paper_pnl_snapshots`: 25 rows × ~400 bytes = ~10 KB/day
- `paper_trading_stats`: 1 row × ~200 bytes = ~200 bytes/day

**Monthly Storage**: ~15 MB/month
**Yearly Storage**: ~180 MB/year (manageable without archiving)

## Retention Policy

**Recommended**:
- `paper_orders`: Keep 90 days
- `paper_fills`: Keep 90 days
- `paper_positions`: Keep all (relatively small)
- `paper_pnl_snapshots`: Keep 180 days
- `paper_trading_stats`: Keep all (one row per day)

**Archiving Strategy**:
```sql
-- Archive old orders to cold storage
CREATE TABLE paper_orders_archive AS
SELECT * FROM paper_orders
WHERE created_at < NOW() - INTERVAL '90 days';

-- Delete archived records
DELETE FROM paper_orders
WHERE created_at < NOW() - INTERVAL '90 days';
```

## Performance Considerations

**Write Performance**:
- ~1000 INSERTs/day on `paper_orders` (negligible)
- Batch insert fills for better performance
- Use prepared statements for INSERTs

**Read Performance**:
- Most queries are time-range based (indexes on timestamps)
- Symbol-based queries are indexed
- Views provide pre-filtered data
- Consider materialized views for heavy aggregations

**Optimization Tips**:
1. Regularly VACUUM and ANALYZE tables
2. Monitor index usage with pg_stat_user_indexes
3. Use EXPLAIN ANALYZE for slow queries
4. Consider partitioning paper_orders by created_at if volume increases significantly
