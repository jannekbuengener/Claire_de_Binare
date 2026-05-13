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
| `system_config` | SELECT | — | ALL | Access-domain config fingerprints only (no runtime writes) |
| `security_policy_refs` | SELECT | — | ALL | Governance mirror (no runtime writes) |
| `schema_version` | SELECT | SELECT | ALL | Migration tracking (admin writes only) |

**DELETE**: Not granted to any role except `cdb_admin`. No production code uses DELETE.

**Note**: `validation_runs` is managed locally via SQLite (`real_validation_fetcher.py`), not Postgres. It is not part of this Postgres hardening.

## Scripts

All scripts are in `infrastructure/database/`:

| Script | Purpose | Run as |
|--------|---------|--------|
| `roles_and_grants.sql` | Create roles + explicit grants (idempotent) | superuser |
| `operator_create_readonly_login.sql` | Create optional operator-managed readonly login `cdb_readonly` | superuser |
| `enforce_least_privilege.sql` | Revoke ALL from `claire_user`, assign `cdb_writer` | superuser |
| `rollback_least_privilege.sql` | Restore `claire_user` ALL PRIVILEGES | superuser |
| `verify_privileges.sql` | Show effective grants, memberships, ownership | superuser |

## Optional readonly login canon (`cdb_readonly`)

`cdb_reader` remains the canonical `NOLOGIN` read-grant foundation. A dedicated
readonly login such as `cdb_readonly` is an **optional, operator-managed**
follow-up for read-only discovery and MCP access.

Guardrails:

- `cdb_readonly` is **not** created by `roles_and_grants.sql`.
- `cdb_readonly` must inherit read access **only** via `GRANT cdb_reader TO cdb_readonly`.
- `cdb_readonly` must **not** be a member of `cdb_writer` or `cdb_admin`.
- `cdb_readonly` must keep these flags: `NOSUPERUSER`, `NOCREATEDB`,
  `NOCREATEROLE`, `NOREPLICATION`, `NOBYPASSRLS`.
- The password / DSN must be managed outside the repo via the canonical secret
  workflow. Do not commit or paste real credentials.
- `claire_user` is a runtime credential and is **not acceptable** as a
  readonly Agent-/MCP-discovery login.

Operator entrypoint:

- `infrastructure/database/operator_create_readonly_login.sql`

Before any later `#1905` DB discovery, the operator path must prove a dedicated
readonly session identity:

```sql
SELECT current_user, session_user;
```

Expected: `current_user` must show a dedicated readonly login, preferably
`cdb_readonly`, or an explicitly approved equivalent readonly principal.

## Secret Policy

- Canonical Secret Store: `C:\Users\janne\Documents\.secrets\.cdb`
- Rotation / changes: rotator-only via `infrastructure/scripts/manage_secrets.ps1`; do not hand-edit secret files and do not create alternate secret copies inside the repo.
- Connection env: export or load `POSTGRES_DSN`, `DATABASE_URL`, and related connection material via the rotator workflow before running these commands. Do not paste credentials directly into shells, docs, or committed config.

## Rotator Proof of Use

Use the rotator entrypoint from an operator shell that is configured for the
canonical secret store `C:\Users\janne\Documents\.secrets\.cdb`. The current
script does not expose a separate `status` or `dry-run` verb; use the
non-mutating `list` and `validate` actions as proof-of-use commands.

```powershell
pwsh -File infrastructure/scripts/manage_secrets.ps1 -Action list
pwsh -File infrastructure/scripts/manage_secrets.ps1 -Action validate
pwsh -File infrastructure/scripts/manage_secrets.ps1 -Action rotate -SecretName <secret-name>
```

- `list`: confirms that the rotator can see the managed secret files without
  printing secret values.
- `validate`: confirms that the required secret set is present and non-empty.
- `rotate`: use only when an approved rotation is required; provide the secret
  value through the rotator workflow, not by hand-editing files.
