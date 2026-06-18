# ARVP Guarded Natural-Paper Window Execution — #3217

Status Class: Scoped evidence / guarded extraction result
Issue: #3217
Parent: #1900
Control Refs: #2985, #2977, #3212, #3215, #2961
Live-Readiness: NO-GO
Echtgeld: not authorized

---

## 1. Brain Evidence Block

```
brain_source: repo-only, validated via readonly DB extract
brain_status: used
tools_or_queries:
  - read: canonical read-order per AGENTS.md
  - read: docs/evidence/arvp_window_bank_2961_extraction_2026-06-04.md
  - read: docs/evidence/arvp_readonly_preflight_2967_closeout.md
  - read: docs/evidence/arvp_window_bank_inventory_3212.md
  - read: docs/evidence/arvp_bounded_natural_paper_window_extraction_3215.md
  - read: core/replay/paper_reference_window_export.py
  - read: services/validation/paper_reference_window_runner.py
  - bash: git status, gh pr/issue checks
  - execute: paper_reference_window_runner.py (guarded readonly extract)
records_or_results:
  - HEAD == origin/main == cea0532626 at session start
  - #3217 OPEN; #3215 CLOSED; #3212 CLOSED; #2985 OPEN; #1900 OPEN; #2977 OPEN/BLOCKED
  - POSTGRES_READONLY_PASSWORD_DSN confirmed set (checked via os.getenv without printing value)
  - Readonly identity verified: cdb_readonly/cdb_readonly on claire_de_binare
  - Readonly privileges verified: SELECT=true, INSERT=false, UPDATE=false, DELETE=false
  - Candidate window extracted: 1-hour (60min) window [1780702200000, 1780705800000]
  - 11 events, 4 correlation_ids, actual data span 52.6 min
  - contract_version=arvp_paper_reference_window.v1, evidence_class=natural_paper_evidence
  - Existing artifacts unchanged; new artifact at artifacts/paper_reference_windows/paper_reference_window_june6_1h.json
repo_crosscheck:
  - arvp_window_bank_inventory_3212.md (prior bank state: 2 windows)
  - arvp_bounded_natural_paper_window_extraction_3215.md (route plan)
  - paper_reference_window_runner.py (guarded runner on main)
  - paper_reference_window_export.py (exporter on main)
impact_on_plan:
  - The 1h window is technically contract-valid but does not change A4 (regime) readiness
  - regime_segments remain unavailable for all windows (no continuous price data in window artifacts)
  - The bank now has 3 artifacts: 2 committed (pilot 1m + #3028 2m) + 1 new (1h)
limitation:
  - This slice executed the guarded runner with a secret-managed env; no env values were printed or committed
  - No runtime/Docker/Compose was started or modified
  - No strategy changes, no new paper trading, no DB mutation
```

---

## 2. Bootloader / Read-Order

Canonical read-order executed per `agents/AGENTS.md`:

1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md`
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `knowledge/CDB_KNOWLEDGE_HUB.md`
6. `docs/meta/WORKING_REPO_CANON.md`
7. `CURRENT_STATUS.md`
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
9. `docs/runbooks/CONTROL_REGISTER.md`
10. `agents/OPEN_CODE_AGENTS.md`

Verified boundaries:

- `CURRENT_STATUS.md` treated as ledger, not live truth.
- LR SSOT remains `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` (NO-GO).
- Board stage `trade-capable` is not Live-Go.
- No secret values printed, committed, or inspected.

---

## 3. Live-Lage

| Item | Status |
|---|---|
| Branch at session start | `main` |
| HEAD / origin/main | `cea0532626` / equal |
| Working tree | clean (except untracked `.opencode/plans/`, `docs/decisions/`, new artifact) |
| #3217 | OPEN |
| #3215 | CLOSED |
| #3212 | CLOSED |
| #2985 | OPEN |
| #1900 | OPEN |
| #2977 | OPEN / BLOCKED |
| Open PRs | Dependabot-only |
| LR verdict | NO-GO |
| Board stage | `trade-capable` (not Live-Go) |

No live-truth conflict found.

---

## 4. Safe Execution Preamble

### 4.1 Identity Verification

The guarded runner (`services/validation/paper_reference_window_runner.py`) performs mandatory identity and privilege verification before any SELECT query:

**Identity probe (SQL):**
```sql
SELECT current_database(), current_user, session_user;
```

**Result:** `current_database=claire_de_binare`, `current_user=cdb_readonly`, `session_user=cdb_readonly`

**Privilege probe (SQL):**
```sql
SELECT
  has_table_privilege(current_user, 'public.correlation_ledger', 'SELECT'),
  has_table_privilege(current_user, 'public.correlation_ledger', 'INSERT'),
  has_table_privilege(current_user, 'public.correlation_ledger', 'UPDATE'),
  has_table_privilege(current_user, 'public.correlation_ledger', 'DELETE');
