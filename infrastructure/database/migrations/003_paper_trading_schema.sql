-- Migration 003: Paper Trading Schema
-- Claire de Binare Trading Bot
-- Created: 2025-12-19
-- Purpose: Dedicated schema for paper trading history and analytics

-- ============================================================================
-- TABLE: paper_orders
-- Stores all paper trading orders with execution details
-- ============================================================================

CREATE TABLE IF NOT EXISTS paper_orders (
    -- Identification
    order_id VARCHAR(50) PRIMARY KEY,
    client_id VARCHAR(50),

    -- Order details
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type VARCHAR(20) DEFAULT 'MARKET' CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')),

    -- Quantities and prices
    quantity DECIMAL(18,8) NOT NULL CHECK (quantity > 0),
    price DECIMAL(18,8),  -- Limit price (NULL for market orders)
    filled_quantity DECIMAL(18,8) DEFAULT 0 CHECK (filled_quantity >= 0),
    filled_price DECIMAL(18,8),  -- Average fill price

    -- Status
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'SUBMITTED', 'FILLED', 'PARTIAL', 'PARTIALLY_FILLED', 'REJECTED', 'CANCELLED', 'FAILED')),

    -- Execution details
    slippage_pct DECIMAL(10,6),  -- Slippage percentage
    fees_usdt DECIMAL(18,8) DEFAULT 0,  -- Trading fees in USDT
    fee_type VARCHAR(10) CHECK (fee_type IN ('TAKER', 'MAKER', NULL)),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    submitted_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Rejection/Error info
    rejection_reason TEXT,
    error_message TEXT,

    -- Metadata (JSON for extensibility)
    metadata JSONB,

    -- Computed fields
    fill_ratio DECIMAL(5,4) GENERATED ALWAYS AS (
        CASE
            WHEN quantity > 0 THEN filled_quantity / quantity
            ELSE 0
        END
    ) STORED
);

-- Indexes for performance
CREATE INDEX idx_paper_orders_symbol ON paper_orders(symbol);
CREATE INDEX idx_paper_orders_created_at ON paper_orders(created_at DESC);
CREATE INDEX idx_paper_orders_filled_at ON paper_orders(filled_at DESC) WHERE filled_at IS NOT NULL;
CREATE INDEX idx_paper_orders_status ON paper_orders(status);
CREATE INDEX idx_paper_orders_client_id ON paper_orders(client_id) WHERE client_id IS NOT NULL;

-- Composite indexes for common queries
CREATE INDEX idx_paper_orders_symbol_status ON paper_orders(symbol, status);
CREATE INDEX idx_paper_orders_symbol_created ON paper_orders(symbol, created_at DESC);

-- Comment
COMMENT ON TABLE paper_orders IS 'Paper trading order history with execution details';

-- ============================================================================
-- TABLE: paper_fills
-- Individual fill records for partial fills
-- ============================================================================

CREATE TABLE IF NOT EXISTS paper_fills (
    -- Identification
    fill_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL REFERENCES paper_orders(order_id) ON DELETE CASCADE,

    -- Fill details
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(18,8) NOT NULL CHECK (quantity > 0),
    price DECIMAL(18,8) NOT NULL CHECK (price > 0),

    -- Fees
    fees_usdt DECIMAL(18,8) DEFAULT 0,
    fee_type VARCHAR(10) CHECK (fee_type IN ('TAKER', 'MAKER')),

    -- Timestamp
    filled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Metadata
    metadata JSONB
);

-- Indexes
CREATE INDEX idx_paper_fills_order_id ON paper_fills(order_id);
CREATE INDEX idx_paper_fills_symbol ON paper_fills(symbol);
CREATE INDEX idx_paper_fills_filled_at ON paper_fills(filled_at DESC);

-- Comment
COMMENT ON TABLE paper_fills IS 'Individual fill records for partial order fills';

-- ============================================================================
-- TABLE: paper_positions
-- Current positions by symbol
-- ============================================================================

