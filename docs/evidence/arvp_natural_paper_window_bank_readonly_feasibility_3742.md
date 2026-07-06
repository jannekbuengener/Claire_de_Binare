# ARVP Natural-Paper Window Bank — Readonly Feasibility (#3742)

Status Class: Scoped evidence — readonly access repaired; data verdict HOLD_NO_VALID_WINDOWS_READONLY
Issue: #3742
Parent: #1900
Control Refs: #2985, #3343, #3212, #3217, #3219, #2974
Live-Readiness: NO-GO
Echtgeld: not authorized

---

## 1. Brain Evidence Block

```text
brain_source: repo-only
brain_status: used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none

tools_or_queries:
  - read: canonical read-order per agents/AGENTS.md
  - read: AGENTS.md, agents/AGENTS.md
  - read: CURRENT_STATUS.md
  - read: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md
  - read: docs/runbooks/CONTROL_REGISTER.md
  - read: scripts/arvp_3742_natural_paper_window_inventory.py
  - read: infrastructure/database/operator_create_readonly_login.sql
  - read: docs/evidence/arvp_window_bank_expansion_regime_segments_3343.md
  - read: docs/evidence/arvp_three_window_replay_vs_paper_calibration_3219.md
  - bash: git fetch origin --prune; git status -sb; git rev-parse HEAD; git rev-parse origin/main
  - gh: issue view 3742/1900/2985; pr list --state open --limit 20
  - execute: python scripts/arvp_3742_natural_paper_window_inventory.py (readonly preflight attempt)
  - execute: ruff check scripts/arvp_3742_natural_paper_window_inventory.py

records_or_results:
  - HEAD == origin/main == 782ab3f3dc59dd78af5b3e8916141c3b29c0d96b
  - open PRs: 0
  - #3742 OPEN; #1900 OPEN; #2985 OPEN
  - POSTGRES_READONLY_PASSWORD_DSN env: SET (value not inspected or printed)
  - operator DSN file POSTGRES_READONLY_PASSWORD_DSN: exists under operator credential store
  - cdb_postgres container: Up, healthy
  - readonly connection: FAIL — authentication failed for user cdb_readonly
  - script exit: 1, VERDICT_ENUM: HOLD_READONLY_ACCESS_UNAVAILABLE
  - ruff check on inventory script: PASS

repo_crosscheck:
  - docs/evidence/arvp_window_bank_expansion_regime_segments_3343.md (prior PB1 readonly negative finding)
  - docs/evidence/arvp_three_window_replay_vs_paper_calibration_3219.md (A4 FAIL, regime_segments unavailable)
  - infrastructure/database/operator_create_readonly_login.sql (operator-only readonly login repair path)
  - services/validation/paper_reference_window_runner.py (same cdb_readonly contract)

impact_on_plan:
  - #3742 DB cluster inventory not executed — blocked before SELECT queries
  - ARVP §5.2.4 regime_segments gap cannot be re-assessed from live DB in this slice
  - Prior artifact evidence (#3219, #3343) remains authoritative for window-bank / A4 state
  - Next step is operator readonly-login repair, then script re-run — not ARVP data rescue

limitations:
  - No live cluster inventory rows produced in this session
  - No DB-backed brain claims; no MCP mutation; no Docker/Runtime/Replay executed
  - Auth failure root cause not fully isolated (stale credential vs missing role) — repair path documented only
  - No credential values printed, committed, or inspected in outputs
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

- LR SSOT: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — **NO-GO**
- Board stage `trade-capable` is not Live-Go (`docs/runbooks/CONTROL_REGISTER.md`)
- `CURRENT_STATUS.md` is ledger, not live GitHub truth
- No credential values printed, committed, or inspected

---

## 3. Live-Lage (Git / GitHub)

| Item | Status |
|------|--------|
| Branch at session start | `main` |
| HEAD / origin/main | `782ab3f3` / equal |
| Working tree | clean except new inventory script + this evidence slice |
| Open PRs | **0** |
| #3742 | **OPEN** |
| #1900 | **OPEN** (parent; §5.2.4 NOT MET) |
| #2985 | **OPEN** (meta navigation) |
| LR verdict | **NO-GO** |
| Board stage | `trade-capable` (not Live-Go) |

---

## 4. Readonly Preflight Result

| Check | Result |
|-------|--------|
| `POSTGRES_READONLY_PASSWORD_DSN` env present | **Yes** (redacted — no value recorded) |
| Operator DSN file present | **Yes** (path only; no content read into evidence) |
| Target host/port reachable | **Yes** — TCP connection reached Postgres |
| `cdb_postgres` container | **Up, healthy** |
| Login principal | `cdb_readonly` (from DSN user component; value not printed) |
| Authentication | **FAIL** — `authentication failed for user "cdb_readonly"` |
| Identity/privilege probe (`current_user`, SELECT-only) | **Not reached** — failed at connect |
| DB mutations | **None** |

Preflight conclusion: readonly access surface is configured at the operator layer, but the database login is not currently usable. This is an **access hold**, not an ARVP data-negative finding.

---

## 5. Script Result

Inventory script: `scripts/arvp_3742_natural_paper_window_inventory.py`

Purpose (planned when auth succeeds):

- Exhaustive cluster inventory for admissible natural-paper sources (`primary_breakout_v1`, `paper`, `paper_`-qualified chains)
- Per-candidate classification: comparable / non-comparable / inadmissible
- `regime_segments` feasibility flags
- Optional `candles_1m` coverage probe (SELECT-only)

Execution output (this session):

```text
=== #3742 Natural-Paper Window Bank Inventory ===
DSN env: POSTGRES_READONLY_PASSWORD_DSN=SET (value not printed)

