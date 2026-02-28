-- ============================================================================
-- Rollback: Restore claire_user ALL PRIVILEGES (Issue #741)
-- ============================================================================
-- Reverses enforce_least_privilege.sql.
-- After this, claire_user has full access again (pre-#741 state).
--
-- Run as superuser:
--   psql -U postgres -d claire_de_binare -f rollback_least_privilege.sql
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Verify claire_user exists
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'claire_user') THEN
        RAISE EXCEPTION 'claire_user does not exist. Nothing to rollback.';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 2. Restore ALL PRIVILEGES to claire_user
-- ----------------------------------------------------------------------------

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO claire_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO claire_user;
GRANT CREATE ON SCHEMA public TO claire_user;

-- ----------------------------------------------------------------------------
-- 3. Revoke cdb_writer inheritance (no longer needed with ALL PRIVILEGES)
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cdb_writer') THEN
        REVOKE cdb_writer FROM claire_user;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 4. Verification
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    RAISE NOTICE '---------------------------------------------';
    RAISE NOTICE 'rollback_least_privilege.sql applied';
    RAISE NOTICE 'claire_user: ALL PRIVILEGES restored (pre-#741 state)';
    RAISE NOTICE 'cdb_reader/cdb_writer/cdb_admin roles still exist but are unused';
    RAISE NOTICE '---------------------------------------------';
END $$;
