-- Migration 004: Governance v0 tables (mirror + audit)
-- Datum: 2026-01-29
-- Zweck: Minimal governance/audit mirror tables for DB-hardening tasks (#750-#753)
--
-- Notes:
--   - No secrets/values stored (refs/fingerprints only)
--   - Canonical authority remains versioned YAML in Claire_de_Binare
--   - Append-only readiness (no upserts)

CREATE TABLE core_secrets_metadata (
    secret_name VARCHAR(255) PRIMARY KEY,
    provider_ref TEXT,
    fingerprint TEXT,
    integrity_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_trail (
    id BIGSERIAL PRIMARY KEY,
    service_name TEXT,
    action_type TEXT,
    actor_id TEXT,
    payload JSONB,
    integrity_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_trail_created_at ON audit_trail(created_at);

CREATE TABLE governance_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT,
    evidence_ref TEXT,
    integrity_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_governance_events_event_type ON governance_events(event_type);

CREATE TABLE deployment_approvals_mirror (
    id BIGSERIAL PRIMARY KEY,
    pr_id TEXT,
    commit_sha TEXT,
    yaml_evidence_path TEXT,
    integrity_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_deployment_approvals_mirror_pr_id ON deployment_approvals_mirror(pr_id);

CREATE TABLE security_policy_refs (
    policy_id TEXT PRIMARY KEY,
    version_hash TEXT,
    docs_path TEXT,
    integrity_hash TEXT,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_security_policy_refs_version_hash ON security_policy_refs(version_hash);

INSERT INTO schema_version (version, description) VALUES
    ('1.0.3', 'Add governance mirror tables v0 (DB-HARDENING #750-#753)');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'core_secrets_metadata'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: core_secrets_metadata fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_trail'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: audit_trail fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'governance_events'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: governance_events fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'deployment_approvals_mirror'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: deployment_approvals_mirror fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'security_policy_refs'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: security_policy_refs fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE tablename = 'audit_trail' AND indexname = 'idx_audit_trail_created_at'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: idx_audit_trail_created_at fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE tablename = 'governance_events' AND indexname = 'idx_governance_events_event_type'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: idx_governance_events_event_type fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE tablename = 'deployment_approvals_mirror' AND indexname = 'idx_deployment_approvals_mirror_pr_id'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: idx_deployment_approvals_mirror_pr_id fehlt';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE tablename = 'security_policy_refs' AND indexname = 'idx_security_policy_refs_version_hash'
    ) THEN
        RAISE EXCEPTION 'Migration fehlgeschlagen: idx_security_policy_refs_version_hash fehlt';
    END IF;

    RAISE NOTICE 'Migration 004 erfolgreich: governance v0 Tabellen und Indizes erstellt';
END $$;
