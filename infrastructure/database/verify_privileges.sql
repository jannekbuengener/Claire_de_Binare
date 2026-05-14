-- ============================================================================
-- Verify Postgres Least-Privilege Setup (Issue #741)
-- ============================================================================
-- Non-destructive, read-only queries.  Run after roles_and_grants.sql
-- and/or enforce_least_privilege.sql to confirm effective state.
--
-- Run as superuser:
--   psql -U postgres -d claire_de_binare -f verify_privileges.sql
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Role existence
-- ----------------------------------------------------------------------------
\echo '=== 1. Role existence ==='
SELECT
    rolname,
    rolcanlogin,
    rolsuper,
    rolcreatedb,
    rolcreaterole,
    rolreplication,
    rolbypassrls,
    rolinherit
FROM pg_roles
WHERE rolname IN ('cdb_reader', 'cdb_writer', 'cdb_admin', 'claire_user', 'cdb_readonly')
ORDER BY rolname;

-- Expected:
--   cdb_admin    | f | f | f | f | f | f | t
--   cdb_reader   | f | f | f | f | f | f | t
--   cdb_readonly | t | f | f | f | f | f | t
--   cdb_writer   | f | f | f | f | f | f | t
--   claire_user  | t | f | ... deployment-dependent ...

-- ----------------------------------------------------------------------------
-- 2. Role memberships (who inherits what)
-- ----------------------------------------------------------------------------
\echo '=== 2. Role memberships ==='
SELECT r.rolname AS role, m.rolname AS member
FROM pg_auth_members am
JOIN pg_roles r ON r.oid = am.roleid
JOIN pg_roles m ON m.oid = am.member
WHERE r.rolname IN ('cdb_reader', 'cdb_writer', 'cdb_admin')
ORDER BY r.rolname, m.rolname;

-- After enforce: claire_user should appear as member of cdb_writer.

-- ----------------------------------------------------------------------------
-- 2b. Dedicated readonly login checks
-- ----------------------------------------------------------------------------
\echo '=== 3. Dedicated readonly login flags (cdb_readonly) ==='
WITH readonly_role AS (
    SELECT
        oid,
        rolcanlogin,
        rolsuper,
        rolcreatedb,
        rolcreaterole,
        rolreplication,
        rolbypassrls
    FROM pg_roles
    WHERE rolname = 'cdb_readonly'
)
SELECT
    EXISTS (SELECT 1 FROM readonly_role) AS cdb_readonly_exists,
    COALESCE((SELECT rolcanlogin FROM readonly_role), false) AS rolcanlogin,
    COALESCE((SELECT rolsuper FROM readonly_role), false) AS rolsuper,
    COALESCE((SELECT rolcreatedb FROM readonly_role), false) AS rolcreatedb,
    COALESCE((SELECT rolcreaterole FROM readonly_role), false) AS rolcreaterole,
    COALESCE((SELECT rolreplication FROM readonly_role), false) AS rolreplication,
    COALESCE((SELECT rolbypassrls FROM readonly_role), false) AS rolbypassrls;

\echo '=== 4. Dedicated readonly memberships (cdb_readonly) ==='
WITH readonly_role AS (
    SELECT oid
    FROM pg_roles
    WHERE rolname = 'cdb_readonly'
),
target_roles AS (
    SELECT rolname, oid
    FROM pg_roles
    WHERE rolname IN ('cdb_reader', 'cdb_writer', 'cdb_admin')
)
SELECT
    tr.rolname AS target_role,
    CASE
        WHEN NOT EXISTS (SELECT 1 FROM readonly_role) THEN false
        ELSE pg_has_role((SELECT oid FROM readonly_role), tr.oid, 'MEMBER')
    END AS is_member
FROM target_roles tr
ORDER BY tr.rolname;

-- ----------------------------------------------------------------------------
-- 3. Table privileges per role
-- ----------------------------------------------------------------------------
\echo '=== 5. Table privileges (cdb_writer) ==='
SELECT table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = 'cdb_writer'
  AND table_schema = 'public'
ORDER BY table_name, privilege_type;

-- Expected: INSERT on 8 tables, SELECT on 9, UPDATE only on positions.

\echo '=== 6. Table privileges (cdb_reader) ==='
SELECT table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = 'cdb_reader'
  AND table_schema = 'public'
ORDER BY table_name, privilege_type;

-- Expected: SELECT only on all listed tables.

\echo '=== 7. Effective privileges (cdb_readonly -> public.correlation_ledger) ==='
WITH readonly_role AS (
    SELECT oid
    FROM pg_roles
    WHERE rolname = 'cdb_readonly'
)
SELECT
    EXISTS (SELECT 1 FROM readonly_role) AS cdb_readonly_exists,
    COALESCE((SELECT has_table_privilege(oid, 'public.correlation_ledger', 'SELECT') FROM readonly_role), false) AS can_select,
    COALESCE((SELECT has_table_privilege(oid, 'public.correlation_ledger', 'INSERT') FROM readonly_role), false) AS can_insert,
    COALESCE((SELECT has_table_privilege(oid, 'public.correlation_ledger', 'UPDATE') FROM readonly_role), false) AS can_update,
    COALESCE((SELECT has_table_privilege(oid, 'public.correlation_ledger', 'DELETE') FROM readonly_role), false) AS can_delete;

-- NOTE: use has_table_privilege(...) here because inherited privileges via
-- GRANT cdb_reader TO cdb_readonly are not reliably visible via
-- information_schema.table_privileges WHERE grantee = 'cdb_readonly'.

\echo '=== 8. Table privileges (claire_user direct) ==='
SELECT table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = 'claire_user'
  AND table_schema = 'public'
ORDER BY table_name, privilege_type;

-- Before enforce: ALL on every table.
-- After enforce: empty (all privileges come via cdb_writer inheritance).

-- ----------------------------------------------------------------------------
-- 4. Sequence privileges for cdb_writer
-- ----------------------------------------------------------------------------
\echo '=== 9. Sequence privileges (cdb_writer) ==='
SELECT object_name AS sequence_name, privilege_type
FROM information_schema.usage_privileges
WHERE grantee = 'cdb_writer'
  AND object_schema = 'public'
  AND object_type = 'SEQUENCE'
ORDER BY object_name;

-- ----------------------------------------------------------------------------
-- 5. Table ownership (informational)
-- ----------------------------------------------------------------------------
\echo '=== 10. Table ownership ==='
SELECT tablename, tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- NOTE: If claire_user owns tables, owner privileges apply regardless of
-- GRANT/REVOKE.  Ownership transfer to cdb_admin is a separate operator step.
