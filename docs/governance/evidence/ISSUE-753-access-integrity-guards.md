# Evidence Spec for Issue #753 — Access Integrity Guards for system_config + security_policies

Purpose:
- Capture implementation evidence for row-level integrity validation of
  `system_config` and `security_policy_refs` (`security_policies` in issue naming).
- Ensure access-domain drift, missing integrity metadata, and missing HMAC
  secrets surface in the report as explicit failures.

Pass criteria:
- [ ] At least one implementation PR is linked for #753.
- [ ] At least one CI/test run is linked for the implementation.
- [ ] At least one doc/spec reference is linked that explains the hash input,
      naming drift, required environment, and fail-closed behavior.
- [ ] Evidence shows the access report emits a schema check and an integrity
      status for every inspected row.

Current status:
- Implementation in progress. Date: 2026-03-01

---

## Implementation

- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/1009
- CI/Test run: https://github.com/jannekbuengener/Claire_de_Binare/pull/1009/checks
- Doc/ADR: `docs/governance/access-integrity-report.md`

### What Changed

- Reused the shared integrity helper in `core/utils/governance_integrity.py`
  instead of introducing a parallel access-domain hash implementation.
- Added `scripts/audit/access_integrity_report.py` as a fail-closed report entry
  point for `system_config` and `security_policy_refs`.
- Added an additive migration for `system_config` plus `integrity_algo` /
  `integrity_version` metadata on `security_policy_refs`.
- Added deterministic unit tests for canonical hashing, alias-aware reporting,
  schema-gap detection, and tamper detection.

### Naming Drift

- Issue language: `security_policies`
- Repo-visible Postgres / SurrealDB storage: `security_policy_refs`
- Accepted fixture alias: `global_settings` -> `system_config`

### Status Codes

- `INTEGRITY_OK`
- `INTEGRITY_HASH_MISMATCH`
- `INTEGRITY_HASH_MISSING`
- `INTEGRITY_KEY_MISSING`
- `INTEGRITY_VALIDATION_SKIPPED_FORCED_FAIL`
- `INTEGRITY_UNSUPPORTED_ALGO`
- `INTEGRITY_UNSUPPORTED_VERSION`
- `ACCESS_SCHEMA_GAP`
- `ACCESS_SCHEMA_NOT_PROVABLE_FROM_FIXTURE`

### Gaps That Remain

- No live database evidence is attached here yet for deployed Postgres grants or
  access-domain records; that operational proof still belongs with the
  governance anchor and least-privilege follow-ups.
- The report is intentionally fail-closed and audit-only. It does not enforce
  runtime blocking or database triggers.
- `security_policies` remains a naming alias; the repo-visible storage surface
  continues to be `security_policy_refs`.

### Related Issues

- Parent anchor: `#744`
- Least-privilege baseline: `#741`
- Adjacent domains: `#750`, `#751`, `#752`
