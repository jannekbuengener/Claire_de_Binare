# DB-Record Evidence Response Schema

| Field | Value |
| --- | --- |
| Status | **active** |
| Version | `db-record-evidence-response/v1` |
| Issue | [#3421](https://github.com/jannekbuengener/Claire_de_Binare/issues/3421) |
| Parent meta | [#3368](https://github.com/jannekbuengener/Claire_de_Binare/issues/3368) (SLICE-03) |
| Validator | [`tools/surrealdb/db_record_evidence_response.py`](../../../tools/surrealdb/db_record_evidence_response.py) |
| Predecessor pattern | [`tools/mcp/memory_output_contract.py`](../../../tools/mcp/memory_output_contract.py) |
| Claim contract | [`docs/contracts/context_tooling/DB_RECORD_EVIDENCE_CONTRACT.md`](DB_RECORD_EVIDENCE_CONTRACT.md) |
| Query contract | [`docs/contracts/context_tooling/READONLY_QUERY_CONTRACT.md`](READONLY_QUERY_CONTRACT.md) |

## Purpose

This schema defines the standardized response envelope for evidence retrieved
from the SurrealDB Context Intelligence database via the MCP read-only query
adapter. Every DB-backed response from Wave-14 tools (`cdb_context_evidence_resolve`,
`cdb_context_claim_resolve`, `cdb_context_memory_get`) and the trust summary tool
(`cdb_context_trust_summary`) MUST conform to this envelope.

The schema wraps raw SurrealDB query results into a consistent format that
surfaces source provenance, trust classification, confidence scores, freshness
signals, and record-level metadata. This enables downstream tooling and
agent briefings to make reliable trust assessments without re-interpreting
raw database rows.

## Schema Structure

```yaml
schema_version: "db-record-evidence-response/v1"
tool: string                    # MCP tool name
status: "ok" | "error"         # Response status
source: "surrealdb-local" | "surrealdb-local-unavailable" | "in_memory"
metadata:
  source: string               # Same as source above (from derive_guarded_source_label)
  read_only: true
  query_time_ms: integer
record_count: integer           # Number of records in results
records: list<object>           # Normalised SurrealDB rows
filters_applied: object         # Active WHERE clause filters
trust:
  level: "HIGH" | "MEDIUM" | "LOW" | "BLOCKED"
  classification: string        # valid_db_backed | partial | repo_only | in_memory_fixture | accepted_limitation | invalid_fake_db
  confidence: float            # 0.0 – 1.0
  source_priority: string      # live_github | repo_files | surrealdb_context | ledger_snapshots | fallback
freshness:
  age_seconds: integer
  stale_threshold_seconds: integer
  is_stale: boolean
  freshness_signal: string     # Human-readable freshness assessment
limitations: list<string>       # Standard + tool-specific limitations
no_echtgeld_go: true
```

## Field Specifications

### `schema_version` (required)
Always `"db-record-evidence-response/v1"`. Must be the first field validated.

### `tool` (required)
The MCP tool name that produced this response. One of:
- `cdb_context_evidence_resolve`
- `cdb_context_claim_resolve`
- `cdb_context_memory_get`
- `cdb_context_trust_summary`

### `status` (required)
- `"ok"` — Query succeeded, results returned (may be empty).
- `"error"` — Query failed (error envelope returned).

### `source` (required)
Derived from `derive_guarded_source_label()` in `surrealdb_adapter_factory.py`:
- `"surrealdb-local"` — Query executed against a reachable local SurrealDB.
- `"surrealdb-local-unavailable"` — DB unreachable, soft-fail with empty results.
- `"in_memory"` — No adapter config supplied; caller-provided records.

### `metadata` (required)
Carries the same `source` label plus `read_only: true` and `query_time_ms`.
This mirrors the envelope structure from `memory_output_contract.py`.

### `record_count` (required)
Integer count of records in `results`. Must equal `len(results)`.

### `records` (required)
List of normalised record objects. For DB-backed responses, each record is a
mapping with SurrealDB field names projected to contract-compatible names per
the normalisation functions in `context_evidence_memory_tools.py`:
- `_normalize_evidence_ref_row()` for evidence records
- `_normalize_claim_row()` for claim records
- `_normalize_memory_row()` for memory records

### `filters_applied` (required)
Documents which WHERE clause filters were active during the query. Keys include
`mode`, any parameters passed to the `_build_*_where()` functions, and the
effective `limit` value. When no safe filter can be constructed, the filter is
omitted and `filters_applied` records `"filter_mode": "full_page_with_in_memory_filtering"`.

### `trust` (required)
Aggregate trust assessment for the response:

| Field | Source |
| --- | --- |
| `level` | Derived from `CDB_CONTEXT_TRUST_THRESHOLD_CONTRACT.md` thresholds |
| `classification` | `valid_db_backed`, `partial`, `repo_only`, `in_memory_fixture`, `accepted_limitation`, `invalid_fake_db` |
| `confidence` | 0.0–1.0; aggregate over record-level confidences or adapter status |
| `source_priority` | From the source priority hierarchy in `DB_RECORD_EVIDENCE_CONTRACT.md` |

Trust derivation rules:
- `source = "surrealdb-local"` with valid records → `classification = "valid_db_backed"`, `level >= "MEDIUM"`.
- `source = "surrealdb-local-unavailable"` → `classification = "partial"`, `level <= "LOW"`.
- `source = "in_memory"` → `classification = "in_memory_fixture"`, `level = "LOW"`.
- Empty results from any source → `classification = "partial"`, `level = "LOW"`.

### `freshness` (required)
Assesses record timeliness:

- `age_seconds`: Wall-clock time since the query was issued.
- `stale_threshold_seconds`: Config-driven; default 3600 (1 hour).
- `is_stale`: `true` when `age_seconds > stale_threshold_seconds`.
- `freshness_signal`: Human-readable label — `"fresh"`, `"aging"`, `"stale"`, or `"unknown"`.

### `limitations` (required)
Copied from `memory_output_contract.py` default limitations plus any
tool-specific extensions. Must always include:
```
"Memory is provided as context, not as authoritative truth."
"stale/superseded memory is flagged but not auto-removed."
"LR remains NO-GO; no live-go or Echtgeld-GO implied."
```

### `no_echtgeld_go` (required)
Always `true`. Reaffirms that this response does not authorize live capital,
trading actions, or strategy changes.

## Error Response Schema

When `status = "error"`, the envelope collapses to:

```yaml
schema_version: "db-record-evidence-response/v1"
tool: string
status: "error"
error:
  code: string
  message: string
metadata:
  source: "in_memory"
  read_only: true
  query_time_ms: 0
limitations: [...]               # Standard limitations still apply
no_echtgeld_go: true
```

## Validation Rules

The `DbRecordEvidenceResponseValidator` in `db_record_evidence_response.py`
enforces:

1. `schema_version` must be `"db-record-evidence-response/v1"`.
2. `tool` must be a recognised Wave-14 tool name.
3. `source` must be in `{"surrealdb-local", "surrealdb-local-unavailable", "in_memory"}`.
4. `status` must be `"ok"` or `"error"`.
5. For `status = "ok"`:
   - `records` must be a list.
   - `record_count` must equal `len(records)`.
   - `trust.classification` must be a valid trust classification.
   - `trust.confidence` must be between 0.0 and 1.0.
   - `freshness.is_stale` must be boolean.
   - `no_echtgeld_go` must be `true`.
6. For `status = "error"`:
   - `error.code` and `error.message` must be non-empty strings.
7. Response must not contain secret-like substrings (same rules as
   `DB_RECORD_EVIDENCE_CONTRACT.md` § Redaction).
8. `limitations` must include the three standard limitation strings.

## Integration with Existing Contracts

### DB_RECORD_EVIDENCE_CONTRACT.md
The claim evidence contract defines the *claim-level* contract for individual
evidence assertions. This response schema defines the *envelope-level* contract
for bulk responses from the database. The trust classification and source
priority fields are shared between both contracts.

### READONLY_QUERY_CONTRACT.md
The query contract defines the read-only boundary between MCP tools and
SurrealDB. Responses that pass through that boundary MUST be wrapped in this
envelope before reaching the MCP client.

### memory_output_contract.py
This schema extends the memory output contract pattern to the DB-backed
evidence surface. The `metadata`, `source`, `limitations`, and `no_echtgeld_go`
fields are inherited directly from that contract.

## Testing

```bash
python -m pytest tests/surrealdb/test_mcp_evidence_contract.py -q
```

Test coverage requirements (see `test_mcp_evidence_contract.py`):
- Schema field validation (ok and error paths)
- Source label enforcement
- Trust classification consistency
- Freshness computation and staleness detection
- LIMIT and filter transparency
- Secret leak detection
- Empty results handling
- `no_echtgeld_go` enforcement