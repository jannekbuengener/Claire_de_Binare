# Context Intelligence Permission Matrix v0

**Issue:** #3426 (Slice-08)  
**Meta:** #3418 — Build SurrealDB-native ContextBrain / VectorGraph Foundation  
**Status:** Canonical (v0, software-only, no productive DB)

---

## 1. Purpose

This document defines the **SurrealDB-level permission matrix** for the Context Intelligence system. It specifies which operations the read-only agent user (`cdb_context_agent`) may and may not perform, and how the three defense-in-depth layers interact.

---

## 2. Permission Matrix

### 2.1 Layer Overview

| Layer | Scope | Mechanism | Authority |
|---|---|---|---|
| **SurrealDB RBAC** | Database `context_intel` | `DEFINE USER ... ROLES VIEWER` | Built-in SurrealDB system roles |
| **Table PERMISSIONS** | Per table | `DEFINE TABLE ... PERMISSIONS FOR select/create/update/delete` | Baseline = all NONE (fail-closed) |
| **Server Capabilities** | SurrealDB process | CLI startup flags (`--deny-all`, `--deny-scripting`, etc.) | Server-level deny-by-default |

### 2.2 Principal Matrix

| Principal | Type | Level | Auth | Allowed Ops | Forbidden Ops | Table Scope | Mechanism |
|---|---|---|---|---|---|---|---|
| `cdb_context_agent` | System user (VIEWER) | DATABASE | PASSHASH placeholder `${CDB_CONTEXT_AGENT_READONLY_PASS_HASH}` | SELECT, INFO, USE | CREATE, UPDATE, DELETE, DEFINE, REMOVE, RELATE, INSERT, MERGE, REBUILD, TRUNCATE, GRANT, REVOKE | All 21 context intelligence tables | SurrealDB built-in VIEWER role (RBAC) |
| Guests / unauthenticated | None | DATABASE | None | None | All operations | None | Table PERMISSIONS = NONE (no guest override) |
| System OWNER/EDITOR | System user | DATABASE | Password / Passhash | All | None (by role) | All | SurrealDB RBAC (not scoped to this contract) |

### 2.3 Context Intelligence Tables (21)

| # | Table | Type | In Permission Scope |
|---|---|---|---|
| 1 | `repo_artifact` | SCHEMAFULL | Yes (VIEWER read) |
| 2 | `code_symbol` | SCHEMAFULL | Yes |
| 3 | `doc_page` | SCHEMAFULL | Yes |
| 4 | `doc_section` | SCHEMAFULL | Yes |
| 5 | `doc_chunk` | SCHEMAFULL | Yes |
| 6 | `concept` | SCHEMAFULL | Yes |
| 7 | `dependency_edge` | SCHEMAFULL | Yes |
| 8 | `evidence_ref` | SCHEMAFULL | Yes |
| 9 | `claim` | SCHEMAFULL | Yes |
| 10 | `decision_event` | SCHEMAFULL | Yes |
| 11 | `agent_memory` | SCHEMAFULL | Yes |
| 12 | `context_query` | SCHEMAFULL | Yes |
| 13 | `audit_observation` | SCHEMAFULL | Yes |
| 14 | `contradiction` | SCHEMAFULL | Yes |
| 15 | `stale_context` | SCHEMAFULL | Yes |
| 16 | `scope_drift_event` | SCHEMAFULL | Yes |
| 17 | `knowledge_quality_score` | SCHEMAFULL | Yes |
| 18 | `visual_control_view` | SCHEMAFULL | Yes |
| 19 | `artifact_cites_decision` | TYPE RELATION | Yes |
| 20 | `memory_supports_decision` | TYPE RELATION | Yes |
| 21 | `chunk_mentions_symbol` | TYPE RELATION | Yes |

### 2.4 Operation Semantics

