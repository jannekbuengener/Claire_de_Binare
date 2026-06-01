---
relations:
  role: doc
  domain: agents
  upstream:
    - agents/AGENTS.md
    - governance/CDB_AGENT_POLICY.md
    - governance/CDB_TRUST_SCORE_POLICY.md
  downstream: []
  status: active
  tags: [opencode, agents, trust]
---

Context Brain default posture (read-only, conditional): [`knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](../../knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md); Brain Evidence Gate: [`agents/AGENTS.md`](../AGENTS.md) § Brain Evidence Gate.

# OpenCode Agents — Shared Contract

Gilt für **alle** OpenCode Agents (egal welcher Provider).

## Pflicht
- `agent_id` Format: `OPENCODE/<agent-name>`
- `provider`: `opencode`
- Decision Events nach `knowledge/agent_trust/ledger/`
- Unsicherheit markieren statt durchentscheiden

## Nicht verhandelbar
- Canon-Governance ist read-only
- Delivery-Gate / Tresor-Regeln gelten identisch
