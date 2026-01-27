# SurrealDB Rollback & Cutover Plan (P0)

SurrealDB is a **sidecar**. Postgres remains the source of truth for trading state.
All cutovers must be reversible and **zero-data-loss**.

## Feature Flags (Env/Config)

**Config file:** `infrastructure/config/surrealdb/feature-flags.yaml`

- `surrealdb_enabled` (bool): master switch (default: false)
- `governance_source` (git | surrealdb): query source for governance reads
- `mirror_enabled` (bool): enable mirror ingestion (default: false)

**One-command disable (immediate rollback):**
```
set CDB_GOVERNANCE_SOURCE=git
```
or set `surrealdb_enabled: false` in the config file.

## Cutover (Reversible)

1. Enable mirror ingestion (`mirror_enabled: true`)
2. Run shadow reads (SurrealDB vs Git) and compare hashes
3. Switch read source (`governance_source: surrealdb`)
4. Keep Git as canonical (no writes to SurrealDB)

**Rollback:** set `governance_source: git` and/or `surrealdb_enabled: false`.

## No Data Loss Guarantees

- Trading state stays in Postgres
- Governance data remains in Git
- SurrealDB is mirror-only / append-only

## Restore Drill (Scenario + Steps)

**Scenario:** SurrealDB corruption or outage.

**Steps:**
1. Set `governance_source: git` (immediate fallback)
2. Stop SurrealDB container
3. Rebuild SurrealDB from Git snapshots + ledger events

**Acceptance check:** compare doc counts + hash set equality between Git and SurrealDB.

## Machine-Readable Config

- `infrastructure/config/surrealdb/feature-flags.yaml`