CREATE TABLE IF NOT EXISTS paper_positions (
    -- Identification
    symbol VARCHAR(20) PRIMARY KEY,

    -- Position details
    quantity DECIMAL(18,8) NOT NULL,  -- Current position size (+ for long, - for short)
    avg_entry_price DECIMAL(18,8) NOT NULL CHECK (avg_entry_price > 0),
    current_price DECIMAL(18,8),

    -- P&L
    unrealized_pnl_usdt DECIMAL(18,8) DEFAULT 0,
    realized_pnl_usdt DECIMAL(18,8) DEFAULT 0,
    total_pnl_usdt DECIMAL(18,8) GENERATED ALWAYS AS (unrealized_pnl_usdt + realized_pnl_usdt) STORED,

    -- Cost basis
    cost_basis_usdt DECIMAL(18,8) NOT NULL,
    market_value_usdt DECIMAL(18,8),

    -- Trade count
    entry_trades INT DEFAULT 0,
    exit_trades INT DEFAULT 0,

    -- Timestamps
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB
);

-- Indexes
CREATE INDEX idx_paper_positions_pnl ON paper_positions(total_pnl_usdt DESC);
CREATE INDEX idx_paper_positions_updated ON paper_positions(updated_at DESC);
CREATE INDEX idx_paper_positions_open ON paper_positions(closed_at) WHERE closed_at IS NULL;

-- Comment
COMMENT ON TABLE paper_positions IS 'Current and historical positions with P&L tracking';

-- ============================================================================
-- TABLE: paper_pnl_snapshots
-- Hourly/daily P&L snapshots for time-series analysis
-- ============================================================================

CREATE TABLE IF NOT EXISTS paper_pnl_snapshots (
    -- Identification
    snapshot_id SERIAL PRIMARY KEY,
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    snapshot_type VARCHAR(10) NOT NULL CHECK (snapshot_type IN ('HOURLY', 'DAILY', 'MANUAL')),

    -- Aggregate P&L
    total_pnl_usdt DECIMAL(18,8) NOT NULL,
    realized_pnl_usdt DECIMAL(18,8) NOT NULL,
    unrealized_pnl_usdt DECIMAL(18,8) NOT NULL,

    -- Account metrics
    balance_usdt DECIMAL(18,8),
    equity_usdt DECIMAL(18,8),
    margin_used_usdt DECIMAL(18,8) DEFAULT 0,

    -- Performance metrics
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    win_rate DECIMAL(5,4) GENERATED ALWAYS AS (
        CASE
            WHEN total_trades > 0 THEN winning_trades::DECIMAL / total_trades
            ELSE 0
        END
    ) STORED,

    -- Volume metrics
    total_volume_usdt DECIMAL(18,8) DEFAULT 0,
    total_fees_usdt DECIMAL(18,8) DEFAULT 0,

    -- Symbol breakdown (JSON)
    symbol_pnl JSONB,  -- {"BTCUSDT": {"pnl": 150.50, "trades": 10}, ...}

    -- Metadata
    metadata JSONB,

    -- Unique constraint (one snapshot per time + type)
    UNIQUE(snapshot_time, snapshot_type)
);

-- Indexes
CREATE INDEX idx_paper_pnl_time ON paper_pnl_snapshots(snapshot_time DESC);
CREATE INDEX idx_paper_pnl_type_time ON paper_pnl_snapshots(snapshot_type, snapshot_time DESC);

-- Comment
COMMENT ON TABLE paper_pnl_snapshots IS 'Time-series P&L snapshots for historical analysis';

-- ============================================================================
-- TABLE: paper_trading_stats
-- Aggregate statistics and metrics
-- ============================================================================

CREATE TABLE IF NOT EXISTS paper_trading_stats (
    -- Identification
    stat_id SERIAL PRIMARY KEY,
    stat_date DATE NOT NULL,

    -- Order statistics
    total_orders INT DEFAULT 0,
    filled_orders INT DEFAULT 0,
    partial_fills INT DEFAULT 0,
    rejected_orders INT DEFAULT 0,
    cancelled_orders INT DEFAULT 0,

    -- Fill rate
    fill_rate DECIMAL(5,4) GENERATED ALWAYS AS (
        CASE
            WHEN total_orders > 0 THEN filled_orders::DECIMAL / total_orders
            ELSE 0
        END
    ) STORED,

    -- Average metrics
    avg_slippage_pct DECIMAL(10,6),
    avg_fee_pct DECIMAL(10,6),
    avg_latency_ms DECIMAL(10,2),

    -- Volume
    total_volume_usdt DECIMAL(18,8) DEFAULT 0,
    total_fees_usdt DECIMAL(18,8) DEFAULT 0,

    -- P&L
    daily_pnl_usdt DECIMAL(18,8) DEFAULT 0,
    cumulative_pnl_usdt DECIMAL(18,8) DEFAULT 0,

    -- Updated
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint
    UNIQUE(stat_date)
);

