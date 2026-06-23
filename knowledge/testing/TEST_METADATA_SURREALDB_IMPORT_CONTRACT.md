# Test-Metadata SurrealDB Import Contract v1

**Status:** active contract
**Scope:** Test-First Metadata SurrealDB dry-run import planning
**Date:** 2026-06-23
**Predecessors:** PR #3409 (Scanner), PR #3415 (Import Bundle), PR #3416 (Ledger)

---

## 1. Purpose

This contract defines the deterministic translation of a Test-First Metadata
Import Bundle (v1) into a SurrealDB-ready dry-run Import Plan (v1). The plan
describes `test_case:*` target records but **never writes to SurrealDB**.

The contract bridges two read-only tools:
- **Scanner** (`tools/test_metadata_scanner.py`) — finds and validates metadata blocks in Python test files
- **Bundle Builder** (`tools/test_metadata_import_bundle.py`) — transforms scanner output into deterministic import bundle records
- **Import Plan Builder** (`tools/test_metadata_surrealdb_import_plan.py`) — translates bundle records into a SurrealDB dry-run import plan

A future real Import Adapter (separate gate slice) will consume the plan and
execute actual SurrealDB writes.

---

## 2. Scope

### 2.1 In Scope

- Translation of Import Bundle v1 records to import plan operations
- Deterministic sorting of plan operations
- Validation of bundle contract (required fields, path safety, hash integrity)
- Dry-run only — no SurrealDB connection, no SurrealQL execution
- Explicit limitation documentation for unresolvable fields (e.g. missing `pilot_id`)

### 2.2 Out of Scope

- SurrealDB connection or write of any kind
- SurrealQL execution or `.surql` file generation as primary output
- Real import adapter or apply pipeline
- Database migrations or schema changes
- MCP tool changes or MCP write paths
- Runtime / Docker / Secrets / Exchange scope
- `test_title` to `test_name` migration
- Live or Echtgeld trading readiness

---

## 3. Input: Import Bundle v1

The plan builder consumes output from `tools/test_metadata_import_bundle.py`.

### 3.1 Bundle Envelope

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | `test-metadata-import-bundle/v1` |
| `source_scanner` | string | yes | `test_metadata_scanner/v1.0.0` |
| `record_count` | int | yes | Number of records |
| `records` | array | yes | Array of record objects |

### 3.2 Bundle Record

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Bundle schema version |
| `record_type` | string | yes | `test_case` |
| `record_id` | string | yes | `test_case:<24-char-hex>` from `source_file + test_id` |
| `source_file` | string | yes | Relative POSIX path to test file |
| `pilot_id` | string | yes | `CDB-PILOT-NNN` or empty string |
| `test_id` | string | yes | Unique test identifier |
| `test_type` | string | yes | One of the 15 test types |
| `ci_artifact` | string | yes | CI artifact type (e.g. `test-report`) |
| `surrealdb_export` | bool | yes | `true` for all exported records |
| `metadata` | object | yes | Full scanner output fields (unchanged) |
| `content_hash` | string | yes | SHA-256 hex via `canonical_hash()` |
| `source_scanner` | string | yes | Scanner version |
| `limitations` | array | yes | Known limitation strings |

---

## 4. Output: Dry-run Import Plan v1

### 4.1 Plan Envelope

```json
{
  "schema_version": "test-metadata-surrealdb-import-plan/v1",
  "source_bundle_schema": "test-metadata-import-bundle/v1",
  "plan_type": "upsert_dry_run",
  "operation_count": 1,
  "dry_run": true,
  "surrealdb_write": false,
  "warnings": [],
  "limitations": [],
  "operations": [
    {
      "operation": "upsert_dry_run",
      "target_table": "test_case",
      "target_id": "test_case:f7cbdae5b69b6355575cf520",
      "record": {
        "source_file": "tests/unit/validation/test_profitability_evidence_packet_assembler.py",
        "pilot_id": "CDB-PILOT-001",
        "test_id": "cdb-test-pilot-001",
        "test_type": "mixed",
        "ci_artifact": "test-report",
        "surrealdb_export": true
      },
      "content_hash": "9cb810756e8cb05f5ebe62352517cc23c98797294a6a8a26c374efc03676b574",
      "source_bundle_record_id": "test_case:f7cbdae5b69b6355575cf520",
      "limitations": []
    }
  ]
}
```

### 4.2 Operation Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `operation` | string | yes | `upsert_dry_run` (the only operation type in v1) |
| `target_table` | string | yes | `test_case` |
| `target_id` | string | yes | `test_case:<stable_id>` — matches `record_id` from bundle |
| `record` | object | yes | The actual record payload (fields for DB write) |
| `content_hash` | string | yes | Stable content hash from bundle |
| `source_bundle_record_id` | string | yes | Echo of the source bundle's `record_id` |
| `limitations` | array | yes | Per-operation limitations |

### 4.3 Record Subset in Operation

The `record` object in each operation contains only the fields relevant to a
SurrealDB `test_case:*` record:

