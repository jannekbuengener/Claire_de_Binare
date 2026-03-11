# SurrealDB Dual-Write / Mirror Strategy (P0)

SurrealDB is a **read-only mirror** for governance/doc/ledger data. Postgres remains the
single source of truth for trading state. The mirror must **never** block trading flows.

## Write Pattern (Postgres-first)

1. **Primary write** to canonical source:
   - Governance docs/policies: Git (Working Repo canon)
   - Decision events/evidence: Git ledger
2. **Mirror write** to SurrealDB (async by default):
   - Append-only ingestion, no updates-in-place unless idempotent
3. **Failure handling**:
   - SurrealDB lag or failure must **not** block primary writes
   - Mirror retries are queued and can be replayed

## Read-Only Boundaries

- Trading pipeline **never** writes to SurrealDB.
- SurrealDB endpoints are used by **read-only** governance queries.
- No bidirectional writes; SurrealDB is a **sink**.

## Data Contract (What Mirrors)

**Included (mirror/append-only):**
- Governance docs snapshots
- Policy snapshots
- Ledger decision events
- Evidence references (hash + path)

**Excluded (never mirrored):**
- Orders, positions, risk state, fills
- Live trading state

## Idempotence Rules

- Mirror records must include a **source id**:
  - Git commit hash + document path
  - Ledger event id + file path
- Re-import of the same source id must be a **no-op**.

## Operational Guardrails

- Mirror write failures are logged and retried; they do not block primary writes.
- SurrealDB is append-only; deletes are prohibited.
- Drift detection compares SurrealDB hashes vs Git hashes.

## Machine-Readable Spec

- `infrastructure/config/surrealdb/mirror-strategy.yaml`
