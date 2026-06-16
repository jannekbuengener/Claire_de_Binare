# SurrealDB / Context Intelligence Docs

Dokumentation für Context Brain, MCP-Tools, Memory-Gates und SurrealDB-Mirror — **read-only / gate-bound** auf `main`.

## Developer Onboarding

If you are new to Repo Brain / Context Intelligence, start here:

- [`../onboarding/repo_brain_context_intelligence.md`](../onboarding/repo_brain_context_intelligence.md) — developer onboarding page with first-use flow, safety boundaries, Brain Evidence Block guide, and local readiness check
- `make context-doctor` — one-command local readiness preflight

## Operator entry (read first)

| Doc | Zweck |
|---|---|
| [`../runbooks/surrealdb_context_mcp_access.md`](../runbooks/surrealdb_context_mcp_access.md) | MCP capability resolution, tool matrix |
| [`../runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md`](../runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md) | Lokaler Runtime-Pfad |
| [`db-runtime-ci-proof-path-v1.md`](db-runtime-ci-proof-path-v1.md) | CI proof matrix |
| [`../evidence/context_tooling/README.md`](../evidence/context_tooling/README.md) | Benchmark #2 evidence index |

## Grandparent / Phase-2 closeout (#1976)

| Doc | Zweck |
|---|---|
| [`SURREALDB_1976_GRANDPARENT_DOD_AND_REAL_TASK_PROOF.md`](SURREALDB_1976_GRANDPARENT_DOD_AND_REAL_TASK_PROOF.md) | DoD + RTP SSOT |
| [`SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md`](SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md) | Wave recert |
| [`SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md`](SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md) | Phase-2 closeout |
| [`SURREALDB_PRE_PHASE2_DOCS_CANON_AUDIT.md`](SURREALDB_PRE_PHASE2_DOCS_CANON_AUDIT.md) | Pre-Phase-2 audit |

## Core contracts (Auswahl)

- [`context-mcp-bridge-contract.md`](context-mcp-bridge-contract.md)
- [`context-package-model-v2.md`](context-package-model-v2.md)
- [`memory-write-gate-v1.md`](memory-write-gate-v1.md)
- [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md)
- [`scoped-agent-memory-model-v1.md`](scoped-agent-memory-model-v1.md)

## Wave completion gates

Wellen-Dokumente: `context-wave7-completion-gates.md` … `context-wave21-completion-gates.md`, `wave16-completion-gates.md` — jeweils Wellen-Abschlusskriterien.

## Code / infra pointers

- MCP server: `tools/mcp/server.py` — `python -m tools.mcp.server`
- Tooling: `tools/surrealdb/`
- Schema bootstrap: `infrastructure/surrealdb/setup.surql`
- Mirror overview: `infrastructure/surrealdb/README.md`

## SSOT boundary

- Produktive Writes / managed runtime: **NOT ACTIVATED** ohne expliziten Human-GO.
- LR **NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- Repo/engineering ledger: `CURRENT_STATUS.md`