- `source_file` (string, relative POSIX path)
- `pilot_id` (string, may be empty)
- `test_id` (string)
- `test_type` (string)
- `ci_artifact` (string, never bool)
- `surrealdb_export` (bool, always `true`)
- All fields from `metadata`

**Excluded from `record` (present in bundle but not in import target):**
- `schema_version` — bundle metadata, not a DB field
- `record_type` — expressed by `target_table` + `target_id`
- `record_id` — expressed by `target_id`
- `content_hash` — expressed at operation level
- `source_scanner` — bundle provenance, not a DB field
- `limitations` — expressed at operation level

### 4.4 Warnings

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Machine-readable code (e.g. `empty_pilot_id`) |
| `message` | string | Human-readable explanation |
| `target_id` | string | Optional affected target ID |

---

## 5. Validation Rules

### 5.1 Bundle Validation

| Check | Fail Behaviour |
|-------|---------------|
| Invalid JSON | Exit 2 |
| Missing `records` key | Exit 2 |
| Empty `records` array | Exit 1 |
| Record missing `record_id` | Exit 1 |
| Record missing `content_hash` | Exit 1 |
| Record missing `test_id` | Exit 1 |
| Record missing `ci_artifact` | Exit 1 |
| Record missing `surrealdb_export` | Exit 1 |
| `ci_artifact` is not a string | Exit 1 (must be string, never bool) |
| `source_file` contains absolute path | Exit 1 |
| `record_id` does not start with `test_case:` | Warning (not blocking in v1) |

### 5.2 Hash Determinism

- `content_hash` is computed via `canonical_hash()` from `core/replay/canonical_json.py`.
- The hash input excludes `record_id` and `content_hash` itself.
- Records with identical content produce identical `content_hash` values.
- `content_hash` passes through from the bundle; the plan builder does **not**
  recompute it.

### 5.3 Path Safety

- `source_file` must be a relative POSIX path.
- Windows drive letters (`C:\`, `D:/`) and Unix absolute paths (`/root/...`) are
  rejected fail-closed.
- Backslashes are normalized to forward slashes before validation.

### 5.4 pilot_id Limitation

- `pilot_id` is derived from the `cdb-test-pilot-NNN` naming convention.
- If `pilot_id` is empty, a warning `empty_pilot_id` is emitted and
  `"pilot_id: not derivable from test_id (expected cdb-test-pilot-NNN pattern)"`
  is added to `limitations`.

### 5.5 Forbidden Content

- No secrets or credentials (no `token`, `password`, `secret` key patterns in output)
- No absolute paths
- No SurrealDB connection parameters
- No database target addresses
- No write authorization flags

---

## 6. Determinism Rules

| Aspect | Rule |
|--------|------|
| Record order | Sort by `(source_file, test_id, record_id)` — same as bundle |
| Operation order | Same order as sorted records |
| `content_hash` | Passed through from bundle (not recomputed) |
| `record` content | Sorted keys via `json.dumps(sort_keys=True)` |
| Bundle fingerprint | SHA-256 of `source_bundle_schema + "," + sorted(target_ids)` |

---

## 7. Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Valid dry-run plan produced |
| 1 | No importable records or contract validation error |
| 2 | Parse / usage error (invalid JSON, missing file, bad arguments) |

---

## 8. Safety Boundaries

- **No SurrealDB write.** The plan sets `"surrealdb_write": false` and
  `"dry_run": true`. Any future adapter must check these flags fail-closed.
- **No SurrealQL.** The plan builder never imports or calls SurrealQL code.
- **No DB connector.** The plan builder never imports `surrealdb` or
  `psycopg2` or any DB library.
- **No MCP.** The plan builder is a pure CLI tool with no MCP dependencies.
- **No Runtime/Docker/Secrets.** The plan builder does not start services,
  access secrets, or open network connections.
- **No Live/Echtgeld.** LR remains NO-GO. Board `trade-capable` is not a live
  trading authorization.

---

## 9. Pipeline Summary

```
Python test file
    │
    ▼
tools/test_metadata_scanner.py  (read-only)
    │  finds metadata blocks, validates 15 fields, outputs JSON report
    ▼
Scanner JSON report
    │
    ▼
tools/test_metadata_import_bundle.py  (read-only)
    │  filters is_valid + surrealdb_export, builds deterministic records
    ▼
Import Bundle v1
    │
    ▼
tools/test_metadata_surrealdb_import_plan.py  (read-only, dry-run)
    │  translates records to planned operations, no DB write
    ▼
Import Plan v1  ──►  Future: SurrealDB Import Adapter (gate slice)
```

---

## 10. Limitations

- `pilot_id` relies on `cdb-test-pilot-NNN` naming convention. Blocks outside
  this pattern get empty `pilot_id` with a warning.
- The plan describes `test_case:*` records only. Relation edges
  (`prueft`, `betrifft`, `gehoert_zu`, etc.) are not part of v1.
- No existing-records reconciliation (diff against current DB state) — this
  would require a real SurrealDB connection and is deferred.
- `test_title` remains inside `metadata`; no `test_name` field migration.
