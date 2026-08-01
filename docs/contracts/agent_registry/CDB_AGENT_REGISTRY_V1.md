# CDB Agent Registry v1

Status: Canonical (engineering contract)  
Schema id: `cdb.agent_registry.v1`  
Schema version: `1.0.0`  
Issue: `#4252`  
Parent: `#4249`  
Predecessors: `#4250` (ACP Canon), `#4251` (`cdb.agent_execution.v1`)

## Purpose

Provider-neutral, declarative **Desired State** for governed agents plus a
deterministic reconciler that plans create/update/disable/noop/block against an
observed local state. Configuration and validation are fully repository- and
CLI-driven. No dashboard click path is required.

## Authority

1. Binding governance and ratified ACP remain above this registry.
2. `cdb.agent_execution.v1` remains the execution-authority ceiling.
3. Registry entries **must not** expand Execution Contract permissions.
4. Unknown fields, duplicate IDs, invalid references, plaintext secrets, and
   cyclic dependencies are rejected fail-closed.
5. An invalid registry blocks the entire plan — no partial application.

## Desired-state location

Canonical example / operator config:

- `config/agent-control/agents/registry.v1.yaml`
- `config/agent-control/profiles/**`

Self-contained fixtures (tests/examples) may inline `profiles` in one document.

## Minimum agent fields

- `agent_id`
- `version`
- `enabled`
- `description`
- `execution_contract_profile`
- `provider_profile`
- `environment_profile`
- `skills`
- `mcp_profiles`
- `subagents`
- `labels_or_routing_selectors`

Optional: `depends_on`, `permission_overrides` (attenuation only).

## CLI

```bash
python -m tools.agent_control registry validate --config <PATH>
python -m tools.agent_control registry plan --config <PATH> --state <PATH>
python -m tools.agent_control registry reconcile --config <PATH> --dry-run
```

`<PATH>` may be a single registry document or the `config/agent-control` root.

## Reconciler

| Behavior | Rule |
| --- | --- |
| Default mode | `dry-run` |
| Observed state | Read only via a bounded backend interface |
| Plan ops | `create` / `update` / `disable` / `noop` / `block` |
| Stability | Identical inputs → byte-identical plan JSON (`plan_digest`) |
| Disabled desired | Never `create`/`update`; only `noop` or `disable` |
| Invalid registry | Single `block` plan; no partial ops |
| Live providers | Forbidden in `#4252` (mock only) |

## Non-goals

- Dispatcher / state machine (`#4253`)
- Cursor provider adapter (`#4254`)
- Environment provisioning (`#4255`)
- Run evidence (`#4256`)
- Approval agent (`#4257`)
- Live provider mutations, UI automation, private APIs
- Merge / `cdb-local-ci` publish / issue close

## Safety

LR remains **NO-GO**. Secrets only as `env:` / `secret:` references.
