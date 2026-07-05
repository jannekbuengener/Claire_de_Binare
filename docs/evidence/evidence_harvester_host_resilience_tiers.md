# Evidence Harvester Host-Resilience Tiers (#3733)

Status: **#3733 CLOSED** — Tier-1 external supervisor proof **PASS**
(`tier1-retry-20260705T111436Z`, main @ `2b007240`). Tier 3 (host sleep/hibernate/reboot)
remains **not proven** — explicit limitation.

LR remains **NO-GO**. No Live-Go, no Echtgeld-Go.

Parent issue [#3345](https://github.com/jannekbuengener/Claire_de_Binare/issues/3345)
remains **OPEN** — deployment-ready always-on daemon and Tier-3 host events are parent
residual scope, not #3733 closure blockers.

Child [#3362](https://github.com/jannekbuengener/Claire_de_Binare/issues/3362) is
**CLOSED** — Slice-E `>=72h` PASS proves in-process coordinator continuity only,
not deployment-ready external auto-resume across all host events.

Canonical Tier-1 evidence:
[`evidence_harvester_tier1_supervisor_proof_2026-07-05.md`](evidence_harvester_tier1_supervisor_proof_2026-07-05.md)

## Tier model

| Tier | Scenario | Status | Proof requirement |
|------|----------|--------|-------------------|
| **Tier 1** | Coordinator process killed during sleep window | **PASS** (`tier1-retry-20260705T111436Z`) | Controlled kill → external supervisor `RELAUNCH_RESUME` → `run_resumed` + continued cycles. First attempt `tier1-20260705T104800Z` **FAIL**; fixed in PR #3736; retry PASS under Operator Runtime-GO. |
| **Tier 2** | Shell / IDE close while detached coordinator runs | Covered by Slice-E pattern | Documented; no separate proof required in #3733. |
| **Tier 3** | Host sleep / hibernate / reboot across evidence window | **Not proven** | Explicit limitation. Future path: Windows Task + boot readiness under separate Ops GO / #3345 parent scope. |

## Engineering deliverables (merged)

- `tools/evidence_harvester/supervisor.py`
  - `coordinator_pid.json` record + PID liveness probe
  - `supervision_state.json` durable poll/relaunch state
  - `plan-external`, `supervise-external`, `record-coordinator-pid` CLI
  - injectable subprocess resume launcher (fail-closed without `--explicit`)
- Windows-hardened detached resume `Popen` (PR #3736) + `resume_launch_evidence.jsonl` per relaunch
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

### `resume_launch_evidence.jsonl`

Append-only relaunch audit (PR #3736): argv, cwd, pid, immediate exit, launch_error.

## Closure linkage

### #3733 — CLOSED

Tier-1 runtime proof PASS + Tier-3 documented limitation satisfies issue acceptance
(host-resilience proof **or** documented limitation with evidence).

### #3345 — still OPEN

Tier-1 external supervisor proof delivered; parent still tracks deployment-ready
always-on daemon, Tier-3 host events, and evidence-bridge follow-ups ([#3382](https://github.com/jannekbuengener/Claire_de_Binare/issues/3382) etc.).

## Safety boundaries

- Fixture/dry research only
- No Windows Task install in Tier-1 proof slice
- No Docker / BLUE+RED / DB / MCP mutation
- No new `>=72h` coordinator run in #3733
- LR **NO-GO** unchanged

## References

- [`docs/evidence/evidence_harvester_tier1_supervisor_proof_2026-07-05.md`](evidence_harvester_tier1_supervisor_proof_2026-07-05.md)
- [`docs/runbooks/CDB_EVIDENCE_HARVESTER_OPS.md`](../runbooks/CDB_EVIDENCE_HARVESTER_OPS.md)
- [`tools/evidence_harvester/README.md`](../../tools/evidence_harvester/README.md)
- Slice-E PASS: `artifacts/evidence_harvester/72h_ops_validation/slice-e-20260701T204615Z/`
- Tier-1 PASS compact artifacts: `docs/evidence/host_resilience_proof/tier1-retry-20260705T111436Z/`
