-- Migration 008: Access-domain integrity guard metadata
-- Datum: 2026-03-01
-- Zweck: Add additive access-domain mirror storage + integrity metadata (#753)

CREATE TABLE IF NOT EXISTS system_config (
    config_key TEXT PRIMARY KEY,
    config_scope TEXT NOT NULL DEFAULT 'global',
    value_ref TEXT,
    value_hash TEXT NOT NULL,
    source_path TEXT,
    integrity_hash TEXT,
    integrity_algo TEXT,
    integrity_version INTEGER,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_config_observed_at
    ON system_config(observed_at);

ALTER TABLE security_policy_refs
    ADD COLUMN IF NOT EXISTS integrity_algo TEXT,
    ADD COLUMN IF NOT EXISTS integrity_version INTEGER;

INSERT INTO schema_version (version, description)
SELECT '1.0.7', 'Add access-domain integrity metadata and system_config mirror (#753)'
WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = '1.0.7');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'system_config'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: system_config fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'system_config'
          AND column_name = 'integrity_hash'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: system_config.integrity_hash fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'system_config'
          AND column_name = 'integrity_algo'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: system_config.integrity_algo fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'system_config'
          AND column_name = 'integrity_version'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: system_config.integrity_version fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'security_policy_refs'
          AND column_name = 'integrity_algo'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: security_policy_refs.integrity_algo fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'security_policy_refs'
          AND column_name = 'integrity_version'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: security_policy_refs.integrity_version fehlt';
    END IF;

    RAISE NOTICE 'Migration 008 erfolgreich: access-domain integrity metadata erweitert';
END $$;
