\set ON_ERROR_STOP on

\if :{?roles_out}
\else
\set roles_out 'roles.csv'
\endif

\if :{?role_memberships_out}
\else
\set role_memberships_out 'role_memberships.csv'
\endif

\if :{?table_privileges_out}
\else
\set table_privileges_out 'table_privileges.csv'
\endif

\if :{?column_privileges_out}
\else
\set column_privileges_out 'column_privileges.csv'
\endif

\if :{?rls_tables_out}
\else
\set rls_tables_out 'rls_tables.csv'
\endif

\if :{?policies_out}
\else
\set policies_out 'policies.csv'
\endif

\if :{?default_privileges_out}
\else
\set default_privileges_out 'default_privileges.csv'
\endif

-- ============================================================================
-- Dump Postgres least-privilege + RLS evidence for Issue #741
-- ============================================================================
-- Read-only psql script. Each query writes a standalone CSV artifact via
-- ``\copy (... ) TO STDOUT`` with ``\o`` redirection.
-- ============================================================================

\echo 'writing roles -> ' :roles_out
\o :roles_out
\copy (
    SELECT
        rolname,
        rolcanlogin,
        rolinherit,
        rolsuper
    FROM pg_roles
    WHERE rolname IN ('cdb_admin', 'cdb_reader', 'cdb_writer', 'claire_user')
    ORDER BY rolname
) TO STDOUT WITH CSV HEADER
\o

\echo 'writing role memberships -> ' :role_memberships_out
\o :role_memberships_out
\copy (
    SELECT
        role_ref.rolname AS role_name,
        member_ref.rolname AS member_name
    FROM pg_auth_members memberships
    JOIN pg_roles role_ref ON role_ref.oid = memberships.roleid
    JOIN pg_roles member_ref ON member_ref.oid = memberships.member
    WHERE role_ref.rolname IN ('cdb_admin', 'cdb_reader', 'cdb_writer')
       OR member_ref.rolname = 'claire_user'
    ORDER BY role_name, member_name
) TO STDOUT WITH CSV HEADER
\o

\echo 'writing table privileges -> ' :table_privileges_out
\o :table_privileges_out
\copy (
    SELECT
        grantee,
        table_schema,
        table_name,
        privilege_type
    FROM information_schema.table_privileges
    WHERE table_schema = 'public'
      AND grantee IN ('cdb_admin', 'cdb_reader', 'cdb_writer', 'claire_user')
    ORDER BY grantee, table_schema, table_name, privilege_type
) TO STDOUT WITH CSV HEADER
\o

\echo 'writing column privileges -> ' :column_privileges_out
\o :column_privileges_out
\copy (
    SELECT
        grantee,
        table_schema,
        table_name,
        column_name,
        privilege_type
    FROM information_schema.column_privileges
    WHERE table_schema = 'public'
      AND grantee IN ('cdb_admin', 'cdb_reader', 'cdb_writer', 'claire_user')
    ORDER BY grantee, table_schema, table_name, column_name, privilege_type
) TO STDOUT WITH CSV HEADER
\o

\echo 'writing rls table flags -> ' :rls_tables_out
\o :rls_tables_out
\copy (
    SELECT
        namespace_ref.nspname AS table_schema,
        class_ref.relname AS table_name,
        class_ref.relrowsecurity AS row_security_enabled,
        class_ref.relforcerowsecurity AS force_row_security_enabled
    FROM pg_class class_ref
    JOIN pg_namespace namespace_ref ON namespace_ref.oid = class_ref.relnamespace
    WHERE class_ref.relkind = 'r'
      AND namespace_ref.nspname = 'public'
      AND class_ref.relname IN (
          'signals',
          'orders',
          'trades',
          'positions',
          'portfolio_snapshots',
          'risk_events',
          'correlation_ledger',
          'blocked_decisions',
          'core_secrets_metadata',
          'audit_trail',
          'governance_events',
          'deployment_approvals_mirror',
          'system_config',
          'security_policy_refs',
          'schema_version'
      )
    ORDER BY table_schema, table_name
) TO STDOUT WITH CSV HEADER
\o

\echo 'writing policies -> ' :policies_out
\o :policies_out
\copy (
    SELECT
        schemaname AS table_schema,
        tablename AS table_name,
        policyname,
        permissive,
        array_to_string(roles, ',') AS roles,
        cmd,
        COALESCE(qual, '') AS qual,
        COALESCE(with_check, '') AS with_check
    FROM pg_policies
    WHERE schemaname = 'public'
    ORDER BY table_schema, table_name, policyname
) TO STDOUT WITH CSV HEADER
\o

\echo 'writing default privileges -> ' :default_privileges_out
\o :default_privileges_out
\copy (
    SELECT
        pg_get_userbyid(default_acl.defaclrole) AS role_name,
        COALESCE(namespace_ref.nspname, 'public') AS object_schema,
        CASE default_acl.defaclobjtype
            WHEN 'r' THEN 'table'
            WHEN 'S' THEN 'sequence'
            WHEN 'f' THEN 'function'
            WHEN 'T' THEN 'type'
            WHEN 'n' THEN 'schema'
            ELSE default_acl.defaclobjtype::text
        END AS object_type,
        COALESCE(acl_item::text, '') AS privilege_spec
    FROM pg_default_acl default_acl
    LEFT JOIN pg_namespace namespace_ref
      ON namespace_ref.oid = default_acl.defaclnamespace
    LEFT JOIN LATERAL unnest(
        COALESCE(default_acl.defaclacl, '{}'::aclitem[])
    ) AS acl_item ON TRUE
    ORDER BY role_name, object_schema, object_type, privilege_spec
) TO STDOUT WITH CSV HEADER
\o
