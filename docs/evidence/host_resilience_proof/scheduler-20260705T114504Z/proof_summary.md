# Scheduler deployment smoke PASS (#3738 GO-1)

- run_id: scheduler-20260705T114504Z
- main_sha: 41ca6ba4
- Runtime-GO: RUNTIME-GO #3738 Scheduler Deployment Smoke
- boot preflight/status: **PASS** (21/21)
- scheduler install: **PASS** (via `run_task.cmd` short-path `/TR`)
- schtasks /Run: **PASS** (snapshot `20260705T114617.635900Z`)
- scheduler uninstall: **PASS**
- proof_verdict: **PASS**
- LR NO-GO unchanged

## Install fix

First attempt failed: schtasks `/TR` exceeded 261 chars. Fixed in `scheduler.py` by writing
`artifacts/evidence_harvester/scheduled/run_task.cmd` and passing its path to `/TR`.
