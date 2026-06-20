# Evidence Harvester to Profitability Evidence Packet Mapping

## Purpose

This document maps Evidence Harvester artifacts to the required fields of
`profitability_evidence_packet.v1` for issue #3380.

The mapping is intentionally conservative. It identifies which packet inputs can
be supported by the Evidence Harvester, which inputs require ARVP, Data Quality,
Execution Economics, or paper-reference producers, and which items remain
blocked until the active #3374 run has final validation evidence.

## Scope and Non-Goals

In scope:

- Map every required field from
  `docs/contracts/profitability_evidence_packet.v1.schema.json`.
- Inventory the Evidence Harvester artifacts that may be referenced by a future
  packet assembler.
- Separate Harvester health from Candidate Profitability Evidence.
- Mark #3374-dependent continuity evidence separately.
- Provide issue-ready follow-up gaps for #3381, #3383, #3362, and #3345.

Out of scope:

- No code implementation.
- No schema change.
- No test change.
- No runtime start, stop, or restart.
- No active #3374 artifact modification.
- No Docker, DB, Redis, secrets, or MCP mutation.
- No LR-Go, Live-Go, or Echtgeld-Go.
- No candidate promotion, recommendation execution, or capital allocation.

## Control State

| Surface | Current conservative state |
|---|---|
| Issue scope | #3380 docs-only mapping |
| Parent tracker | #3345 remains open |
| Continuous proof | #3362 remains open until final `>=72h` PASS evidence exists |
| Active retry | #3374 run `20260620T200144Z` is active and must not be touched |
| Board stage | `trade-capable`, ratified via #1492 |
| LR status | `NO-GO` |
| Live / Echtgeld | no Live-Go, no Echtgeld-Go |
| Runtime / DB / Docker | not in scope |
| Context Brain | repo-only fallback after low-trust/no-record context preflight |

Control interpretation:

- Board stage and LR status are separate systems.
- `trade-capable` is not Live-Go and not candidate-profitability proof.
- Harvester artifacts are evidence-supporting artifacts, not authority for
  strategy promotion.

## Harvester Boundary

Evidence Harvester proves evidence production, provenance, integrity,
continuity, and safety-boundary visibility.

Evidence Harvester does not prove candidate profitability.

Gross/net returns, trade metrics, execution economics, replay-vs-paper
alignment, simulator drift, and recommendations require other producers.

The active #3374 run must not be treated as final `>=72h` proof until final
validation exists.

Useful Harvester contributions:

- Source refs and artifact integrity.
- Operational continuity evidence.
- Provenance and gap findings.
- Safety flag visibility.
- Paper-chain coverage gap signals.
- Limitations and trust notes.

Harvester cannot produce:

- `gross_return`, `net_return`, `fees`, `spread_cost`, `slippage_cost`.
- `profit_factor`, `expectancy`, `win_rate`, `avg_win`, `avg_loss`,
  `max_drawdown`, `loss_streak`, or candidate `trade_count`.
- Candidate `scenario_results`.
- `replay_vs_paper_status` or `simulator_drift`.
- `risk_blocks` or `kill_switch_events`.
- Final packet `recommendation`.

## Candidate Profitability Evidence Packet v1 Contract

Contract source:
`docs/contracts/profitability_evidence_packet.v1.schema.json`.

The packet is a research evidence contract only. Its own description states that
evidence packets support comparison and review only; they do not authorize paper,
micro-live, live capital, runtime changes, or capital scaling.

Required packet field groups:

| Group | Fields |
|---|---|
| Packet identity | `schema_version`, `evidence_packet_id`, `candidate_id`, `generated_at` |
| Dataset identity | `dataset_id`, `dataset_fingerprint`, `source_run_refs` |
| Economics | `gross_return`, `net_return`, `fees`, `spread_cost`, `slippage_cost` |
| Trade statistics | `profit_factor`, `expectancy`, `win_rate`, `avg_win`, `avg_loss`, `max_drawdown`, `loss_streak`, `trade_count` |
| Robustness / scenarios | `regime_scorecard`, `scenario_results` |
| Paper / simulator comparison | `replay_vs_paper_status`, `simulator_drift` |
| Safety / controls | `risk_blocks`, `kill_switch_events`, `recommendation`, `limitations`, `safety_boundaries` |

