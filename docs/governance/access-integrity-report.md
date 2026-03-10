# Access Integrity Report

This report validates row-level integrity for `system_config` and
`security_policy_refs`.

## What Is Hashed

Integrity hashes use HMAC-SHA256 over canonical JSON from
`core/replay/canonical_json.py` via the shared helper in
`core/utils/governance_integrity.py`.

- `system_config`: `config_key`, `config_scope`, `value_ref`, `value_hash`,
  `source_path`, `observed_at`
- `security_policy_refs`: `policy_id`, `version_hash`, `docs_path`,
  `observed_at`

The canonical payload also binds the table name and integrity version, so the
same row body cannot be replayed across tables without changing the hash.

## Naming Drift

- `security_policies` is the governance name used by Issue #753 and the report
  display output.
- The repo-visible storage table is `security_policy_refs`.
- `global_settings` is accepted as a fixture/input alias for `system_config`.

## Required Environment

- `CDB_ACCESS_INTEGRITY_KEY`: external HMAC key used to compute and validate
  `integrity_hash`

The key must come from environment or another external secret source. It is not
stored in the database.

## Failure Behavior

- Missing `CDB_ACCESS_INTEGRITY_KEY` => report fails closed with
  `INTEGRITY_VALIDATION_SKIPPED_FORCED_FAIL`
- Missing integrity metadata => row status `FAIL` with
  `INTEGRITY_HASH_MISSING`, `INTEGRITY_UNSUPPORTED_ALGO`, or
  `INTEGRITY_UNSUPPORTED_VERSION`
- Schema/field drift => report status `FAIL` with `ACCESS_SCHEMA_GAP`
- Hash mismatch => row status `FAIL` with `INTEGRITY_HASH_MISMATCH`

Every row in the report gets an explicit `OK` or `FAIL` status plus a stable
reason code. The report never attempts repair or mutation.

## Usage

Fixture-based validation:

```bash
python scripts/audit/access_integrity_report.py \
  --input-dir ./path/to/fixtures \
  --out-dir ./artifacts/access_integrity
```

Database validation:

```bash
python scripts/audit/access_integrity_report.py \
  --from-db \
  --out-dir ./artifacts/access_integrity
```

The report writes:

- `report.json`
- `verification.md`
