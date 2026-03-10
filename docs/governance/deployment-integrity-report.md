# Deployment Integrity Report

This report validates row-level integrity for deployment approval evidence
stored in the deployment-domain mirror table.

## What Is Hashed

Integrity hashes use HMAC-SHA256 over canonical JSON from
`core/replay/canonical_json.py` via the shared helper in
`core/utils/governance_integrity.py`.

- `deployment_approvals_mirror`: `pr_id`, `commit_sha`, `yaml_evidence_path`,
  `created_at`

The canonical payload also binds the table name and integrity version, so the
same row body cannot be replayed across tables without changing the hash.

## Naming Drift

- `deployment_approvals` is the governance-domain name used by Issue #752 and
  the report display output.
- The repo-visible storage table is `deployment_approvals_mirror`.
- `yaml_evidence_path` is expected to reference the external
  `DELIVERY_APPROVED.yaml` evidence path.

## Required Environment

- `CDB_DEPLOYMENT_INTEGRITY_KEY`: external HMAC key used to compute and
  validate `integrity_hash`

The key must come from environment or another external secret source. It is not
stored in the database.

## Failure Behavior

- Missing `CDB_DEPLOYMENT_INTEGRITY_KEY` => report fails closed with
  `INTEGRITY_VALIDATION_SKIPPED_FORCED_FAIL`
- Missing integrity metadata => row status `FAIL` with
  `INTEGRITY_HASH_MISSING`, `INTEGRITY_UNSUPPORTED_ALGO`, or
  `INTEGRITY_UNSUPPORTED_VERSION`
- Schema/field drift => report status `FAIL` with `DEPLOYMENT_SCHEMA_GAP`
- Hash mismatch => row status `FAIL` with `INTEGRITY_HASH_MISMATCH`

Every row in the report gets an explicit `OK` or `FAIL` status plus a stable
reason code. The report never attempts repair or mutation.

## Usage

Fixture-based validation:

```bash
python scripts/audit/deployment_integrity_report.py \
  --input-dir ./path/to/fixtures \
  --out-dir ./artifacts/deployment_integrity
```

Database validation:

```bash
python scripts/audit/deployment_integrity_report.py \
  --from-db \
  --out-dir ./artifacts/deployment_integrity
```

The report writes:

- `report.json`
- `verification.md`
