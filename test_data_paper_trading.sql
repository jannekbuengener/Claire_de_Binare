-- ============================================================================
-- Claire de Binare - Test Data für Paper Trading Dashboard
-- ============================================================================
-- Generiert realistische Trading-Daten für die letzten 24 Stunden
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. SIGNALS - Trading-Signale
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
-- 2. ORDERS - Approved Orders vom Risk Manager
-- ============================================================================

INSERT INTO orders (symbol, side, quantity, price, status, timestamp) VALUES
('BTCUSDT', 'buy', 0.002, 50000.00, 'filled', NOW() - INTERVAL '23 hours'),
('ETHUSDT', 'buy', 0.033, 3000.00, 'filled', NOW() - INTERVAL '22 hours'),
('BTCUSDT', 'sell', 0.002, 50500.00, 'filled', NOW() - INTERVAL '20 hours'),
('SOLUSDT', 'buy', 0.667, 150.00, 'filled', NOW() - INTERVAL '18 hours'),
('BTCUSDT', 'buy', 0.002, 49800.00, 'filled', NOW() - INTERVAL '16 hours'),
('ETHUSDT', 'sell', 0.033, 3050.00, 'filled', NOW() - INTERVAL '14 hours'),
('ADAUSDT', 'buy', 222.22, 0.45, 'rejected', NOW() - INTERVAL '12 hours'), -- Risk rejected
('BTCUSDT', 'sell', 0.002, 50200.00, 'filled', NOW() - INTERVAL '10 hours'),
('SOLUSDT', 'sell', 0.667, 152.00, 'filled', NOW() - INTERVAL '8 hours'),
('ETHUSDT', 'buy', 0.034, 2980.00, 'filled', NOW() - INTERVAL '6 hours'),
('BTCUSDT', 'buy', 0.002, 50100.00, 'filled', NOW() - INTERVAL '4 hours'),
('MATICUSDT', 'buy', 117.65, 0.85, 'filled', NOW() - INTERVAL '2 hours'),
('BTCUSDT', 'sell', 0.002, 50300.00, 'filled', NOW() - INTERVAL '1 hour');

-- ============================================================================
-- 3. TRADES - Completed Trades mit PnL
-- ============================================================================

-- Trade 1: BTC Long +$10 (Win)
INSERT INTO trades (symbol, side, quantity, entry_price, exit_price, pnl, timestamp)
VALUES ('BTCUSDT', 'buy', 0.002, 50000.00, 50500.00, 1.00, NOW() - INTERVAL '20 hours');

-- Trade 2: ETH Long +$1.65 (Win)
INSERT INTO trades (symbol, side, quantity, entry_price, exit_price, pnl, timestamp)
VALUES ('ETHUSDT', 'buy', 0.033, 3000.00, 3050.00, 1.65, NOW() - INTERVAL '14 hours');

-- Trade 3: BTC Long -$8 (Loss)
INSERT INTO trades (symbol, side, quantity, entry_price, exit_price, pnl, timestamp)
VALUES ('BTCUSDT', 'buy', 0.002, 49800.00, 50200.00, 0.80, NOW() - INTERVAL '10 hours');

-- Trade 4: SOL Long +$1.33 (Win)
INSERT INTO trades (symbol, side, quantity, entry_price, exit_price, pnl, timestamp)
VALUES ('SOLUSDT', 'buy', 0.667, 150.00, 152.00, 1.33, NOW() - INTERVAL '8 hours');

-- Trade 5: BTC Long -$4 (Loss)
INSERT INTO trades (symbol, side, quantity, entry_price, exit_price, pnl, timestamp)
VALUES ('BTCUSDT', 'buy', 0.002, 50100.00, 50300.00, 0.40, NOW() - INTERVAL '1 hour');

-- Trade 6: BTC Short (gestern) +$15 (Win)
INSERT INTO trades (symbol, side, quantity, entry_price, exit_price, pnl, timestamp)
VALUES ('BTCUSDT', 'sell', 0.003, 51000.00, 50000.00, 3.00, NOW() - INTERVAL '30 hours');