```

**Result:** SELECT=true, INSERT=false, UPDATE=false, DELETE=false

Conclusion: Identity and privilege probes PASS. The runner is operating as the readonly role `cdb_readonly` with no write capability on `public.correlation_ledger`.

### 4.2 Env Handling

`POSTGRES_READONLY_PASSWORD_DSN` was confirmed set in the shell environment (checked via `os.getenv()` return-truthiness, not value inspection). No secret value was printed, logged, or committed in any artifact.

### 4.3 Source Query Intent

```
select correlation_ledger events by symbol+timestamp_ms window;
validate payload.strategy_id;
resolve bot_id/config_hash via SIGNAL anchors;
enforce homogeneity+chain-integrity fail-closed;
qualify paper via order_id prefix;
chain_source=live
```

---

## 5. Candidate Bound Selection

Per #3215 §8.2, candidate windows were tried in descending evidence value:

### Candidate A: 15-minute window around #3028 area

| Parameter | Value |
|---|---|
| strategy-id | `primary_breakout_v1` |
| symbol | BTCUSDT |
| start-ts-ms | `1780705300000` (2026-06-06T00:21:40Z) |
| end-ts-ms | `1780706200000` (2026-06-06T00:36:40Z) |
| causal-lookup-start-ms | `1780703500000` (2026-06-05T23:51:40Z) |
| causal-lookup-end-ms | `1780706200000` (same as end) |

**Result:** SUCCESS — 6 events, 2 chains, 15min window width.

### Candidate B: 1-hour window (superset)

| Parameter | Value |
|---|---|
| strategy-id | `primary_breakout_v1` |
| symbol | BTCUSDT |
| start-ts-ms | `1780702200000` (2026-06-05T23:30:00Z) |
| end-ts-ms | `1780705800000` (2026-06-06T00:30:00Z) |
| causal-lookup-start-ms | `1780700400000` (2026-06-05T23:00:00Z) |
| causal-lookup-end-ms | `1780705800000` (same as end) |

**Result:** SUCCESS — 11 events, 4 chains, 60min window width, actual data span 52.6 min.

**Candidate A is superseded by Candidate B.** The 1-hour window captures all events from Candidate A plus additional data from earlier in the night (23:36 UTC June 5).

### Candidate C: April 24 pilot area (30min)

| Parameter | Value |
|---|---|
| strategy-id | `primary_breakout_v1` |
| symbol | BTCUSDT |
| start-ts-ms | `1776990454682` (2026-04-24T00:27:34Z) |
| end-ts-ms | `1776992254682` (2026-04-24T00:57:34Z) |

**Result:** FAIL — `chain-integrity failed: window contains no SIGNAL anchors`. The pilot area has ORDER/FILL events for `primary_breakout_v1` but no SIGNAL anchors, so no complete chain can be reconstructed per contract. Consistent with #2961 findings that the pilot data is SIGNAL-incomplete.

---

## 6. Extraction Result

### 6.1 Primary Artifact

| Field | Value |
|---|---|
| Artifact path | `artifacts/paper_reference_windows/paper_reference_window_june6_1h.json` |
| contract_version | `arvp_paper_reference_window.v1` |
| strategy_id | `primary_breakout_v1` |
| symbol | BTCUSDT |
| start_ts_ms_utc | 1780702200000 (2026-06-05T23:30:00Z) |
| end_ts_ms_utc | 1780705800000 (2026-06-06T00:30:00Z) |
| Window width | 60 minutes (3600s) |
| Actual data span | 52.6 min (3154s from first to last event) |
| Event count | 11 |
| Event types | 4 SIGNAL, 4 DECISION, 2 ORDER, 1 FILL |
| Correlation IDs | 4 distinct chains |
| Paper-qualified ORDER | 2 (`paper_758f0ff9...`, `paper_4efa2f82...`) |
| Paper-qualified FILL | 1 (`paper_4efa2f82...`) |
| Causal context events | 0 |
| evidence_class | `natural_paper_evidence` |
| source_table | `public.correlation_ledger` |
| extracted_by | `issue3217_guarded_natural_paper` |
| produced_by | `paper_reference_window_runner` |

### 6.2 Chain Breakdown

| # | correlation_id | Events | Paper-qualified | Notes |
|---|---|---|---|---|
| 1 | `93a8fe65-f72f-5cdf-ae5b-c9d6989903e7` | SIGNAL + DECISION | No | 2026-06-05 23:36:38 UTC, no trade entry |
| 2 | `3c8aaa25-8f1f-5545-b2db-eaa90079b940` | SIGNAL + DECISION + ORDER | Yes (ORDER) | 2026-06-06 00:17:55 UTC, order entered but no fill in this window |
| 3 | `18a321c6-16de-5620-86c9-072edbc36cb2` | SIGNAL + DECISION | No | 2026-06-06 00:23:12 UTC, no trade entry |
| 4 | `0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab` | SIGNAL + DECISION + FILL + ORDER | Yes (ORDER + FILL) | 2026-06-06 00:29:12 UTC, complete chain — this is the existing #3028 window |

### 6.3 Timestamp Coverage

```
23:30    23:40    23:50    00:00    00:10    00:20    00:30 UTC
  |--------|--------|--------|--------|--------|--------|
                                                      #3028 chain (complete)
                                    #2 chain (ORDER only)
                        #3 chain (signal only)
  #1 chain (signal only) ← Jun 5
