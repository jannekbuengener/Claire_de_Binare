# DB Layer Access Control Matrix & Threat Model

- Issue: `#744`
- Status: `Implemented as documentation anchor`
- Last updated: `2026-03-10`

This document records the current repo-visible DB-layer access model for
Postgres and the SurrealDB governance mirror. It documents the current state
only. It is not live privilege proof for any environment.

## Canonical Repo Inputs

- `infrastructure/compose/base.yml`
- `infrastructure/compose/compose.blue.yml`
- `infrastructure/compose/reports.yml`
- `infrastructure/database/schema.sql`
- `infrastructure/database/roles_and_grants.sql`
- `infrastructure/database/enforce_least_privilege.sql`
- `infrastructure/database/verify_privileges.sql`
- `scripts/audit/desired_privileges.json`
- `scripts/audit/postgres_least_privilege_report.py`
- `docs/runbooks/postgres_least_privilege_rls.md`
- `services/risk/service.py`
- `services/signal/service.py`
- `services/execution/config.py`
- `services/execution/database.py`
- `services/db_writer/db_writer.py`
- `services/reports/daily_orders_summary.py`
- `services/validation/runner.py`
- `tools/paper_trading/service.py`
- `infrastructure/monitoring/grafana/provisioning/datasources/postgres.yml`
- `infrastructure/surrealdb/README.md`
- `infrastructure/surrealdb/setup.surql`
- `docs/surrealdb/data-ownership-matrix.md`

## Current DB Actors and Connection Paths

| Actor | DB surface | Credential / connection path | Repo-visible access pattern | Evidence |
| --- | --- | --- | --- | --- |
| `cdb_risk` | Postgres | `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD` via compose secrets | writes `risk_events`, `correlation_ledger`, `blocked_decisions` | `infrastructure/compose/compose.blue.yml`, `services/risk/service.py` |
| `cdb_signal` | Postgres | direct `POSTGRES_*` config to `psycopg2.connect(...)` | writes `correlation_ledger` | `services/signal/service.py` |
| `cdb_execution` | Postgres | `DATABASE_URL` built from `POSTGRES_*`; compose injects `POSTGRES_USER=${POSTGRES_USER:-claire_user}` | writes and reads `orders`, `trades`, `correlation_ledger` | `services/execution/config.py`, `services/execution/database.py`, `infrastructure/compose/compose.blue.yml` |
| `cdb_db_writer` | Postgres | `POSTGRES_*` plus Docker secret `postgres_password` | writes `signals`, `orders`, `trades`, `positions`, `portfolio_snapshots` | `services/db_writer/db_writer.py`, `infrastructure/compose/compose.blue.yml` |
| `cdb_reports` | Postgres | `POSTGRES_DSN_FILE=/run/secrets/postgres_password_dsn` with fallback to `/run/secrets/postgres_password` | reads `orders` and `trades` for reporting | `services/reports/daily_orders_summary.py`, `infrastructure/compose/reports.yml` |
| `cdb_paper_runner` | Postgres | `POSTGRES_*` injected from compose secrets | health probe plus read-only reporting queries over `portfolio_snapshots`, `signals`, and `trades` | `tools/paper_trading/service.py`, `infrastructure/compose/compose.blue.yml` |
| `cdb_grafana` | Postgres | datasource user `claire_user` with secret-backed password export | dashboard read surface against Postgres | `infrastructure/compose/base.yml`, `infrastructure/monitoring/grafana/provisioning/datasources/postgres.yml` |
| `cdb_postgres_exporter` | Postgres | `DATA_SOURCE_NAME` built from secret password and `POSTGRES_USER` | monitoring query surface | `infrastructure/compose/base.yml` |
| audit / validation scripts | Postgres | `POSTGRES_DSN`, `POSTGRES_PASSWORD`, or `core.utils.postgres_client` | dump, verify, integrity-report, and validation reads | `docs/runbooks/postgres_least_privilege_rls.md`, `scripts/audit/postgres_privilege_dump.sql`, `scripts/audit/access_integrity_report.py`, `services/validation/runner.py`, `core/utils/postgres_client.py` |
| SurrealDB governance mirror | SurrealDB | no repo-visible `DEFINE USER`, `DEFINE ACCESS`, or `DEFINE SCOPE` | mirror tables expose table permissions, but actor boundary is unresolved | `infrastructure/surrealdb/setup.surql`, `infrastructure/surrealdb/README.md` |

## Access Control Matrix

### Postgres roles and runtime login

| Principal / role | Current repo-visible scope | Allowed access | Important limitation |
| --- | --- | --- | --- |
| `claire_user` | default login in `.env.example` and compose | broad by default in `schema.sql`; after `enforce_least_privilege.sql`, inherits `cdb_writer` | effective least privilege is deployment-dependent until enforcement and ownership transfer are actually verified |
| `cdb_reader` | read surface for audits, dashboards, and governance tables | `SELECT` on the explicit allowlist in `roles_and_grants.sql` | no dedicated login is created by default; read consumers still often use `claire_user` today |
| `cdb_writer` | runtime writer role | `SELECT` on runtime tables plus `schema_version`; `INSERT` on `signals`, `orders`, `trades`, `positions`, `portfolio_snapshots`, `risk_events`, `correlation_ledger`, `blocked_decisions`; `UPDATE` only on `positions` | no `DELETE`; no explicit write grant on governance or access-domain tables |
| `cdb_admin` | deploy / migration role | `ALL` on schema, tables, and sequences | main admin-bypass and ownership-bypass surface |

