# Architecture Decisions (`knowledge/decisions/`)

Recorded decisions (ADR-style) for governance, context/MCP posture, and infrastructure choices.

## Active decisions (examples)

| File | Topic |
|---|---|
| [`CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md) | Brain evidence default (#2775) |
| [`CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md`](CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md) | Managed runtime (not activated) |
| [`CDB_CONTROLLED_WRITE_STRATEGY_V2_DESIGN.md`](CDB_CONTROLLED_WRITE_STRATEGY_V2_DESIGN.md) | Write strategy design only |
| [`K8S_BUDGET_DECISION.md`](K8S_BUDGET_DECISION.md) | Kubernetes GO/NO-GO |
| [`ADR-001-documentation-only-repository.md`](ADR-001-documentation-only-repository.md) | Docs-only repo pattern |

## Where to write

- New **decisions** with durable rationale → this directory (dated filename or ADR-NNN).
- **Operational runbooks** → [`knowledge/runbooks/`](../runbooks/) or [`docs/runbooks/`](../../docs/runbooks/) per topic.
- **Status** → `CURRENT_STATUS.md` / LR SSOT — not in decision files alone.

## SSOT boundary

Decisions document intent and gates; they do not override LR **NO-GO** without explicit human live approval.
