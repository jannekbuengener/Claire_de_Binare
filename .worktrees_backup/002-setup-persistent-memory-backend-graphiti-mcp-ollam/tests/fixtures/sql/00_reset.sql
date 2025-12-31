-- Test Fixture: Reset Database State
-- Purpose: Truncate all tables for clean E2E test runs
-- Usage: Applied before each E2E test to ensure deterministic state

-- Truncate tables in reverse dependency order to avoid FK violations
TRUNCATE TABLE portfolio_snapshots RESTART IDENTITY CASCADE;
TRUNCATE TABLE positions RESTART IDENTITY CASCADE;
TRUNCATE TABLE trades RESTART IDENTITY CASCADE;
TRUNCATE TABLE orders RESTART IDENTITY CASCADE;
TRUNCATE TABLE signals RESTART IDENTITY CASCADE;

-- Reset schema version (optional - only if testing migrations)
-- TRUNCATE TABLE schema_version RESTART IDENTITY CASCADE;

-- Verify reset completed
DO $$
DECLARE
    signals_count INTEGER;
    orders_count INTEGER;
    trades_count INTEGER;
    positions_count INTEGER;
    snapshots_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO signals_count FROM signals;
    SELECT COUNT(*) INTO orders_count FROM orders;
    SELECT COUNT(*) INTO trades_count FROM trades;
    SELECT COUNT(*) INTO positions_count FROM positions;
    SELECT COUNT(*) INTO snapshots_count FROM portfolio_snapshots;

    RAISE NOTICE 'DB Reset Complete:';
    RAISE NOTICE '  signals: %', signals_count;
    RAISE NOTICE '  orders: %', orders_count;
    RAISE NOTICE '  trades: %', trades_count;
    RAISE NOTICE '  positions: %', positions_count;
    RAISE NOTICE '  portfolio_snapshots: %', snapshots_count;

    IF signals_count > 0 OR orders_count > 0 OR trades_count > 0
       OR positions_count > 0 OR snapshots_count > 0 THEN
        RAISE EXCEPTION 'Reset failed: tables not empty';
    END IF;
END $$;
