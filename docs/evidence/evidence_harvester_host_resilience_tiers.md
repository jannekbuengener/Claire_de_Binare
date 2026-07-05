# Evidence Harvester Host-Resilience Tiers (#3733)

Status: Phase 1 scaffold merged — **no Tier-1 runtime proof in this slice**.
LR remains **NO-GO**. No Live-Go, no Echtgeld-Go.

Parent issue [#3345](https://github.com/jannekbuengener/Claire_de_Binare/issues/3345)
remains **OPEN** (`HOLD_3345_DAEMON_BRIDGE_EVIDENCE_OPEN`) until
[#3733](https://github.com/jannekbuengener/Claire_de_Binare/issues/3733) delivers
Tier-1 proof **or** an accepted formal requirement downgrade.

Child [#3362](https://github.com/jannekbuengener/Claire_de_Binare/issues/3362) is
**CLOSED** — Slice-E `>=72h` PASS proves in-process coordinator continuity only,
not deployment-ready external auto-resume across all host events.

## Tier model

| Tier | Scenario | Phase 1 status | Proof requirement |
|------|----------|----------------|-------------------|
| **Tier 1** | Coordinator process killed during sleep window | Scaffold only | Controlled kill → external supervisor `RELAUNCH_RESUME` → `sleep_resumed` + continued cycles. Requires separate **Operator Runtime-GO**. |
| **Tier 2** | Shell / IDE close while detached coordinator runs | Covered by Slice-E pattern | Documented; no new proof required in #3733 Phase 1. |
| **Tier 3** | Host sleep / hibernate / reboot across evidence window | **Not proven** | Explicit limitation in Phase 1. Future path: Windows Task + boot readiness (#3733 Phase 2+ or separate Ops GO). |

## Phase 1 deliverables (engineering scaffold)

- `tools/evidence_harvester/supervisor.py`
  - `coordinator_pid.json` record + PID liveness probe
  - `supervision_state.json` durable poll/relaunch state
  - `plan-external`, `supervise-external`, `record-coordinator-pid` CLI
  - injectable subprocess resume launcher (fail-closed without `--explicit`)
- `scripts/evidence_harvester_supervisor.ps1` — safe default `plan`; execution requires `-Explicit`
- Unit tests under `tests/unit/tools/evidence_harvester/test_supervisor_external.py`

## Artifact contracts

### `coordinator_pid.json`

Written by `record-coordinator-pid` or external launcher after coordinator spawn.

| Field | Meaning |
|-------|---------|
| `schema_version` | `cdb.evidence_harvester.coordinator_pid.v1` |
| `run_id` | Must match `runner_state.json` `run_id` |
| `pid` | OS process id for liveness probe |
| `recorded_at_utc` | UTC timestamp |

Stale PID (`run_id` mismatch) is treated as dead for supervision decisions.

### `supervision_state.json`

Written during external supervision polls.

| Field | Meaning |
|-------|---------|
| `schema_version` | `cdb.evidence_harvester.supervision_state.v1` |
| `run_id` | Active run id |
| `artifact_dir` | Absolute artifact directory |
| `coordinator_pid` | Last known coordinator pid (nullable) |
| `poll_count` | Completed wait polls |
| `relaunch_count` | Resume relaunches performed |
| `last_decision` | Latest `decide_supervision` payload |
| `last_error` | Non-empty on stale PID or probe errors |
| `updated_at_utc` | UTC timestamp |

## Closure linkage

### #3733 closes when

- Tier-1 runtime proof artifacts exist under
  `artifacts/evidence_harvester/host_resilience_proof/<run_id>/`, **or**
- A formal downgrade ADR is merged and accepted by issue semantics.

Phase 1 alone does **not** close #3733.

### #3345 becomes closure-ready when

- #3733 is **CLOSED** with proof or accepted downgrade, and
- Parent reconcile criteria from PR #3734 remain satisfied.

## Safety boundaries

- Fixture/dry research only
- No Windows Task install in Phase 1
- No Docker / BLUE+RED / DB / MCP mutation
- No new `>=72h` coordinator run
- LR **NO-GO** unchanged

## References

- [`docs/runbooks/CDB_EVIDENCE_HARVESTER_OPS.md`](../runbooks/CDB_EVIDENCE_HARVESTER_OPS.md)
- [`tools/evidence_harvester/README.md`](../../tools/evidence_harvester/README.md)
- Slice-E PASS: `artifacts/evidence_harvester/72h_ops_validation/slice-e-20260701T204615Z/`
