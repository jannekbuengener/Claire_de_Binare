-- Migration 002: orders.price nullable für Market-Orders
-- Datum: 2025-11-22
-- Grund: Market-Orders haben keinen Limit-Preis
--
-- Semantik:
--   price IS NULL     → Market-Order ohne Limit-Preis
--   price IS NOT NULL → Limit-/Stop-Order mit festem Preis
--
-- Related: Fix #6 - PostgreSQL Persistence Bugs

-- Drop NOT NULL constraint auf orders.price
ALTER TABLE orders
  ALTER COLUMN price DROP NOT NULL;

-- Kommentar aktualisieren
COMMENT ON COLUMN orders.price IS 'Limit-Preis (NULL für Market-Orders ohne Limit)';

-- Migration-Version aktualisieren
INSERT INTO schema_version (version, description) VALUES
    ('1.0.1', 'orders.price nullable für Market-Orders (Fix #6)');

-- Validierung
DO $$
BEGIN
    -- Prüfe dass Constraint erfolgreich entfernt wurde
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders'
        AND column_name = 'price'
        AND is_nullable = 'NO'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: orders.price ist noch NOT NULL';
    END IF;

    RAISE NOTICE 'Migration 002 erfolgreich: orders.price ist jetzt nullable';
END $$;
