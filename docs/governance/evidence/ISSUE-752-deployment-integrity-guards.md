# Evidence Spec for Issue #752 — Deployment Integrity Guards for deployment_approvals

Purpose:
- Capture implementation evidence for row-level integrity validation of
  `deployment_approvals_mirror` (`deployment_approvals` in issue naming).
- Ensure deployment approval drift, missing integrity metadata, and missing
  HMAC secrets surface in the report as explicit failures.

Pass criteria:
- [ ] At least one implementation PR is linked for #752.
- [ ] At least one CI/test run is linked for the implementation.
- [ ] At least one doc/spec reference is linked that explains the hash input,
      naming drift, required environment, and fail-closed behavior.
- [ ] Evidence shows the deployment report emits a schema check and an
      integrity status for every inspected row.

Current status:
- Implementation in progress. Date: 2026-03-01

---

## Implementation

- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/1010
- CI/Test run: https://github.com/jannekbuengener/Claire_de_Binare/pull/1010/checks
- Doc/ADR: `docs/governance/deployment-integrity-report.md`

### What Changed

- Reused the shared integrity helper in `core/utils/governance_integrity.py`
  instead of introducing a deployment-domain-specific hash implementation.
- Added `scripts/audit/deployment_integrity_report.py` as a fail-closed report
  entry point for `deployment_approvals_mirror`.
- Added an additive migration for deployment-domain `integrity_algo` /
  `integrity_version` metadata and aligned SurrealDB field definitions.
- Added deterministic unit tests for canonical hashing, alias-aware reporting,
  schema-gap detection, and tamper detection.

### Naming Drift

- Issue language: `deployment_approvals`
- Repo-visible Postgres / SurrealDB storage: `deployment_approvals_mirror`
- External evidence reference: `yaml_evidence_path` -> `DELIVERY_APPROVED.yaml`

### Status Codes

- `INTEGRITY_OK`
- `INTEGRITY_HASH_MISMATCH`
- `INTEGRITY_HASH_MISSING`
- `INTEGRITY_KEY_MISSING`
- `INTEGRITY_VALIDATION_SKIPPED_FORCED_FAIL`
- `INTEGRITY_UNSUPPORTED_ALGO`
- `INTEGRITY_UNSUPPORTED_VERSION`
- `DEPLOYMENT_SCHEMA_GAP`
- `DEPLOYMENT_SCHEMA_NOT_PROVABLE_FROM_FIXTURE`

### Gaps That Remain

- No live database evidence is attached here yet for deployed Postgres grants,
  mirror rows, or delivery approvals; that operational proof remains outside
  this additive audit/report change.
- The report is intentionally fail-closed and audit-only. It does not enforce
  runtime blocking, triggers, or delivery authorization at write time.
- `deployment_approvals` remains a logical alias; the repo-visible storage
  surface continues to be `deployment_approvals_mirror`.

### Related Issues

- Parent anchor: `#744`
- Least-privilege baseline: `#741`
- Adjacent domains: `#750`, `#751`, `#753`
