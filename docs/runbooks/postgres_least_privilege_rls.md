# Runbook: Postgres Least-Privilege & RLS Hardening (Issue #741)

## Overview

This PR introduces three Postgres roles with explicit, minimal grants:

| Role | Login | Capabilities | Used by |
|------|-------|-------------|---------|
| `cdb_reader` | No (NOLOGIN) | SELECT on all listed tables | Audit / dashboards / Grafana |
| `cdb_writer` | No (NOLOGIN) | SELECT + INSERT on 8 tables, UPDATE on 1 | Runtime services (via `claire_user`) |
| `cdb_admin` | No (NOLOGIN) | ALL (DDL, migrations) | Deploy / migration scripts |

`claire_user` retains LOGIN and keeps ALL PRIVILEGES by default.
Enforcement (revoking ALL from `claire_user` and assigning `cdb_writer`)
is a **separate, deliberate operator step**.

**Note on RLS**: This PR covers least-privilege via explicit GRANT/REVOKE only.
Row-Level Security (RLS policies) is not activated here — that is a separate
hardening phase if needed. The filename includes "rls" for traceability
against Issue #741 which scopes both topics.

## Access Matrix

| Table | cdb_reader | cdb_writer | cdb_admin | Rationale |
|-------|-----------|-----------|----------|-----------|
| `signals` | SELECT | SELECT, INSERT | ALL | Append-only signal log |
| `orders` | SELECT | SELECT, INSERT | ALL | Append-only order log |
| `trades` | SELECT | SELECT, INSERT | ALL | Append-only trade log |
| `positions` | SELECT | SELECT, INSERT, **UPDATE** | ALL | db_writer updates size/price/pnl on trade execution |
| `portfolio_snapshots` | SELECT | SELECT, INSERT | ALL | Append-only portfolio snapshots |
| `risk_events` | SELECT | SELECT, INSERT | ALL | Append-only risk decisions |
| `correlation_ledger` | SELECT | SELECT, INSERT | ALL | Append-only correlation audit trail |
| `blocked_decisions` | SELECT | SELECT, INSERT | ALL | Append-only blocked decision log |
| `core_secrets_metadata` | SELECT | — | ALL | Governance mirror (no runtime writes) |
| `audit_trail` | SELECT | — | ALL | Governance mirror (no runtime writes) |
| `governance_events` | SELECT | — | ALL | Governance mirror (no runtime writes) |
| `deployment_approvals_mirror` | SELECT | — | ALL | Governance mirror (no runtime writes) |
| `security_policy_refs` | SELECT | — | ALL | Governance mirror (no runtime writes) |
| `schema_version` | SELECT | SELECT | ALL | Migration tracking (admin writes only) |

**DELETE**: Not granted to any role except `cdb_admin`. No production code uses DELETE.

**Note**: `validation_runs` is managed locally via SQLite (`real_validation_fetcher.py`), not Postgres. It is not part of this Postgres hardening.

## Scripts

All scripts are in `infrastructure/database/`:

| Script | Purpose | Run as |
|--------|---------|--------|
| `roles_and_grants.sql` | Create roles + explicit grants (idempotent) | superuser |
| `enforce_least_privilege.sql` | Revoke ALL from `claire_user`, assign `cdb_writer` | superuser |
| `rollback_least_privilege.sql` | Restore `claire_user` ALL PRIVILEGES | superuser |
| `verify_privileges.sql` | Show effective grants, memberships, ownership | superuser |

## Apply Steps

### Step 1: Create roles and grants (safe, additive)

```bash
docker exec cdb_postgres psql -U postgres -d claire_de_binare \
  -f /path/to/roles_and_grants.sql
```

This is safe to run at any time. It does not revoke anything from `claire_user`.

### Step 2: Verify roles exist

```bash
docker exec cdb_postgres psql -U postgres -d claire_de_binare \
  -f /path/to/verify_privileges.sql
```

Check output sections 1-4. Roles should exist, grants should be listed.

### Step 3: Enforce (deliberate operator step)

```bash
docker exec cdb_postgres psql -U postgres -d claire_de_binare \
  -f /path/to/enforce_least_privilege.sql
```

After this, `claire_user` can only do what `cdb_writer` allows.

### Step 4: Verify enforcement

Run `verify_privileges.sql` again. Section 5 ("claire_user direct") should
now be empty — all privileges come via `cdb_writer` inheritance.

## Verify: Denied Operations

After enforcement, these operations should fail for `claire_user`:

```sql
-- reader cannot INSERT (connect as cdb_readonly if created):
INSERT INTO signals (symbol, signal_type, price, confidence)
VALUES ('TEST', 'buy', 1.0, 0.5);
-- Expected: ERROR: permission denied for table signals

-- writer (claire_user) cannot DELETE:
DELETE FROM signals WHERE id = 1;
-- Expected: ERROR: permission denied for table signals

-- writer cannot UPDATE on append-only tables:
UPDATE orders SET status = 'cancelled' WHERE id = 1;
-- Expected: ERROR: permission denied for table orders

-- writer CAN update positions (allowed):
UPDATE positions SET current_price = 100.0 WHERE symbol = 'BTCUSDT';
-- Expected: UPDATE 0 (or UPDATE 1 if row exists) — no permission error
```

## Rollback

```bash
docker exec cdb_postgres psql -U postgres -d claire_de_binare \
  -f /path/to/rollback_least_privilege.sql
```

This restores `claire_user` to full ALL PRIVILEGES (pre-#741 state).

**Note**: If table ownership was manually transferred to `cdb_admin`
(via `ALTER TABLE ... OWNER TO cdb_admin`), rollback does not reverse
ownership changes. Those must be reverted manually if needed.

## Ownership Caveat

If `claire_user` is the OWNER of tables (likely from initial schema creation),
owner privileges apply regardless of GRANT/REVOKE. To fully enforce
least-privilege, transfer ownership:

```sql
-- Manual operator step (per table):
ALTER TABLE signals OWNER TO cdb_admin;
ALTER TABLE orders OWNER TO cdb_admin;
-- ... etc.
```

This is intentionally not automated to avoid breaking migrations.
