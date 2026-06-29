# CDB Context Brain — Data Model Ownership Matrix

**Status:** CANONICAL  
**Version:** 1  
**Issues:** #3483, #3479  
**PR:** #3498  
**Canonical Sources:** `infrastructure/config/surrealdb/ownership.yaml`, `docs/surrealdb/data-ownership-matrix.md`, `docs/surrealdb/context-core-schema-v1.md`, `docs/surrealdb/context-ontology-v0.yaml`

---

## Purpose

Define which data categories the CDB Context Brain operates on, who owns them, what the source of truth is, what may be mirrored or persisted, and which data categories are explicitly forbidden. This matrix is the canonical answer to: *Was lebt wo, wer pflegt was?*

---

## Data Categories Overview

| # | Category | Owner | Source of Truth | SurrealDB Role | Persist Allowed |
|---|----------|-------|----------------|----------------|-----------------|
| 1 | `repo_file` | context_indexer | Git (working repo) | `mirror_read_only` | Yes (hash-verified) |
| 2 | `github_issue` | jannek | GitHub live | `cache` | Yes (TTL-bound) |
| 3 | `github_pr` | jannek | GitHub live | `cache` | Yes (TTL-bound) |
| 4 | `context_tool` | context_indexer | Git (working repo) | `none` | **No** (repo-only) |
| 5 | `mcp_boundary` | context_indexer | Git (working repo) | `none` | **No** (repo-only) |
| 6 | `evidence` | context_indexer | Git + SurrealDB | `primary_scoped` | Yes (append-only) |
| 7 | `claim` | context_indexer | Git + SurrealDB | `primary_scoped` | Yes (append-only) |
| 8 | `decision` | agents_via_ledger | Git ledger | `append_only_mirror` | Yes (append-only) |
| 9 | `agent_memory` | agents | SurrealDB | `primary_scoped` | Yes (TTL + scope) |
| 10 | `external_doc` | context_indexer | External upstream | `cache` | Yes (TTL-bound) |

---

## Mirror vs Primary

| Role | Meaning | Examples |
|------|---------|---------|
| `mirror_read_only` | Replicated from Git, never edited in SurrealDB | repo_file, doc_chunk, code_symbol |
| `cache` | Temporary mirror of live external state | github_issue, github_pr, external_doc |
| `append_only_mirror` | Ingested from Git ledger, never modified | decision, decision_event |
| `primary_scoped` | SurrealDB is the primary store, with scope/TTL/evidence constraints | agent_memory, evidence, claim |
| `none` | Not stored in SurrealDB at all | context_tool, mcp_boundary |

---

## Forbidden Categories (Never in Context Brain)

| Category | Reason | Governance Rule |
|----------|--------|-----------------|
| `secrets` | API keys, passwords, tokens, private keys | CDB_AGENT_POLICY.md, gitleaks enforced |
| `broker_credentials` | Exchange API credentials, wallet secrets | LR NO-GO, CDB_TRESOR_POLICY.md |
| `live_positions` | Open/closed/pending positions | Postgres-only runtime data |
| `live_orders` | Orders in any state | Postgres-only runtime data |
| `live_fills` | Fill data | Postgres-only runtime data |
| `live_risk_state` | Live exposure, drawdown, limits, margin | Postgres-only runtime data |
| `trading_runtime_control` | Kill-switch, execution mode, trading flags | Postgres-only runtime data |

These categories are blocked at every layer: MCP tools, permission guard, Context Bridge, and this ownership matrix.

---

## TTL and Lifecycle

| Category | TTL Policy | Refresh Trigger |
|----------|-----------|-----------------|
| repo_file | No expiry (hash-verified) | Git push to main |
| github_issue | 24h or state change | Poll or event |
| github_pr | 24h or state change | Poll or event |
| context_tool | Repo refresh on main merge | Git pull |
| mcp_boundary | Repo refresh on main merge | Git pull |
| evidence | No expiry (hash-verified) | On creation |
| claim | No expiry (hash-verified) | On creation |
| decision | No expiry | On creation via ledger |
| agent_memory | TTL-bound (agent_id + namespace) | On write, TTL expiry |
| external_doc | 7 days or upstream change | Scheduled refresh |

