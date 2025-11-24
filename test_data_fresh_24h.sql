-- ============================================================================
-- Claire de Binare - Fresh Test Data (Last 24 Hours)
-- ============================================================================
-- Schema-konform: size, execution_price, fees, total_realized_pnl, etc.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. SIGNALS - Last 24h
-- ============================================================================
INSERT INTO signals (symbol, signal_type, confidence, price, timestamp) VALUES
('BTCUSDT', 'buy', 0.78, 50000.00, NOW() - INTERVAL '23 hours'),
('ETHUSDT', 'buy', 0.65, 3000.00, NOW() - INTERVAL '22 hours'),
('BTCUSDT', 'sell', 0.72, 50500.00, NOW() - INTERVAL '20 hours'),
('SOLUSDT', 'buy', 0.81, 150.00, NOW() - INTERVAL '18 hours'),
('BTCUSDT', 'buy', 0.69, 49800.00, NOW() - INTERVAL '16 hours'),
('ETHUSDT', 'sell', 0.75, 3050.00, NOW() - INTERVAL '14 hours'),
('ADAUSDT', 'buy', 0.58, 0.45, NOW() - INTERVAL '12 hours'),
('BTCUSDT', 'sell', 0.84, 50200.00, NOW() - INTERVAL '10 hours'),
('SOLUSDT', 'sell', 0.77, 152.00, NOW() - INTERVAL '8 hours'),
('ETHUSDT', 'buy', 0.71, 2980.00, NOW() - INTERVAL '6 hours'),
('BTCUSDT', 'buy', 0.66, 50100.00, NOW() - INTERVAL '4 hours'),
('MATICUSDT', 'buy', 0.79, 0.85, NOW() - INTERVAL '2 hours'),
('BTCUSDT', 'sell', 0.73, 50300.00, NOW() - INTERVAL '1 hour');

