# Core Secrets Integrity Report

This report validates row-level integrity for the repo-visible core-secrets
metadata mirror and related naming-drift aliases.

## What Is Hashed

Integrity hashes use HMAC-SHA256 over canonical JSON from
`core/replay/canonical_json.py` via the shared helper in
`core/utils/governance_integrity.py`.

- `core_secrets_metadata`: `secret_name`, `provider_ref`, `fingerprint`,
  `created_at`
- `core_secrets` / `service_secrets`: same field set when an environment still
  exposes those legacy drift names

The canonical payload also binds the storage table name and integrity version,
so the same row body cannot be replayed across tables without changing the
hash.

## Naming Drift

- `core_secrets` is the issue-domain name used by Issue #750.
- The repo-visible Postgres storage table is `core_secrets_metadata`.
- `service_secrets` is supported as a read-only drift alias if an environment
  still exposes that table name.
- The report validates metadata and fingerprints only. Secret values remain
  outside the mirrored storage and outside the report scope.

## Required Environment

- `CDB_CORE_SECRETS_INTEGRITY_KEY`: external HMAC key used to compute and
  validate `integrity_hash`

The key must come from environment or another external secret source. It is not
stored in the database.

## Failure Behavior

- Missing `CDB_CORE_SECRETS_INTEGRITY_KEY` => report fails closed with
  `INTEGRITY_VALIDATION_SKIPPED_FORCED_FAIL`
- Missing integrity metadata => row status `FAIL` with
  `INTEGRITY_HASH_MISSING`, `INTEGRITY_UNSUPPORTED_ALGO`, or
  `INTEGRITY_UNSUPPORTED_VERSION`
- Schema/field drift => report status `FAIL` with `CORE_SECRETS_SCHEMA_GAP`
- Hash mismatch => row status `FAIL` with `INTEGRITY_HASH_MISMATCH`

Every row in the report gets an explicit `OK` or `FAIL` status plus a stable
reason code. The report never attempts repair or mutation.

## Usage

Fixture-based validation:

```bash
python scripts/audit/core_secrets_integrity_report.py \
  --input-dir ./path/to/fixtures \
  --out-dir ./artifacts/core_secrets_integrity
```

Database validation:

```bash
python scripts/audit/core_secrets_integrity_report.py \
  --from-db \
  --out-dir ./artifacts/core_secrets_integrity
```

The report writes:

- `report.json`
- `verification.md`
