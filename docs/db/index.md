# DB Index

Kurzer Einstieg fuer Schema, Migrations, Privileges, Fixtures und Validierung.
Postgres ist der Canon fuer Runtime-Daten; SurrealDB ist eine optionale Mirror-Schicht.

## Postgres Canon

- Schema:
  - [`infrastructure/database/schema.sql`](../../infrastructure/database/schema.sql)
- Migrations:
  - [`infrastructure/database/migrations/`](../../infrastructure/database/migrations/)
- Access Control / Threat Model:
  - [docs/governance/evidence/ISSUE-744-access-control-matrix-threat-model.md](../governance/evidence/ISSUE-744-access-control-matrix-threat-model.md)
- Least-Privilege / Rollen / Verifikation:
  - [docs/runbooks/postgres_least_privilege_rls.md](../runbooks/postgres_least_privilege_rls.md)
  - [`infrastructure/database/roles_and_grants.sql`](../../infrastructure/database/roles_and_grants.sql)
  - [`infrastructure/database/enforce_least_privilege.sql`](../../infrastructure/database/enforce_least_privilege.sql)
  - [`infrastructure/database/rollback_least_privilege.sql`](../../infrastructure/database/rollback_least_privilege.sql)
  - [`infrastructure/database/verify_privileges.sql`](../../infrastructure/database/verify_privileges.sql)

## Fixtures und Seed-Daten

- Einstieg:
  - [`tests/fixtures/README.md`](../../tests/fixtures/README.md)
- SQL:
  - [`tests/fixtures/sql/00_reset.sql`](../../tests/fixtures/sql/00_reset.sql)
  - [`tests/fixtures/sql/01_seed_data.sql`](../../tests/fixtures/sql/01_seed_data.sql)
- Python-Fixtures:
  - [`tests/fixtures/db_fixtures.py`](../../tests/fixtures/db_fixtures.py)

## Validierung und Audits

- Pipeline-DB-Validierung:
  - [`tests/integration/validation/test_pipeline_db.py`](../../tests/integration/validation/test_pipeline_db.py)
- Schema-/Contract-Validierung:
  - [`tests/integration/test_lr005_schema_compliance.py`](../../tests/integration/test_lr005_schema_compliance.py)
  - [`tests/contract/test_event_schemas.py`](../../tests/contract/test_event_schemas.py)
- Redis/Postgres-Integration:
  - [`tests/integration/verlosung/test_redis_postgres_integration.py`](../../tests/integration/verlosung/test_redis_postgres_integration.py)
- Least-Privilege-Audit:
  - [`scripts/audit/postgres_privilege_dump.sql`](../../scripts/audit/postgres_privilege_dump.sql)
  - [`scripts/audit/postgres_least_privilege_report.py`](../../scripts/audit/postgres_least_privilege_report.py)
  - [`tests/unit/audit/test_postgres_least_privilege_report.py`](../../tests/unit/audit/test_postgres_least_privilege_report.py)

## SurrealDB Mirror

- Mirror-Ueberblick:
  - [`infrastructure/surrealdb/README.md`](../../infrastructure/surrealdb/README.md)
- Mirror-Config:
  - [`infrastructure/config/surrealdb/feature-flags.yaml`](../../infrastructure/config/surrealdb/feature-flags.yaml)
  - [`infrastructure/config/surrealdb/ownership.yaml`](../../infrastructure/config/surrealdb/ownership.yaml)
  - [`infrastructure/config/surrealdb/mirror-strategy.yaml`](../../infrastructure/config/surrealdb/mirror-strategy.yaml)
  - [`infrastructure/config/surrealdb/ledger-mapping.yaml`](../../infrastructure/config/surrealdb/ledger-mapping.yaml)
- Operative Docs:
  - [docs/runbooks/surrealdb_append_only_enforcement.md](../runbooks/surrealdb_append_only_enforcement.md)
  - [docs/surrealdb/rollback-cutover-plan.md](../surrealdb/rollback-cutover-plan.md)
  - [docs/surrealdb/dual-write-mirror-strategy.md](../surrealdb/dual-write-mirror-strategy.md)
  - [docs/surrealdb/data-ownership-matrix.md](../surrealdb/data-ownership-matrix.md)

## Context Intelligence System (CIS)

- Architektur & Roadmap:
  - [docs/surrealdb/context-intelligence-system.md](../surrealdb/context-intelligence-system.md)
  - [docs/surrealdb/context-intelligence-roadmap.md](../surrealdb/context-intelligence-roadmap.md)
- Ontology & Schema:
  - [docs/surrealdb/context-ontology-v0.yaml](../surrealdb/context-ontology-v0.yaml)
  - [`infrastructure/surrealdb/context_intelligence_v0.surql`](../../infrastructure/surrealdb/context_intelligence_v0.surql)
- Validation & Gates:
  - [docs/surrealdb/context-intelligence-validation.md](../surrealdb/context-intelligence-validation.md)
- Planung & Governance (Wave 21):
  - [docs/surrealdb/context-wave21-cross-cutting-hardening.md](../surrealdb/context-wave21-cross-cutting-hardening.md)
  - [docs/surrealdb/context-wave21-completion-gates.md](../surrealdb/context-wave21-completion-gates.md)
- Operational & Handoff:
  - [docs/surrealdb/context-agent-handoff.md](../surrealdb/context-agent-handoff.md)
  - [docs/surrealdb/context-wave7-completion-gates.md](../surrealdb/context-wave7-completion-gates.md)
