# CDB Agent Control Pilot Report v1

Status: Canonical (foundation slice `#4258`)  
Schema id: `cdb.agent_control_pilot_report.v1`  
Schema: [`../cdb_agent_control_pilot_report.v1.schema.json`](../cdb_agent_control_pilot_report.v1.schema.json)  
Manifest schema: [`../cdb_agent_control_pilot_manifest.v1.schema.json`](../cdb_agent_control_pilot_manifest.v1.schema.json)

## Purpose

Orchestration envelope for the **mock-first ACP E2E foundation pilot**.
It references digests and step results from existing ACP layers and does **not**
create a second Run-Evidence truth.

## Scope boundary

- Foundation slice proves Contract → Registry → Dispatch → Environment →
  MockProvider → Run Evidence → Approval Context wiring.
- Live Cursor path (Human-GO `--provider cursor-cloud-api --human-go-live-cursor`)
  extends the same report envelope; default remains mock.
- It does **not** close Issue `#4258` until a real cloud delivery + CDB approval
  handoff is evidenced (use `Refs #4258`, never premature `Closes #4258`).
- Cursor Dashboard Approval Agents remain `MANUAL_BOOTSTRAP_ONLY` (no API handoff).
- Operator runbook: [`docs/runbooks/agent_control_live_cursor_pilot.md`](../../runbooks/agent_control_live_cursor_pilot.md).

## Head-SHA binding

Canonical pilot head binding lives in:

1. Pilot manifest / report (`head_sha` / `subject.head_sha`)
2. Approval context (`subject.head_sha`)

`cdb.agent_run_evidence.v1` is consumed **as-is** without schema expansion for
`head_sha`.

## Authority limits

All hardcoded `false`: merge, publish_cdb_local_ci, modify_branch_protection,
modify_rulesets, execute_live_agent, live_go, real_money_go, close_issue.

## Final status

`PASS` | `HOLD` | `BLOCKED` | `FAIL` | `UNKNOWN`

`UNKNOWN` never becomes `PASS`.

## CLI

```bash
python -m tools.agent_control pilot run --manifest <PATH> [--out <REPORT>]
python -m tools.agent_control pilot verify --report <PATH>
```

## Safety

- LR remains **NO-GO**
- MockProvider only; no live Cursor
- No GitHub writes from the pilot harness
- No secrets in fixtures or reports
