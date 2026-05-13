-- ============================================================================
-- Operator-only readonly login creation
-- ============================================================================
-- Purpose:
--   Create an optional dedicated readonly LOGIN role for discovery / MCP access.
--
-- Guardrails:
--   - Do NOT wire this file into migrations, startup, or docker-entrypoint init.
--   - Do NOT commit real passwords or secret values.
--   - Run only as a deliberate operator step after roles_and_grants.sql created
--     the NOLOGIN role foundation, especially cdb_reader.
--
-- Run as superuser:
--   psql -U postgres -d claire_de_binare -f operator_create_readonly_login.sql
-- ============================================================================

\set ON_ERROR_STOP on

\if :{?CDB_READONLY_PASSWORD}
\else
\echo 'ERROR: CDB_READONLY_PASSWORD psql variable is required. Load it from the canonical secret store; do not commit or paste secrets.'
\quit 3
\endif

SELECT CASE
    WHEN length(btrim(:'CDB_READONLY_PASSWORD')) > 0 THEN 'true'
    ELSE 'false'
END AS cdb_readonly_password_non_empty
\gset

\if :cdb_readonly_password_non_empty
\else
\echo 'ERROR: CDB_READONLY_PASSWORD must not be empty or whitespace-only.'
\quit 3
\endif

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cdb_reader') THEN
        RAISE EXCEPTION 'cdb_reader role does not exist. Run roles_and_grants.sql first.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cdb_writer') THEN
        RAISE EXCEPTION 'cdb_writer role does not exist. Run roles_and_grants.sql first.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cdb_admin') THEN
        RAISE EXCEPTION 'cdb_admin role does not exist. Run roles_and_grants.sql first.';
    END IF;
END $$;

-- \gexec creates the role only when missing.
SELECT format(
    'CREATE ROLE cdb_readonly LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'CDB_READONLY_PASSWORD'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'cdb_readonly'
)
\gexec

ALTER ROLE cdb_readonly
    INHERIT
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

ALTER ROLE cdb_readonly
    PASSWORD :'CDB_READONLY_PASSWORD';

-- Remove stale direct object grants. cdb_readonly must inherit read access only
-- via cdb_reader.
REVOKE ALL PRIVILEGES ON SCHEMA public FROM cdb_readonly;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM cdb_readonly;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM cdb_readonly;

REVOKE cdb_writer FROM cdb_readonly;
REVOKE cdb_admin FROM cdb_readonly;

-- Existing role password is rotated by the ALTER ROLE statement above.
GRANT cdb_reader TO cdb_readonly;

DO $$
BEGIN
    IF pg_has_role('cdb_readonly', 'cdb_writer', 'MEMBER') THEN
        RAISE EXCEPTION 'cdb_readonly must not be a member of cdb_writer';
    END IF;

    IF pg_has_role('cdb_readonly', 'cdb_admin', 'MEMBER') THEN
        RAISE EXCEPTION 'cdb_readonly must not be a member of cdb_admin';
    END IF;

    IF NOT pg_has_role('cdb_readonly', 'cdb_reader', 'MEMBER') THEN
        RAISE EXCEPTION 'cdb_readonly must be a member of cdb_reader';
    END IF;

    IF to_regclass('public.correlation_ledger') IS NULL THEN
        RAISE EXCEPTION 'public.correlation_ledger must exist before readonly discovery verification';
    END IF;

    IF NOT has_table_privilege('cdb_readonly', 'public.correlation_ledger', 'SELECT') THEN
        RAISE EXCEPTION 'cdb_readonly must have SELECT on public.correlation_ledger via cdb_reader';
    END IF;

    IF has_table_privilege('cdb_readonly', 'public.correlation_ledger', 'INSERT')
       OR has_table_privilege('cdb_readonly', 'public.correlation_ledger', 'UPDATE')
       OR has_table_privilege('cdb_readonly', 'public.correlation_ledger', 'DELETE') THEN
        RAISE EXCEPTION 'cdb_readonly must not have write privileges on public.correlation_ledger';
    END IF;

    RAISE NOTICE '---------------------------------------------';
    RAISE NOTICE 'operator_create_readonly_login.sql applied';
    RAISE NOTICE 'cdb_readonly remains operator-managed';
    RAISE NOTICE 'Password was loaded via psql variable CDB_READONLY_PASSWORD';
    RAISE NOTICE 'Verify via verify_privileges.sql before DB discovery';
    RAISE NOTICE '---------------------------------------------';
END $$;
