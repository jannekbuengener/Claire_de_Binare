# ARVP Window Bank Extraction — #2961 A1 Readonly Check (2026-06-04)

Status: **HOLD** — no additional comparison-grade paper reference windows extractable
Parent: #2961
Roadmap: Phase A1 (`docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`)
Live-Readiness: **NO-GO** (unchanged)
Echtgeld: **not authorized**

---

## 1. Brain Evidence

```
## Brain Evidence
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - bootloader: AGENTS.md, agents/AGENTS.md, CDB_AGENT_POLICY.md
  - LR SSOTs: LR-AUDIT-STATUS-2026-03-05.md, GO_NO_GO.md
  - ARVP docs: arvp_platform.md, arvp_paper_reference_contract.md
  - Evidence: arvp_calibration_batch_2961_2026-06-04.md, arvp_calibration_pilot_1932_2026-04-26.md
  - Roadmap: ARVP_TO_LIVE_GO_ROADMAP_2026-06.md
  - Code: services/validation/paper_reference_window_runner.py, core/replay/paper_reference_window_export.py
  - Live: git fetch/status/rev-parse, gh issue view 2961/1900/1784, gh pr list
  - DB readonly: docker exec cdb_postgres psql (SELECT-only, no writes)
records_or_results:
  - paper_reference_window_runner.py: safe (readonly, identity/privilege verified) but requires cdb_readonly user + POSTGRES_READONLY_PASSWORD_DSN — neither configured
  - correlation_ledger: 34,237 rows, ALL event types present, ONLY BTCUSDT
  - paper-prefixed ORDER/FILL: 1 (paper_1909_1776991354682 — existing pilot window)
  - All other ORDER/FILL: MOCK_* prefixed (mock trading, not paper)
  - Latest data: 2026-04-24T00:42:34Z (pilot window)
repo_crosscheck:
  - HEAD = origin/main = 3efb1e18 (roadmap merged)
  - No open PRs
  - #2961 OPEN, #1900 OPEN, #1784 OPEN
impact_on_plan:
  - extraction-first cannot yield additional windows from existing correlation_ledger
  - new paper trading execution with paper_ prefix correlation_ledger writes is required
  - runner is safe but needs cdb_readonly user setup first
limitations:
  - Could not test runner directly (missing DSN + user)
  - DB inspection via docker exec — read-only SELECT queries, no writes
  - historical_bridge.py BTCUSDT-only limitation not addressed here
```

---

## 2. Runner Safety Analysis

### 2.1 Code-Level Safety Verdict

`services/validation/paper_reference_window_runner.py` is **provably read-only**:

| Aspect | Status | Detail |
|--------|--------|--------|
| DB writes | **None** | Only `SELECT` against `correlation_ledger` by `symbol` + `timestamp_ms` range |
| Identity check | Fail-closed | Requires `current_user` = `cdb_readonly` — not `claire_user` |
| Privilege check | Fail-closed | Verifies `SELECT`=yes, `INSERT`=`UPDATE`=`DELETE`=no |
| Env var | `POSTGRES_READONLY_PASSWORD_DSN` | Explicit readonly DSN, not generic DATABASE_URL |
| Output | File write only | `artifacts/paper_reference_windows/paper_reference_window.json` |
| Network | Postgres only | No exchange, broker, or external API calls |
| Docker | None | No container orchestration |

### 2.2 Runtime Preconditions (not met)

| Precondition | Status | Reason |
|-------------|--------|--------|
| `POSTGRES_READONLY_PASSWORD_DSN` env var | **NOT SET** | Not configured in shell or compose |
| `cdb_readonly` Postgres role | **NOT CONFIGURED** | Docker compose uses `claire_user`, no readonly role defined |
| Postgres running | **YES** | `cdb_postgres` container healthy, uptime 4h+ |
| `correlation_ledger` table | **YES** | Table exists, 34,237 rows |

### 2.3 Why the Runner Cannot Be Executed Now

Creating the `cdb_readonly` user requires a DB mutation (CREATE ROLE, GRANT SELECT), which is explicitly forbidden by the stop rules ("Keine produktive DB-Mutation"). Even if the user were created, the `POSTGRES_READONLY_PASSWORD_DSN` would contain a secret value that cannot be committed or hardcoded.

**Decision**: Runner not executed. Readonly DB inspection performed via `docker exec` as fallback.

---

## 3. correlation_ledger Data Inventory

### 3.1 Table Statistics

