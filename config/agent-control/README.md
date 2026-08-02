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
| `profiles/providers/` | Provider profiles (`mock`, `cursor-sdk`, `cursor-cli`, `cursor-cloud-api`, legacy `cursor`) |
| `profiles/environments/` | Environment profiles |
| `profiles/skills/` | Skill pack profiles |
| `profiles/mcp/` | MCP profiles (`mutation_allowed` must be false here) |
| `policies/` | Future overlays (unused in `#4252`) |
| `capability-baselines/` | Offline capability baseline hooks (`#4254`) |

## CLI (zero-click / no dashboard)

```bash
python -m tools.agent_control registry validate --config config/agent-control
python -m tools.agent_control registry plan --config config/agent-control --state <STATE>
python -m tools.agent_control registry reconcile --config config/agent-control --dry-run
python -m tools.agent_control dispatch --contract <PATH> --registry config/agent-control \
  --agent-id acp-mock-dispatcher --dry-run
python -m tools.agent_control dispatch ... --state <RUNSTORE> --execute --allow-mock-dispatch
python -m tools.agent_control provider capabilities --provider cursor-sdk --offline
python -m tools.agent_control provider capabilities --provider cursor-cli --offline
python -m tools.agent_control provider capabilities --provider cursor-cloud-api --offline
python -m tools.agent_control environment validate --config config/agent-control
python -m tools.agent_control environment doctor --profile cdb-agent-skills.v1 \
  --config config/agent-control --offline
```

`reconcile` / `dispatch` default to dry-run. Live provider create/update/delete
and live Cursor dispatch are forbidden. Mock execute is test-only
(`--execute --allow-mock-dispatch`). Cursor adapters are constructible offline /
with injected fake transports only. Registry agents:
`acp-mock-dispatcher` (`#4253`), `acp-cursor-sdk-adapter` (`#4254`/`#4255`,
`live_dispatch: false`, environment `cdb-agent-skills.v1`).

Governed environment profiles (`#4255`):
`cdb-docs-readonly.v1`, `cdb-agent-skills.v1`, `cdb-python-fast.v1`,
`cdb-ci-debug.v1`, `cdb-validation-research.v1`,
`cdb-runtime-risk-restricted.v1`. Cursor config: `.cursor/environment.json`.
Evidence bundle remains `#4256`; approval `#4257`; live pilot `#4258`.

## Schema

Canonical JSON Schema:
[`docs/contracts/cdb_agent_registry.v1.schema.json`](../../docs/contracts/cdb_agent_registry.v1.schema.json)

Spec:
[`docs/contracts/agent_registry/CDB_AGENT_REGISTRY_V1.md`](../../docs/contracts/agent_registry/CDB_AGENT_REGISTRY_V1.md)

## Safety

- LR remains **NO-GO**
- No plaintext secrets (use `env:` / `secret:` references only)
- Cursor API key is `MANUAL_BOOTSTRAP_ONLY` (`env:CURSOR_API_KEY`); never read
  during dry-run / offline capability probes / environment doctor
- Environment profiles + doctor: `#4255`; evidence bundle `#4256`; approval `#4257`
