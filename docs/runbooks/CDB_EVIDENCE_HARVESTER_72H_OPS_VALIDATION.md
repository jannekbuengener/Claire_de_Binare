# CDB Evidence Harvester - 72h Ops Validation Runbook

## Purpose

Validate the real always-on `>=72h` dry operation for the Evidence Harvester
without granting any live, Echtgeld, trading, runtime, or infrastructure GO.

This runbook defines the final validation tooling for Issue
[#3362](https://github.com/jannekbuengener/Claire_de_Binare/issues/3362). The
tooling is implemented in `tools/evidence_harvester/ops_validation.py` and is
used only after the real dry run finishes.

## Preconditions

- Child slices [#3358](https://github.com/jannekbuengener/Claire_de_Binare/issues/3358), [#3359](https://github.com/jannekbuengener/Claire_de_Binare/issues/3359), [#3360](https://github.com/jannekbuengener/Claire_de_Binare/issues/3360), and [#3361](https://github.com/jannekbuengener/Claire_de_Binare/issues/3361) are merged.
- `tools/evidence_harvester/ops_validation.py` is on `main`.
- The real run has already written artifacts to one dedicated runtime directory.
- LR remains `NO-GO`.

## Safety State

| Check | Expected |
|---|---|
| LR status | `NO-GO` |
| Live status | `NO-GO` |
| Echtgeld status | `NO-GO` |
| Runtime actions | `not_allowed` |
| DB execution | `not_allowed` |
| Source mode | `fixture` or `future_readonly` |
| GitHub writes from module code | forbidden |

## Phase-2 Runtime Contract

- Seed fixture: `artifacts/evidence_harvester/24h_dry_run/collector_input.json`
- Artifact dir: `artifacts/evidence_harvester/72h_ops_validation/<run_id>/`
- Runner cadence: every `900` seconds / `15` minutes
- Watchdog: after each runner cycle
- Write-audit: after each runner cycle
- Final validation: after `>=72h` over the whole artifact directory

## Required Artifacts

- `collector_report_<stamp>.json`
- `snapshot_<stamp>.json`
- `snapshot_<stamp>.md`
- `alert_<stamp>.json`
- `alert_<stamp>.md`
- `coordinator_events.jsonl`
- `runner_heartbeat.json`
- `runner_state.json`
- `watchdog_report_<stamp>.json`
- `watchdog_report_<stamp>.md`
- `write_audit_report_<stamp>.json`
- `write_audit_report_<stamp>.md`
- `boot_readiness_report.json`
- `boot_readiness_report.md`
- `ops_validation_report.json`
- `ops_validation_report.md`

## Validation Contract

### PASS

- `>=72h` window covered
- runner continuity evidenced by heartbeat/state counters, coordinator lifecycle telemetry, and stamped cadence history
- lifecycle cycle count consistent with `runner_state.total_cycles_completed` and artifact snapshot count
- watchdog history PASS or justified WARN; `coordinator_liveness` must not be FATAL_STOP or STALE_NEXT_CYCLE
- write-audit history PASS with no FAIL findings
- boot-readiness PASS or justified WARN
- no side effects

### INCONCLUSIVE (FAIL with classification)

A run that ended before the required window but with all-PASS cycles and
no final validation marker receives a dedicated `INCONCLUSIVE` finding.
Example: Slice-B (68.5h, 259/259 PASS cycles, 0 failures, crashed during
sleep). Partial evidence is preserved but does not satisfy the `>=72h`
requirement. The run is marked FAIL with an `INCONCLUSIVE` explanation so
it is never confused with a clean PASS or a cycle-failure FAIL.

### WARN

- minor cadence drift
- documented non-critical boot warning
- documented non-critical watchdog warning
- missing lifecycle telemetry (non-final validation only, `--no-final`)

### FAIL

- window shorter than required (includes INCONCLUSIVE classification)
- missing or malformed required artifacts
- write-audit FAIL
- watchdog FAIL
- boot-readiness FAIL
- safety-flag violation
- forbidden live/echtgeld/trading content

## Validation Command

```powershell
python -m tools.evidence_harvester.ops_validation validate-dir ^
    --artifact-dir artifacts\evidence_harvester\72h_ops_validation\<run_id> ^
    --json-output artifacts\evidence_harvester\72h_ops_validation\<run_id>\ops_validation_report.json ^
    --markdown-output artifacts\evidence_harvester\72h_ops_validation\<run_id>\ops_validation_report.md ^
    --pretty

# Non-final validation (lifecycle telemetry WARN instead of FAIL):
python -m tools.evidence_harvester.ops_validation validate-dir ^
    --artifact-dir artifacts\evidence_harvester\72h_ops_validation\<run_id> ^
    --no-final --pretty
```

## Runtime Handoff

### Boot preflight

```powershell
python -m tools.evidence_harvester.boot status --pretty
python -m tools.evidence_harvester.boot status ^
    --json-output artifacts\evidence_harvester\72h_ops_validation\<run_id>\boot_readiness_report.json ^
    --markdown-output artifacts\evidence_harvester\72h_ops_validation\<run_id>\boot_readiness_report.md ^
    --pretty
```

### Optional scheduler enablement

Only under a separate Runtime-GO:

```powershell
python -m tools.evidence_harvester.scheduler install --fixture artifacts\evidence_harvester\24h_dry_run\collector_input.json --explicit
```

### 72h dry operation start

```powershell
python -m tools.evidence_harvester.runner loop-fixture ^
    --fixture artifacts\evidence_harvester\24h_dry_run\collector_input.json ^
    --output-dir artifacts\evidence_harvester\72h_ops_validation\<run_id> ^
    --iterations 289 ^
    --interval-seconds 900 ^
    --pretty
```

Operational note:

- After each runner cycle, write the latest `watchdog_report.json/.md` for
  `write_audit.py` compatibility and archive stamped copies as
  `watchdog_report_<stamp>.json/.md`.
- After each runner cycle, archive stamped write-audit outputs as
  `write_audit_report_<stamp>.json/.md`.

### Stop / disable

```powershell
python -m tools.evidence_harvester.ops_validation validate-dir --artifact-dir artifacts\evidence_harvester\72h_ops_validation\<run_id> --pretty
python -m tools.evidence_harvester.scheduler uninstall --explicit
```

## Side-Effect Checklist

- [ ] No Docker mutation without documented Infra-Mutation-Gate approval
- [ ] No runtime start beyond the dry runner loop itself
- [ ] No DB mutation
- [ ] No secrets output
- [ ] No GitHub writes from module code
- [ ] No LR-Go / Live-Go / Echtgeld-Go
- [ ] No trading / order / risk / execution mutation

## Operator Approval Checkpoint

Before any Docker or infrastructure mutation, stop and obtain a separate,
documented Jannek-Ops-GO / Infra-Mutation-Gate approval.

## Status Boundary

This runbook validates a dry/paper/research-only evidence run.
It does not change LR status.
LR remains `NO-GO`.

## References

- Parent issue: [#3345](https://github.com/jannekbuengener/Claire_de_Binare/issues/3345)
- Validation issue: [#3362](https://github.com/jannekbuengener/Claire_de_Binare/issues/3362)
- Runner: `tools/evidence_harvester/runner.py`
- Watchdog: `tools/evidence_harvester/watchdog.py`
- Write-audit: `tools/evidence_harvester/write_audit.py`
- Boot readiness: `tools/evidence_harvester/boot.py`
- Final validator: `tools/evidence_harvester/ops_validation.py`
