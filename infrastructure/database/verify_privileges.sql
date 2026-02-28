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
SELECT rolname, rolcanlogin, rolsuper, rolinherit
FROM pg_roles
WHERE rolname IN ('cdb_reader', 'cdb_writer', 'cdb_admin', 'claire_user')
ORDER BY rolname;

-- Expected:
--   cdb_admin   | f | f | t
--   cdb_reader  | f | f | t
--   cdb_writer  | f | f | t
--   claire_user | t | f | t

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
-- 3. Table privileges per role
-- ----------------------------------------------------------------------------
\echo '=== 3. Table privileges (cdb_writer) ==='
SELECT table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = 'cdb_writer'
  AND table_schema = 'public'
ORDER BY table_name, privilege_type;

-- Expected: INSERT on 9 tables, SELECT on 10, UPDATE only on positions + validation_runs.

\echo '=== 4. Table privileges (cdb_reader) ==='
SELECT table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = 'cdb_reader'
  AND table_schema = 'public'
ORDER BY table_name, privilege_type;

-- Expected: SELECT only on all listed tables.

\echo '=== 5. Table privileges (claire_user direct) ==='
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
\echo '=== 6. Sequence privileges (cdb_writer) ==='
SELECT sequence_name, privilege_type
FROM information_schema.usage_privileges
WHERE grantee = 'cdb_writer'
  AND object_schema = 'public'
  AND object_type = 'SEQUENCE'
ORDER BY sequence_name;

-- ----------------------------------------------------------------------------
-- 5. Table ownership (informational)
-- ----------------------------------------------------------------------------
\echo '=== 7. Table ownership ==='
SELECT tablename, tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- NOTE: If claire_user owns tables, owner privileges apply regardless of
-- GRANT/REVOKE.  Ownership transfer to cdb_admin is a separate operator step.
