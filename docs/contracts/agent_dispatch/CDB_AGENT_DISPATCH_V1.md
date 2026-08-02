# CDB Agent Dispatch v1

Status: Canonical (engineering contract)
Schema id: `cdb.agent_dispatch_run.v1`
Issue: `#4253` (dispatcher) / `#4254` (Cursor providers)
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
python -m tools.agent_control provider capabilities --provider cursor-sdk --offline
python -m tools.agent_control watch --run-id <ID> --state <PATH>
python -m tools.agent_control cancel --run-id <ID> --state <PATH> --reason <TEXT>
python -m tools.agent_control retry --previous-run-id <ID> --contract <PATH> \
  --reason <TEXT> --state <PATH>
python -m tools.agent_control evidence --run-id <ID> --state <PATH>
python -m tools.agent_control evidence snapshot --run <ID> --state <PATH>
python -m tools.agent_control evidence emit --run <ID> --state <PATH> [--store <JSONL>]
python -m tools.agent_control evidence verify --bundle <PATH>
python -m tools.agent_control evidence verify --store <JSONL>
python -m tools.agent_control evidence show --run <ID> --store <JSONL>
```

`dispatch` defaults to dry-run (no provider calls, no state writes).
Live Cursor dispatch remains fail-closed (`PROVIDER_LIVE_DISPATCH_FORBIDDEN` /
`ENVIRONMENT_LIVE_DISPATCH_FORBIDDEN`). Environment preflight (#4255) never
enables live dispatch. Recorded/fake transports are test-only and require a
`READY_FOR_RECORDED_TEST` attestation fixture.

## Authority

- Execution Contract + Registry ceilings are the maximum authority.
- Dispatcher does not route, approve, publish `cdb-local-ci`, or merge.
- Provider success ≠ `DELIVERED`/`PASS` without a validated delivery receipt.
- `evidence snapshot` / legacy `evidence --run-id` returns a dispatcher
  lifecycle snapshot, **not** `#4256` Agent Run Evidence Bundle / JSONL store.
- `evidence emit` / `evidence --run` produces `cdb.agent_run_evidence.v1`
  (see [`../agent_run_evidence/CDB_AGENT_RUN_EVIDENCE_V1.md`](../agent_run_evidence/CDB_AGENT_RUN_EVIDENCE_V1.md)).

## Providers

| provider_id | Driver | Notes |
| --- | --- | --- |
| `mock` | `MockProvider` | `#4253` in-process only |
| `cursor-sdk` | `CursorSdkDriver` | Primary Python surface; optional `cursor-sdk` dep |
| `cursor-cli` | `CursorCliDriver` | Headless `--print` / `stream-json`; no `--force` |
| `cursor-cloud-api` | `CursorCloudApiDriver` | Public Cloud Agents API v1; no DELETE |

Registry agents: `acp-mock-dispatcher` (`mock.v1`), `acp-cursor-sdk-adapter`
(`cursor-sdk.v1`, `live_dispatch: false`).
