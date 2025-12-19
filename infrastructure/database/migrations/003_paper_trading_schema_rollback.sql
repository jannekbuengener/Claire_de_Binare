-- Rollback Migration 003: Paper Trading Schema
-- Claire de Binare Trading Bot
-- Purpose: Remove all paper trading tables, views, and functions

-- ============================================================================
-- DROP VIEWS
-- ============================================================================

DROP VIEW IF EXISTS v_paper_daily_summary;
DROP VIEW IF EXISTS v_paper_active_positions;
DROP VIEW IF EXISTS v_paper_recent_orders;

-- ============================================================================
-- DROP FUNCTIONS
-- ============================================================================

DROP FUNCTION IF EXISTS get_paper_fill_rate(VARCHAR, INT);
DROP FUNCTION IF EXISTS get_paper_total_pnl();

-- ============================================================================
-- DROP TABLES (in reverse order of dependencies)
-- ============================================================================

DROP TABLE IF EXISTS paper_trading_stats CASCADE;
DROP TABLE IF EXISTS paper_pnl_snapshots CASCADE;
DROP TABLE IF EXISTS paper_positions CASCADE;
DROP TABLE IF EXISTS paper_fills CASCADE;
DROP TABLE IF EXISTS paper_orders CASCADE;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name LIKE 'paper_%';

    IF v_count = 0 THEN
        RAISE NOTICE 'All paper trading tables successfully removed';
    ELSE
        RAISE WARNING 'Warning: % paper trading tables still exist', v_count;
    END IF;
END $$;

-- Rollback complete
SELECT 'Migration 003 Rollback: Paper Trading Schema - COMPLETE' AS status;