Primary upstream contracts:

| Contract | Role |
|---|---|
| `profitability_candidate_contract.v1` | Candidate identity, research assumptions, unsafe zones, and allowed next gate |
| `profitability_dataset_quality_report.v1` | Dataset id, `sha256:<64>` fingerprint, coverage, and quality verdict |
| `profitability_arvp_batch_manifest.v1` | Candidate inputs, dataset selection, runner surfaces, evidence hooks |
| `profitability_execution_economics_model.v1` | Fee, spread, slippage, and net-economics model requirements |
| `profitability_execution_economics_assessment.v1` | Candidate-level gross-to-net assessment output |

## Harvester Artifact Inventory

| Artifact | Harvester role | PEP contribution | #3374 dependency |
|---|---|---|---|
| `runner_state.json` | Cumulative runner and coordinator state | Operational continuity ref; limitation/trust note | Final continuity proof remains blocked until #3374 final PASS |
| `runner_heartbeat.json` | Latest cycle metadata and artifact refs | Source refs for latest Harvester cycle; freshness context | Intermediate only until final validation |
| `coordinator_events.jsonl` | Canonical lifecycle event stream | Continuity timeline and lifecycle evidence | Required for final #3374 proof |
| `boot_readiness_report.json/.md` | Read-only boot readiness checks | Preconditions and safety-boundary support | Can support continuity only |
| `collector_report_*.json` | Raw normalized coverage and gap report | Provenance, coverage, gap findings, paper-chain absence signals | Stamped cycle evidence only |
| `snapshot_*.json/.md` | Normalized Harvester snapshot | Coverage summary, provenance status, gap findings, safety flags | Stamped cycle evidence only |
| `watchdog_report*.json/.md` | Stalled/stale evidence monitor | Artifact integrity and liveness support | Final proof requires history over `>=72h` |
| `write_audit_report*.json/.md` | Artifact completeness and consistency audit | Hash linkage, schema versions, safety flags, markdown companion checks | Final proof requires history over `>=72h` |
| `ops_validation_report.json/.md` | Final `>=72h` composition validator | Operational continuity proof only | Missing for active #3374 run until final validation |
| `alert_*.json/.md` | Deterministic evidence-gap alert report | Limitations and manual escalation signals | Stamped cycle evidence only |

Important distinction:

- These artifacts can support `source_run_refs`, `limitations`, and
  `safety_boundaries`.
- They do not replace ARVP/replay, Data Quality, Execution Economics, or paper
  reference artifacts.

## Field Mapping

