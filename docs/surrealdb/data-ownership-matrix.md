# SurrealDB Data Ownership Matrix (P0)

This matrix defines **source-of-truth** vs **mirror** for SurrealDB integration.
Postgres remains the single source of truth for all trading state.

## Ownership Matrix

| Data Domain | Canonical Source | SurrealDB Role | Write Authority | Read Consumers | Notes |
| --- | --- | --- | --- | --- | --- |
| Trading state (orders, positions, risk, fills) | Postgres | None | Trading services only | Trading pipeline | **Never** mirrored into SurrealDB |
| Governance docs/policies | Git (Docs Hub) | Mirror | Docs owners (Git) | Governance queries | SurrealDB is read-only mirror |
| Decision events + evidence | Git (ledger) | Append-only mirror | Agents -> ledger | Audit + analytics | SurrealDB ingest only |
| Shared memory (scoped) | SurrealDB | Primary | Agents (scoped) | Agents | Scoped by namespace + TTL |
| Metrics / Observability | Prometheus / Grafana | None | Observability stack | Ops dashboards | SurrealDB excluded |

## Write Permissions (Codified)

- **Postgres**: trading services only (orders/positions/risk/fills).
- **Git (Docs Hub)**: human owners; agents via PR only.
- **SurrealDB**: ingest-only for mirrors; **append-only** for decision events.
- **Shared memory**: scoped agent writes; no backflow into Git or Postgres.

## Read Patterns

- **Trading runtime** reads **Postgres** only.
- **Governance queries** read **SurrealDB** (mirror) with fallback to Git.
- **Audit/analytics** can read **SurrealDB** (decision events).
- **Observability** reads **Prometheus/Grafana** only.

## Drift Detection Rules

- SurrealDB doc nodes must reference a Git hash (missing hash = drift).
- SurrealDB decision events must map to a ledger source file + event id.
- Any SurrealDB record claiming trading-state ownership is invalid.

## Audit Trail

- This matrix is tracked in Git; any change requires PR review.
- SurrealDB mirrors must reference Git commit hashes for traceability.
- Machine-readable version: `infrastructure/config/surrealdb/ownership.yaml`
