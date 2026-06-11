# ARVP Campaign Supervisor — Manifest Contract + State Machine

**Version:** 1.0
**Status:** Canonical
**Issue:** #3109
**Parent:** #3102 (Campaign Supervisor Umbrella)
**Design Source:** #3094 docs/evidence/arvp_deterministic_window_production_3094.md

---

## 1. Purpose

### 1.1 Why the Supervisor Is Needed

Current ARVP volatility-window campaigns require manual agent babysitting:
- Every 20–30 minutes an agent must check correlation_ledger, docker ps, regimes, and candle data
- Campaigns are interrupted by host shutdown (Campaign #1, #2) without automated recovery
- Each campaign consumes 8h of agent session time for what is essentially polling
- 4 campaigns have been executed (1, 1R, 2, 2R) with 2 full-window timeouts and 0 chains — the pattern is now predictable

### 1.2 Goal

Replace manual campaign babysitting with a **deterministic, machine-readable manifest contract** and **state machine** that:
- Defines all required campaign fields before start (anti-cherry-pick)
- Tracks campaign state deterministically
- Classifies outcomes correctly (timeout vs interruption vs chain found)
- Enables future automated supervisor components (#3110–#3115) to operate without improvisation

### 1.3 Scope

Paper-window monitoring only:
- MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false
- Readonly DB access (cdb_readonly or claire_user SELECT only)
- No runtime mutation, no strategy changes, no DB writes
- No Live-Go, no Echtgeld-Go

---

## 2. Campaign Manifest Contract

Every campaign MUST produce a machine-readable manifest with the following fields before start.

### 2.1 Required Fields

| # | Field | Type | Required | Description | Validation |
|---|-------|------|----------|-------------|------------|
| 1 | schema_version | string | **yes** | Manifest schema version | Must be "1.0" for this version |
| 2 | campaign_id | string | **yes** | Unique campaign identifier | Pattern: rvp_3095_vol_window_<N><r?>_<YYYYMMDD_HHMM> |
| 3 | parent_issue | int | **yes** | Campaign execution issue | 3095 for volatility-window campaigns |
| 4 | elated_issues | int[] | **yes** | Related issues for cross-referencing | At minimum: [3087] |
| 5 | symbol | string | **yes** | Trading symbol | Currently BTCUSDT only |
| 6 | strategy_id | string | **yes** | Strategy identifier | primary_breakout_v1 |
| 7 | vidence_class | string | **yes** | Evidence classification | One of the 4 canonical evidence classes from #3094 |
| 8 | start_utc | ISO-8601 | **yes** | Campaign start timestamp | UTC, not local time |
| 9 | 	imeout_utc | ISO-8601 | **yes** | Planned timeout = start + max_duration | UTC |
| 10 | max_duration_hours | float | **yes** | Maximum campaign duration | Currently 8.0 |
| 11 | start_criteria | object | **yes** | Pre-documented criteria that were met | Must include pre_documented: true |
| 12 | safety_flags | object | **yes** | Safety flag values at start | All 4 flags required |
| 13 | untime_targets | string[] | **yes** | Runtime services to monitor | Canonical list |
| 14 | db_readonly_targets | string[] | **yes** | DB tables/surfaces to monitor | Canonical list |
| 15 | vidence_doc | string | **yes** | Path to human-readable evidence document | Relative to repo root |
| 16 | vidence_log_jsonl | string | **yes** | Path to machine-readable evidence log | Relative to repo root |
| 17 | github_reporting | object | **yes** | GitHub communication plan | Per §8 contract |
| 18 | llowed_statuses | string[] | **yes** | All states the campaign may enter | Fixed list from §4 |
| 19 | 	erminal_statuses | string[] | **yes** | Terminal states that stop the supervisor | Subset of allowed_statuses |

### 2.2 Campaign Slot Rules

| Rule | Value |
|------|-------|
| Maximum campaigns | 3 (per #3094 design) |
| Per-campaign duration | Maximum 8 hours |
| Early stop | On first SIGNAL → DECISION → ORDER(paper_) → FILL chain |
| Escalation | After ≥3 true no-chain failures → Option E (waiver/split) |
| Interruption | Does NOT consume a campaign slot |
| Restart (R suffix) | Counts toward the slot it replaces |

### 2.3 Campaign Slot Classification Rules

| Slot Status | Counts as Failure? | Example |
|-------------|-------------------|---------|
| 	imeout_no_chain | **Yes** | Campaign #1R, #2R — full 8h with 0 chains |
| interrupted | **No** | Campaign #1, #2 — host/stack failure before timeout |
| locked_* | **No** | Infrastructure issue — not market verdict |
| chain_found | **N/A (success)** | Campaign stops, evidence is produced |

---

## 3. Example Manifest

### 3.1 Campaign #3 Example (YAML)

`yaml
schema_version: "1.0"
campaign_id: arvp_3095_vol_window_3_20260611_0800
parent_issue: 3095
related_issues:
  - 3087
  - 3102
symbol: BTCUSDT
strategy_id: primary_breakout_v1
evidence_class: natural_paper_evidence
start_utc: "2026-06-11T08:00:00Z"
timeout_utc: "2026-06-11T16:00:00Z"
max_duration_hours: 8.0
start_criteria:
  description: "15m rolling range >= 0.35% (P1) OR 60m range >= 0.75% (P2) OR regime TREND with directional plausibility (P3). HIGH_VOL_CHAOTIC alone is NOT sufficient - see #3103 start policy."
  start_policy_ref: docs/evidence/arvp_volatility_window_start_policy_3103.md
  primary_p1_threshold_pct: 0.35
  primary_p2_threshold_pct: 0.75
  primary_p3_regimes:
    - TREND
    - HIGH_VOL_CHAOTIC
  actual_p1_pct: 0.42
  actual_p3: HIGH_VOL_CHAOTIC
  criteria_met: true
  pre_documented: true
safety_flags:
  mock_trading: true
  use_real_balance: false
  dry_run: true
  mexc_testnet: true
runtime_targets:
  - cdb_execution
  - cdb_regime
  - cdb_risk
  - cdb_market
  - cdb_candles
  - cdb_db_writer
db_readonly_targets:
  - public.correlation_ledger
  - public.candles_1m
evidence_doc: docs/evidence/arvp_volatility_window_campaign_3095_3.md
evidence_log_jsonl: artifacts/campaigns/arvp_3095_vol_window_3/evidence_log.jsonl
github_reporting:
  post_on_issue_3095: true
  post_on_issue_3087: false
  post_on_issue_3102: true
  pr_create_on_chain_found: true
  issue_close_after_acceptance: false
allowed_statuses:
  - planned
  - preflight_failed
  - running
  - chain_found
  - timeout_no_chain
  - interrupted
  - blocked_runtime
  - blocked_db_readonly
  - blocked_governance
  - evidence_pr_open
  - evidence_merged
terminal_statuses:
  - chain_found
  - timeout_no_chain
  - interrupted
  - blocked_runtime
  - blocked_db_readonly
  - blocked_governance
  - evidence_merged
`

---

## 4. State Machine

### 4.1 State Diagram (Text)

`
                    ┌──────────────────────────────────┐
                    │            planned                │
                    └──────┬───────────────┬───────────┘
                           │               │
                    preflight          start-go
                    fails               given
                           │               │
                           ▼               ▼
                 ┌───────────────┐   ┌──────────┐
                 │preflight_failed│  │ running  │
                 └───────────────┘   └─┬──┬──┬──┼──┬──┬──┐
                                       │  │  │  │  │  │  │
                  ┌────────────────────┘  │  │  │  │  │  │
                  │            ┌──────────┘  │  │  │  │  │
                  │            │  ┌──────────┘  │  │  │  │
                  ▼            ▼  ▼             ▼  ▼  ▼  ▼
           ┌──────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
           │chain_found│ │timeout_no_ │ │ interrupted│ │blocked_*   │
           └─────┬─────┘ │  chain     │ └────────────┘ └──────┬─────┘
                 │        └────────────┘                       │
                 │                                             │
                 ▼                                      (retry after fix)
           ┌──────────┐                                     │
           │evidence_ │                               ┌──────┴──────┐
           │pr_open   │                               │   planned   │
           └─────┬────┘                               └─────────────┘
                 │
                 ▼
           ┌──────────┐
           │evidence_ │
           │ merged   │
           └──────────┘
`

### 4.2 State Definitions

| State | Category | Description | Evidence Log Required? |
|-------|----------|-------------|----------------------|
| planned | Non-terminal | Campaign defined, manifest created, awaiting start-go | No (pre-start) |
| preflight_failed | Terminal (blocked) | Preflight checks failed (host, Docker, safety, DB) | Yes (reason) |
| unning | Non-terminal | Campaign actively monitoring | Yes (each cycle) |
| chain_found | Terminal (success) | Complete SIGNAL→DECISION→ORDER→FILL chain detected | Yes (chain evidence) |
| 	imeout_no_chain | Terminal (failure) | Planned duration expired without chain | Yes (closeout evidence) |
| interrupted | Terminal (neutral) | Host/stack failure before timeout | Yes (forensic evidence) |
| locked_runtime | Terminal (blocked) | Runtime service unhealthy for extended period | Yes (health evidence) |
| locked_db_readonly | Terminal (blocked) | DB read-only access lost | Yes (DB error evidence) |
| locked_governance | Terminal (blocked) | Safety flag violation or governance stop | Yes (violation evidence) |
| vidence_pr_open | Non-terminal | Evidence PR created, awaiting review/merge | Yes (PR URL) |
| vidence_merged | Terminal (success) | Evidence PR merged into main | Yes (merge SHA) |

---

## 5. Transitions

### 5.1 Transition Table

| # | From | To | Trigger | Required Evidence | Allowed Action | Forbidden Action |
|---|------|----|---------|------------------|---------------|------------------|
| T1 | planned | preflight_failed | Preflight check fails | Specific check failure output | Document failure; abort campaign | Retry without fixing root cause |
| T2 | planned | unning | Preflight PASS + start-go given | Preflight evidence (host, docker, safety, DB) | Begin monitoring loop | Skip preflight; start without start-go |
| T3 | unning | chain_found | Complete chain detected in correlation_ledger | SIGNAL + DECISION + ORDER(paper_) + FILL events with shared lineage | Stop campaign; extract window; create evidence PR | Continue monitoring; start another campaign |
| T4 | unning | 	imeout_no_chain | Current UTC >= 	imeout_utc AND no chain | Closeout evidence: all monitoring cycles, host continuity, final correlation_ledger count | Classify as campaign failure; log to history; count slot | Extend campaign; re-run start criteria |
| T5 | unning | interrupted | Host/stack becomes unavailable before timeout | Forensic evidence: boot time, candle gaps, Docker logs, correlation_ledger last event | Classify as interruption; NOT count as failure; schedule retry if slot permits | Count as market failure; discard interruption record |
| T6 | unning | locked_runtime | Runtime probe fails consistently (n consecutive failures) | Health check evidence: which service failed, duration, attempt count | Log blocker; stop campaign; classify as infrastructure issue | Continue with degraded checks; ignore health failure |
| T7 | unning | locked_db_readonly | DB SELECT fails or times out | DB error evidence: error type, retry count | Log blocker; stop campaign | Use write credentials; retry indefinitely |
| T8 | unning | locked_governance | Safety flag drift detected or governance stop signal | Drift evidence: before/after flag values or explicit governance signal | STOP immediately; log violation; classify as governance block | Continue with changed flags; ignore governance signal |
| T9 | locked_runtime | planned | Runtime health restored + root cause fixed | Health re-check evidence | Re-plan campaign with fresh start criteria | Auto-restart without preflight |
| T10 | locked_db_readonly | planned | DB read access restored + root cause fixed | DB re-check evidence | Re-plan campaign with fresh start criteria | Auto-restart without preflight |
| T11 | locked_governance | planned | Governance blocker resolved + explicit GO | Resolution evidence (issue comment, PR, human signal) | Re-plan ONLY with explicit new start-go | Auto-restart; bypass governance |
| T12 | chain_found | vidence_pr_open | Evidence window extracted + PR created | Evidence doc + PR URL | PR for review | Merge without review |
| T13 | vidence_pr_open | vidence_merged | PR approved + merged to main | Merge SHA + PR URL | Confirm delivery; close campaign tracking | Auto-approve without human review |
| T14 | preflight_failed | planned | Root cause fixed + re-preflight passes | Re-check evidence | Re-plan campaign | Skip re-preflight |
| T15 | interrupted | planned | Host/stack restored + fresh start-go | Fresh preflight evidence | Re-plan as replacement campaign (N+1R) | Auto-restart without fresh start-go |
| T16 | unning | unning (cycle) | Monitoring interval elapsed + no termination condition | Per-cycle evidence (health, host, safety, ledger, regime) | Continue monitoring loop | Skip cycle; modify cycle logic |

### 5.2 Monitoring Cycle Contract (T16)

Each running cycle MUST capture:

| Field | Method | Example |
|-------|--------|---------|
| Cycle timestamp | UTC clock | 2026-06-11T09:00:00Z |
| Core BLUE services health | docker ps | All healthy |
| Host continuity | Get-CimInstance Win32_OperatingSystem + powercfg /lastwake | 0 sleep events |
| Safety flags | docker inspect cdb_execution env | MOCK=true, DRY=true, TESTNET=true, REAL_BALANCE=false |
| Regime state | docker logs cdb_regime --tail 3 | HIGH_VOL_CHAOTIC |
| BTCUSDT 15m range | SQL SELECT on candles_1m | 0.35% |
| correlation_ledger events since start | SQL SELECT count | 0 |
| Chain candidate | Manual or heuristic check | None |

---

## 6. Terminal Classification Rules

### 6.1 Classification Categories

| Category | Terminal States Included | Examples from Evidence |
|----------|------------------------|----------------------|
| **Campaign Failure** | 	imeout_no_chain | Campaign #1R (8h, 0 chain), Campaign #2R (8h, 0 chain) |
| **Interruption** | interrupted | Campaign #1 (host shutdown @~1h), Campaign #2 (host reboot @~3h14m) |
| **Blocked** | locked_runtime, locked_db_readonly, locked_governance | Not yet observed (blocker states are new in this contract) |
| **Success** | chain_found, vidence_merged | Not yet observed (this is the target outcome) |
| **Preflight Failure** | preflight_failed | Not yet observed |

### 6.2 Classification Rules

1. **	imeout_no_chain zählt als Campaign-Failure** — Die volle 8h wurden beobachtet, die Strategie hat nicht getriggert. Dies ist ein Market-Verdikt, kein Infrastruktur-Fehler.
2. **interrupted zählt NICHT als Campaign-Failure** — Der Host oder Stack war nicht durchgehend verfügbar. Das Fenster wurde nicht vollständig beobachtet. Dies ist ein Infrastruktur-Problem, kein Market-Verdikt.
3. **chain_found stoppt alle weiteren Campaigns** — Sobald eine vollständige Kette existiert, ist das Ziel erreicht (§5.2.4). Keine weiteren Campaigns nötig. Gehe direkt zu Evidence-Extraktion.
4. **locked_* zählen NICHT als Market-Failure** — Infrastruktur- oder Governance-Probleme sind keine Market-Aussage. Sie zählen nicht gegen das 3er-Limit.
5. **3 echte no-chain Failures → Option E / Waiver-Split-Escalation** — Nach drei vollständig beobachteten 8h-Fenstern ohne Kette muss auf Option E (#3094) eskaliert werden. Dieses Limit kann durch Interruptions oder Blocker nicht künstlich erhöht werden — nur echte 	imeout_no_chain zählen.
6. **Jeder Campaign-Failure muss dokumentiert werden** — Kein stilles Verwerfen. Der Slot wird im Campaign-History-Tracker erfasst.
7. **Interrupted Campaigns nach Wiederherstellung als N+1R restartbar** — Ersetzt den unterbrochenen Slot, verbraucht keinen neuen.

### 6.3 Escalation Matrix

| Failures | Action | Reference |
|----------|--------|-----------|
| 0 | Continue campaign plan | #3095 |
| 1 | Continue; prefer TREND regime | #3094 Option B |
| 2 | Continue; evaluate if waiver prep needed | #3094 Option B |
| **3 (or more)** | **Escalate to Option E — Waiver/Split** | #3094 Option E |
| Any count + chain_found | **Stop all campaigns** | #3087 |

---

## 7. Evidence Requirements Per State

### 7.1 unning (Per Monitoring Cycle)

| Evidence | Required | Format | Example |
|----------|----------|--------|---------|
| Timestamp | **Yes** | ISO-8601 UTC | 2026-06-11T09:00:00Z |
| Core BLUE health | **Yes** | String summary | All healthy (3h uptime) |
| Host continuity | **Yes** | Uptime + sleep events | Continuous since boot, 0 sleep events |
| Safety flags | **Yes** | 4 flag values | MOCK=true, DRY=true, TESTNET=true, REAL_BALANCE=false |
| Regime | **Yes** | Regime ID | HIGH_VOL_CHAOTIC |
| BTCUSDT 15m range | **Yes** | Percentage | .35% |
| BTCUSDT latest price | **Yes** | Decimal | ~62100 |
| correlation_ledger events since start | **Yes** | Integer count |  |
| Chain candidate | **Yes** | None or chain details | None |
| Candle gap detected | Recommended | Boolean | alse |
| Notes | Optional | Free text | — |

### 7.2 chain_found

| Evidence | Required | Format |
|----------|----------|--------|
| SIGNAL event | **Yes** | Full correlation_ledger event |
| DECISION event | **Yes** | Full correlation_ledger event with shared lineage |
| ORDER event (paper_) | **Yes** | Full correlation_ledger event |
| FILL event | **Yes** | Full correlation_ledger event |
| Shared lineage hash | **Yes** | Lineage chain confirming all 4 events connected |
| Window timestamps | **Yes** | SIGNAL ts_ms → FILL ts_ms |
| Safety flags at detection | **Yes** | Re-confirmed MOCK/DRY/TESTNET/REAL_BALANCE |
| Evidence class | **Yes** | 
atural_paper_evidence |

### 7.3 	imeout_no_chain

| Evidence | Required | Format |
|----------|----------|--------|
| Campaign ID | **Yes** | String |
| Start UTC | **Yes** | ISO-8601 |
| Timeout UTC | **Yes** | ISO-8601 |
| Closeout UTC | **Yes** | ISO-8601 |
| All monitoring cycles | **Yes** | Full cycle data (§7.1 for each) |
| Host continuity (full window) | **Yes** | Boot time + 0 sleep events |
| Docker health (full window) | **Yes** | All cycles healthy |
| Safety flags (at closeout) | **Yes** | Re-confirmed unchanged |
| correlation_ledger events (final count) | **Yes** | 0 (or actual count) |
| Chain produced | **Yes** | alse |
| Root cause summary | **Yes** | Free text (market conditions) |
| Classification | **Yes** | campaign_timeout_record |

### 7.4 interrupted

| Evidence | Required | Format |
|----------|----------|--------|
| Campaign ID | **Yes** | String |
| Last known good timestamp | **Yes** | ISO-8601 |
| Last candle before gap | **Yes** | ts_ms |
| First candle after gap | **Yes** | ts_ms |
| Host forensics | **Yes** | Boot time (current), boot time (prior), sleep/wake events |
| Docker forensics | **Yes** | Docker uptime at recovery |
| correlation_ledger last event | **Yes** | ts_ms |
| Events observed before interruption | **Yes** | Count + details |
| Chain before interruption | **Yes** | alse or actual |
| Candle gap analysis | **Yes** | Gap duration in minutes |
| Classification | **Yes** | interruption_record |

### 7.5 locked_runtime

| Evidence | Required | Format |
|----------|----------|--------|
| Health check evidence | **Yes** | Which service failed, how many consecutive failures |
| Error details | **Yes** | Docker inspect/log output |
| Timestamp of first failure | **Yes** | ISO-8601 |
| Retry attempts | **Yes** | Count |
| Chain produced before block | **Yes** | None, partial, or complete |

### 7.6 locked_db_readonly

| Evidence | Required | Format |
|----------|----------|--------|
| DB error evidence | **Yes** | Error type, error message |
| Timestamp of first failure | **Yes** | ISO-8601 |
| Retry attempts | **Yes** | Count |
| Connection details used | **Yes** | Host, port, user (no password!) |
| Chain produced before block | **Yes** | None, partial, or complete |

### 7.7 locked_governance

| Evidence | Required | Format |
|----------|----------|--------|
| Safety flag drift evidence | **Yes** | Before/after flag values |
| Governance stop signal | **Yes** | Source (issue/PR/comment) + content |
| Timestamp | **Yes** | ISO-8601 |
| Chain produced before block | **Yes** | None, partial, or complete |

---

## 8. GitHub Reporting Contract

### 8.1 Per-Campaign Reporting

| Event | Issue | Content | Required? |
|-------|-------|---------|-----------|
| Campaign planned | **#3095** | Campaign ID, start criteria, duration, safety flags | **Yes** |
| Campaign started | **#3095** | Preflight PASS summary, start UTC | **Yes** |
| Each monitoring cycle | **#3095** | Compact one-liner: timestamp, health, regime, 15m range, events count | Recommended (may batch) |
| Campaign closed | **#3095** | Final state, duration, events count, classification | **Yes** |
| chain_found | **#3095** + new evidence PR | Chain evidence, PR link | **Yes** (mandatory) |

### 8.2 Cross-Referencing Rules

| Rule | Condition | Action |
|------|-----------|--------|
| #3087 comment | State changes to chain_found or campaign limit reached (3 failures) | Short update: §5.2.4 status |
| #3087 comment | Routine campaign closeout (no chain, not final) | **Do not comment** — no relevant change |
| #3102 reference | Campaign interrupted by host/runtime failure | Reference in interruption record |
| #3102 reference | Normal campaign timeout | **Do not reference** — no watchdog relevance |
| #3109 comment | This document created/updated | PR link + merge SHA |

### 8.3 Issue Closure Rules

| Issue | May Close? | When? |
|-------|-----------|-------|
| **#3109** | **Yes** | After this document is merged AND acceptance criteria met |
| **#3095** | **No** (in this task) | Only when all campaigns complete OR success + evidence merged |
| **#3087** | **No** | Only when §5.2.4 is satisfied (chain found OR waiver accepted) |
| **#3102** | **No** | Parent umbrella — remains open until all child issues done |

### 8.4 PR Rules

| Action | Rule |
|--------|------|
| PR creation | On chain_found → create evidence PR. On vidence_pr_open → keep open for human review |
| PR merge | **No auto-merge.** Human review required for evidence PRs |
| PR for this contract | Docs-only → squash-merge after green checks |

---

## 9. Safety / Forbidden Actions

The following actions are **ABSOLUTELY FORBIDDEN** for the Campaign Supervisor or any component implementing this contract:

| # | Forbidden Action | Rationale |
|---|-----------------|-----------|
| 1 | **No Live-Go** | LR remains NO-GO per LR-AUDIT-STATUS-2026-03-05.md (#2535) |
| 2 | **No Echtgeld-Go** | No real capital, no real trades, no real exchange orders |
| 3 | **No strategy parameter changes** | primary_breakout_v1 remains unchanged (0.5% breakout, 15m lookback) |
| 4 | **No runtime/config changes** | No Docker, compose, env, or service config mutation |
| 5 | **No DB migration** | No schema changes, no new tables, no ALTER |
| 6 | **No productive DB writes** | SELECT only on correlation_ledger and candles_1m. Never INSERT/UPDATE/DELETE |
| 7 | **No synthetic evidence as 
atural_paper_evidence** | Stimulus runner output is pipeline_test_evidence, never 
atural_paper_evidence |
| 8 | **No silent evidence-class upgrade** | pipeline_test_evidence cannot become 
atural_paper_evidence by omission of label |
| 9 | **No auto-merge without human approval** | Evidence PRs need human review; docs-only PRs may squash-merge after green checks |

### 9.1 Safety Boundary Enforcement

| Boundary | How Enforced |
|----------|-------------|
| MOCK_TRADING=true | Verified at start AND each monitoring cycle via docker inspect cdb_execution |
| USE_REAL_BALANCE=false | Verified at start AND each monitoring cycle |
| DRY_RUN=true | Verified at start (code defaults) |
| MEXC_TESTNET=true | Verified at start (code defaults) |
| correlation_ledger dormant status | Verified at start (no recent events) |
| No secrets in outputs | Manual review; g for known patterns |

---

## 10. Downstream Dependencies

### 10.1 Child Issues Dependency Map

| Issue | Title | Needs from this Contract | Section Reference |
|-------|-------|-------------------------|-------------------|
| **#3110** | Read-only probe layer | Manifest fields: untime_targets, db_readonly_targets, safety_flags | §2.1 fields #13–14, §5.2 cycle contract |
| **#3111** | CLI polling loop | States planned, preflight_failed, unning, transitions T1–T8 | §4 state definitions, §5 transition table |
| **#3112** | Chain detector + evidence export | chain_found state, vidence_pr_open, transition T3, evidence requirements §7.2 | §4, §5 T3, §7.2 |
| **#3113** | GitHub reporter | GitHub Reporting Contract §8, issue closure rules, comment format | §8 full section |
| **#3114** | Windows background runner | State machine (must survive host restart), interrupted classification rules, T15 retry | §4, §6, §5 T15 |
| **#3115** | Test/failure-simulation pack | All states, all transitions, terminal classification rules | Full document as test matrix |

### 10.2 Recommended Implementation Order

Per #3102 umbrella comment:

1. **#3109** (this contract) — Done first
2. **#3110** — Read-only probes (runtime, DB, safety)
3. **#3111** — CLI polling loop (core supervisor)
4. **#3112** — Chain detector (outcome classification)
5. **#3113** — GitHub reporter (communication)
6. **#3114** — Windows background runner (8h operation)
7. **#3115** — Tests/failure-sims (validation)

---

## 11. References

- **#3109** — This issue (Campaign manifest + state machine)
- **#3102** — Parent umbrella (Campaign Supervisor)
- **#3095** — Campaign execution issue
- **#3087** — Comparison-grade reference window production
- **#3094** — Deterministic paper-window production design (docs/evidence/arvp_deterministic_window_production_3094.md)
- **#3103** — blocked_regimes policy clarification
- docs/evidence/arvp_volatility_window_campaign_3095_1r.md — Campaign #1R evidence
- docs/evidence/arvp_volatility_window_campaign_3095_2.md — Campaign #2 evidence
- docs/evidence/arvp_volatility_window_campaign_3095_2r.md — Campaign #2R evidence
- docs/evidence/arvp_volatility_window_campaign_3095_interruption.md — Campaign #1 interruption
- docs/evidence/arvp_deterministic_window_production_3094.md — Design doc with evidence classes
- docs/runbooks/ARVP_OPERATOR_RUNBOOK.md — Existing ARVP operator runbook
- docs/runbooks/CONTROL_REGISTER.md — Board stage, LR NO-GO
- docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md — LR verdict NO-GO
- knowledge/governance/CDB_CONSTITUTION.md — §2 determinism principle
- knowledge/governance/CDB_AGENT_POLICY.md — Agent operating rules, write-gates

---

## 12. Safety Boundaries (all affirmed)

| Boundary | Status |
|----------|--------|
| LR remains **NO-GO** | Confirmed throughout document |
| Board stage 	rade-capable ≠ Live-Go | Confirmed |
| No Echtgeld-Go | Confirmed |
| No strategy parameter changes | Confirmed |
| No runtime/config mutation | Confirmed |
| No Docker/compose changes | Confirmed |
| No DB migration | Confirmed |
| No productive DB writes (SELECT only) | Confirmed |
| No synthetic evidence as natural paper | Confirmed |
| No silent evidence-class upgrade | Confirmed |
| No secrets in outputs | Confirmed |
| Docs-only, no code changes | Confirmed |