FATAL: readonly PostgreSQL connection failed
error_class: OperationalError
hint: verify POSTGRES_READONLY_PASSWORD_DSN operator config, cdb_readonly role, and that cdb_postgres is reachable on the DSN host/port
VERDICT_ENUM: HOLD_READONLY_ACCESS_UNAVAILABLE
```

| Item | Result |
|------|--------|
| Exit code | 1 (fail-closed) |
| Cluster rows emitted | 0 |
| `ruff check` | PASS |

---

## 6. Auth-Failure Diagnosis

Observed failure mode:

- Postgres is running and accepting connections.
- The readonly DSN is present in the operator environment.
- Authentication for `cdb_readonly` fails before any inventory SQL executes.

Likely causes (not fully proven without operator DB inspection):

1. `cdb_readonly` role credential in Postgres does not match the canonical operator value backing `POSTGRES_READONLY_PASSWORD_DSN`.
2. `cdb_readonly` login was never applied or was rotated without updating the operator DSN file.
3. DSN points at the correct host/port but references a stale credential.

**This slice did not:**

- Print or commit any DSN or credential value
- Run `operator_create_readonly_login.sql`
- Perform any DB write or role mutation
- Start Docker, runtime, replay, or backfill

Operator repair path (separate GO):

1. Load `CDB_READONLY_PASSWORD` from the canonical operator credential store (not into repo/chat).
2. Apply [`infrastructure/database/operator_create_readonly_login.sql`](../../infrastructure/database/operator_create_readonly_login.sql) as superuser/operator.
3. Verify with [`infrastructure/database/verify_privileges.sql`](../../infrastructure/database/verify_privileges.sql).
4. Re-run `python scripts/arvp_3742_natural_paper_window_inventory.py`.

---

## 7. Classification Matrix (This Slice)

| Surface | Status | Notes |
|---------|--------|-------|
| DB cluster inventory | **not executed** | Blocked by readonly auth failure |
| DB trade-dense cluster verdict | **not assessable** | No SELECT session established |
| Repo artifact window bank | **unchanged** | Prior 3-window bank still best available evidence |
| `regime_segments` on existing bank | **unavailable** | Per #3219 / #3212 — A4 FAIL |
| PB1-only readonly expansion (#3343) | **still valid prior finding** | Not superseded — simply not re-run live |
| §5.2.4 Product-Complete gate | **NOT MET** | No new evidence produced |
| Compare/replay path for regime_segments | **not in scope** | Requires separate Runtime/Replay GO |

---

## 8. Verdict (Prior Session — 2026-07-05)

**`HOLD_READONLY_ACCESS_UNAVAILABLE`** *(superseded by §13 post-repair rerun; retained as prior state)*

Why this verdict (and not a data verdict):

- The inventory script fail-closed at PostgreSQL authentication.
- No cluster inventory or extraction attempt reached `correlation_ledger`.
- Therefore this slice cannot honestly claim `HOLD_NO_VALID_WINDOWS_READONLY`, `REQUIRES_RUNTIME_GO_FOR_FRESH_PAPER`, or `WINDOW_EXTRACTED_*` from live DB evidence.

What remains true from prior repo-backed evidence:

- ARVP Phase A §5.2.4 (`regime_segments`) is still **NOT MET** (#2974, #3219).
- Window bank remains 3 windows with **regime_segments unavailable** on all (#3219).
- #3343 PB1-only readonly expansion was exhausted under a working readonly session (2026-06-19).

**#3742 stayed OPEN** pending operator readonly repair and inventory re-run.

---

## 13. Post-Access-Repair Rerun (2026-07-06)

Operator Human-GO applied for `cdb_readonly` login repair and SELECT-only inventory re-run.

### 13.1 Brain Evidence Block

```text
brain_source: repo-only
brain_status: used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none

