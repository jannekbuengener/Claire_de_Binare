-- Migration 013: Add candle backfill provenance for ARVP replay market data
-- Date: 2026-04-24
-- Reason: Issue #1906 requires real-source, provenance-backed candle backfills.

CREATE TABLE IF NOT EXISTS candle_backfill_imports (
    import_id              UUID PRIMARY KEY,
    source                 TEXT                     NOT NULL,
    source_url             TEXT                     NOT NULL,
    import_command         TEXT                     NOT NULL,
    imported_at            TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol                 VARCHAR(20)              NOT NULL,
    start_ts_ms            BIGINT                   NOT NULL,
    end_ts_ms              BIGINT                   NOT NULL,
    row_count              INTEGER                  NOT NULL,
    inserted_count         INTEGER                  NOT NULL,
    skipped_existing_count INTEGER                  NOT NULL,
    checksum_sha256        CHAR(64)                 NOT NULL,
    payload                JSONB                    NOT NULL,

    CONSTRAINT candle_backfill_window_valid CHECK (start_ts_ms <= end_ts_ms),
    CONSTRAINT candle_backfill_counts_nonneg CHECK (
        row_count >= 0 AND inserted_count >= 0 AND skipped_existing_count >= 0
    ),
    CONSTRAINT candle_backfill_checksum_hex CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE INDEX IF NOT EXISTS idx_candle_backfill_symbol_window
    ON candle_backfill_imports(symbol, start_ts_ms, end_ts_ms);

COMMENT ON TABLE candle_backfill_imports IS
    'Provenance records for real-source candle backfills into public.candles_1m (#1906).';
COMMENT ON COLUMN candle_backfill_imports.source IS
    'Real historical source identifier, e.g. binance_spot_api_v3_klines. No mock source allowed.';
COMMENT ON COLUMN candle_backfill_imports.checksum_sha256 IS
    'SHA-256 over canonical imported candle rows.';
COMMENT ON COLUMN candle_backfill_imports.payload IS
    'Full import manifest including source query/URL, command, row counts, and stable row payloads.';

GRANT ALL PRIVILEGES ON TABLE candle_backfill_imports TO claire_user;

INSERT INTO schema_version (version, description)
SELECT '1.1.1', 'Add candle backfill provenance table for ARVP replay data continuity (Issue #1906)'
WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = '1.1.1');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'candle_backfill_imports'
    ) THEN
        RAISE EXCEPTION 'Migration failed: public.candle_backfill_imports table missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM schema_version WHERE version = '1.1.1'
    ) THEN
        RAISE EXCEPTION 'Migration failed: schema_version 1.1.1 not found';
    END IF;

    RAISE NOTICE 'Migration 013 successful: public.candle_backfill_imports created';
END $$;
