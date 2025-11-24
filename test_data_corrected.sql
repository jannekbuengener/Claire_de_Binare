-- ============================================================================
-- Claire de Binare - Test Data (CORRECTED für echtes Schema)
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. SIGNALS
-- ============================================================================
INSERT INTO signals (symbol, signal_type, confidence, price, timestamp) VALUES
('BTCUSDT', 'buy', 0.78, 50000.00, NOW() - INTERVAL '23 hours'),
('ETHUSDT', 'buy', 0.65, 3000.00, NOW() - INTERVAL '22 hours'),
('BTCUSDT', 'sell', 0.72, 50500.00, NOW() - INTERVAL '20 hours'),
('SOLUSDT', 'buy', 0.81, 150.00, NOW() - INTERVAL '18 hours'),
('BTCUSDT', 'buy', 0.69, 49800.00, NOW() - INTERVAL '16 hours'),
('ETHUSDT', 'sell', 0.75, 3050.00, NOW() - INTERVAL '14 hours'),
('BTCUSDT', 'buy', 0.66, 50100.00, NOW() - INTERVAL '4 hours'),
('MATICUSDT', 'buy', 0.79, 0.85, NOW() - INTERVAL '2 hours');

-- ============================================================================
-- 2. ORDERS (mit size statt quantity, approved = true für filled)
-- ============================================================================
INSERT INTO orders (symbol, side, price, size, approved, status, filled_size, avg_fill_price, created_at, filled_at) VALUES
('BTCUSDT', 'buy', 50000.00, 0.002, true, 'filled', 0.002, 50000.00, NOW() - INTERVAL '23 hours', NOW() - INTERVAL '23 hours'),
('ETHUSDT', 'buy', 3000.00, 0.033, true, 'filled', 0.033, 3000.00, NOW() - INTERVAL '22 hours', NOW() - INTERVAL '22 hours'),
('BTCUSDT', 'sell', 50500.00, 0.002, true, 'filled', 0.002, 50500.00, NOW() - INTERVAL '20 hours', NOW() - INTERVAL '20 hours'),
('SOLUSDT', 'buy', 150.00, 0.667, true, 'filled', 0.667, 150.00, NOW() - INTERVAL '18 hours', NOW() - INTERVAL '18 hours'),
('BTCUSDT', 'buy', 49800.00, 0.002, true, 'filled', 0.002, 49800.00, NOW() - INTERVAL '16 hours', NOW() - INTERVAL '16 hours'),
('ETHUSDT', 'sell', 3050.00, 0.033, true, 'filled', 0.033, 3050.00, NOW() - INTERVAL '14 hours', NOW() - INTERVAL '14 hours'),
('BTCUSDT', 'buy', 50100.00, 0.002, true, 'filled', 0.002, 50100.00, NOW() - INTERVAL '4 hours', NOW() - INTERVAL '4 hours'),
('MATICUSDT', 'buy', 0.85, 117.65, true, 'filled', 117.65, 0.85, NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours');

-- ============================================================================
-- 3. TRADES (mit size statt quantity, execution_price, fees)
-- ============================================================================
INSERT INTO trades (symbol, side, price, size, execution_price, fees, timestamp) VALUES
-- BTC Trades
('BTCUSDT', 'buy', 50000.00, 0.002, 50000.00, 0.02, NOW() - INTERVAL '23 hours'),
('BTCUSDT', 'sell', 50500.00, 0.002, 50500.00, 0.02, NOW() - INTERVAL '20 hours'),
('BTCUSDT', 'buy', 49800.00, 0.002, 49800.00, 0.02, NOW() - INTERVAL '16 hours'),
('BTCUSDT', 'buy', 50100.00, 0.002, 50100.00, 0.02, NOW() - INTERVAL '4 hours'),

-- ETH Trades
('ETHUSDT', 'buy', 3000.00, 0.033, 3000.00, 0.10, NOW() - INTERVAL '22 hours'),
('ETHUSDT', 'sell', 3050.00, 0.033, 3050.00, 0.10, NOW() - INTERVAL '14 hours'),

-- SOL Trade
('SOLUSDT', 'buy', 150.00, 0.667, 150.00, 0.10, NOW() - INTERVAL '18 hours'),

-- MATIC Trade
('MATICUSDT', 'buy', 0.85, 117.65, 0.85, 0.10, NOW() - INTERVAL '2 hours');

-- ============================================================================
-- 4. POSITIONS (mit size statt quantity)
-- ============================================================================

-- Position 1: BTC Long (2x 0.002 = 0.004 BTC)
INSERT INTO positions (symbol, side, size, entry_price, current_price, unrealized_pnl, realized_pnl, opened_at, updated_at)
VALUES ('BTCUSDT', 'long', 0.004, 49950.00, 50200.00, 1.00, 0.00, NOW() - INTERVAL '16 hours', NOW())
ON CONFLICT (symbol) DO UPDATE SET
    side = EXCLUDED.side,
    size = EXCLUDED.size,
    entry_price = EXCLUDED.entry_price,
    current_price = EXCLUDED.current_price,
    unrealized_pnl = EXCLUDED.unrealized_pnl,
    realized_pnl = EXCLUDED.realized_pnl,
    updated_at = EXCLUDED.updated_at;

-- Position 2: MATIC Long
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
-- 5. PORTFOLIO_SNAPSHOTS
-- ============================================================================
INSERT INTO portfolio_snapshots (total_equity, total_pnl, daily_pnl, max_drawdown, timestamp) VALUES
(100000.00, 0.00, 0.00, 0.00, DATE_TRUNC('day', NOW())),
(100003.18, 3.18, 3.18, 0.00, NOW() - INTERVAL '6 hours'),
(100005.18, 5.18, 5.18, 0.00, NOW());

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
