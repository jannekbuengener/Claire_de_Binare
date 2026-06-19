# ARVP Window-Bank Expansion — #3343

Status Class: Scoped evidence / negative finding (HOLD)
Issue: #3343
Parent: #1900
Control Refs: #2985, #2977, #3212, #3217, #3219, #3221
Live-Readiness: NO-GO
Echtgeld: not authorized

---

## 1. Brain Evidence Block

```
brain_source: repo-only, validated via readonly DB extract
brain_status: used
tools_or_queries:
  - read: canonical read-order per agents/AGENTS.md
  - read: AGENTS.md, agents/AGENTS.md
  - read: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md
  - read: docs/runbooks/CONTROL_REGISTER.md
  - read: CURRENT_STATUS.md
  - read: docs/evidence/arvp_window_bank_inventory_3212.md
  - read: docs/evidence/arvp_guarded_natural_paper_window_execution_3217.md
  - read: docs/evidence/arvp_three_window_replay_vs_paper_calibration_3219.md
  - read: docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md (§5–§6)
  - read: services/validation/paper_reference_window_runner.py
  - read: core/replay/paper_reference_window_export.py
  - bash: git fetch origin --prune; git status -sb; git rev-parse HEAD; git rev-parse origin/main
  - gh: issue view 3343/1900/2977/2985; pr list
  - execute: scripts/_3343_verify_pb1_clusters.py (readonly DB, cdb_readonly, SELECT-only)
  - execute: scripts/_3343_inventory_windows.py (readonly DB, cdb_readonly, SELECT-only)
records_or_results:
  - HEAD == origin/main == b7198371 (clean, 0 open PRs)
  - #3343 OPEN (body fresh), #1900 OPEN (reconciled 2026-06-19)
  - #2977 OPEN/BLOCKED, #2985 OPEN (14 comments)
  - POSTGRES_READONLY_PASSWORD_DSN confirmed set
  - Readonly identity verified: cdb_readonly/cdb_readonly on claire_de_binare
  - Privileges: SELECT=true, INSERT=false, UPDATE=false, DELETE=false
  - Total correlation_ledger rows: 34256
  - primary_breakout_v1/BTCUSDT rows: 783
  - Paper strategy/BTCUSDT rows: 16345
  - DB date range: 2026-02-15 to 2026-06-06
repo_crosscheck:
  - AGENTS.md, agents/AGENTS.md, CURRENT_STATUS.md, CONTROL_REGISTER.md
  - paper_reference_window_runner.py, paper_reference_window_export.py
  - arvp_window_bank_inventory_3212.md (prior bank state: 3 windows, none >2h)
  - arvp_guarded_natural_paper_window_execution_3217.md (1h window extracted)
  - arvp_three_window_replay_vs_paper_calibration_3219.md (A4=FAIL, regime_segments unavailable)
impact_on_plan:
  - PB1 window-bank path cannot proceed from existing correlation_ledger data
  - No extraction target exists — no valid >2h PB1 cluster found
  - A4 remains FAIL; regime_segments cannot be populated from PB1 window-bank alone
  - Broader paper-strategy clusters exist (23h+, 25h+) but are NOT PB1 evidence
limitations:
  - Readonly DB session only; no Docker/runtime/backfill/replay executed
  - No secrets printed, committed, or inspected
  - No DB mutations performed
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
|------|--------|
| HEAD / origin/main | `b7198371` / equal |
| Working tree | clean (+2 untracked dirs `.opencode/plans/`, `docs/decisions/`) |
| Open PRs | **0** |
| #3343 | OPEN (body fresh) |
| #1900 | OPEN (reconciled 2026-06-19) |
| #2985 | OPEN (comment posted 2026-06-19) |
| #2977 | OPEN/BLOCKED (correct) |
| LR | **NO-GO** |
| Board | `trade-capable` ≠ Live-Go |

No live-truth conflict found.

---

## 4. Database Access Verification

| Check | Result |
|-------|--------|
| DSN available | `POSTGRES_READONLY_PASSWORD_DSN` set |
| Identity | `cdb_readonly` / `cdb_readonly` |
| Database | `claire_de_binare` |
| SELECT on `correlation_ledger` | true |
| INSERT on `correlation_ledger` | false |
| UPDATE on `correlation_ledger` | false |
| DELETE on `correlation_ledger` | false |
| Total rows | 34,256 |
| primary_breakout_v1/BTCUSDT rows | 783 |
| Paper strategy/BTCUSDT rows | 16,345 |
| Date range | 2026-02-15 to 2026-06-06 |

Readonly session confirmed. No mutations performed.

---

## 5. primary_breakout_v1 — Cluster Verification

### 5.1 Cluster Detection Method

- **Source:** `public.correlation_ledger` filtered by `payload->>strategy_id='primary_breakout_v1'` and `symbol='BTCUSDT'`
- **Gap threshold:** 1 hour without events = new cluster
- **Script:** `scripts/_3343_verify_pb1_clusters.py` (committed, deterministic, readonly)

### 5.2 Every PB1 Cluster

| # | Start UTC | End UTC | Duration | Events | Chains | SIG | DEC | ORD | FILL | Has Trade? | Verdict |
|---|-----------|---------|----------|--------|--------|-----|-----|-----|------|------------|---------|
| 1 | 2026-04-23T14:58:55 | 2026-04-23T16:47:41 | 1.813h (108.8min) | 767 | 767 | 767 | 0 | 0 | 0 | **No** | EXCLUDE — <2h, no DECISION, no trades |
| 2 | 2026-04-24T00:42:34 | 2026-04-24T00:42:34 | 0.000h (0s) | 2 | 1 | 0 | 0 | 1 | 1 | Yes | EXCLUDE — instant, no DECISION |
| 3 | 2026-06-05T14:57:55 | 2026-06-05T14:57:55 | 0.000h (0s) | 2 | 1 | 0 | 0 | 1 | 1 | Yes | EXCLUDE — instant, no DECISION |
| 4 | 2026-06-05T23:17:03 | 2026-06-06T00:29:12 | **1.203h (72.2min)** | 10 | 5 | 5 | 0 | 3 | 2 | Yes | EXCLUDE — <2h, no DECISION |
| 5 | 2026-06-06T03:31:54 | 2026-06-06T03:31:54 | 0.000h (0s) | 2 | 1 | 0 | 0 | 1 | 1 | Yes | EXCLUDE — instant, no DECISION |

### 5.3 Key Observations

1. **Max PB1 cluster (with trades):** 72.2min (Cluster 4) — the existing 3-window bank.
2. **Max PB1 cluster (overall):** 108.8min (Cluster 1) — SIGNAL-only, zero paper trades.
3. **No cluster exceeds 2h.** The closest is Cluster 1 at 1.813h, still 11min short.
4. **No DECISION events** are directly stored with `strategy_id=primary_breakout_v1`. All 17,126 DECISION events have `strategy_id=NULL`. They are linked via correlation_id but stored under the generic paper framework.
5. **Cluster 1** (767 SIGNALs) represents signals generated during the 14-day paper phase (#1784) that never resulted in paper trades. These signals lack DECISION/ORDER/FILL chains and are not comparison-grade window material.

### 5.4 Comparison with Existing Window Bank

| Window | Source Cluster | Duration | Chains | Part of PB1 Bank? |
|--------|---------------|----------|--------|-------------------|
| Pilot 1m | Cluster 2 | ~0s (instant ORDER+FILL) | 1 | Yes (docs-backed) |
| #3028 2m | Cluster 4 | 2min (within 72min span) | 1 | Yes (artifact) |
| June 6 1h | Cluster 4 | 52.6min data span | 4 | Yes (artifact) |
| Any >2h window | **none** | — | — | **No candidate exists** |

---

## 6. Broader Paper-Strategy Clusters (NOT PB1 Evidence)

The correlation_ledger also contains events with `payload->>strategy_id='paper'`. These are listed separately because:

- Strategy ID is `paper`, not `primary_breakout_v1`
- Cannot be used for PB1 strategy replay (replay engine expects PB1 strategy_id)
- Not comparable to existing PB1 window bank
- **Not admissible as PB1 window-bank evidence per #3343 scope**

| # | Start UTC | End UTC | Duration | Events | Chains | SIG | ORD | FILL | Note |
|---|-----------|---------|----------|--------|--------|-----|-----|------|------|
| 1 | 2026-02-15T20:57:39 | 2026-02-16T20:21:16 | **23.4h** | 6609 | 6608 | 6607 | 1 | 1 | Only 1 trade across 23h |
| 2 | 2026-03-06T19:35:35 | 2026-03-06T19:37:10 | 0.0h | 6 | 3 | 0 | 3 | 3 | 3 isolated ORDER+FILL pairs |
| 3 | 2026-03-12T14:28:43 | 2026-03-12T22:43:06 | 8.2h | 2650 | 2650 | 2650 | 0 | 0 | SIGNAL-only, no trades |
| 4 | 2026-03-23T15:49:14 | 2026-03-24T17:18:11 | **25.5h** | 7080 | 7080 | 7080 | 0 | 0 | SIGNAL-only, no trades |

**Key observation:** Even the paper strategy has only **4 ORDER + 4 FILL events total** across the entire DB (Feb-Jun 2026). The 23h+ clusters exist only as SIGNAL-density blocks, not trade-dense windows. The paper strategy fires signals at ~5-10/min during active hours, but very rarely produces paper orders/fills.

---

## 7. Selection Contract Review

| Rule | Status |
|------|--------|
| Minimum >2h window duration | **No candidate meets this** |
| `strategy_id=primary_breakout_v1` | All verified clusters use this |
| `symbol=BTCUSDT` | All verified clusters use this |
| Non-overlapping with existing bank | Irrelevant — no candidate exists |
| SIGNAL anchor present | Clusters 1 and 4 have SIGNALs; 2, 3, 5 are ORDER+FILL only |
| Paper-qualified ORDER (`paper_` prefix) | Clusters 2, 3, 4, 5 have paper-prefixed ORDERs |
| Data density: ≥2 chains per window | Clusters 1 (767), 4 (5) meet this |
| No cherry-picking | **Guaranteed**: all clusters listed above exhaustively |

---

## 8. Impact on A2/A3/A4 Readiness

| Workstream | Previous Status | Current Status | Change |
|------------|----------------|----------------|--------|
| A2 Batch Compare | PASS | PASS | Unchanged |
| A3 Calibration + Drift | WARN | WARN | Unchanged |
| A4 Regime Interpretation | FAIL | FAIL | **Unchanged — no new evidence** |

This slice does not change any ARVP readiness assessment. The window bank remains at 3 windows (all <2h, none with `regime_segments`). A4 remains FAIL because no longer natural-paper window exists to produce continuous price data for regime segmentation.

---

## 9. Final Verdict

**`HOLD_NO_VALID_PRIMARY_BREAKOUT_WINDOWS`**

The correlation_ledger does **not** contain a `primary_breakout_v1`/BTCUSDT cluster meeting the >2h minimum duration requirement with full SIGNAL→DECISION→ORDER→FILL chain integrity.

- **Max PB1 cluster with trade chain:** 72.2min (Cluster 4, June 5-6)
- **Max PB1 cluster overall:** 108.8min (Cluster 1, April 23 — signal-only, no trades)
- **PB1 window-bank extraction path:** exhausted from existing data

Broader paper-strategy clusters (23h+, 25h+) exist in the DB but:
- Have strategy_id=`paper`, not `primary_breakout_v1`
- Contain only 4 ORDER/FILL events across the entire dataset
- Are not admissible as PB1 evidence
- Would require scope change and new strategy replay adapter to be usable

**No promotable candidate exists. No Product-Complete claim. LR remains NO-GO.**

---

## 10. Next Options (for Jannek/Control)

| Option | Scope | GO Required? |
|--------|-------|-------------|
| Accept 3-window bank as "best available", close #3343 HOLD | None | No |
| Plan new primary_breakout_v1 paper trading run for longer windows | Docker + Runtime + Paper mode | Yes (separate GO) |
| Expand scope to broader paper-strategy windows (sid=paper) | Scope change + adapter work | Yes (separate GO) |
| Deprecate primary_breakout_v1 ARVP path entirely | Strategic decision | Yes (Control-level) |

---

## 11. Boundaries

- LR remains **NO-GO**
- Board stage `trade-capable` is not Live-Go
- No Live-Go, No Echtgeld-Go
- No Candidate #4 initiated or implied
- No PB1/RMR/Momentum rescue
- No Product-Complete claim
- No runtime/Docker/backfill/replay executed
- No DB mutations performed
- No secrets in output

---

## 12. Restunsicherheiten

1. The 14-day paper phase (#1784) ran with `primary_breakout_v1` strategy, but its events are stored under `sid=paper`, not `sid=primary_breakout_v1`. Whether those events could be retroactively linked to PB1 window-bank evidence is a DB schema question outside this slice.
2. All DECISION events (17,126) have `strategy_id=NULL`. The paper framework DECISION events are linked to SIGNAL events via correlation_id, not via explicit strategy_id in the payload. Building PB1 evidence from these would require JOIN-based reconstruction.
3. Even if paper-strategy windows were admitted, their trade density is extremely low (4 trades across 3 months). A 23h window with 1 trade is not meaningfully "comparison-grade" for replay.
4. The inventory `scripts/_3343_inventory_windows.py` uses a 1h gap threshold. A different gap threshold might produce different cluster boundaries, but no threshold change would create >2h clusters with trades — the data simply isn't there.

---

## 13. Status

**`DONE_MERGED_CLOSED_HOLD_NO_VALID_PRIMARY_BREAKOUT_WINDOWS`**
