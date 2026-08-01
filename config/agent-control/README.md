# Agent Control Configuration (`config/agent-control/`)

Declarative **Desired State** for the CDB Agent Control Plane registry
(Issue `#4252`).

Repository configuration is the Desired State. The Agent Execution Contract
(`cdb.agent_execution.v1`) remains the authority ceiling. Registry entries may
only reduce permissions; they never invent merge, Live-Go, or mutation rights.

## Layout

| Path | Role |
| --- | --- |
| `agents/registry.v1.yaml` | Desired agent entries |
| `profiles/execution_contracts/` | Permission ceilings |
| `profiles/providers/` | Provider profiles (mock/cursor/local) |
| `profiles/environments/` | Environment profiles |
| `profiles/skills/` | Skill pack profiles |
| `profiles/mcp/` | MCP profiles (`mutation_allowed` must be false here) |
| `policies/` | Future overlays (unused in `#4252`) |
| `capability-baselines/` | Future capability inventory hooks |

## CLI (zero-click / no dashboard)

```bash
python -m tools.agent_control registry validate --config config/agent-control
python -m tools.agent_control registry plan --config config/agent-control --state <STATE>
python -m tools.agent_control registry reconcile --config config/agent-control --dry-run
```

`reconcile` defaults to dry-run. Live provider create/update/delete is forbidden
in this slice. Mock apply is test-only (`--apply --allow-mock-apply`).

## Schema

Canonical JSON Schema:
[`docs/contracts/cdb_agent_registry.v1.schema.json`](../../docs/contracts/cdb_agent_registry.v1.schema.json)

Spec:
[`docs/contracts/agent_registry/CDB_AGENT_REGISTRY_V1.md`](../../docs/contracts/agent_registry/CDB_AGENT_REGISTRY_V1.md)

## Safety

- LR remains **NO-GO**
- No plaintext secrets (use `env:` / `secret:` references only)
- No dispatcher (`#4253`) and no Cursor adapter (`#4254`) in this tree