tools_or_queries:
  - read: agents/AGENTS.md, docs/evidence/arvp_natural_paper_window_bank_readonly_feasibility_3742.md
  - gh: issue view 3742/1900/2985/2974/3219/3343; pr view 3767
  - bash: git fetch; git switch ops/3742-readonly-login-repair-inventory-rerun @ b3076fa
  - operator: roles_and_grants.sql (prerequisite — missing cdb_* roles on fresh cdb_postgres)
  - operator: operator_create_readonly_login.sql via claire_user superuser
  - operator: verify_privileges.sql
  - execute: python scripts/arvp_3742_natural_paper_window_inventory.py
  - fix: scripts/arvp_3742_natural_paper_window_inventory.py candles_1m column ts_ms (was open_time_ms)

records_or_results:
  - HEAD base: b3076fa76ce79fd9eb4241ce86122002294a3b55 (origin/main)
  - cdb_postgres: Up, healthy
  - POSTGRES_READONLY_PASSWORD_DSN env: SET (not printed)
  - POSTGRES_READONLY_PASSWORD operator credential file: EXISTS (not printed)
  - roles_and_grants.sql: applied — cdb_reader/cdb_writer/cdb_admin created
  - operator_create_readonly_login.sql: applied — cdb_readonly LOGIN created
  - verify_privileges: PASS — cdb_readonly LOGIN, not superuser, member of cdb_reader only
  - correlation_ledger effective: SELECT=yes, INSERT/UPDATE/DELETE=no
  - candles_1m effective: SELECT=yes, write=no
  - inventory: 34256 correlation_ledger rows; 12 clusters scanned
  - trade-dense clusters (paper ORDER+FILL): 6; >=2h span: 0; new comparable: 0
  - VERDICT_ENUM: HOLD_NO_VALID_WINDOWS_READONLY
  - artifact: artifacts/evidence/arvp_3742_readonly_inventory/inventory_rerun_2026-07-06.txt

repo_crosscheck:
  - docs/evidence/arvp_window_bank_expansion_regime_segments_3343.md (prior PB1 negative)
  - docs/evidence/arvp_three_window_replay_vs_paper_calibration_3219.md (A4 FAIL)
  - docs/runbooks/postgres_least_privilege_rls.md (Step 1 roles_and_grants before Step 2 readonly login)

impact_on_plan:
  - HOLD_READONLY_ACCESS_UNAVAILABLE resolved — readonly path now operational
  - Live DB inventory executed; confirms no new >=2h comparable natural-paper window
  - §5.2.4 remains NOT MET; next honest gate is fresh-paper runtime under #1784

limitations:
  - roles_and_grants.sql was required prerequisite (cdb_* roles absent on ~36min fresh postgres)
  - regime_segments not populated via readonly export path; replay/compare still required
  - No MCP brain records; no business-table data mutation
```

### 13.2 Operator Boundary

| Step | Action | Result |
|------|--------|--------|
| Preflight | `cdb_postgres` healthy; DSN env SET; password file EXISTS | PASS |
| Prerequisite | `roles_and_grants.sql` (idempotent role foundation) | Applied — roles missing on fresh container |
| Repair | `operator_create_readonly_login.sql` with `CDB_READONLY_PASSWORD` psql var | Applied |
| Verify | `verify_privileges.sql` | PASS — least-privilege readonly login |
| Inventory | `scripts/arvp_3742_natural_paper_window_inventory.py` | Completed (exit 0) |

No schema migration. No business/trading/evidence table data changes. No credentials printed.

### 13.3 Readonly Identity / Privilege Verification

| Check | Result |
|-------|--------|
| `cdb_readonly` exists | **Yes** |
| `rolcanlogin` | **true** |
| `rolsuper` / `createdb` / `createrole` / `replication` / `bypassrls` | **all false** |
| Member of `cdb_reader` | **Yes** |
| Member of `cdb_writer` / `cdb_admin` | **No** |
| `correlation_ledger` SELECT | **Yes** |
| `correlation_ledger` INSERT/UPDATE/DELETE | **No** |
| `candles_1m` SELECT | **Yes** |
| Session identity | `current_user=session_user=cdb_readonly` |

### 13.4 Inventory Command Summary (No Credentials)

```text
# Operator repair (superuser claire_user inside cdb_postgres):
# 1) roles_and_grants.sql — prerequisite when cdb_* roles absent
# 2) operator_create_readonly_login.sql -v CDB_READONLY_PASSWORD=...
# 3) verify_privileges.sql

