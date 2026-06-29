# CDB Context Fulltext BM25 Contract

**Status:** CONTRACT_ONLY — no live DB operationality claimed.

**Issues:** [#3485], [#3483], [#3479]

## 1. Purpose

This contract defines which context categories are indexable via SurrealDB
FULLTEXT BM25, the canonical analyzer and index configuration, score semantics,
freshness policies, and the explicit forbidden-category blocklist. It formalises
the gap proven by Issue #3485: the SurrealDB analyzer and BM25 index exist in
`.surql` definitions but had zero CDB-level contract document or machine-readable
artifact.

The contract is **CONTRACT_ONLY** until adapter evidence proves
`DB_BACKED_READONLY_PROVEN` for at least one category.

## 2. Canonical Analyzer

All indexable categories use the same canonical analyzer:

| Property | Value |
|----------|-------|
| Analyzer name | `cdb_code_analyzer` |
| TOKENIZERS | `class`, `camel` |
| FILTERS | `lowercase`, `ascii` |
| Defined in | `context_intelligence_v0.surql`, `context_intelligence_v0_deploy.surql`, `proof_graph_vector_setup.surql` |

## 3. Canonical BM25 Index

| Property | Value |
|----------|-------|
| Index name | `idx_doc_chunk_content_ft` |
| ON TABLE | `doc_chunk` |
| FIELDS | `content` |
| Type | FULLTEXT |
| Analyzer | `cdb_code_analyzer` |
| Scoring | BM25 |
| Highlights | Enabled (`BM25 HIGHLIGHTS`) |

## 4. Indexable Categories

| Category | Analyzer | Indexed Fields | Score | Highlights | Evidence Required | Source of Truth | Freshness Policy |
|----------|----------|----------------|------|------------|-------------------|-----------------|-----------------|
| `repo_file` | cdb_code_analyzer | content, file_path | BM25 | yes | source_hash | repo | no_expiry_hash_verified |
| `github_issue` | cdb_code_analyzer | title, body | BM25 | yes | issue_url_or_number | github_live | stale_after_24h_or_state_change |
| `github_pr` | cdb_code_analyzer | title, body, diff | BM25 | yes | pr_url_or_number | github_live | stale_after_24h_or_state_change |
| `evidence` | cdb_code_analyzer | content, description | BM25 | yes | source_hash_and_provenance | repo_and_surrealdb | no_expiry_hash_verified |
| `claim` | cdb_code_analyzer | statement, rationale | BM25 | yes | evidence_ref_and_source_hash | repo_and_surrealdb | no_expiry_hash_verified |
| `decision` | cdb_code_analyzer | description, rationale | BM25 | yes | ledger_source_and_event_id | git_ledger | no_expiry |
| `external_doc` | cdb_code_analyzer | content, title | BM25 | yes | source_url_or_ref | external_upstream | stale_after_7d_or_upstream_change |

All seven categories share:

- **operational:** `false`
- **backing_status:** `CONTRACT_ONLY`
- **live_index_exists:** `false`

These three fields must remain `false`/`CONTRACT_ONLY` until a real SurrealDB
adapter is operational and evidence of `DB_BACKED_READONLY_PROVEN` exists
per category.

## 5. Forbidden Categories

These categories are **explicitly blocked** from fulltext BM25 indexing:

| Category | Reason |
|----------|--------|
| `secrets` | CDB_AGENT_POLICY section 4 — never stored in any CDB system |
| `broker_credentials` | Broker/exchange credentials — never stored or indexed |
| `live_positions` | Postgres-only runtime data |
| `live_orders` | Postgres-only runtime data |
| `live_fills` | Postgres-only runtime data |
| `live_risk_state` | Postgres-only runtime data |
| `trading_runtime_control` | Postgres-only runtime data |
| `agent_memory_raw` | Raw agent memory excluded from fulltext per data ownership model |

Categories not in either list (`context_tool`, `mcp_boundary`, `agent_memory`)
are **repo-only or scoped** surfaces. `context_tool` and `mcp_boundary` remain
repo-only — not fulltext-indexable — as confirmed by the ownership matrix.
`agent_memory` is scoped to SurrealDB but `agent_memory_raw` is explicitly
blocked from fulltext indexing.

## 6. Governance Rules

- **No live DB operationality** may be claimed without adapter evidence.
- `cdb_code_analyzer` is the **canonical** fulltext analyzer for all CDB context
  categories.
- `repo-rg (ripgrep)` is the documented **fallback** for repo-local fulltext
  search where SurrealDB BM25 is not available.
- `context_tool` and `mcp_boundary` remain **repo-only** — no DB-backed fulltext.
- `agent_memory_raw` is **explicitly blocked** from fulltext indexing (sub-category
  of `agent_memory` per ownership matrix).

## 7. References

- [Context Data Model Ownership Matrix](../../artifacts/surrealdb/context_data_model_ownership_matrix.json)
- [Context Data Model Ownership Doc](./CDB_CONTEXT_DATA_MODEL_OWNERSHIP.md)
- [Context Core Schema](./context-core-schema-v1.md)
- [Hybrid Retrieval Strategy](./context-hybrid-retrieval-strategy-v1.md)
- `infrastructure/surrealdb/context_intelligence_v0.surql`
- `infrastructure/surrealdb/context_intelligence_v0_deploy.surql`
- `infrastructure/surrealdb/proof_graph_vector_setup.surql`
- `infrastructure/surrealdb/hybrid_retrieval_fixtures.surql`
