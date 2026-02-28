# Evidence Spec for Issue #743 — Ledger Import Integrity Guard (Anti-Replay / Anti-Spoof)
Purpose:
- Define the evidence contract for proving anti-replay / anti-spoof protections in ledger import paths without changing implementation code.
- Provide a stable reference that can be linked in Issue #743 until implementation evidence exists.

Pass criteria:
- [ ] At least one implementation PR is linked that introduces replay/spoof/integrity checks or guardrails relevant to ledger import.
- [ ] At least one CI/test run is linked that validates the guard behavior (or related constraints).
- [ ] At least one doc/spec/runbook reference is linked that explains the integrity guard approach and expected failure behavior.

Evidence plan:
- Expected PR(s): import integrity / replay guard / spoof protection PR(s) referencing #743 (or explicitly covering the same scope).
- Expected CI runs: test runs for integrity guard checks, constraint tests, or import validation pipelines.
- Expected docs/ADRs: ADR/spec/runbook documenting replay prevention, spoof rejection, and auditability of import errors.

Current status:
- Spec only (no implementation evidence yet). Date: 2026-02-24

---

## Implementation

- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/1005
- CI/Test run: https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22531042412
- Doc/ADR: `docs/surrealdb/ledger-importer.md`

### What Changed

- Added importer preflight checks for duplicate `event_id`, canonical hash mismatch, and signature-present fail-closed handling.
- Added stable machine-readable error codes and structured audit logs with `import_correlation_id`.
- Wrapped generated SurrealQL in a transaction so the import path remains all-or-nothing.

### Error Codes

- `LEDGER_IMPORT_DUPLICATE_EVENT_ID`
- `LEDGER_IMPORT_HASH_MISMATCH`
- `LEDGER_IMPORT_SIGNATURE_INVALID`
- `LEDGER_IMPORT_SIGNATURE_UNSUPPORTED`

### Failure Behavior

- Any integrity conflict aborts the entire import before write.
- Duplicate conflicts detected during the final `CREATE` request are still rejected and audit-logged.
- Audit logs include reason plus sampled event identifiers without leaking secret material.
