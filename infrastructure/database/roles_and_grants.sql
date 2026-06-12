-- ============================================================================
-- Postgres Least-Privilege Roles & Grants (Issue #741)
-- ============================================================================
-- Idempotent: safe to re-run.  All GRANTs guarded by IF EXISTS checks.
-- Does NOT revoke existing claire_user privileges.
-- Enforcement (revoke ALL from claire_user) is a separate, deliberate step —
-- see enforce_least_privilege.sql.
--
-- Run as superuser / database owner:
--   psql -U postgres -d claire_de_binare -f roles_and_grants.sql
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Create roles (idempotent)
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cdb_reader') THEN
        CREATE ROLE cdb_reader NOLOGIN;
        RAISE NOTICE 'Created role cdb_reader';
    ELSE
        RAISE NOTICE 'Role cdb_reader already exists';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cdb_writer') THEN
        CREATE ROLE cdb_writer NOLOGIN;
        RAISE NOTICE 'Created role cdb_writer';
    ELSE
        RAISE NOTICE 'Role cdb_writer already exists';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cdb_admin') THEN
        CREATE ROLE cdb_admin NOLOGIN;
        RAISE NOTICE 'Created role cdb_admin';
    ELSE
        RAISE NOTICE 'Role cdb_admin already exists';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 2. Schema access
-- ----------------------------------------------------------------------------

GRANT USAGE ON SCHEMA public TO cdb_reader;
GRANT USAGE ON SCHEMA public TO cdb_writer;
GRANT ALL ON SCHEMA public TO cdb_admin;

-- ----------------------------------------------------------------------------
-- 3. cdb_reader: SELECT-only on explicit tables
-- ----------------------------------------------------------------------------

DO $$
DECLARE
    tbl TEXT;
    reader_tables TEXT[] := ARRAY[
        'signals', 'orders', 'trades', 'positions', 'portfolio_snapshots',
        'risk_events', 'correlation_ledger', 'blocked_decisions',
        'candles_1m', 'candle_backfill_imports',
        'core_secrets_metadata', 'audit_trail', 'governance_events',
        'deployment_approvals_mirror', 'system_config', 'security_policy_refs',
        'schema_version'
    ];
BEGIN
    FOREACH tbl IN ARRAY reader_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('GRANT SELECT ON %I TO cdb_reader', tbl);
            RAISE NOTICE 'GRANT SELECT ON % TO cdb_reader', tbl;
        ELSE
            RAISE NOTICE 'SKIP % (table does not exist)', tbl;
        END IF;
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- 4. cdb_writer: INSERT on tables the code actually writes to,
--    UPDATE only where production code requires it, no DELETE anywhere
-- ----------------------------------------------------------------------------

-- Tables the writer INSERTs into (from repo-scan of services/):
--   signals          — signal service
--   orders           — execution service, db_writer
--   trades           — execution service, db_writer
--   positions        — db_writer (also UPDATE)
--   portfolio_snapshots — db_writer
--   risk_events      — risk service
--   correlation_ledger — execution, signal, risk services
--   blocked_decisions — risk service
-- NOTE: validation_runs is SQLite-only (real_validation_fetcher.py), not a Postgres table.

DO $$
DECLARE
    tbl TEXT;
    -- Tables writer can SELECT:
    select_tables TEXT[] := ARRAY[
        'signals', 'orders', 'trades', 'positions', 'portfolio_snapshots',
        'risk_events', 'correlation_ledger', 'blocked_decisions',
        'schema_version'
    ];
    -- Tables writer can INSERT:
    insert_tables TEXT[] := ARRAY[
        'signals', 'orders', 'trades', 'positions', 'portfolio_snapshots',
        'risk_events', 'correlation_ledger', 'blocked_decisions'
    ];
    -- Tables writer can UPDATE (fachlich begründet):
    --   positions: db_writer.py updates size/price/pnl on trade execution
    update_tables TEXT[] := ARRAY[
        'positions'
    ];
    seq_name TEXT;
BEGIN
    -- SELECT grants
    FOREACH tbl IN ARRAY select_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('GRANT SELECT ON %I TO cdb_writer', tbl);
        END IF;
    END LOOP;

    -- INSERT grants
    FOREACH tbl IN ARRAY insert_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('GRANT INSERT ON %I TO cdb_writer', tbl);
            RAISE NOTICE 'GRANT INSERT ON % TO cdb_writer', tbl;
        ELSE
            RAISE NOTICE 'SKIP INSERT % (table does not exist)', tbl;
        END IF;
    END LOOP;

    -- UPDATE grants (only where code requires it)
    FOREACH tbl IN ARRAY update_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('GRANT UPDATE ON %I TO cdb_writer', tbl);
            RAISE NOTICE 'GRANT UPDATE ON % TO cdb_writer', tbl;
        ELSE
            RAISE NOTICE 'SKIP UPDATE % (table does not exist)', tbl;
        END IF;
    END LOOP;

    -- Sequence grants: dynamically find sequences owned by insert_tables
    -- (covers SERIAL, BIGSERIAL, GENERATED columns — no hardcoded names)
    FOREACH tbl IN ARRAY insert_tables LOOP
        FOR seq_name IN
            SELECT s.relname
            FROM pg_class s
            JOIN pg_depend d ON d.objid = s.oid
            JOIN pg_class t ON t.oid = d.refobjid
            WHERE s.relkind = 'S'
              AND t.relname = tbl
              AND t.relnamespace = 'public'::regnamespace
        LOOP
            EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %I TO cdb_writer', seq_name);
            RAISE NOTICE 'GRANT USAGE ON SEQUENCE % TO cdb_writer', seq_name;
        END LOOP;
    END LOOP;
END $$;

-- Explicitly: NO DELETE granted to cdb_writer on any table.
-- Explicitly: NO UPDATE on signals, orders, trades, portfolio_snapshots,
--             risk_events, correlation_ledger, blocked_decisions,
--             core_secrets_metadata, audit_trail, governance_events,
--             deployment_approvals_mirror, security_policy_refs, schema_version.
--             system_config remains read-only for runtime roles.

-- ----------------------------------------------------------------------------
-- 5. cdb_admin: full privileges for DDL/migrations (not used at runtime)
-- ----------------------------------------------------------------------------

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cdb_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cdb_admin;

-- ----------------------------------------------------------------------------
-- 6. Verification
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    RAISE NOTICE '---------------------------------------------';
    RAISE NOTICE 'roles_and_grants.sql applied successfully';
    RAISE NOTICE 'cdb_reader: SELECT on explicit table list';
    RAISE NOTICE 'cdb_writer: INSERT on 8 tables, UPDATE on 1 (positions)';
    RAISE NOTICE 'cdb_admin:  ALL (for migrations only)';
    RAISE NOTICE 'claire_user: unchanged — run enforce_least_privilege.sql to migrate';
    RAISE NOTICE '---------------------------------------------';
END $$;