```

Actual data spans 52.6 minutes, concentrated in 4 brief bursts (<1s each) around 23:36, 00:17, 00:23, 00:29.

---

## 7. Contract Validation

Per #3215 §7 requirements:

| Requirement | Status | Detail |
|---|---|---|
| `contract_version = arvp_paper_reference_window.v1` | PASS | |
| `strategy_id` non-empty and consistent | PASS | `primary_breakout_v1` across all events |
| `symbol` non-empty and consistent | PASS | BTCUSDT across all events |
| `start_ts_ms < end_ts_ms` | PASS | 1780702200000 < 1780705800000 |
| All event timestamps inside window | PASS | All 11 events within [start, end] |
| Event types from SIGNAL/DECISION/ORDER/FILL | PASS | |
| `payload.strategy_id` present and matching | PASS | |
| At least one SIGNAL anchor | PASS | 4 SIGNAL anchors present |
| Every non-SIGNAL maps to SIGNAL | PASS | Chain integrity holds |
| At least one paper-qualified ORDER | PASS | 2 paper-prefixed orders |
| At least one paper-qualified FILL | PASS | 1 paper-prefixed fill |
| Provenance fields present | PASS | extracted_by, source_table, produced_at_utc |

**Contract result: PASS**

---

## 8. Window Bank Update

| # | Window ID | Width | Data span | Chains | Paper chains | Artifact |
|---|---|---|---|---|---|---|
| 1 | Pilot (paper_1909) | 1 min | ~0s | 1 | 1 | Not re-extracted (docs-backed) |
| 2 | #3028 (0c39ac88) | 2 min | ~0s | 1 | 1 | `artifacts/paper_reference_windows/paper_reference_window.json` |
| **3** | **June 6 1h** | **60 min** | **52.6 min** | **4** | **1 complete + 1 partial** | `artifacts/paper_reference_windows/paper_reference_window_june6_1h.json` |

**Current count: 3 comparison-grade window artifacts** (was 2 before #3217).

---

## 9. regime_segments Assessment

The 1-hour window artifact contains 11 discrete events across 4 disjoint bursts. It does not contain continuous price/time-series data. As with the existing 2 windows, `regime_segments` remain `unavailable` because:

1. The artifact captures only SIGNAL/DECISION/ORDER/FILL events, not tick/candle data
2. `regime_segments` are populated by a downstream comparison/regime stage, not by the window extraction itself
3. A longer window artifact is necessary but not sufficient for regime evidence

**Finding:** The 1-hour window is a necessary data increment for potential future regime assessment, but it does not resolve the A4 regime gap by itself. A3/A4 readiness remains WARN/FAIL per #3212.

---

## 10. Safety Boundaries

| Rule | Status |
|---|---|
| No Live-Go | Enforced — LR remains NO-GO |
| No Real-Money-Go | Enforced — no live capital |
| No Runtime Start | Enforced — no Docker/Compose commands |
| No DB mutation | Enforced — SELECT-only via cdb_readonly identity |
| No workflow_dispatch | Enforced |
| No secrets exposed | Enforced — env presence checked, values never printed |
| No issue closure | Enforced — #3217 remains OPEN |
| No strategy changes | Enforced |
| No Candidate #4 / PB1 / RMR / Momentum rescue | Enforced |

---

## 11. Verdict

**Decision: EXTRACTED_WINDOW_READY_FOR_REVIEW**

The guarded extraction route produced a contract-valid 60-minute paper reference window. The window contains 4 chains across 52.6 minutes of actual data span, with 1 complete paper-qualified chain and 1 partial paper-qualified ORDER chain.

The window does not change A4 regime readiness (regime_segments still produced by downstream stages, not window extraction). But it is a substantive improvement in window width (60 min vs previous best of 2 min) and chain count (4 vs previous best of 1).

This is not:
- A Product-Complete claim
- A Live-Go / Echtgeld-Go step
- A new candidate-family opening
- A strategy rescue path

---

## 12. Required Follow-up

1. **Downstream consumption:** The 1-hour window can now be used in replay-vs-paper comparison and calibration stages to test whether wider windows yield better regime evidence.
2. **Batch compare expansion:** The existing batch compare (#2971) ran on 2 windows. A re-run with 3 windows would increase calibration coverage.
3. **Regime evidence:** regime_segments must be evaluated by downstream comparison/regime tooling. This extraction does not short-circuit that.
4. **More paper data:** The correlation_ledger still has only 2 partial paper chains and 1 complete paper chain. New paper runtime execution (Human-GO gated per #2961 §6) is required for additional windows.

---

## 13. Stop Rules

- LR remains NO-GO.
- Board stage `trade-capable` is not Live-Go.
- No Live-Go / Echtgeld-Go.
- No Product-Complete claim.
- No runtime start.
- No Docker/Compose orchestration.
- No DB mutation.
- No secrets in outputs.
- No Candidate #4.
- No PB1/RMR/Momentum rescue.

---

## 14. Restunsicherheiten

1. The 1-hour window still captures only discrete events. Continuous price data is in separate tables/streams, not in `correlation_ledger`.
2. `regime_segments` cannot be determined from the window artifact alone; downstream stages are required.
3. The 14-day paper phase (#1784) produced extensive running logs but not correlation_ledger SIGNAL/DECISION/ORDER/FILL chains with paper_ prefix.
4. New paper runtime execution would be the most reliable way to produce more complete chains.

---

## 15. Status

`EXTRACTED_WINDOW_READY_FOR_REVIEW`

Bank: 3 window artifacts (pilot 1m + #3028 2m + June 6 1h).
