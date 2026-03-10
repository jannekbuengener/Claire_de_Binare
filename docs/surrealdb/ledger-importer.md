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

## Integrity Guard

Before the first `CREATE`, the importer runs a fail-closed preflight:

- Canonical payload hash is computed from a normalized event payload with stable key ordering.
- Self-referential integrity fields (`event_hash`, `hash`, `sha256`, `signature`) are excluded from the hash input.
- If a declared hash is present and does not match the canonical payload hash, the entire import aborts.
- If a signature field is present, the importer aborts unless a verifier already exists. No new PKI or key infrastructure is created by this importer.
- All incoming `event_id` values are checked batchwise for duplicates in the import batch and against `ledger_event` before any write request is sent.

Imported records now include `integrity.sha256` with the canonical payload hash used by preflight.

## Failure Behavior

- Import is all-or-nothing: generated SurrealQL is wrapped in a transaction.
- Any preflight conflict aborts the full import with exit code `1`.
- Duplicate conflicts that still surface during `CREATE` after preflight are treated as deterministic rejection and logged with the same machine-readable error code family.

## Error Codes

- `LEDGER_IMPORT_DUPLICATE_EVENT_ID`: duplicate `event_id` in the batch or already present in `ledger_event`
- `LEDGER_IMPORT_HASH_MISMATCH`: declared event hash does not match canonical payload hash
- `LEDGER_IMPORT_SIGNATURE_INVALID`: signature field is malformed or empty
- `LEDGER_IMPORT_SIGNATURE_UNSUPPORTED`: signature was supplied but no verifier exists in this repo path

Audit logs emit structured JSON with:

- `import_correlation_id`
- `code`
- `reason`
- `event_ids_count`
- `event_ids_sample`

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