| PEP field | Classification | Harvester satisfies? | Harvester artifact contribution | Required producer | Blocked by | Notes |
|---|---|---|---|---|---|---|
| `schema_version` | `OUT_OF_SCOPE_FOR_HARVESTER` | No | None | Packet assembler | #3381 | Constant must be emitted by the packet writer. |
| `evidence_packet_id` | `OUT_OF_SCOPE_FOR_HARVESTER` | No | None | Packet assembler | #3381 | Deterministic packet identity belongs to assembly policy. |
| `candidate_id` | `COVERED_BY_ARVP` | No | None | Candidate contract / ARVP manifest | #3381 | Harvester artifacts are not candidate contracts. |
| `generated_at` | `OUT_OF_SCOPE_FOR_HARVESTER` | No | Harvester has its own artifact timestamps only | Packet assembler | #3381 | Packet generation timestamp is distinct from Harvester cycle timestamps. |
| `dataset_id` | `COVERED_BY_DATA_QUALITY` | No | Coverage scopes can mention symbol/venue/timeframe | Data Quality report / ARVP dataset selection | #3381 | Harvester coverage scope is not canonical dataset identity. |
| `dataset_fingerprint` | `COVERED_BY_DATA_QUALITY` | No | Snapshot has collector report hash, not dataset fingerprint | Data Quality report | #3381 | PEP expects `sha256:<64>`; ARVP manifest may use bare `<64>`. |
| `source_run_refs` | `COVERED_BY_ARVP` | Partial | Add Harvester report refs, watchdog/write-audit refs, boot readiness refs, final ops-validation ref when available | ARVP/replay plus packet assembler | #3374 final PASS for final Harvester continuity refs | Harvester refs are adjunct provenance, not the only source run refs. |
| `gross_return` | `COVERED_BY_EXECUTION_ECONOMICS` | No | None | ARVP/replay and Execution Economics assessment | #3381 | Harvester health cannot be interpreted as return. |
| `net_return` | `COVERED_BY_EXECUTION_ECONOMICS` | No | None | Execution Economics assessment | #3381 | Requires explicit fee/spread/slippage treatment. |
| `fees` | `COVERED_BY_EXECUTION_ECONOMICS` | No | None | Execution Economics model/assessment | #3381 | Fee assumptions belong to economics producer. |
| `spread_cost` | `COVERED_BY_EXECUTION_ECONOMICS` | No | None | Execution Economics model/assessment | #3381 | Harvester does not observe candidate spread attribution. |
| `slippage_cost` | `COVERED_BY_EXECUTION_ECONOMICS` | No | None | Execution Economics model/assessment | #3381 | May depend on scenario/replay compare inputs. |
| `profit_factor` | `COVERED_BY_ARVP` | No | None | Replay/ARVP candidate run | #3381 | Candidate metric; not paper-chain coverage. |
| `expectancy` | `COVERED_BY_ARVP` | No | None | Replay/ARVP candidate run | #3381 | Requires candidate trade outcomes. |
| `win_rate` | `COVERED_BY_ARVP` | No | None | Replay/ARVP candidate run | #3381 | Requires candidate closed-trade counts. |
| `avg_win` | `COVERED_BY_ARVP` | No | None | Replay/ARVP candidate run | #3381 | Requires candidate trade distribution. |
| `avg_loss` | `COVERED_BY_ARVP` | No | None | Replay/ARVP candidate run | #3381 | Requires candidate trade distribution. |
| `max_drawdown` | `COVERED_BY_ARVP` | No | None | Replay/ARVP scenario or candidate run | #3381 | Harvester snapshot gaps are not drawdown. |
| `loss_streak` | `COVERED_BY_ARVP` | No | None | Replay/ARVP candidate run | #3381 | Requires ordered candidate trades. |
| `trade_count` | `COVERED_BY_ARVP` | No | Paper-chain counts can reveal missing chains | Replay/ARVP candidate run | #3381 | Harvester `paper_chains.*count` is not candidate trade count. |
| `regime_scorecard` | `COVERED_BY_ARVP` | Partial | Regime coverage gaps and stale/missing regime signals | ARVP/regime calibration or regime scorecard artifact | #3381 | Harvester can downgrade trust but cannot produce the scorecard. |
| `scenario_results` | `COVERED_BY_ARVP` | No | None | Scenario harness / ARVP batch output | #3381 | Harvester cycles are not candidate scenarios. |
| `replay_vs_paper_status` | `REQUIRES_PAPER_REFERENCE` | Partial | Missing or zero paper-chain signals can support `missing_reference` limitations | Replay-vs-paper compare producer | #3381 / paper reference source | Needs explicit paper reference and compare semantics. |
| `simulator_drift` | `REQUIRES_PAPER_REFERENCE` | No | None | Replay-vs-paper / calibration drift producer | #3381 / paper reference source | Requires drift classification contract or producer. |
| `risk_blocks` | `REQUIRES_PAPER_REFERENCE` | No | None | Risk/paper event source | Paper reference source | Harvester does not own risk event truth. |
| `kill_switch_events` | `REQUIRES_PAPER_REFERENCE` | No | None | Kill-switch/risk event source | Paper reference source | Harvester safety flags are not kill-switch event counts. |
| `recommendation` | `OUT_OF_SCOPE_FOR_HARVESTER` | No | Limitations may inform review | Packet assembler / review policy | #3381 | Harvester must not recommend candidate promotion. |
| `limitations` | `COVERED_BY_HARVESTER` | Partial | Gap findings, provenance contamination, missing/zero paper chains, source-mode caveats, active-run status | Packet assembler with all producers | #3374 final PASS for final continuity limitations | Harvester limitations should be appended, not used as metric substitutes. |
| `safety_boundaries` | `COVERED_BY_HARVESTER` | Partial | Snapshot safety flags and runbook boundaries: LR `NO-GO`, no Live-Go, no Echtgeld-Go, no runtime/DB actions | Packet assembler | none for generic boundary; #3374 for final continuity boundary | Harvester can provide explicit safety text, not authorization. |

