# SurrealDB Ledger Importer (P0)

This importer ingests **ledger decision events** into SurrealDB as an
append-only mirror. It is **idempotent** and will not block primary writes.

## Scope (P0)

Supported action types:
- work.start
- branch.create
- pr.create
- pr.merge
- issue.close

Other action types are imported with `event_kind=other`.

## Idempotence

- Uses `event_id` from the ledger file as the SurrealDB record id.
- If `event_id` is missing, a deterministic SHA-256 of the event payload is used.
- Re-import of the same event produces the same `ledger_event:<id>` record.

## Agent Chain

- Each event includes `agent.id`.
- Importer links to the **previous event** for the same agent (`prev_event_id`).

## Redaction Rules (No Sensitive Strings)

The importer redacts evidence strings that look like credentials:
- auth-like values after `=` or `:`
- GitHub PAT-style prefixes (redacted)

Redacted values are replaced with `[REDACTED]`.

## Files

- Importer: `tools/surrealdb/ledger_importer.py`
- Mapping: `infrastructure/config/surrealdb/ledger-mapping.yaml`

## Usage

```bash
python tools/surrealdb/ledger_importer.py ./path/to/ledger --dry-run
```

To execute against SurrealDB:
```bash
python tools/surrealdb/ledger_importer.py ./path/to/ledger \
  --url http://localhost:8000/sql \
  --namespace cdb \
  --database cdb
```
