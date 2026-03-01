# Governance Audit Integrity Report

This report validates row-level integrity for `audit_trail` and
`governance_events`.

## What Is Hashed

Integrity hashes use HMAC-SHA256 over canonical JSON from
`core/replay/canonical_json.py`.

- `audit_trail`: `id`, `service_name`, `action_type`, `actor_id`, `payload`, `created_at`
- `governance_events`: `id`, `event_type`, `evidence_ref`, `created_at`

The canonical payload also binds the table name and integrity version, so the
same row body cannot be replayed across tables without changing the hash.

## Required Environment

- `CDB_AUDIT_INTEGRITY_KEY`: external HMAC key used to compute and validate
  `integrity_hash`

The key must come from environment or another external secret source. It is not
stored in the database.

## Failure Behavior

- Missing `CDB_AUDIT_INTEGRITY_KEY` => report fails closed with
  `INTEGRITY_VALIDATION_SKIPPED_FORCED_FAIL`
- Missing `integrity_hash` => row status `FAIL` with `INTEGRITY_HASH_MISSING`
- Hash mismatch => row status `FAIL` with `INTEGRITY_HASH_MISMATCH`
- Unsupported metadata => row status `FAIL` with
  `INTEGRITY_UNSUPPORTED_ALGO` or `INTEGRITY_UNSUPPORTED_VERSION`

Every row in the report gets an explicit `OK` or `FAIL` status plus a stable
reason code.

## Usage

Fixture-based validation:

```bash
python scripts/audit/governance_integrity_report.py \
  --input-dir ./path/to/fixtures \
  --out-dir ./artifacts/governance_integrity
```

Database validation:

```bash
python scripts/audit/governance_integrity_report.py \
  --from-db \
  --out-dir ./artifacts/governance_integrity
```

The report writes:

- `report.json`
- `verification.md`
