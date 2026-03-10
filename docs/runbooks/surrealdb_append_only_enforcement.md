# Runbook: SurrealDB Append-Only Enforcement (Issue #742)

## What changed

The ledger importer (`tools/surrealdb/ledger_importer.py`) now uses
**`CREATE ... CONTENT`** instead of `UPSERT ... MERGE`.

This means:

- **First import** of an `event_id` succeeds (record created).
- **Re-import** of the same `event_id` fails deterministically
  (SurrealDB rejects `CREATE` on an existing record ID).
- The original record is **never overwritten**.

## How append-only is enforced

### 1. Importer level (code)

`build_surrealql()` emits only `CREATE ledger_event:<event_id> CONTENT {...}`.
No `UPSERT`, `MERGE`, `UPDATE`, or `DELETE` statements are generated.

On duplicate, `post_surrealql()` parses the SurrealDB JSON response,
detects `"already exists"` errors, and raises `DuplicateEventError`.
`main()` catches this and exits with code **1**.

### 2. Database level (schema)

`infrastructure/surrealdb/setup.surql` defines:

```sql
DEFINE TABLE ledger_event PERMISSIONS
  FOR select FULL,
  FOR create FULL,
  FOR update NONE,
  FOR delete NONE;
```

Even if a caller bypasses the importer, SurrealDB itself blocks
`UPDATE` and `DELETE` on `ledger_event` records.

### 3. Role separation (operational)

| Role   | Capabilities                        | Used by             |
|--------|-------------------------------------|----------------------|
| admin  | Schema DDL (root credentials)       | Deploy / migration   |
| writer | `CREATE` + `SELECT` on ledger tables| Ledger importer      |
| reader | `SELECT` only                       | Audit / dashboards   |

Admin applies `setup.surql`. Writer credentials are used by the importer
at runtime. Reader credentials are used for queries/reporting.

## Reproduce re-import failure

```bash
# First import (succeeds)
python tools/surrealdb/ledger_importer.py ./path/to/ledger.yaml \
  --url http://localhost:8000/sql --namespace cdb --database cdb

# Second import of the same file (fails with exit code 1)
python tools/surrealdb/ledger_importer.py ./path/to/ledger.yaml \
  --url http://localhost:8000/sql --namespace cdb --database cdb
# Expected: "ERROR: APPEND-ONLY VIOLATION: ..." + exit 1
```

Dry-run mode (`--dry-run`) prints the generated SQL without executing:

```bash
python tools/surrealdb/ledger_importer.py ./path/to/ledger.yaml --dry-run
# Output: CREATE ledger_event:<id> CONTENT {...}; ...
```

## Test coverage

```bash
pytest tests/unit/surrealdb/test_ledger_importer.py -v
```

Tests verify:
- `build_surrealql` emits `CREATE`, not `UPSERT`/`MERGE`
- Duplicate detection parses SurrealDB error responses correctly
- `post_surrealql` raises `DuplicateEventError` on conflict
- Unknown error formats are not silently swallowed
