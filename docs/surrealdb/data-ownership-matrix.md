# SurrealDB Data Ownership Matrix (P0)

This matrix defines **source-of-truth** vs **mirror** for SurrealDB integration.
Postgres remains the single source of truth for all trading state.

## Ownership Matrix

| Data Domain | Canonical Source | SurrealDB Role | Write Authority | Read Consumers | Notes |
| --- | --- | --- | --- | --- | --- |
| Trading state (orders, positions, risk, fills) | Postgres | None | Trading services only | Trading pipeline | **Never** mirrored into SurrealDB |
| Governance docs/policies | Git (Working Repo canon) | Mirror | Docs owners (Git) | Governance queries | SurrealDB is read-only mirror |
| Decision events + evidence | Git (ledger) | Append-only mirror | Agents -> ledger | Audit + analytics | SurrealDB ingest only |
| Shared memory (scoped) | SurrealDB | Primary | Agents (scoped) | Agents | Cross-agent interchange; namespace + TTL; lighter/shorter-lived than agent_memory; no trading state; no secrets |
| Metrics / Observability | Prometheus / Grafana | None | Observability stack | Ops dashboards | SurrealDB excluded |
| Context intelligence (CIS) | Git (Working Repo canon) | Mirror | Context indexer | Agents, CDB-MCP | Umbrella domain: metadata, knowledge graph edges, computed knowledge; hash-backed; no trading state; no secrets |
| Repo knowledge | Git (Working Repo canon) | Mirror | Context indexer | Agents, CDB-MCP | Static code symbols, interfaces, types, dependency edges; source-hash required; conditional ingestion only |
| Doc knowledge | Git (Working Repo canon) | Mirror | Context indexer | Agents, CDB-MCP | Markdown docs, governance, runbooks, agents; source-hash per chunk required; stale refs are drift |
| Agent memory | SurrealDB | Primary | Agents (per-agent scoped) | Agents | Per-agent memory: agent_id + namespace + TTL; source-hash-backed evidence refs; audit-trailed; distinct from shared_memory |
| Evidence fabric | SurrealDB | Primary | Context indexer, agents | Agents, CDB-MCP, audit | Queryable evidence graph; claims with source hashes; provenance trail; append-only; no trading-proofs |
| Decision context | Git (ledger) | Append-only mirror | Agents -> ledger | Agents, audit | Decision events with rationale + evidence bundle refs; ingest only; no automatic trade execution |

## Write Permissions (Codified)

- **Postgres**: trading services only (orders/positions/risk/fills).
- **Git (Working Repo canon)**: human owners; agents via PR only.
- **SurrealDB**: ingest-only for mirrors; **append-only** for decision events and decision_context.
- **Shared memory**: scoped agent writes; no backflow into Git or Postgres.
- **Agent memory**: per-agent scoped writes (agent_id + namespace); no cross-agent bypass; no trading state; no secrets.
- **Evidence fabric**: context indexer + agent writes; append-only; source-hash-backed claims.
- **Context intelligence / Repo knowledge / Doc knowledge**: context indexer only; no direct agent writes; mirror of Git truth.

## Read Patterns

- **Trading runtime** reads **Postgres** only.
- **Governance queries** read **SurrealDB** (mirror) with fallback to Git.
- **Audit/analytics** can read **SurrealDB** (decision events, decision_context, evidence_fabric).
- **Agents** read **SurrealDB** (context_intelligence, repo_knowledge, doc_knowledge, agent_memory, evidence_fabric, shared_memory).
- **CDB-MCP** reads **SurrealDB** (context_intelligence, repo_knowledge, doc_knowledge, evidence_fabric).
- **Observability** reads **Prometheus/Grafana** only.

## Drift Detection Rules

- SurrealDB doc nodes must reference a Git hash (missing hash = drift).
- SurrealDB decision events must map to a ledger source file + event id.
- Any SurrealDB record claiming trading-state ownership is invalid.
- CIS records (repo_knowledge, doc_knowledge, evidence_fabric) MUST reference a source hash (git commit + path). Missing source hash = drift.
- Claims in evidence_fabric and decision_context MUST reference ledger source + event_id. Missing evidence ref = drift.
- Doc references in doc_knowledge MUST match current working-repo Git hash. Stale references = drift.
- Any trading-state record (orders, positions, fills, balances, risk-state) in ANY SurrealDB domain is invalid (extends trading-state rule to all CIS domains).
- Agent memory writes outside scoped namespace (agent_id + namespace) are invalid. Unscoped memory = drift.

## Explicit Exclusions (guardrails)

All SurrealDB domains — including context intelligence, repo knowledge, doc knowledge, agent memory, evidence fabric, decision context, and shared memory — MUST NEVER contain:

- Orders (any form, any status)
- Positions (open, closed, pending)
- Fills (partial, complete)
- Risk-State-Runtime-Daten (live exposure, drawdown, limits)
- Secrets (API keys, passwords, private keys, credentials, tokens)
- Broker-Credentials
- Wallet-Secrets
- Session-Secrets
- Balance- oder Konto-Zustandsdaten
- Productive Redis-/Postgres-Betriebszustandsdaten
- Live-/Echtgeld-Go-Autorisierungen
- Personenbezogene Daten (PII) beyond public repo metadata

## Audit Trail

- This matrix is tracked in Git; any change requires PR review.
- SurrealDB mirrors must reference Git commit hashes for traceability.
- Machine-readable version: `infrastructure/config/surrealdb/ownership.yaml`