-- Indexes
CREATE INDEX idx_paper_stats_date ON paper_trading_stats(stat_date DESC);

-- Comment
COMMENT ON TABLE paper_trading_stats IS 'Daily aggregate statistics for paper trading performance';

-- ============================================================================
-- VIEWS
-- Useful views for common queries
-- ============================================================================

-- Recent orders (last 24 hours)
CREATE OR REPLACE VIEW v_paper_recent_orders AS
SELECT
    order_id,
    symbol,
    side,
    order_type,
    quantity,
    filled_quantity,
    filled_price,
    status,
    slippage_pct,
    fees_usdt,
    created_at,
    filled_at
FROM paper_orders
WHERE created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

-- Active positions
CREATE OR REPLACE VIEW v_paper_active_positions AS
SELECT
    symbol,
    quantity,
    avg_entry_price,
    current_price,
    unrealized_pnl_usdt,
    realized_pnl_usdt,
    total_pnl_usdt,
    market_value_usdt,
    opened_at,
    updated_at
FROM paper_positions
WHERE closed_at IS NULL
ORDER BY total_pnl_usdt DESC;

-- Daily summary
CREATE OR REPLACE VIEW v_paper_daily_summary AS
SELECT
    DATE(created_at) as trade_date,
    symbol,
    COUNT(*) as total_orders,
    COUNT(*) FILTER (WHERE status = 'FILLED') as filled_orders,
    COUNT(*) FILTER (WHERE status = 'REJECTED') as rejected_orders,
    SUM(filled_quantity * filled_price) as total_volume_usdt,
    SUM(fees_usdt) as total_fees_usdt,
    AVG(slippage_pct) as avg_slippage_pct
FROM paper_orders
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), symbol
ORDER BY trade_date DESC, symbol;

-- ============================================================================
-- FUNCTIONS
-- Helper functions for common operations
-- ============================================================================

-- Function: Get current P&L
CREATE OR REPLACE FUNCTION get_paper_total_pnl()
RETURNS DECIMAL(18,8) AS $$
BEGIN
    RETURN COALESCE(
        (SELECT SUM(total_pnl_usdt) FROM paper_positions WHERE closed_at IS NULL),
        0
    );
END;
$$ LANGUAGE plpgsql;

-- Function: Get fill rate for symbol
CREATE OR REPLACE FUNCTION get_paper_fill_rate(p_symbol VARCHAR(20), p_days INT DEFAULT 7)
RETURNS DECIMAL(5,4) AS $$
DECLARE
    v_total INT;
    v_filled INT;
BEGIN
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE status IN ('FILLED', 'PARTIAL', 'PARTIALLY_FILLED'))
    INTO v_total, v_filled
    FROM paper_orders
    WHERE symbol = p_symbol
      AND created_at >= NOW() - (p_days || ' days')::INTERVAL;

    IF v_total = 0 THEN
        RETURN 0;
    END IF;

    RETURN v_filled::DECIMAL / v_total;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANTS
-- Set appropriate permissions
-- ============================================================================

-- Grant to execution service user (assumes user 'claire_user' exists)
GRANT SELECT, INSERT, UPDATE ON paper_orders TO claire_user;
GRANT SELECT, INSERT ON paper_fills TO claire_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON paper_positions TO claire_user;
GRANT SELECT, INSERT ON paper_pnl_snapshots TO claire_user;
GRANT SELECT, INSERT, UPDATE ON paper_trading_stats TO claire_user;

-- Grant sequence access
GRANT USAGE, SELECT ON SEQUENCE paper_pnl_snapshots_snapshot_id_seq TO claire_user;
GRANT USAGE, SELECT ON SEQUENCE paper_trading_stats_stat_id_seq TO claire_user;

-- Grant view access
GRANT SELECT ON v_paper_recent_orders TO claire_user;
GRANT SELECT ON v_paper_active_positions TO claire_user;
GRANT SELECT ON v_paper_daily_summary TO claire_user;

-- Grant function execution
GRANT EXECUTE ON FUNCTION get_paper_total_pnl() TO claire_user;
GRANT EXECUTE ON FUNCTION get_paper_fill_rate(VARCHAR, INT) TO claire_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify tables created
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name LIKE 'paper_%';

    RAISE NOTICE 'Created % paper trading tables', v_count;
END $$;

-- Migration complete
SELECT 'Migration 003: Paper Trading Schema - COMPLETE' AS status;
