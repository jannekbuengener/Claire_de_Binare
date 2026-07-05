# Evidence Harvester Scheduler Deployment Proof (#3738 GO-1)

Status: **PASS** — closes scheduler deployment-ready validation slice for #3738.
LR **NO-GO**.

## Run summary

| Field | Value |
|-------|-------|
| run_id | `scheduler-20260705T114504Z` |
| main_sha | `41ca6ba4` |
| boot preflight/status | **PASS** (21/21) |
| scheduler install/uninstall | **PASS** |
| schtasks manual run | **PASS** |
| proof_verdict | **PASS** |

## Install fix

First attempt failed: schtasks `/TR` > 261 chars. Fixed via `run_task.cmd` short-path
launcher in `tools/evidence_harvester/scheduler.py`.

## Compact artifacts

- [`host_resilience_proof/scheduler-20260705T114504Z/proof_result.json`](host_resilience_proof/scheduler-20260705T114504Z/proof_result.json)
- [`host_resilience_proof/scheduler-20260705T114504Z/proof_summary.md`](host_resilience_proof/scheduler-20260705T114504Z/proof_summary.md)
