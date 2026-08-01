---
relations:
  role: doc
  domain: governance
  upstream: []
  downstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
    - knowledge/governance/CDB_AGENT_POLICY.md
    - knowledge/governance/CDB_AGENT_CONTROL_PLANE.md
---
# Canonical governance policies and rules.

## Where to write / Where not to write
*   **Write here:** New or updated governance policies, policy amendments.
*   **Do NOT write here:** Operational logs, agent-specific knowledge, temporary working memory.
*   Agent-authored files under this directory are **not** binding canon unless an
    explicit owner-authored transition authorizes them (`CDB_AGENT_POLICY.md`
    Zone D; sole documented exception `#4202`).

## Key entrypoints
*   [CDB Constitution (CDB_CONSTITUTION.md)](CDB_CONSTITUTION.md)
*   [CDB Governance (CDB_GOVERNANCE.md)](CDB_GOVERNANCE.md)
*   [CDB Agent Policy (CDB_AGENT_POLICY.md)](CDB_AGENT_POLICY.md)
*   [CDB Agent Control Plane proposal (CDB_AGENT_CONTROL_PLANE.md)](CDB_AGENT_CONTROL_PLANE.md) — **Proposal / Pending Owner Canonization** (`#4250`); not binding policy; distinct from `.github` Workflow Control Plane
*   Agent Execution Contract v1 — [`docs/contracts/agent_execution/CDB_AGENT_EXECUTION_CONTRACT_V1.md`](../../docs/contracts/agent_execution/CDB_AGENT_EXECUTION_CONTRACT_V1.md) (`cdb.agent_execution.v1`, `#4251`; technical schema/tooling; ACP governance binding deferred)
*   [CDB Trust Score Policy (CDB_TRUST_SCORE_POLICY.md)](CDB_TRUST_SCORE_POLICY.md)
*   [ARVP Product Intent (ARVP_PRODUCT_INTENT.md)](ARVP_PRODUCT_INTENT.md) — north-star anchor for accelerated replay paper-mode platform

## SSOT boundary
Governance policies do not override Live-Readiness verdicts. LR **NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