### SurrealDB governance mirror

| Principal / scope | Current repo-visible scope | Allowed access | Important limitation |
| --- | --- | --- | --- |
| implicit mirror writer / reader | `governance_events`, `audit_trail`, `deployment_approvals_mirror`, `system_config`, `security_policy_refs`, `access_matrix` | `CREATE` and `SELECT` are declared at table level | no named auth principal is defined in-repo |
| `ledger_event` writer | append-only event mirror | `SELECT FULL`, `CREATE FULL`, `UPDATE NONE`, `DELETE NONE` | strongest explicit append-only rule in the SurrealDB snapshot |
| namespace / database owner | full mirror namespace | not documented in repo | privileged actor boundary is unresolved |

### Current-state notes

- `scripts/audit/desired_privileges.json` expects `claire_user` to have no direct
  table privileges after enforcement and expects all tracked RLS flags to remain
  `false`.
- `docs/runbooks/postgres_least_privilege_rls.md` explicitly documents grant
  hardening first; it does not claim active Postgres RLS enforcement.
- `docs/surrealdb/data-ownership-matrix.md` keeps Postgres as the source of
  truth and treats SurrealDB as a mirror, not a trading-state owner.

## Threat Model

| Threat | Repo evidence | Current control | Gap / follow-up |
| --- | --- | --- | --- |
| Over-privileged runtime login | `schema.sql` grants `ALL PRIVILEGES` to `claire_user`; compose defaults still use `claire_user` | `roles_and_grants.sql`, `enforce_least_privilege.sql`, `verify_privileges.sql`, offline baseline report | environment-by-environment proof remains external to this repo and belongs with the least-privilege evidence flow |
| Owner or admin bypass | runbook and `verify_privileges.sql` both call out ownership bypass; `cdb_admin` keeps full power | explicit documentation of deploy-only role and manual ownership-transfer caveat | no repo proof that ownership has been transferred away from `claire_user` everywhere |
| Read surfaces reuse the runtime login | Grafana datasource, reports service, exporter, and many defaults still use `claire_user` | `cdb_reader` exists as a role model in grants and baseline files | a dedicated readonly login is optional only; reporting and dashboards are not provably isolated from runtime credentials |
| Connection-path drift between services | execution falls back to `POSTGRES_USER=cdb_user` in code, while compose and `.env.example` default to `claire_user`; some components use DSN files, others raw env vars | compose overlays usually normalize `POSTGRES_USER` to `claire_user`; `core.utils.postgres_client` exists for shared usage | service-level fallback drift remains possible outside the compose path |
| Secret-to-env expansion inside containers | multiple compose entrypoints export `POSTGRES_PASSWORD=$(cat /run/secrets/postgres_password)` before starting Python services | secret source files stay under `/run/secrets/*` instead of committed plaintext | the password still becomes process environment state for those containers after startup |
| No observed Postgres RLS | `desired_privileges.json` expects all tracked `row_security_enabled` flags to be `false`; runbook states RLS is not activated here | docs do not overclaim RLS | row-level isolation is still absent from the repo-visible current state |
| Manual SQL or script bypass | backup, restore, analytics, reconciliation, and dump tooling connect directly to Postgres | operator runbooks and audit scripts make these paths explicit | approved operational write/read paths are documented, but not technically fenced by separate credentials |
| SurrealDB actor ambiguity | `setup.surql` defines table permissions but no named users, scopes, or access methods | README constrains SurrealDB to a mirror role; `ledger_event` has explicit append-only permissions | actor attribution and privileged-admin boundaries remain undocumented |

## Related Repo Docs

- `docs/runbooks/postgres_least_privilege_rls.md`
- `docs/governance/evidence/ISSUE-741-postgres-least-privilege-rls.md`
- `docs/governance/access-integrity-report.md`
- `docs/governance/audit-integrity-report.md`
- `docs/governance/evidence/ISSUE-750-core-secrets-integrity-guards.md`
- `docs/governance/evidence/ISSUE-751-audit-integrity-guards.md`
- `docs/governance/evidence/ISSUE-752-deployment-integrity-guards.md`
- `docs/governance/evidence/ISSUE-753-access-integrity-guards.md`

## Boundaries

- This document is the repo-level current-state matrix and threat anchor for
  `#744`.
- It must not be used as proof that least-privilege or RLS is active in a live
  environment.
- Live grant dumps, live role memberships, and any future RLS proof remain the
  job of the least-privilege evidence path around `postgres_privilege_dump.sql`,
  `postgres_least_privilege_report.py`, and the `#741` evidence doc.
