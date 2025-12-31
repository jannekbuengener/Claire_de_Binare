-- Migration 003: Add order_id column to orders table
-- Datum: 2025-12-29
-- Grund: Fix Issue #224 - order_id als separate column statt nur in metadata
--
-- Problem:
--   - database.py speichert order_id in metadata JSON
--   - get_order_by_id() erwartet order_id als column (fehlt aktuell)
--   - Führt zu "column order_id does not exist" Error
--
-- Related: Issue #224 - order_results not published (DB schema mismatch)

-- Add order_id column to orders table
ALTER TABLE orders
  ADD COLUMN order_id VARCHAR(100) UNIQUE;

-- Create index for fast lookups
CREATE INDEX idx_orders_order_id ON orders(order_id);

-- Comment
COMMENT ON COLUMN orders.order_id IS 'Execution Service Order ID (unique identifier for order tracking)';

-- Migrate existing data: Extract order_id from metadata JSON to new column
UPDATE orders
SET order_id = metadata->>'order_id'
WHERE metadata IS NOT NULL AND metadata ? 'order_id';

-- Migration-Version aktualisieren
INSERT INTO schema_version (version, description) VALUES
    ('1.0.2', 'Add order_id column to orders table (Fix Issue #224)');

-- Validierung
DO $$
BEGIN
    -- Prüfe dass Column erfolgreich hinzugefügt wurde
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders'
        AND column_name = 'order_id'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: orders.order_id column fehlt';
    END IF;

    -- Prüfe dass Index erstellt wurde
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'orders'
        AND indexname = 'idx_orders_order_id'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: idx_orders_order_id index fehlt';
    END IF;

    RAISE NOTICE 'Migration 003 erfolgreich: orders.order_id column und index erstellt';
END $$;
