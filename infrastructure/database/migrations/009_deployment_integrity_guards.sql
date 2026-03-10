-- Migration 009: Deployment-domain integrity guard metadata
-- Datum: 2026-03-01
-- Zweck: Add additive deployment approvals integrity metadata (#752)

ALTER TABLE deployment_approvals_mirror
    ADD COLUMN IF NOT EXISTS integrity_algo TEXT,
    ADD COLUMN IF NOT EXISTS integrity_version INTEGER;

ALTER TABLE IF EXISTS deployment_approvals
    ADD COLUMN IF NOT EXISTS integrity_algo TEXT,
    ADD COLUMN IF NOT EXISTS integrity_version INTEGER;

INSERT INTO schema_version (version, description)
SELECT '1.0.8', 'Add deployment-domain integrity metadata (#752)'
WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = '1.0.8');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'deployment_approvals_mirror'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: deployment_approvals_mirror fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'deployment_approvals_mirror'
          AND column_name = 'integrity_hash'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: deployment_approvals_mirror.integrity_hash fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'deployment_approvals_mirror'
          AND column_name = 'integrity_algo'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: deployment_approvals_mirror.integrity_algo fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'deployment_approvals_mirror'
          AND column_name = 'integrity_version'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: deployment_approvals_mirror.integrity_version fehlt';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'deployment_approvals'
    ) THEN
        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'deployment_approvals'
              AND column_name = 'integrity_algo'
        ) THEN
            RAISE EXCEPTION 'Migration fehlgeschlagen: deployment_approvals.integrity_algo fehlt';
        END IF;

        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'deployment_approvals'
              AND column_name = 'integrity_version'
        ) THEN
            RAISE EXCEPTION 'Migration fehlgeschlagen: deployment_approvals.integrity_version fehlt';
        END IF;
    END IF;

    RAISE NOTICE 'Migration 009 erfolgreich: deployment-domain integrity metadata erweitert';
END $$;
