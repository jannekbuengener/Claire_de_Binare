# CDB Agent Memory Contract

**Status:** CONTRACT_ONLY - no productive DB write claims.

**Issues:** [#3490], [#3483], [#3485], [#3479]

## 1. Purpose

Agent Memory in CDB is a controlled subconscious context layer. It may help an
agent remember scoped observations, issue-local findings, decision pointers,
evidence summaries, and repo facts, but it is never truth and never
authorisation.

This contract defines the agent-facing memory classes that a future CDB memory
implementation may accept, which inputs are forbidden, and which scope, TTL,
evidence, read, write, and redaction gates must hold before any later runtime
implementation is allowed to persist or expose memory.

This slice is intentionally limited to contract documentation plus a
machine-readable artifact. It does not operationalise memory writes, SurrealDB
adapters, MCP mutation, or any live database behavior.

## 2. Relationship To Existing Memory Surfaces

This contract sits above the existing lower-level memory model in
`docs/surrealdb/scoped-agent-memory-model-v1.md`.

- `scoped-agent-memory-model-v1.md` defines the current low-level storage-side
  memory families such as `working_memory`, `semantic_memory`, and
  `episodic_memory`.
- This contract defines the higher-level agent-facing memory classes that CDB
  wants to allow at the policy boundary.
- No runtime mapping from these contract classes to the lower-level storage
  families is implemented in this slice.

Because that mapping is not yet implemented and no adapter evidence exists, this
contract remains `CONTRACT_ONLY`.

## 3. Allowed Memory Types

The following memory classes are allowed at the contract level.

| Type | Practical role | Scope rule | TTL rule | Evidence rule | Read rule | Write rule |
|------|----------------|------------|----------|---------------|-----------|------------|
| `operator_note` | Human or operator observation summarized for a bounded task | issue/task/agent scoped | short-to-medium TTL | source hash or issue ref plus evidence | read-only, scoped, non-authoritative | dry-run gate only |
| `issue_memory` | condensed issue-local status or findings | issue scoped | issue-state or 24h-bound refresh | issue ref plus evidence | read-only, scoped, non-authoritative | dry-run gate only |
| `decision_memory` | bounded summary of a prior decision | decision/issue scoped | no-expiry only as contract pointer | ledger or decision evidence | read-only, scoped, non-authoritative | dry-run gate only |
| `evidence_summary` | compact summary of evidence already collected | artifact/issue scoped | hash/freshness bound | evidence ref plus provenance | read-only, scoped, non-authoritative | dry-run gate only |
| `session_lesson` | summarized lesson from a finished session | session/agent scoped | short-to-medium TTL | repo or issue evidence | read-only, scoped, non-authoritative | dry-run gate only |
| `repo_fact_cache` | cached repo fact for repeated use | repo path/component scoped | refresh on main merge or hash change | source hash required | read-only, scoped, non-authoritative | dry-run gate only |

All allowed types share the same hard boundaries:

- scope is mandatory
- TTL or freshness policy is mandatory
- evidence linkage is mandatory
- redaction is mandatory
- reads are read-only-first
- writes remain dry-run-only at the contract surface
- `operational=false`
- `persist_allowed=false`
- `mutation_allowed=false`
- `backing_status=CONTRACT_ONLY`

## 4. Forbidden Inputs

The following inputs are explicitly forbidden at the contract boundary:

| Input | Why forbidden |
|-------|---------------|
| `secrets` | secrets are never stored in any CDB system |
| `broker_credentials` | exchange or broker credentials are never stored |
| `live_positions` | trading runtime data is Postgres-only |
| `live_orders` | trading runtime data is Postgres-only |
| `live_fills` | trading runtime data is Postgres-only |
| `live_risk_state` | trading runtime data is Postgres-only |
| `trading_runtime_control` | kill-switch and execution flags are runtime-only |
| `raw_chat_dump` | raw chat transcripts are unredacted, unscoped, and not evidence-stable |
| `unscoped_agent_memory` | global or cross-agent unscoped memory violates the scoped memory model |

Additional exclusion inherited from the fulltext contract:

- `agent_memory_raw` remains excluded from BM25/fulltext indexing.

## 5. Scope, TTL, Evidence, Read, And Write Gates

### Scope gate

- No memory entry is valid without an explicit scope.
- Issue, task, session, artifact, or agent scope must be named.
- Cross-agent bypass remains forbidden.
- `unscoped_agent_memory` is invalid by contract.

### TTL gate

- Memory is TTL-bound or freshness-bound.
- Short-lived session knowledge must expire quickly.
- Repo and issue facts must refresh when the underlying repo hash or GitHub
  state changes.
- No agent may treat stale memory as current truth.

### Evidence gate

- Every allowed memory type needs provenance.
- A source hash, issue/PR reference, decision pointer, or evidence reference is
  mandatory depending on type.
- Memory without evidence remains invalid by contract.

### Read gate

- `cdb_context_memory_get` remains read-only.
- Returned memory is advisory context, not truth.
- Stale or superseded memory may be visible, but must not be treated as current
  authority.

### Write gate

- `cdb_context_memory_write_intent` remains `dry_run_only`.
- This contract does not authorise productive writes.
- `PERSIST_ALLOWED` stays false at the contract surface.
- `MUTATION_ALLOWED` stays false at the contract surface.

### Redaction gate

- Raw chat dumps are forbidden.
- Sensitive values must be summarized or redacted before any future memory write
  flow is considered.
- Secrets, credentials, and live trading state remain blocked before any
  SurrealDB capability is considered.

## 6. Why The Contract Is Not Operational Yet

This contract is not operational because the current repo evidence shows:

- `cdb_context_memory_get` is exposed as read-only, but remains
  `DB_BACKED_READONLY_UNPROVEN` in the MCP boundary matrix.
- `cdb_context_memory_write_intent` is exposed as a dry-run gate only and stays
  `CONTRACT_ONLY` in tool inventory.
- no adapter evidence proves `DB_BACKED_READONLY_PROVEN`
- no productive write path is authorised by this slice

Therefore this contract must not claim:

- `operational=true`
- `PERSIST_ALLOWED=true`
- `MUTATION_ALLOWED=true`
- `DB_BACKED_READONLY_PROVEN`

## 7. Relationship To #3483 Ownership And #3485 Fulltext

### Ownership matrix (#3483)

`artifacts/surrealdb/context_data_model_ownership_matrix.json` defines the
underlying `agent_memory` category as scoped, TTL-bound, and evidence-linked.
It also marks the category as conceptually persist-capable inside the ownership
model.

This contract does not elevate that ownership capability into current runtime
write permission. At the agent-facing boundary, persistence remains blocked
until a dedicated implementation slice proves the adapter, gate, and audit path.

### Fulltext contract (#3485)

`artifacts/surrealdb/context_fulltext_bm25_contract.json` explicitly excludes
`agent_memory_raw` from BM25 indexing.

This contract inherits that boundary:

- no raw chat dump storage
- no raw agent memory indexing
- no assumption that agent memory is searchable as normal repo/evidence content

## 8. What A Later GO Would Still Need

The following is outside this slice and requires a separate GO:

- runtime mapping from these contract types to low-level memory families
- adapter-backed evidence for any DB-backed claim
- explicit approval model for any productive memory persistence
- cross-agent handoff semantics beyond read-only consumption
- validated redaction pipeline for memory creation

Until then, the only allowed outcome is a documented contract surface plus a
machine-readable artifact.

## 9. References

- `docs/surrealdb/scoped-agent-memory-model-v1.md`
- `docs/surrealdb/CDB_CONTEXT_DATA_MODEL_OWNERSHIP.md`
- `artifacts/surrealdb/context_data_model_ownership_matrix.json`
- `docs/surrealdb/CDB_CONTEXT_FULLTEXT_BM25_CONTRACT.md`
- `artifacts/surrealdb/context_fulltext_bm25_contract.json`
- `artifacts/mcp/mcp_access_boundary_matrix.json`
- `artifacts/context_tool_inventory/tool_inventory.json`
- `tools/mcp_access_boundary.py`
