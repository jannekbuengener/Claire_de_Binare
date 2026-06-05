# Database (`infrastructure/database/`)

Postgres schema, migrations, and least-privilege scripts for CDB.

## Layout

| Path | Purpose |
|---|---|
| [`schema.sql`](schema.sql) | Base schema reference |
| [`migrations/`](migrations/) | Numbered SQL migrations (`002_` … `013_`) |
| [`roles_and_grants.sql`](roles_and_grants.sql) | Role/grant setup |
| [`enforce_least_privilege.sql`](enforce_least_privilege.sql) | Least privilege enforcement |
| [`verify_privileges.sql`](verify_privileges.sql) | Verification queries |
| [`operator_create_readonly_login.sql`](operator_create_readonly_login.sql) | Read-only operator login |
| [`rollback_least_privilege.sql`](rollback_least_privilege.sql) | Rollback helper |

## Operator docs

- Navigation hub: [`docs/db/index.md`](../../docs/db/index.md)
- RLS runbook: [`docs/runbooks/postgres_least_privilege_rls.md`](../../docs/runbooks/postgres_least_privilege_rls.md)

## Apply / verify

Use project Makefile/operator scripts documented in `docs/db/index.md` and playbooks under `knowledge/playbooks/03_DB_*` — do not apply migrations ad hoc without migration runner discipline.

## SSOT boundary

Postgres is trading SSOT; SurrealDB remains experimental mirror (see `infrastructure/surrealdb/README.md`). LR **NO-GO**.