| Operation | Allowed for cdb_context_agent? | SurrealDB Keyword | Notes |
|---|---|---|---|
| SELECT rows | Yes | `SELECT` | VIEWER role grants read on all child resources |
| INFO schema | Yes | `INFO FOR` | VIEWER role grants schema introspection |
| USE namespace/db | Yes | `USE` | VIEWER role grants session context switching |
| CREATE records | No | `CREATE` | Blocked by VIEWER role |
| UPDATE records | No | `UPDATE` | Blocked by VIEWER role |
| DELETE records | No | `DELETE` | Blocked by VIEWER role |
| DEFINE schema | No | `DEFINE` | Blocked by VIEWER role + server capabilities |
| REMOVE schema | No | `REMOVE` | Blocked by VIEWER role + server capabilities |
| RELATE edges | No | `RELATE` | Blocked by VIEWER role |
| INSERT records | No | `INSERT` | Blocked by VIEWER role |
| REBUILD indexes | No | `REBUILD` | Blocked by VIEWER role + server capabilities |
| TRUNCATE table | No | `TRUNCATE` | Blocked by VIEWER role |
| GRANT permissions | No | `GRANT` | Blocked by VIEWER role |
| REVOKE permissions | No | `REVOKE` | Blocked by VIEWER role |
| MERGE records | No | `MERGE` | Blocked by VIEWER role |

---

## 3. File Locations

| Artifact | Path |
|---|---|
| Permission contract (SurrealQL template) | `infrastructure/surrealdb/context_intelligence_readonly_agent_permissions.surql` |
| Deploy schema (baseline PERMISSIONS NONE) | `infrastructure/surrealdb/context_intelligence_v0_deploy.surql` |
| Permission matrix (this document) | `docs/surrealdb/context-intelligence-permission-matrix-v0.md` |
| Permission contract tests | `tests/surrealdb/test_permission_contract.py` |
| Tool-level MCP permission guard | `tools/mcp/permission_guard.py` (separate, unchanged by #3426) |

---

## 4. Defense-in-Depth

```
Agent/MCP  ─►  MCP PermissionGuard (tool-level, regex scan)
                    │
                    ▼
              SurrealDB Server (capability flags: --deny-all --deny-scripting ...)
                    │
                    ▼
              context_intel Database
                    │
                    ▼
              DEFINE USER cdb_context_agent ROLES VIEWER (RBAC)
                    │
                    ▼
              Table PERMISSIONS FOR select NONE (fail-closed baseline)
```

The `cdb_context_agent` VIEWER role overrides the NONE baseline at runtime. This is intentional: guests and unauthenticated sessions still see NONE, while the authenticated agent reads through RBAC.

---

## 5. Relation to Tool-Level Permissions

The MCP PermissionGuard (`tools/mcp/permission_guard.py`) is a **separate parallel layer** at the tool/application level. It scans tool parameters for forbidden SQL keywords (INSERT, UPDATE, DELETE, CREATE, DROP, etc.) and runtime operations. It is **not modified** by this permission matrix contract.

The two layers are complementary:

| Scenario | MCP PermissionGuard | SurrealDB VIEWER |
|---|---|---|
| Agent sends SELECT via MCP tool | Passes (read-only keywords) | Allowed (VIEWER read) |
| Agent sends raw SurrealQL via MCP tool | Blocked (forbidden patterns) | Not reached |
| Direct SurrealDB connection (non-MCP) | Not applicable | Allowed for SELECT, blocked for writes (VIEWER) |
| MCP bridge executes malformed query | Blocked (input scan) | Not reached |

---

## 6. Non-Goals

- **No changes to `tools/mcp/permission_guard.py`** — tool-level guardrail remains as-is
- **No live user creation** — this is a template contract
- **No real secrets, JWTs, passwords, or root tokens committed**
- **No productive SurrealDB writes**
- **No DEFINE TOKEN** — deprecated and removed in SurrealDB 3.0
- **No DEFINE CAPABILITIES** — capabilities are server-level CLI flags, not SurrealQL statements
- **No trading state tables** (orders, fills, positions, risk_state, position_state, trade)
- **No scope growth** to #3421 (MCP Evidence Contract), #3427 (ContextBrain Ledger)

---

## 7. Next Slice

**#3421 — Readonly MCP Brain Evidence Contract**  
Builds on this permission matrix by connecting the MCP evidence tools to SurrealDB using the `cdb_context_agent` credential for read-only queries.

---

## 8. Changelog

| Date | Change | Author |
|---|---|---|
| 2026-06-24 | v0 — Initial permission matrix for #3426 | Agent (OpenCode) |