| Metric | Value |
|--------|-------|
| Total rows | 34,237 |
| Earliest event | 2026-02-16T09:54:23.718Z (MOCK order) |
| Latest event | 2026-04-24T00:42:34.803Z (paper fill from pilot) |
| Symbols | BTCUSDT (only) |
| Strategy IDs | primary_breakout_v1 (in SIGNAL payload) |

### 3.2 Event Type Distribution

| Event Type | Count |
|-----------|-------|
| SIGNAL | 17,104 |
| DECISION | 17,121 |
| ORDER | 6 |
| FILL | 6 |

### 3.3 ORDER/FILL Identity

| order_id | Type | Count | Paper-Qualified |
|----------|------|-------|-----------------|
| MOCK_37400562 | MOCK | 2 (ORDER + FILL) | No |
| MOCK_52185555 | MOCK | 2 (ORDER + FILL) | No |
| MOCK_54538499 | MOCK | 2 (ORDER + FILL) | No |
| MOCK_90409546 | MOCK | 2 (ORDER + FILL) | No |
| MOCK_41250577 | MOCK | 2 (ORDER + FILL) | No |
| paper_1909_1776991354682 | PAPER | 2 (ORDER + FILL) | **Yes — existing pilot window** |

### 3.4 Paper Window Count

| Category | Count | Window IDs |
|----------|-------|-----------|
| Comparison-grade paper windows | **1** | `paper_1909_1776991354682` (2026-04-24T00:42Z) |
| Additional paper windows | **0** | N/A |
| MOCK-trade windows (not paper) | **5** | MOCK_* (not comparison-grade for ARVP) |

---

## 4. Gap Analysis: Why Only 1 Paper Window

### 4.1 The 14-Day Paper Phase (#1784) and correlation_ledger

The 14-day paper phase ran from approximately April 24 through May 8, 2026. Multiple operator checkpoints in #1784 confirm:
- Stack healthy (cdb_paper_runner, cdb_execution, cdb_risk, cdb_signal all healthy)
- Event logs growing (80,686 events in one session, 233,450 cumulative)
- Market data provenance PASS (84,384 MEXC tick entries for BTCUSDT)

However, **the latest `correlation_ledger` entry is April 24, 2026 00:42 UTC** — the exact timestamp of the pilot window ORDER/FILL. This means:

