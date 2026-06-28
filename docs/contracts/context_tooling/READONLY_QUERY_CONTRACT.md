# Read-only Query Contract (MCP Evidence → SurrealDB)

| Field | Value |
| --- | --- |
| Status | **active** |
| Version | `readonly-query-contract/v1` |
| Issue | [#3421](https://github.com/jannekbuengener/Claire_de_Binare/issues/3421) |
| Parent meta | [#3368](https://github.com/jannekbuengener/Claire_de_Binare/issues/3368) (SLICE-03) |
| Validator | [`tools/surrealdb/context_query.py`](../../../tools/surrealdb/context_query.py) — `classify_statement()` |
| Permission layer | [`tools/mcp/permission_guard.py`](../../../tools/mcp/permission_guard.py) |
| DB permission contract | [`infrastructure/surrealdb/context_intelligence_readonly_agent_permissions.surql`](../../../infrastructure/surrealdb/context_intelligence_readonly_agent_permissions.surql) |
| Response contract | [`docs/contracts/context_tooling/DB_RECORD_EVIDENCE_RESPONSE_SCHEMA.md`](DB_RECORD_EVIDENCE_RESPONSE_SCHEMA.md) |

## Purpose

This contract establishes the formal read-only boundary between MCP evidence tools
and the SurrealDB Context Intelligence database. It documents the three-layer
defense-in-depth architecture that ensures no MCP tool path can execute writes,
mutations, or schema changes — even when an adapter config is supplied.

This contract formalizes what already exists and is enforced at runtime. No new
code behavior is introduced; the contract serves as a specification and audit
surface for the read-only guarantees already implemented across the stack.

## Three-Layer Defense Architecture

### Layer 1 — MCP Permission Guard (`tools/mcp/permission_guard.py`)

- All Wave-14 evidence/memory tools are listed in `INPUT_SCAN_EXEMPT_TOOLS`.
- The registry enforces `read_only=True` on every registered `ToolDefinition`.
- `assert_read_only_consistency()` runs post-init to catch any bypass.
- Structural tools (readiness, briefing, stop_resolver) are exempt from input
  scanning because their handlers validate inputs with operation_mode enums.

### Layer 2 — SurrealQL Statement Classifier (`tools/surrealdb/context_query.py`)

`classify_statement()` enforces a fail-closed allowlist before any query reaches
the SurrealDB adapter:

**Denied keywords** (statement-level rejection):

```
CREATE, INSERT, UPDATE, UPSERT, DELETE, RELATE, MERGE, PATCH,
DEFINE, REMOVE, ALTER, LIVE, KILL, USE, BEGIN, COMMIT, CANCEL,
EXPLAIN, SHOW CHANGES, INFO FOR ROOT
```

**Allowed prefixes** (statement-level pass):

```
SELECT, INFO FOR DB, INFO FOR TABLE, INFO FOR NS
```

**Additional guards in classify_statement():**

- Multi-statement inputs (containing `;`) are rejected.
- `APPLY`, `MIGRATION`, `TRANSACTION` keywords are rejected.
- Table policy: `_enforce_table_policy_tokens()` validates that referenced
  tables appear in `allowed_tables` and not in `forbidden_tables`.
- `FORBIDDEN_CONTEXT_QUERY_TABLES` includes trading state tables
  (`orders`, `fills`, `positions`, `balances`, `pnl`, `risk_state`,
  `execution_state`) and governance mirror tables (`governance_event`,
  `governance_decision`, `governance_state`).

**USE keyword design note:** `USE` remains in `DENIED_KEYWORDS` at the query
classifier level because `context_query.py` enforces statement-level guards
independently. The MCP adapter layer controls namespace and database selection
through HTTP headers (`surreal-ns`, `surreal-db`) on the `/sql` endpoint, not
through SurrealQL `USE` statements. This is correct by design — the MCP layer's
`SurrealDBLocalQueryAdapter` sets NS/DB on construction from config values.

### Layer 3 — SurrealDB VIEWER Permissions (`infrastructure/surrealdb/context_intelligence_readonly_agent_permissions.surql`)

The `cdb_context_agent` user operates under the `VIEWER` role:

- `SELECT` permission on all context intelligence tables.
- No `CREATE`, `UPDATE`, `DELETE`, `DEFINE`, or `REMOVE` permissions.
- Scope isolation: tables in the `context_intelligence` namespace only.
- Enforced by SurrealDB's own permission system at the database level.

This layer is the last-resort defense: even if layers 1 and 2 were bypassed,
the database itself would reject any non-SELECT operation from the
`cdb_context_agent` user.

## Adapter Flow

When an MCP evidence tool receives `adapter_config_path` in its parameters:

```
MCP Tool Handler
    |
    v
build_adapter_from_params()          [surrealdb_adapter_factory.py]
    |-- load_config()                 [context_query.py]
    |-- _load_query_credentials()     [context_query.py]
    |-- SurrealDBLocalQueryAdapter()  [context_query.py]
    |
    v
adapter.execute(query)
    |-- adapter.classify(query)       [Layer 2: classify_statement()]
    |-- adapter._sql_request(query)   [HTTP POST to localhost /sql]
    |
    v
SurrealDB (localhost)
    |-- User: cdb_context_agent       [Layer 3: VIEWER role]
    |-- NS/DB from HTTP headers       [surreal-ns, surreal-db]
    |
    v
Response → normalize → response envelope → MCP client
```

When no `adapter_config_path` is supplied, the flow uses `NoopQueryAdapter`
(source = `"in_memory"`) and caller-supplied records — no DB contact.

## Query Builder Functions

The following read-only query builders are available in `context_query.py`.
All produce only `SELECT` statements. Parameters are always validated via
`_surrealql_string()` which emits JSON-safe double-quoted literals.

| Builder | Table |
| --- | --- |
| `build_artifact_query()` | `repo_artifact` |
| `build_doc_query()` | `doc_chunk` |
| `build_symbol_query()` | `code_symbol` |
| `build_import_query()` | `import_reference` |
| `build_trace_query()` | `dependency_edge` |
| `build_explain_source_query()` | `repo_artifact` |
| `build_snapshot_query()` | `repo_artifact` |
| `build_drift_query()` | `dependency_edge` |
| `build_audit_query()` | `import_reference` |

Additional table access for evidence/claim/memory/decision tables is handled
directly by the MCP tool handlers using `SELECT * FROM <table> WHERE ... LIMIT`
with `_build_evidence_ref_where()`, `_build_claim_where()`, and
`_build_memory_where()` in `context_evidence_memory_tools.py`.

## Safety Guarantees

1. **No write path exists.** The classifier rejects every known SurrealQL
   mutation statement. The adapter only issues HTTP POST to localhost `/sql`
   with classified-safe queries.

2. **No network egress.** `_validate_local_query_url()` rejects any URL not
   pointing to `127.0.0.1`, `::1`, or `localhost`. HTTP redirects are
   blocked by `_NoRedirectHandler`.

3. **No credential leak.** `_load_query_credentials()` reads credentials from
   `SECRETS_PATH` only when `auth_mode="root"` and `adapter_config_path` is
   explicitly supplied. The Authorization header is never forwarded to a
   redirect target.

4. **Soft DB failure.** `hard_mode=False` on `SurrealDBLocalQueryAdapter` means
   an unreachable DB returns empty results with `status = "surrealdb-local-unavailable"`
   rather than raising exceptions to the MCP client.

5. **LR remains NO-GO.** This surface is context/read-only and does not
   authorize live capital, trading actions, or strategy changes.

## Configuration Constraints

The context query config (`config.context_query_local.yaml`) must enforce:

- `read_only: true`
- `mode.read_only: true`
- `mode.surrealdb_write: "forbidden"`
- `mode.surrealdb_apply: "forbidden"`
- `surreal_url` must be local-only (`127.0.0.1`, `::1`, `localhost`)
- `auth_mode` must be `"none"` or `"root"`
- `allowed_tables` must not intersect `FORBIDDEN_CONTEXT_QUERY_TABLES`
- `forbidden_tables` must include all `FORBIDDEN_CONTEXT_QUERY_TABLES`
- `max_limit_default <= max_limit_hard`

## Response Schema

DB-backed responses MUST conform to the
[DB_RECORD_EVIDENCE_RESPONSE_SCHEMA](DB_RECORD_EVIDENCE_RESPONSE_SCHEMA.md),
which defines the standardized envelope including `source`, `trust`,
`confidence`, `freshness`, `record_metadata`, and `results` fields.

## Related Contracts

- `DB_RECORD_EVIDENCE_CONTRACT.md` — Claim-level evidence contract
- `DB_RECORD_EVIDENCE_RESPONSE_SCHEMA.md` — Standardized response envelope
- `CDB_CONTEXT_TRUST_THRESHOLD_CONTRACT.md` — Trust level thresholds
- `tools/mcp/memory_output_contract.py` — MCP response envelope (predecessor pattern)
- `docs/surrealdb/context-intelligence-permission-matrix-v0.md` — Permission matrix documentation
- `infrastructure/surrealdb/context_intelligence_readonly_agent_permissions.surql` — VIEWER role

## Validation

```bash
python -m pytest tests/unit/surrealdb/test_context_query_classifier.py -q
python -m pytest tests/unit/tools/mcp/test_permission_guard.py -q
python -m pytest tests/unit/tools/mcp/test_mcp_wave14_tools.py -q
python -m pytest tests/surrealdb/test_mcp_evidence_contract.py -q
```