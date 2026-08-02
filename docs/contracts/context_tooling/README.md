# Context tooling contracts

Repo-backed contracts for Context Intelligence / MCP evidence envelopes.

| Doc | Purpose |
|---|---|
| [`DB_RECORD_EVIDENCE_CONTRACT.md`](DB_RECORD_EVIDENCE_CONTRACT.md) | DB record evidence claim envelope |
| [`DB_RECORD_EVIDENCE_RESPONSE_SCHEMA.md`](DB_RECORD_EVIDENCE_RESPONSE_SCHEMA.md) | Response schema |
| [`CDB_CONTEXT_TRUST_THRESHOLD_CONTRACT.md`](CDB_CONTEXT_TRUST_THRESHOLD_CONTRACT.md) | Operator trust threshold |
| [`READONLY_QUERY_CONTRACT.md`](READONLY_QUERY_CONTRACT.md) | Read-only query contract |
| [`TOOL_INVOCATION_JSON_EVIDENCE.md`](TOOL_INVOCATION_JSON_EVIDENCE.md) | Tool invocation evidence JSON |

No Live-Go / persist / mutation authority. Default posture remains
`PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`.

## Navigation

- [Contracts index](../README.md)
- [SurrealDB docs](../../surrealdb/README.md)