-- Trade 7: ETH Long (gestern) +$8 (Win)
INSERT INTO trades (symbol, side, quantity, entry_price, exit_price, pnl, timestamp)
VALUES ('ETHUSDT', 'buy', 0.040, 2950.00, 3000.00, 2.00, NOW() - INTERVAL '28 hours');

-- Trade 8: SOL Short (gestern) -$10 (Loss)
INSERT INTO trades (symbol, side, quantity, entry_price, exit_price, pnl, timestamp)
VALUES ('SOLUSDT', 'sell', 1.0, 155.00, 150.00, -5.00, NOW() - INTERVAL '26 hours');

-- ============================================================================
-- 4. POSITIONS - Offene Positionen
-- ============================================================================

-- Position 1: ETH Long (aktuell im Profit)
INSERT INTO positions (symbol, quantity, entry_price, current_price, unrealized_pnl, updated_at)
VALUES ('ETHUSDT', 0.034, 2980.00, 3020.00, 1.36, NOW())
ON CONFLICT (symbol) DO UPDATE SET
    quantity = EXCLUDED.quantity,
    entry_price = EXCLUDED.entry_price,
    current_price = EXCLUDED.current_price,
    unrealized_pnl = EXCLUDED.unrealized_pnl,
    updated_at = EXCLUDED.updated_at;

-- Position 2: MATIC Long (aktuell leicht im Minus)
INSERT INTO positions (symbol, quantity, entry_price, current_price, unrealized_pnl, updated_at)
VALUES ('MATICUSDT', 117.65, 0.85, 0.84, -1.18, NOW())
ON CONFLICT (symbol) DO UPDATE SET
    quantity = EXCLUDED.quantity,
    entry_price = EXCLUDED.entry_price,
    current_price = EXCLUDED.current_price,
    unrealized_pnl = EXCLUDED.unrealized_pnl,
    updated_at = EXCLUDED.updated_at;

-- ============================================================================
-- 5. PORTFOLIO_SNAPSHOTS - Portfolio-Entwicklung
-- ============================================================================

-- Snapshot heute Morgen (Start des Tages)
INSERT INTO portfolio_snapshots (total_equity, total_pnl, daily_pnl, max_drawdown, timestamp)
VALUES (100000.00, 0.00, 0.00, 0.00, DATE_TRUNC('day', NOW()));

-- Snapshot vor 6 Stunden
INSERT INTO portfolio_snapshots (total_equity, total_pnl, daily_pnl, max_drawdown, timestamp)
VALUES (100003.18, 3.18, 3.18, 0.00, NOW() - INTERVAL '6 hours');

-- Snapshot aktuell
INSERT INTO portfolio_snapshots (total_equity, total_pnl, daily_pnl, max_drawdown, timestamp)
VALUES (100005.18, 5.18, 5.18, 0.00, NOW());

-- Snapshot gestern (für Vergleich)
INSERT INTO portfolio_snapshots (total_equity, total_pnl, daily_pnl, max_drawdown, timestamp)
VALUES (100000.00, 0.00, 0.00, 0.00, NOW() - INTERVAL '24 hours');

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check inserted data
SELECT 'Signals' as table_name, COUNT(*) as count FROM signals
UNION ALL
SELECT 'Orders', COUNT(*) FROM orders
UNION ALL
SELECT 'Trades', COUNT(*) FROM trades
UNION ALL
SELECT 'Positions', COUNT(*) FROM positions WHERE quantity != 0
UNION ALL
SELECT 'Portfolio Snapshots', COUNT(*) FROM portfolio_snapshots;

-- Show today's trading summary
SELECT
    COUNT(*) as total_trades,
    COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
    COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades,
    ROUND(100.0 * COUNT(CASE WHEN pnl > 0 THEN 1 END) / COUNT(*), 1) as win_rate_pct,
    ROUND(SUM(pnl)::numeric, 2) as total_pnl
FROM trades
WHERE DATE(timestamp) = CURRENT_DATE;

-- Show open positions
SELECT
    symbol,
    quantity,
    entry_price,
    current_price,
    ROUND(unrealized_pnl::numeric, 2) as unrealized_pnl
FROM positions
WHERE quantity != 0
ORDER BY ABS(unrealized_pnl) DESC;
