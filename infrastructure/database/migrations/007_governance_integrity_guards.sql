-- Migration 007: Governance integrity guard metadata
-- Datum: 2026-03-01
-- Zweck: Add integrity algorithm/version columns for governance mirror tables (#751)

ALTER TABLE audit_trail
    ADD COLUMN IF NOT EXISTS integrity_algo TEXT,
    ADD COLUMN IF NOT EXISTS integrity_version INTEGER;

ALTER TABLE governance_events
    ADD COLUMN IF NOT EXISTS integrity_algo TEXT,
    ADD COLUMN IF NOT EXISTS integrity_version INTEGER;

INSERT INTO schema_version (version, description)
SELECT '1.0.6', 'Add governance integrity algorithm/version metadata (#751)'
WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = '1.0.6');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'audit_trail'
          AND column_name = 'integrity_algo'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: audit_trail.integrity_algo fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'audit_trail'
          AND column_name = 'integrity_version'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: audit_trail.integrity_version fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'governance_events'
          AND column_name = 'integrity_algo'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: governance_events.integrity_algo fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'governance_events'
          AND column_name = 'integrity_version'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: governance_events.integrity_version fehlt';
    END IF;

    RAISE NOTICE 'Migration 007 erfolgreich: governance integrity metadata erweitert';
END $$;
