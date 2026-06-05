# Knowledge Runbooks (`knowledge/runbooks/`)

Knowledge-tree runbooks (stack, DB, replay, control board). For GitHub/control-plane automation see [`docs/runbooks/`](../../docs/runbooks/).

## Start here

- [`00_INDEX.md`](00_INDEX.md)
- [`CDB_CONTROL_BOARD_RUNBOOK.md`](CDB_CONTROL_BOARD_RUNBOOK.md) — board/stage mapping

## Examples

| File | Topic |
|---|---|
| [`01_CANONICAL_GOLDEN_STATE.md`](01_CANONICAL_GOLDEN_STATE.md) | Golden state |
| [`04_E2E_SHIELD_AND_CI.md`](04_E2E_SHIELD_AND_CI.md) | E2E + CI |
| [`GRAFANA_ADMIN_INCIDENT.md`](GRAFANA_ADMIN_INCIDENT.md) | Grafana incident (local stack) |

## vs `docs/runbooks/`

| Location | Primary focus |
|---|---|
| `docs/runbooks/` | CONTROL_REGISTER, GitHub workflows, SurrealDB MCP operator, merge policy |
| `knowledge/runbooks/` | Engineering playbooks mirrored in knowledge tree |

Avoid duplicating the same procedure in both trees; cross-link instead.

## SSOT boundary

Board stage: [`docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md). LR **NO-GO**.
