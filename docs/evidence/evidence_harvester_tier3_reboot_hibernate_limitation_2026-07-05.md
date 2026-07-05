# Evidence Harvester Tier-3 Reboot/Hibernate Limitation (2026-07-05)

Status: **LIMITATION** — explicit documented gap for [#3738](https://github.com/jannekbuengener/Claire_de_Binare/issues/3738).
LR remains **NO-GO**. No Live-Go, no Echtgeld-Go.

## Summary

| Host event | Status | Evidence |
|------------|--------|----------|
| **Process kill during sleep** | **PASS** (Tier 1) | `tier1-retry-20260705T111436Z` / #3733 CLOSED |
| **In-process coordinator sleep/wake** | **PASS** | Slice-E 72h + tier3 bounded run |
| **OS sleep (S3/Modern Standby)** | **LIMITATION** | Not proven across host event; agent-session constraint |
| **Hibernate** | **LIMITATION** | Not executed; higher recovery risk |
| **Reboot** | **LIMITATION** | No ATLOGON/ONSTART task for coordinator+supervisor |

## Engineering gaps

1. **Scheduler scope (#3348 / GO-1 PASS):** Windows Task is `DAILY` → `run-once-fixture`
   (fixture snapshot). It does **not** autostart coordinator+supervisor daemon.
2. **No startup task:** Repo has no `ATLOGON`/`ONSTART` schtasks wiring for external
   supervisor + coordinator resume after reboot.
3. **Reboot proof would require:** either new startup-task engineering or operator-manual
   relaunch post-reboot — out of bounded #3738 smoke scope.

## Accepted mitigation (canon)

- Tier-1 external supervisor proves dead-process relaunch during sleep window.
- Scheduler deployment smoke PASS (`scheduler-20260705T114504Z`) proves install/run/uninstall
  for daily fixture path + boot readiness PASS.
- Tier-3 host sleep/reboot/hibernate: **documented limitation** satisfies #3738 acceptance
  (same OR-pattern as #3733 Tier-3 limitation within #3733 closure).

## Operator handoff (if always-on daemon desired later)

1. `python -m tools.evidence_harvester.boot render-operator-handoff`
2. Separate scope: ATLOGON/startup task for `supervise-external` + coordinator
3. Separate Runtime-GO for reboot validation with operator-present session

## References

- [`evidence_harvester_host_resilience_tiers.md`](evidence_harvester_host_resilience_tiers.md)
- [`host_resilience_proof/scheduler-20260705T114504Z/proof_summary.md`](host_resilience_proof/scheduler-20260705T114504Z/proof_summary.md)
- [`host_resilience_proof/tier3-sleep-20260705T114800Z/proof_summary.md`](host_resilience_proof/tier3-sleep-20260705T114800Z/proof_summary.md)
- #3733 Tier-1 PASS: [`evidence_harvester_tier1_supervisor_proof_2026-07-05.md`](evidence_harvester_tier1_supervisor_proof_2026-07-05.md)
