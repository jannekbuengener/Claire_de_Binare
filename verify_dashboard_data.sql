-- ============================================================================
-- Dashboard Data Verification
-- ============================================================================
-- Prüft, ob alle Panels Daten haben sollten
-- ============================================================================

\echo '=== Panel 1: Order Approval Rate ==='
SELECT
    COUNT(*) as total_orders,
    COUNT(CASE WHEN approved THEN 1 END) as approved_orders,
    ROUND(100.0 * COUNT(CASE WHEN approved THEN 1 END) / NULLIF(COUNT(*), 0), 2) as approval_rate_pct
FROM orders
WHERE DATE(created_at) >= CURRENT_DATE - INTERVAL '24 hours';

\echo ''
\echo '=== Panel 2: Total PnL Today ==='
SELECT
    COALESCE(SUM(total_realized_pnl + total_unrealized_pnl), 0) as total_pnl
FROM portfolio_snapshots
WHERE DATE(timestamp) = CURRENT_DATE
ORDER BY timestamp DESC
LIMIT 1;

\echo ''
\echo '=== Panel 3: Daily Drawdown ==='
SELECT
    COALESCE(MAX(max_drawdown_pct), 0) as max_drawdown_pct
FROM portfolio_snapshots
WHERE DATE(timestamp) = CURRENT_DATE;

\echo ''
\echo '=== Panel 4: Trades per Hour (Last 24h) ==='
SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as trades
FROM trades
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC
LIMIT 5;

\echo ''
\echo '=== Panel 5: Latest Trades (Last 10) ==='
SELECT
    symbol,
    side,
    ROUND(size::numeric, 4) as size,
    ROUND(execution_price::numeric, 2) as execution_price,
    ROUND(fees::numeric, 4) as fees,
    slippage_bps,
    timestamp
FROM trades
WHERE timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC
LIMIT 10;

\echo ''
\echo '=== Panel 7: Open Positions ==='
SELECT
    symbol,
    side,
    ROUND(size::numeric, 4) as size,
    ROUND(entry_price::numeric, 2) as entry_price,
    ROUND(current_price::numeric, 2) as current_price,
    ROUND(unrealized_pnl::numeric, 2) as unrealized_pnl
FROM positions
WHERE size > 0
ORDER BY ABS(unrealized_pnl) DESC;

\echo ''
\echo '=== Panel 10: Portfolio Equity Over Time ==='
SELECT
    timestamp,
    ROUND(total_equity::numeric, 2) as equity,
    ROUND((total_realized_pnl + total_unrealized_pnl)::numeric, 2) as total_pnl
FROM portfolio_snapshots
WHERE timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp;
