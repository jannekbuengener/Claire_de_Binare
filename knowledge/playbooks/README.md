# Playbooks (`knowledge/playbooks/`)

Step-by-step operator/engineering playbooks (golden paths, DB, Redis, E2E, risk, agents).

## Start here

- [`00_INDEX.md`](00_INDEX.md) — playbook catalog

## Examples

| Playbook | Topic |
|---|---|
| [`01_STACK_GOLDEN_PATH.md`](01_STACK_GOLDEN_PATH.md) | Stack bring-up |
| [`03_DB_MIGRATIONS_AND_INIT.md`](03_DB_MIGRATIONS_AND_INIT.md) | DB migrations |
| [`06_DETERMINISTIC_REPLAY.md`](06_DETERMINISTIC_REPLAY.md) | Replay |
| [`07_RISK_GUARDS_DRAWDOWN_BREAKER.md`](07_RISK_GUARDS_DRAWDOWN_BREAKER.md) | Risk guards |
| [`10_AUTOPILOT_AGENT_OPERATIONS.md`](10_AUTOPILOT_AGENT_OPERATIONS.md) | Agent ops |

## vs other runbook trees

| Tree | Use when |
|---|---|
| [`knowledge/runbooks/`](../runbooks/) | Knowledge-side runbooks (overlap with playbooks — prefer one home for new content) |
| [`docs/runbooks/`](../../docs/runbooks/) | Control plane, GitHub, SurrealDB MCP operator paths |
| [`knowledge/operating_rules/`](../operating_rules/) | Standing operating rules |

## SSOT boundary

Playbooks guide procedure; LR remains **NO-GO** for live capital unless LR SSOT changes.
