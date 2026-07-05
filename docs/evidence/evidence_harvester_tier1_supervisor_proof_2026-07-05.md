# Evidence Harvester Tier-1 External Supervisor Proof (2026-07-05)

Status: **PASS** — closes [#3733](https://github.com/jannekbuengener/Claire_de_Binare/issues/3733)
Tier-1 scope. LR remains **NO-GO**. No Live-Go, no Echtgeld-Go.

Parent [#3345](https://github.com/jannekbuengener/Claire_de_Binare/issues/3345) stays **OPEN**
(Tier 3 host sleep/hibernate/reboot not proven; deployment-ready always-on daemon not
fully closed).

## Run summary

| Field | Value |
|-------|-------|
| run_id | `tier1-retry-20260705T111436Z` |
| main_sha | `2b007240` (PR [#3736](https://github.com/jannekbuengener/Claire_de_Binare/pull/3736)) |
| Runtime-GO | `RUNTIME-GO #3733 Tier-1 Proof` |
| cadence_seconds | 120 |
| killed_pid | 21760 @ `2026-07-05T11:15:10Z` (cycle-1 sleep) |
| supervisor_relaunch_pid | 13516 @ `2026-07-05T11:16:52Z` |
| `run_resumed` | `2026-07-05T11:16:53.449Z` (supervisor subprocess) |
| `relaunch_count` | 1 |
| post-resume cycle | 2 **PASS** |
| proof_verdict | **PASS** |

## Prior FAIL (superseded)

First attempt `tier1-20260705T104800Z` **FAIL**: stall detection and `relaunch_count=1`
worked; Windows subprocess resume did not emit `run_resumed` until PR #3736 detached
`Popen` hardening.

## Versioned compact artifacts

Repo-canonical summaries (no local-only logs):

- [`host_resilience_proof/tier1-retry-20260705T111436Z/proof_result.json`](host_resilience_proof/tier1-retry-20260705T111436Z/proof_result.json)
- [`host_resilience_proof/tier1-retry-20260705T111436Z/proof_summary.md`](host_resilience_proof/tier1-retry-20260705T111436Z/proof_summary.md)
- [`host_resilience_proof/tier1-retry-20260705T111436Z/resume_launch_evidence.jsonl`](host_resilience_proof/tier1-retry-20260705T111436Z/resume_launch_evidence.jsonl)

Full runtime tree (local operator): `artifacts/evidence_harvester/host_resilience_proof/tier1-retry-20260705T111436Z/`

## Tier model outcome

| Tier | Result |
|------|--------|
| **Tier 1** (process kill during sleep) | **PASS** — external `supervise-external` relaunch + `run_resumed` + continued cycles |
| **Tier 2** (shell/IDE close) | Documented via Slice-E pattern; no separate proof in #3733 |
| **Tier 3** (host sleep/hibernate/reboot) | **Not proven** — explicit limitation; future Ops GO / Windows Task scope |

## Closure linkage

- **#3733:** CLOSED — Tier-1 proof + Tier-3 limitation documented (issue acceptance:
  host-resilience proof **or** documented limitation with evidence).
- **#3345:** OPEN — parent daemon/deployment bridge; Tier 3 + scheduler install remain.

## References

- [`evidence_harvester_host_resilience_tiers.md`](evidence_harvester_host_resilience_tiers.md)
- [`docs/runbooks/CDB_EVIDENCE_HARVESTER_OPS.md`](../runbooks/CDB_EVIDENCE_HARVESTER_OPS.md)
- GitHub: [#3733#issuecomment-4885817835](https://github.com/jannekbuengener/Claire_de_Binare/issues/3733#issuecomment-4885817835)
