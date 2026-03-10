# Evidence Spec for Issue #750 — Core Secrets Integrity Guards for core_secrets

Purpose:
- Capture implementation evidence for row-level integrity validation of
  `core_secrets_metadata` (`core_secrets` in issue naming).
- Ensure metadata drift, missing integrity metadata, and missing HMAC secrets
  surface in the report as explicit failures without exposing secret values.

Pass criteria:
- [ ] At least one implementation PR is linked for #750.
- [ ] At least one CI/test run is linked for the implementation.
- [ ] At least one doc/spec reference is linked that explains the hash input,
      naming drift, required environment, and fail-closed behavior.
- [ ] Evidence shows the core-secrets report emits a schema check and an
      integrity status for every inspected row.

Current status:
- Implementation in progress. Date: 2026-03-01

---

## Implementation

- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/1011
- CI/Test run: https://github.com/jannekbuengener/Claire_de_Binare/pull/1011/checks
- Doc/ADR: `docs/governance/core-secrets-integrity-report.md`

### What Changed

- Reused the shared integrity helper in `core/utils/governance_integrity.py`
  instead of introducing a secrets-domain-specific hash implementation.
- Added `scripts/audit/core_secrets_integrity_report.py` as a fail-closed
  report entry point for repo-visible core-secrets metadata rows.
- Added an additive migration for `core_secrets_metadata` plus optional
  read-only naming-drift variants (`core_secrets`, `service_secrets`).
- Added deterministic unit tests for canonical hashing, alias-aware reporting,
  schema-gap detection, and tamper detection.

### Naming Drift

- Issue language: `core_secrets`
- Repo-visible Postgres storage: `core_secrets_metadata`
- Read-only drift alias supported by the report: `service_secrets`
- No repo-visible SurrealDB collection exists for the core-secrets domain in
  the current snapshot, so no Surreal schema was invented here.

### Status Codes

- `INTEGRITY_OK`
- `INTEGRITY_HASH_MISMATCH`
- `INTEGRITY_HASH_MISSING`
- `INTEGRITY_KEY_MISSING`
- `INTEGRITY_VALIDATION_SKIPPED_FORCED_FAIL`
- `INTEGRITY_UNSUPPORTED_ALGO`
- `INTEGRITY_UNSUPPORTED_VERSION`
- `CORE_SECRETS_SCHEMA_GAP`
- `CORE_SECRETS_SCHEMA_NOT_PROVABLE_FROM_FIXTURE`

### Gaps That Remain

- No live database evidence is attached here yet for deployed grants, table
  ownership, or mirrored core-secrets rows; that operational proof remains
  outside this additive audit/report change.
- The report is intentionally fail-closed and audit-only. It does not enforce
  runtime blocking, triggers, or auto-repair of invalid rows.
- No repo-visible SurrealDB `core_secrets*` object exists in the current repo
  snapshot, so the domain remains Postgres-only in this slice.

### Related Issues

- Parent anchor: `#744`
- Least-privilege baseline: `#741`
- Adjacent domains: `#751`, `#752`, `#753`