# Inventory (host shell, DSN from env only):
python scripts/arvp_3742_natural_paper_window_inventory.py
```

### 13.5 Cluster / Window Classification

| Source | Clusters | Trade-dense | >=2h span | New comparable | regime_segments |
|--------|----------|-------------|-----------|----------------|-----------------|
| `primary_breakout_v1` | 5 | 3 | 0 | 0 | unavailable / not_assessable |
| `paper` | 4 | 0 | 0 | 0 | not_assessable (inadmissible) |
| `paper_`-qualified chains | 3 | 3 | 0 | 0 | unavailable |

Key readonly findings:

- Largest `strategy_id=paper` cluster: **23.4h** span but **inadmissible** (no paper_-qualified ORDER+FILL chain; not PB1-comparable).
- Longest trade-dense PB1 cluster: **1.81h** — below 2h comparison target; no paper orders/fills.
- All trade-dense clusters overlap existing bank or fall below span threshold.
- **0** new comparable candidates outside the existing 3-window bank.

### 13.6 regime_segments Feasibility

| Path | Status |
|------|--------|
| Readonly `paper_reference_window` export | **unavailable** — segments not in export surface |
| Artifact path | **no populated segments** in prior repo evidence (#3219) |
| Live DB clusters | **unavailable** on all classified candidates |

§5.2.4 gate: **still NOT MET**.

### 13.7 Final Verdict (Rerun)

**`HOLD_NO_VALID_WINDOWS_READONLY`**

Follow-up gate (honest next step, out of #3742 write scope):

**`REQUIRES_RUNTIME_GO_FOR_FRESH_PAPER`** — separate Runtime Human-GO under #1784 lineage.

Access hold **`HOLD_READONLY_ACCESS_UNAVAILABLE` is resolved**. Data verdict is now evidence-backed from live readonly SELECT.

**#3742 stays OPEN** — inventory complete but §5.2.4 not satisfied; fresh-paper route remains blocked pending Runtime-GO.

---

## 12. Status (Updated 2026-07-06)

**Prior (2026-07-05):** `HOLD_READONLY_ACCESS_UNAVAILABLE` — evidence documented; issue OPEN pending operator repair.

**Current:** Readonly login repaired and verified; inventory re-run complete.

**Verdict:** `HOLD_NO_VALID_WINDOWS_READONLY` with follow-up `REQUIRES_RUNTIME_GO_FOR_FRESH_PAPER`.

**§5.2.4:** NOT MET. LR **NO-GO** unchanged. No Live-Go / Echtgeld-Go. No Product-Complete claim.

---

## 9. Operator Follow-Up (Prior — Superseded by §13)

| Step | Owner | Scope | 2026-07-06 status |
|------|-------|-------|-------------------|
| Repair `cdb_readonly` login | Operator | `operator_create_readonly_login.sql` | **Done** |
| Verify privileges | Operator | `verify_privileges.sql` | **Done** |
| Re-run inventory | #3742 continuation | `scripts/arvp_3742_natural_paper_window_inventory.py` | **Done** |
| If DB still has no valid windows | Future slice | `REQUIRES_RUNTIME_GO_FOR_FRESH_PAPER` under #1784 | **Next gate** |

No Docker, runtime, replay, backfill, or live capital implied by the repair path alone.

---

## 10. Boundaries

- ARVP Phase A is **not Product-Complete**
- LR remains **NO-GO**
- Board stage `trade-capable` is **not** Live-Go
- No Live-Go, no Echtgeld-Go
- No runtime start, no Docker orchestration, no replay execution
- No DB mutation in this slice
- No candidate rescue, no PB1/RMR/Momentum unpark
- No credentials in issues, PRs, logs, or repo files
- Operator prerequisite `roles_and_grants.sql` applied only because `cdb_*` foundation was missing (documented in §13)

---

## 11. Restunsicherheiten (Prior Session)

1. Whether `cdb_readonly` role exists in the live DB was not verified inside this slice (connect failed first).
2. Whether a successful repair would change the prior #3343/#3219 data-negative picture is unknown until inventory re-run.
3. Even with repaired readonly access and new windows, `regime_segments` still require replay/compare pipeline work — not solved by extraction alone. *(Confirmed by 2026-07-06 rerun: all clusters regime_segments unavailable.)*

---

## 14. Restunsicherheiten (Post-Rerun)

1. `roles_and_grants.sql` was required because `cdb_*` roles were absent on a freshly restarted `cdb_postgres`; long-lived operator DBs may already have had the foundation.
2. Whether fresh-paper runtime under #1784 would yield populated `regime_segments` is unproven until Runtime-GO + replay/compare runs.
3. `strategy_id=paper` long clusters (23h+) remain analytically interesting but inadmissible under current PB1-comparable contract without adapter scope change.

---
