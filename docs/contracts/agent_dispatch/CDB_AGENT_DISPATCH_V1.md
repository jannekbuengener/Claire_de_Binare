# CDB Agent Dispatch v1

Status: Canonical (engineering contract)  
Schema id: `cdb.agent_dispatch_run.v1`  
Issue: `#4253`  
Parent: `#4249`  
Predecessors: `#4250` (ACP), `#4251` (execution contract), `#4252` (registry)

## Purpose

Provider-neutral dispatcher with a strictly validated governed run state
machine. A run starts only from a digest-verified `cdb.agent_execution.v1`
contract and an enabled registry agent, within ratified ACP authority.

## Canon lifecycle (ACP §5)

States and transitions are exactly those in
`knowledge/governance/CDB_AGENT_CONTROL_PLANE.md` §5.

Issue `#4253` labels mapped as **events**, not extra states:

| Issue label | Representation |
| --- | --- |
| `VALIDATED` | `validation_success` event → state `CONTRACTED` |
| `EVIDENCE_COLLECTED` | lifecycle snapshot event only |
| `HANDED_OFF` | handoff event after `DELIVERED`→`PASS`/`HOLD` |

## CLI

```bash
python -m tools.agent_control dispatch --contract <PATH> --registry <PATH> \
  --agent-id <ID> --state <PATH> --dry-run
python -m tools.agent_control dispatch ... --execute --allow-mock-dispatch
python -m tools.agent_control watch --run-id <ID> --state <PATH>
python -m tools.agent_control cancel --run-id <ID> --state <PATH> --reason <TEXT>
python -m tools.agent_control retry --previous-run-id <ID> --contract <PATH> \
  --reason <TEXT> --state <PATH>
python -m tools.agent_control evidence --run-id <ID> --state <PATH>
```

`dispatch` defaults to dry-run (no provider calls, no state writes).
Live providers raise `PROVIDER_LIVE_DISPATCH_FORBIDDEN`.

## Authority

- Execution Contract + Registry ceilings are the maximum authority.
- Dispatcher does not route, approve, publish `cdb-local-ci`, or merge.
- Provider success ≠ `DELIVERED`/`PASS` without a validated delivery receipt.
- `evidence` returns a dispatcher lifecycle snapshot, **not** `#4256` Agent Run
  Evidence Bundle / JSONL store.

## Mock agent

Registry agent: `acp-mock-dispatcher` (`provider_profile: mock.v1`).
