# Evidence Spec for Issue #751 — Integrity Guards for audit_trail + governance_events

Purpose:
- Capture implementation evidence for row-level integrity validation of
  `audit_trail` and `governance_events`.
- Ensure tampering through direct DB modification surfaces in the audit report
  as an explicit failure.

Pass criteria:
- [ ] At least one implementation PR is linked for #751.
- [ ] At least one CI/test run is linked for the implementation.
- [ ] At least one doc/spec reference is linked that explains the hash input,
      required environment, and fail-closed behavior.
- [ ] Evidence shows the audit report emits an integrity status for every
      inspected row.

Current status:
- Implementation in progress. Date: 2026-03-01

---

## Implementation

- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/1006
- CI/Test run: https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22534193956
- Doc/ADR: `docs/governance/audit-integrity-report.md`

### What Changed

- Added explicit `integrity_algo` and `integrity_version` metadata for
  `audit_trail` and `governance_events`.
- Added canonical HMAC validation using the external
  `CDB_AUDIT_INTEGRITY_KEY` secret.
- Added a governance integrity report that emits per-row `OK`/`FAIL` status and
  fails closed when the key is missing.

### Status Codes

- `INTEGRITY_OK`
- `INTEGRITY_HASH_MISMATCH`
- `INTEGRITY_HASH_MISSING`
- `INTEGRITY_KEY_MISSING`
- `INTEGRITY_VALIDATION_SKIPPED_FORCED_FAIL`
- `INTEGRITY_UNSUPPORTED_ALGO`
- `INTEGRITY_UNSUPPORTED_VERSION`

### Example Report Output

```text
| Table | Row ID | Status | Reason |
| `audit_trail` | `101` | OK | `INTEGRITY_OK` |
| `governance_events` | `7` | FAIL | `INTEGRITY_HASH_MISMATCH` |
```

### Failure Behavior

- A row modified via SQL without recomputing the HMAC is reported as `FAIL`.
- Missing `CDB_AUDIT_INTEGRITY_KEY` forces the overall report to `FAIL`.
- The report does not attempt auto-repair of corrupted or missing integrity
  fields.