1. The 14-day paper phase (#1784) ran AFTER the pilot was captured
2. The `paper_reference_window_export.py`'s contract requires events to be in `correlation_ledger` (`source_table: public.correlation_ledger`)
3. The correlation_ledger did not receive additional paper-prefixed ORDER/FILL entries during the 14-day phase

### 4.2 Possible Explanations

| Hypothesis | Likelihood | Evidence |
|-----------|-----------|----------|
| Paper trading events during #1784 wrote to correlation_ledger but with MOCK_* prefix, not paper_* | Medium | Execution config defaults to MOCK_TRADING=true |
| Paper trading events during #1784 were not written to correlation_ledger at all | High | The paper runner (#1784) log shows `events_logged: 80686` but these go to JSONL logs, not necessarily correlation_ledger |
| correlation_ledger writes stopped after the pilot | High | Latest timestamp is exactly the pilot window end |
| Phase 8C correlation_ledger writes are gated behind a config flag | Possible | The execution service has `ALLOW_EVIDENCE_DEBT` toggle; may have been disabled during paper phase |

### 4.3 The Operational Reality

The `paper_reference_window_export.py` contract requires `source_table: public.correlation_ledger`. Any paper reference window must come from there. The 14-day paper phase (#1784) produced extensive event logs and observable behavior, but those events are:
- Either in `logs/events/events_*.jsonl` (runner logs, not correlation_ledger)
- Or in PostgreSQL `orders`/`trades`/`positions` tables (not comparison-grade per contract)
- Or in correlation_ledger with `MOCK_*` prefix (not paper-qualified)

**None of these sources produce additional comparison-grade `paper_reference_window.v1` entries.**

---

## 5. Verdict

### Decision: HOLD — extraction-first exhausted; new paper runtime needed

| Criterion | Status |
|-----------|--------|
| Additional windows found | **0** |
| Existing windows confirmed | **1** (same pilot) |
| Readonly extraction possible | **No** — runner needs `cdb_readonly` user (not configured) |
| Alternative discovery possible | Readonly DB inspection confirmed: no additional paper windows |
| New runtime needed for more windows | **Yes** — staged/shadow paper trading with paper_ prefix correlation_ledger writes |

### Classification

This is a **HOLD (type: data-gap)** — not a failure. The extraction-first strategy was correct, but it produced exactly the same result as the prior window selection analysis on #2961: the repo (in this case, the correlation_ledger database) contains only **1 comparison-grade paper reference window**.

---

## 6. Next Step

### Prerequisite: New Staged/Shadow Paper Trading Runtime

To produce 2+ additional comparison-grade paper reference windows, the following is needed:

1. **Configure `cdb_readonly` Postgres role** — a one-time DB setup for safe extraction
2. **Set `POSTGRES_READONLY_PASSWORD_DSN`** — a secret-managed env var for the runner
3. **Run the paper trading stack** under `MOCK_TRADING=true`, `DRY_RUN=true` with paper_ prefix correlation_ledger writes
4. **Run the stack long enough** to produce meaningful windows (hours, not minutes)
5. **Extract windows** using `paper_reference_window_runner.py` with readonly DSN

**Critical**: Steps 1–2 are infrastructure setup (not runtime). Step 3 is a human-GO-gated operator action — not something any agent can do autonomously. The roadmap's stop rules apply: no runtime start, no Docker commands, no workflow_dispatch without explicit human GO.

### Recommendation

The roadmap correctly identifies this as a bottleneck. Before Phase A1 can advance:
- A human operator decision is needed: "GO — run paper staging/shadow to produce additional correlation_ledger paper windows"
- The `cdb_readonly` user must be created
- The stack must run long enough to produce comparison-grade data

Until then, the ARVP window bank remains at **1 window**.

---

## 7. Safety Boundaries

| Rule | Status |
|------|--------|
| No Live-Go | Enforced — LR remains NO-GO |
| No Real-Money-Go | Enforced — no live capital |
| No Runtime Start | Enforced — Docker containers were already running; no new starts initiated |
| No Docker commands (mutating) | Enforced — only `docker exec` with SELECT queries |
| No workflow_dispatch | Enforced |
| No productive DB mutation | Enforced — only SELECT queries on existing container |
| No secrets exposed | Enforced — no env var values, no DSN strings, no passwords |
| No issue closure | Enforced — #2961, #1900, #1784 remain OPEN |

---

## 8. Sources

- `services/validation/paper_reference_window_runner.py` — runner code (217 lines, verified readonly)
- `core/replay/paper_reference_window_export.py` — export logic (377 lines)
- `infrastructure/compose/compose.blue.yml` — Postgres container config
- `docs/governance/arvp_paper_reference_contract.md` — paper reference contract v1
- `docs/evidence/arvp_calibration_batch_2961_2026-06-04.md` — existing batch seed
- `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md` — pilot evidence
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md` — roadmap Phase A1
- `correlation_ledger` (readonly SELECT via docker exec) — 34,237 rows inspected
- GitHub: #2961 (OPEN), #1900 (OPEN), #1784 (OPEN)

---

## 9. Post-Closeout Reconciliation (2026-06-06)

### 9.1 Downstream Closeout Summary

Since this extraction report was written (2026-06-04), the following closeout chain has
completed:

| Issue | Title | Status |
|-------|-------|--------|
| #2967 | cdb_readonly Postgres role + DSN | DONE |
| #2968 | Paper runtime — produce new paper-prefixed windows | **CLOSED** |
| #2969 | Window-bank extraction — extract comparison-grade windows | **CLOSED** |
| #3028 | Paper reference window artifact commit | **MERGED** (`af01c76c`) |

### 9.2 Updated Window Bank

The extraction-first HOLD documented in section 5 has been partially resolved:

| # | Window ID | Symbol | Strategy | Provenance | Artifact |
|---|-----------|--------|----------|-------------|----------|
| 1 | `paper_1909_1776991354682` | BTCUSDT | primary_breakout_v1 | Pilot (2026-04-24) | Docs-backed only |
| 2 | `0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab` | BTCUSDT | primary_breakout_v1 | #3028 (`af01c76c`) | `artifacts/paper_reference_windows/paper_reference_window.json` |

**Current count: 2 comparison-grade windows** (was 1 at the time of original extraction report).

### 9.3 Remaining Gap

- **Target: 3+** for full multi-window batch calibration (`#2971`)
- Calibration on window #2 not yet run (requires replay via Docker stack → Human-GO)
- 3rd window requires additional paper runtime execution → Human-GO

### 9.4 Updated Verdict

Original verdict (section 5) remains valid as a historical record. The post-closeout
update is:

- **`batch_seed_count`**: 1 → **2**
- **`multi_window_coverage`**: still `HOLD` (target 3+)
- **Next step**: calibration on 2-window bank (replay needed for window #2), or 3rd window generation

### 9.5 Safety

- LR remains **NO-GO**
- No Live-Go / Echtgeld-Go
- #2961 remains OPEN
- ARVP evidence does not imply Live-Go