-- ============================================================================
-- 2. ORDERS (Schema: size, approved, filled_size, avg_fill_price)
-- ============================================================================
INSERT INTO orders (symbol, side, price, size, approved, status, filled_size, avg_fill_price, created_at, filled_at) VALUES
('BTCUSDT', 'buy', 50000.00, 0.002, true, 'filled', 0.002, 50000.00, NOW() - INTERVAL '23 hours', NOW() - INTERVAL '23 hours'),
('ETHUSDT', 'buy', 3000.00, 0.033, true, 'filled', 0.033, 3000.00, NOW() - INTERVAL '22 hours', NOW() - INTERVAL '22 hours'),
('BTCUSDT', 'sell', 50500.00, 0.002, true, 'filled', 0.002, 50500.00, NOW() - INTERVAL '20 hours', NOW() - INTERVAL '20 hours'),
('SOLUSDT', 'buy', 150.00, 0.667, true, 'filled', 0.667, 150.00, NOW() - INTERVAL '18 hours', NOW() - INTERVAL '18 hours'),
('BTCUSDT', 'buy', 49800.00, 0.002, true, 'filled', 0.002, 49800.00, NOW() - INTERVAL '16 hours', NOW() - INTERVAL '16 hours'),
('ETHUSDT', 'sell', 3050.00, 0.033, true, 'filled', 0.033, 3050.00, NOW() - INTERVAL '14 hours', NOW() - INTERVAL '14 hours'),
('ADAUSDT', 'buy', 0.45, 222.22, false, 'rejected', 0, 0, NOW() - INTERVAL '12 hours', NULL), -- Risk rejected
('BTCUSDT', 'sell', 50200.00, 0.002, true, 'filled', 0.002, 50200.00, NOW() - INTERVAL '10 hours', NOW() - INTERVAL '10 hours'),
('SOLUSDT', 'sell', 152.00, 0.667, true, 'filled', 0.667, 152.00, NOW() - INTERVAL '8 hours', NOW() - INTERVAL '8 hours'),
('ETHUSDT', 'buy', 2980.00, 0.034, true, 'filled', 0.034, 2980.00, NOW() - INTERVAL '6 hours', NOW() - INTERVAL '6 hours'),
('BTCUSDT', 'buy', 50100.00, 0.002, true, 'filled', 0.002, 50100.00, NOW() - INTERVAL '4 hours', NOW() - INTERVAL '4 hours'),
('MATICUSDT', 'buy', 0.85, 117.65, true, 'filled', 117.65, 0.85, NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours'),
('BTCUSDT', 'sell', 50300.00, 0.002, true, 'filled', 0.002, 50300.00, NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 hour');

-- ============================================================================
-- 3. TRADES (Schema: size, execution_price, fees, slippage_bps)
-- ============================================================================
INSERT INTO trades (symbol, side, price, size, execution_price, fees, slippage_bps, timestamp) VALUES
-- BTC Trades
('BTCUSDT', 'buy', 50000.00, 0.002, 50000.00, 0.02, 0, NOW() - INTERVAL '23 hours'),
('BTCUSDT', 'sell', 50500.00, 0.002, 50500.00, 0.02, 1, NOW() - INTERVAL '20 hours'),
('BTCUSDT', 'buy', 49800.00, 0.002, 49800.00, 0.02, 0, NOW() - INTERVAL '16 hours'),
('BTCUSDT', 'sell', 50200.00, 0.002, 50200.00, 0.02, 2, NOW() - INTERVAL '10 hours'),
('BTCUSDT', 'buy', 50100.00, 0.002, 50100.00, 0.02, 0, NOW() - INTERVAL '4 hours'),
('BTCUSDT', 'sell', 50300.00, 0.002, 50300.00, 0.02, 1, NOW() - INTERVAL '1 hour'),

-- ETH Trades
('ETHUSDT', 'buy', 3000.00, 0.033, 3000.00, 0.10, 0, NOW() - INTERVAL '22 hours'),
('ETHUSDT', 'sell', 3050.00, 0.033, 3050.00, 0.10, 1, NOW() - INTERVAL '14 hours'),
('ETHUSDT', 'buy', 2980.00, 0.034, 2980.00, 0.10, 0, NOW() - INTERVAL '6 hours'),

-- SOL Trades
('SOLUSDT', 'buy', 150.00, 0.667, 150.00, 0.10, 0, NOW() - INTERVAL '18 hours'),
('SOLUSDT', 'sell', 152.00, 0.667, 152.00, 0.10, 1, NOW() - INTERVAL '8 hours'),

-- MATIC Trade
('MATICUSDT', 'buy', 0.85, 117.65, 0.85, 0.10, 0, NOW() - INTERVAL '2 hours');

-- ============================================================================
-- 4. POSITIONS (Schema: side, size, realized_pnl, unrealized_pnl)
-- ============================================================================

-- ETH Long (im Profit)
INSERT INTO positions (symbol, side, size, entry_price, current_price, unrealized_pnl, realized_pnl, opened_at, updated_at)
VALUES ('ETHUSDT', 'long', 0.034, 2980.00, 3020.00, 1.36, 0.00, NOW() - INTERVAL '6 hours', NOW())
ON CONFLICT (symbol) DO UPDATE SET
    side = EXCLUDED.side,
    size = EXCLUDED.size,
    entry_price = EXCLUDED.entry_price,
    current_price = EXCLUDED.current_price,
    unrealized_pnl = EXCLUDED.unrealized_pnl,
    realized_pnl = EXCLUDED.realized_pnl,
    updated_at = EXCLUDED.updated_at;

-- MATIC Long (leicht im Minus)
INSERT INTO positions (symbol, side, size, entry_price, current_price, unrealized_pnl, realized_pnl, opened_at, updated_at)
VALUES ('MATICUSDT', 'long', 117.65, 0.85, 0.84, -1.18, 0.00, NOW() - INTERVAL '2 hours', NOW())
ON CONFLICT (symbol) DO UPDATE SET
    side = EXCLUDED.side,
    size = EXCLUDED.size,
    entry_price = EXCLUDED.entry_price,
    current_price = EXCLUDED.current_price,
    unrealized_pnl = EXCLUDED.unrealized_pnl,
    realized_pnl = EXCLUDED.realized_pnl,
    updated_at = EXCLUDED.updated_at;

-- ============================================================================
-- 5. PORTFOLIO_SNAPSHOTS (Schema: total_realized_pnl, total_unrealized_pnl)
-- ============================================================================

-- Snapshot Start des Tages
INSERT INTO portfolio_snapshots (
    total_equity,
    total_realized_pnl,
    total_unrealized_pnl,
    max_drawdown_pct,
    total_exposure_pct,
    timestamp
)
VALUES (100000.00, 0.00, 0.00, 0.00, 0.00, DATE_TRUNC('day', NOW()));

-- Snapshot vor 12 Stunden
INSERT INTO portfolio_snapshots (
    total_equity,
    total_realized_pnl,
    total_unrealized_pnl,
    max_drawdown_pct,
    total_exposure_pct,
    timestamp
)
VALUES (100001.50, 1.50, 0.00, 0.00, 0.15, NOW() - INTERVAL '12 hours');

-- Snapshot vor 6 Stunden
INSERT INTO portfolio_snapshots (
    total_equity,
    total_realized_pnl,
    total_unrealized_pnl,
    max_drawdown_pct,
    total_exposure_pct,
    timestamp
)
VALUES (100003.18, 3.00, 0.18, 0.00, 0.20, NOW() - INTERVAL '6 hours');

-- Snapshot aktuell
INSERT INTO portfolio_snapshots (
    total_equity,
    total_realized_pnl,
    total_unrealized_pnl,
    max_drawdown_pct,
    total_exposure_pct,
    timestamp
)
VALUES (100005.18, 5.00, 0.18, 0.00, 0.25, NOW());

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
\echo '=== Data Summary ==='
SELECT 'Signals' as table_name, COUNT(*) as count FROM signals
UNION ALL SELECT 'Orders', COUNT(*) FROM orders
UNION ALL SELECT 'Trades', COUNT(*) FROM trades
UNION ALL SELECT 'Positions (open)', COUNT(*) FROM positions WHERE size > 0
UNION ALL SELECT 'Portfolio Snapshots', COUNT(*) FROM portfolio_snapshots;

\echo '=== Todays Stats ==='
SELECT
    COUNT(*) as total_trades,
    ROUND(SUM(size * execution_price)::numeric, 2) as total_volume_usd,
    ROUND(SUM(fees)::numeric, 2) as total_fees
FROM trades
WHERE DATE(timestamp) = CURRENT_DATE;

\echo '=== Open Positions ==='
SELECT
    symbol,
    side,
    ROUND(size::numeric, 4) as size,
    ROUND(entry_price::numeric, 2) as entry,
    ROUND(current_price::numeric, 2) as current,
    ROUND(unrealized_pnl::numeric, 2) as pnl
FROM positions
WHERE size > 0;