## #3374 Dependency Boundary

Current active run `20260620T200144Z` is not final proof.

Final always-on proof remains `blocked_until_3374_final_pass`.

Older 72h validation reports are FAIL/short windows and must not be reused as
proof.

#3374 final `ops_validation_report.json/.md` can support operational continuity
only, not profitability metrics.

Current safe usage before final #3374 PASS:

- Use active-run artifacts only as interim operational observations.
- Do not claim `>=72h` continuity from the active run until final validation
  artifacts exist.
- Do not overwrite, regenerate, stop, restart, or mutate the active run.
- Do not treat Watchdog PASS or Write-Audit PASS for early cycles as final
  Harvester acceptance.

When #3374 final PASS exists, a future packet assembler may include final
Harvester continuity refs under `source_run_refs` and related `limitations` /
`safety_boundaries`. That still will not populate candidate returns, trade
metrics, economics, paper alignment, simulator drift, or recommendation fields.

## Blocked / Missing Producers

Issue-ready missing or blocked producers:

| Producer gap | Affected PEP fields | Suggested owner / follow-up |
|---|---|---|
| Packet assembler | `schema_version`, `evidence_packet_id`, `generated_at`, assembly of all refs, `recommendation` policy application | #3381 |
| Data Quality packet input | `dataset_id`, `dataset_fingerprint` | Data Quality report producer / #3381 fixture inputs |
| ARVP/replay candidate metrics | `candidate_id`, `gross_return`, trade statistics, `regime_scorecard`, `scenario_results` | ARVP/replay producers |
| Execution Economics | `net_return`, `fees`, `spread_cost`, `slippage_cost` | Execution Economics assessment producer |
| Paper reference and replay compare | `replay_vs_paper_status`, `simulator_drift` | Paper-reference / replay-vs-paper producer |
| Risk / kill-switch event source | `risk_blocks`, `kill_switch_events` | Paper/risk event producer |
| Final Harvester continuity | Harvester continuity refs in `source_run_refs`, final continuity limitations | #3374 / #3362 final PASS |
| League-table readiness view | Whether enough evidence exists to compare candidates fairly | #3383 |

## Contract Gaps

Known gaps to keep explicit:

- Dataset fingerprint format mismatch risk: PEP expects `sha256:<64>`, while
  ARVP manifest may use bare `<64>`.
- A paper reference source is required for replay-vs-paper alignment, simulator
  drift, risk blocks, and kill-switch events.
- Packet assembler/review policy owns `recommendation`, not Harvester.
- Execution Economics owns fees, spread, slippage, and net metrics.
- ARVP/replay owns gross, trade, scenario, and statistical candidate metrics.
- Existing committed evidence packets may contain historical schema hygiene
  inconsistencies such as `null` values in fields where the current PEP schema
  requires a number; that is a follow-up hygiene concern, not something the
  Harvester can fix.
- Harvester snapshot `collector_report_hash` is a Harvester artifact hash, not a
  dataset fingerprint.
- Harvester paper-chain gap counts are coverage/trust signals, not candidate
  trade counts.

## Recommended Next Steps

1. Use this mapping as the input contract for #3381.
2. In #3381, require explicit local artifact refs for Candidate Contract, Data
   Quality Report, ARVP/replay output, Scenario Results, Execution Economics,
   paper-reference compare artifacts when available, and optional Harvester refs.
3. In #3381, fail closed on missing required packet fields and add explicit
   limitations instead of inferring unavailable metrics.
4. In #3383, use this mapping to classify candidate evidence bundles as
   ranking-ready, partial, or blocked by missing producer classes.
5. Keep #3374/#3362 separate: final Harvester continuity is useful evidence
   production proof, not candidate profitability proof.
6. Keep #3345 open until its parent acceptance criteria are reconciled; do not
   close it from this mapping alone.

## Safety Boundaries

- LR remains `NO-GO`.
- `trade-capable` is not Live-Go.
- No Live-Go.
- No Echtgeld-Go.
- No runtime change.
- No Docker mutation.
- No DB mutation.
- No secrets access.
- No active #3374 run artifact changes.
- No candidate recommendation execution.
- No automatic strategy promotion.
- No paper, micro-live, live capital, or capital scaling authorization.