- Proof-of-use evidence should capture only timestamp, operator, command name,
  and outcome summary. Do not capture or paste secret values.

## Live Evidence Workflow

Use exactly these three commands to capture live evidence, run the offline
diff, and prepare attachable artifacts without committing secrets. The
evidence bundle must live outside the repo and be linked from the Issue after
upload:

```bash
export EVIDENCE_DIR="/tmp/cdb_pg_evidence_<ENV>_<YYYYMMDD_HHMM>"
mkdir -p "$EVIDENCE_DIR"

# Load POSTGRES_DSN / DATABASE_URL via the rotator first. Do not hand-edit
# secret files or inline credentials here.
psql "$POSTGRES_DSN" \
  -v roles_out="$EVIDENCE_DIR/roles.csv" \
  -v role_memberships_out="$EVIDENCE_DIR/role_memberships.csv" \
  -v table_privileges_out="$EVIDENCE_DIR/table_privileges.csv" \
  -v column_privileges_out="$EVIDENCE_DIR/column_privileges.csv" \
  -v rls_tables_out="$EVIDENCE_DIR/rls_tables.csv" \
  -v policies_out="$EVIDENCE_DIR/policies.csv" \
  -v default_privileges_out="$EVIDENCE_DIR/default_privileges.csv" \
  -f scripts/audit/postgres_privilege_dump.sql

python scripts/audit/postgres_least_privilege_report.py \
  --input-dir "$EVIDENCE_DIR" \
  --out-dir "$EVIDENCE_DIR/report"

zip -r "${EVIDENCE_DIR}.zip" "$EVIDENCE_DIR"
```

Upload `${EVIDENCE_DIR}.zip` via GitHub UI attachment as the default path. If
the UI upload is not available, use an external artifact store and paste the
resulting link or issue-comment permalink into the Issue. Do not commit the
live dump files, the ZIP bundle, or any DSN/secret material.

## Apply Steps

### Step 1: Create roles and grants (safe, additive)

```bash
docker exec cdb_postgres psql -U postgres -d claire_de_binare \
  -f /path/to/roles_and_grants.sql
```

This is safe to run at any time. It does not revoke anything from `claire_user`.

### Step 2: Optionally create dedicated readonly login

```bash
docker exec cdb_postgres psql -U postgres -d claire_de_binare \
  -v CDB_READONLY_PASSWORD="$CDB_READONLY_PASSWORD" \
  -f /path/to/operator_create_readonly_login.sql
```

This is an operator-only step for a dedicated readonly login. It is separate
from the additive role/grant foundation and must stay secret-free in the repo.
Load `CDB_READONLY_PASSWORD` from the canonical secret store before invoking
`psql`; never commit, paste, or log the real value.

### Step 3: Verify roles exist

```bash
docker exec cdb_postgres psql -U postgres -d claire_de_binare \
  -f /path/to/verify_privileges.sql
```

Check output sections 1-8. The readonly verification must confirm:

- `cdb_readonly` has `rolcanlogin = true`
- no superuser / createdb / createrole / replication / bypassrls flags
- membership in `cdb_reader`
- no membership in `cdb_writer` or `cdb_admin`
- effective `SELECT` on `public.correlation_ledger`
- no effective `INSERT`, `UPDATE`, or `DELETE` on `public.correlation_ledger`

### Step 4: Enforce (deliberate operator step)

```bash
docker exec cdb_postgres psql -U postgres -d claire_de_binare \
  -f /path/to/enforce_least_privilege.sql
```

After this, `claire_user` can only do what `cdb_writer` allows.

### Step 5: Verify enforcement

Run `verify_privileges.sql` again. Section 8 ("claire_user direct") should
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

For readonly discovery, verify session identity separately:

```sql
SELECT current_database(), current_user, session_user;
```

Expected: the discovery session shows a dedicated readonly login, preferably
`cdb_readonly`; `claire_user` is not acceptable for Agent-/MCP-discovery.

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
