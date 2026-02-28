-- ============================================================================
-- Enforce Least-Privilege: Revoke ALL from claire_user (Issue #741)
-- ============================================================================
-- DELIBERATE OPERATOR STEP — do NOT run automatically.
-- Prerequisite: roles_and_grants.sql must have been applied first.
--
-- This script:
--   1. Revokes ALL PRIVILEGES from claire_user on all tables + sequences.
--   2. Assigns cdb_writer role to claire_user (INSERT + limited UPDATE).
--   3. claire_user retains LOGIN but loses direct privileges.
--
-- After this, claire_user can only do what cdb_writer allows.
-- To also create a read-only user, see step 4.
--
-- Run as superuser:
--   psql -U postgres -d claire_de_binare -f enforce_least_privilege.sql
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Verify prerequisite: cdb_writer role must exist
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'claire_user') THEN
        RAISE EXCEPTION 'claire_user does not exist. Nothing to enforce.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cdb_writer') THEN
        RAISE EXCEPTION 'cdb_writer role does not exist. Run roles_and_grants.sql first.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cdb_reader') THEN
        RAISE EXCEPTION 'cdb_reader role does not exist. Run roles_and_grants.sql first.';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 2. Revoke ALL from claire_user (tables, sequences, schema CREATE)
-- ----------------------------------------------------------------------------

REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM claire_user;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM claire_user;
REVOKE CREATE ON SCHEMA public FROM claire_user;
-- NOTE: We keep USAGE on schema public so claire_user can still connect and
-- use objects via inherited cdb_writer role.  We also leave CONNECT on the
-- database untouched to avoid breaking the login path.

-- NOTE: If claire_user is OWNER of tables, owner privileges still apply
-- regardless of GRANT/REVOKE.  To fully enforce least-privilege, table
-- ownership should be transferred to postgres or cdb_admin:
--   ALTER TABLE <tbl> OWNER TO cdb_admin;
-- This is left as a manual operator step to avoid breaking migrations.

-- ----------------------------------------------------------------------------
-- 3. Assign cdb_writer to claire_user
-- ----------------------------------------------------------------------------

GRANT cdb_writer TO claire_user;

-- ----------------------------------------------------------------------------
-- 4. (Optional) Create a dedicated read-only login user
--    Uncomment to create:
-- ----------------------------------------------------------------------------

-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cdb_readonly') THEN
--         CREATE ROLE cdb_readonly LOGIN PASSWORD 'CHANGE_ME';
--     END IF;
-- END $$;
-- GRANT cdb_reader TO cdb_readonly;

-- ----------------------------------------------------------------------------
-- 5. Verification
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    RAISE NOTICE '---------------------------------------------';
    RAISE NOTICE 'enforce_least_privilege.sql applied';
    RAISE NOTICE 'claire_user: ALL revoked, now inherits cdb_writer only';
    RAISE NOTICE 'To verify: run verify_privileges.sql';
    RAISE NOTICE 'To rollback: run rollback_least_privilege.sql';
    RAISE NOTICE '---------------------------------------------';
END $$;
