-- Migration 011: Add per-trade realized outcome field
-- Date: 2026-04-09
-- Reason: Issue #203 - make positive trades repo-backed for dashboards and reports
--
-- Semantics:
--   realized_pnl IS NULL  -> execution row has no closed trade outcome yet
--   realized_pnl > 0      -> positive trade outcome
--   realized_pnl = 0      -> breakeven trade outcome
--   realized_pnl < 0      -> negative trade outcome

ALTER TABLE trades
    ADD COLUMN IF NOT EXISTS realized_pnl DECIMAL(18, 8);

COMMENT ON COLUMN trades.realized_pnl IS
    'Realized PnL for exit executions; NULL while the trade row does not carry a closed outcome';

INSERT INTO schema_version (version, description)
SELECT '1.0.10', 'Add trades.realized_pnl for repo-backed positive-trade analytics (#203)'
WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = '1.0.10');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'trades'
          AND column_name = 'realized_pnl'
    ) THEN
        RAISE EXCEPTION 'Migration failed: trades.realized_pnl column missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM schema_version WHERE version = '1.0.10'
    ) THEN
        RAISE EXCEPTION 'Migration failed: schema_version 1.0.10 not found';
    END IF;

    RAISE NOTICE 'Migration 011 successful: trades.realized_pnl added';
END $$;
