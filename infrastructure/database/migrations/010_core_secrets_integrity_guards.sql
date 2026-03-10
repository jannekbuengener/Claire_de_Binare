-- Migration 010: Core-secrets integrity guard metadata
-- Datum: 2026-03-01
-- Zweck: Add additive core-secrets integrity metadata (#750)

ALTER TABLE core_secrets_metadata
    ADD COLUMN IF NOT EXISTS integrity_algo TEXT,
    ADD COLUMN IF NOT EXISTS integrity_version INTEGER;

ALTER TABLE IF EXISTS core_secrets
    ADD COLUMN IF NOT EXISTS integrity_algo TEXT,
    ADD COLUMN IF NOT EXISTS integrity_version INTEGER;

ALTER TABLE IF EXISTS service_secrets
    ADD COLUMN IF NOT EXISTS integrity_algo TEXT,
    ADD COLUMN IF NOT EXISTS integrity_version INTEGER;

INSERT INTO schema_version (version, description)
SELECT '1.0.9', 'Add core-secrets integrity metadata (#750)'
WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = '1.0.9');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'core_secrets_metadata'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: core_secrets_metadata fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'core_secrets_metadata'
          AND column_name = 'integrity_hash'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: core_secrets_metadata.integrity_hash fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'core_secrets_metadata'
          AND column_name = 'integrity_algo'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: core_secrets_metadata.integrity_algo fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'core_secrets_metadata'
          AND column_name = 'integrity_version'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: core_secrets_metadata.integrity_version fehlt';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'core_secrets'
    ) THEN
        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'core_secrets'
              AND column_name = 'integrity_algo'
        ) THEN
            RAISE EXCEPTION 'Migration fehlgeschlagen: core_secrets.integrity_algo fehlt';
        END IF;

        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'core_secrets'
              AND column_name = 'integrity_version'
        ) THEN
            RAISE EXCEPTION 'Migration fehlgeschlagen: core_secrets.integrity_version fehlt';
        END IF;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'service_secrets'
    ) THEN
        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'service_secrets'
              AND column_name = 'integrity_algo'
        ) THEN
            RAISE EXCEPTION 'Migration fehlgeschlagen: service_secrets.integrity_algo fehlt';
        END IF;

        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'service_secrets'
              AND column_name = 'integrity_version'
        ) THEN
            RAISE EXCEPTION 'Migration fehlgeschlagen: service_secrets.integrity_version fehlt';
        END IF;
    END IF;

    RAISE NOTICE 'Migration 010 erfolgreich: core-secrets integrity metadata erweitert';
END $$;