---

## Evidence Requirements

All data categories stored in SurrealDB must reference a source of truth for auditability:

- **repo-based** categories: require `source_hash` (git commit + path)
- **GitHub-based** categories: require `issue_url` or `pr_url`
- **evidence/claim**: require `source_hash` + `provenance_ref`
- **decision**: require `ledger_source` + `event_id`
- **agent_memory**: require `source_hash` or `evidence_ref` + `agent_id` + `namespace`
- **external_doc**: require `source_url` or `ref`

Categories without evidence requirements (`context_tool`, `mcp_boundary`) are repo-only and not DB_BACKED.

---

## Safety Boundaries

| Rule | Enforcement |
|------|-------------|
| `PERSIST_ALLOWED=false` default on main | MCP write-intent gate, permission guard |
| `MUTATION_ALLOWED=false` default on main | FORBIDDEN_MUTATION in access boundary |
| No `DB_BACKED_READONLY_PROVEN` without adapter evidence | Test `test_no_category_claims_db_backed_without_evidence` |
| Live trading state never stored in SurrealDB | Drift rules in ownership.yaml |
| Secrets never ingested | Gitleaks, policy gate, CDB_AGENT_POLICY.md |
| Agent memory TTL-bound | Scoped-agent-memory-model-v1.md |
| Cross-agent memory bypass blocked | ownership.yaml drift_rules |
| LR remains NO-GO for all categories | LR-AUDIT-STATUS-2026-03-05.md |

---

## CDB Governance vs SurrealDB Capabilities

SurrealDB supports schemaless documents, graph relations, fulltext BM25, vector HNSW, and live queries. CDB does not adopt every capability automatically. Governance wins:

1. **FORBIDDEN_MUTATION**: SurrealDB `create`, `insert`, `upsert`, `update`, `delete`, `relate`, `run` are blocked at MCP boundary.
2. **BLOCKED surfaces**: SurrealDB `query`, `select`, `list`, `use`, `info` are not exposed to agents.
3. **No DB_BACKED claim** without adapter evidence: all tools remain `CONTRACT_ONLY` or `REPO_ONLY` until proven.
4. **Agent memory is scoped**: no global/unscoped memory writes.
5. **Secrets and trading state** are excluded at governance level before any SurrealDB capability is considered.

---

## Related Issues and PRs

| Reference | Content |
|-----------|---------|
| #3479 | Meta-issue: Context Brain / SurrealDB Sensory Roadmap |
| #3483 | This issue — canonicalize data model and ownership |
| #3493 | Tool Inventory (PR #3495 merged) |
| #3481 | MCP Access Boundary (PR #3497 merged) |
| #3498 | This PR — RED_ONLY tests + matrix implementation |
| `infrastructure/config/surrealdb/ownership.yaml` | Machine-readable ownership matrix (11 domains) |
| `docs/surrealdb/data-ownership-matrix.md` | Narrative ownership document |
| `docs/surrealdb/context-core-schema-v1.md` | Schema-level table definitions |
| `docs/surrealdb/context-ontology-v0.yaml` | 18 ontology concepts |
| `artifacts/surrealdb/context_data_model_ownership_matrix.json` | Machine-readable per-category ownership matrix |

---

## Remaining Gaps (outside this slice)

1. Per-type lifecycle enforcement (programmatic TTL checks)
2. Automatic refresh scheduling for GitHub/external categories
3. Tool-to-data-domain mapping for all 42 MCP boundary tools
4. DB_BACKED_READONLY_PROVEN classification for any category (requires adapter evidence)
5. Named human owners beyond `context_indexer` / `agents` roles
6. DR/backup/recovery plan
