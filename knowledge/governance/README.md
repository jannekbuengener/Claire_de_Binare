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
*   Agent-authored writes under this directory remain forbidden unless an
    explicit owner-authored transition authorizes them (`CDB_AGENT_POLICY.md`
    Zone D; sole foundation exception `#4202`). Owner ratification of
    `CDB_AGENT_CONTROL_PLANE.md` (2026-08-01, commit `c691a8d0`) is recorded
    in that file and does not authorize later material agent amendments.

## Key entrypoints
*   [CDB Constitution (CDB_CONSTITUTION.md)](CDB_CONSTITUTION.md)
*   [CDB Governance (CDB_GOVERNANCE.md)](CDB_GOVERNANCE.md)
*   [CDB Agent Policy (CDB_AGENT_POLICY.md)](CDB_AGENT_POLICY.md)
*   [CDB Agent Control Plane (CDB_AGENT_CONTROL_PLANE.md)](CDB_AGENT_CONTROL_PLANE.md) — **Canonical** ACP architecture, authority matrix, lifecycle (`#4250`; Owner-ratified 2026-08-01 at `c691a8d0`); distinct from `.github` Workflow Control Plane
*   Agent Execution Contract v1 — [`docs/contracts/agent_execution/CDB_AGENT_EXECUTION_CONTRACT_V1.md`](../../docs/contracts/agent_execution/CDB_AGENT_EXECUTION_CONTRACT_V1.md) (`cdb.agent_execution.v1`, `#4251`)
*   Agent Registry v1 — [`docs/contracts/agent_registry/CDB_AGENT_REGISTRY_V1.md`](../../docs/contracts/agent_registry/CDB_AGENT_REGISTRY_V1.md) + [`config/agent-control/`](../../config/agent-control/README.md) (`cdb.agent_registry.v1`, `#4252`)
*   Agent Dispatch v1 — [`docs/contracts/agent_dispatch/CDB_AGENT_DISPATCH_V1.md`](../../docs/contracts/agent_dispatch/CDB_AGENT_DISPATCH_V1.md) (`cdb.agent_dispatch_run.v1`, `#4253`)
*   [CDB Trust Score Policy (CDB_TRUST_SCORE_POLICY.md)](CDB_TRUST_SCORE_POLICY.md)
*   [ARVP Product Intent (ARVP_PRODUCT_INTENT.md)](ARVP_PRODUCT_INTENT.md) — north-star anchor for accelerated replay paper-mode platform

## SSOT boundary
Governance policies do not override Live-Readiness verdicts. LR **NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
