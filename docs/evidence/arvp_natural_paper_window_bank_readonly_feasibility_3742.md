# ARVP Natural-Paper Window Bank — Readonly Feasibility (#3742)

Status Class: Scoped evidence / access hold (blocked preflight)
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
  - secret file POSTGRES_READONLY_PASSWORD_DSN: exists under operator secrets store
  - cdb_postgres container: Up, healthy
  - readonly connection: FAIL — password authentication failed for user cdb_readonly
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
  - Auth failure root cause not fully isolated (stale password vs missing role) — repair path documented only
  - No secret values printed, committed, or inspected in outputs
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
- No secret values printed, committed, or inspected

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
| Operator secret file present | **Yes** (path only; no content read into evidence) |
| Target host/port reachable | **Yes** — TCP connection reached Postgres |
| `cdb_postgres` container | **Up, healthy** |
| Login principal | `cdb_readonly` (from DSN user component; value not printed) |
| Authentication | **FAIL** — `password authentication failed for user "cdb_readonly"` |
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
hint: verify POSTGRES_READONLY_PASSWORD_DSN secret, cdb_readonly role, and that cdb_postgres is reachable on the DSN host/port
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

1. `cdb_readonly` role password in Postgres does not match the canonical secret backing `POSTGRES_READONLY_PASSWORD_DSN`.
2. `cdb_readonly` login was never applied or was rotated without updating the secret file.
3. DSN points at the correct host/port but references a stale credential.

**This slice did not:**

- Print or commit any DSN or password value
- Run `operator_create_readonly_login.sql`
- Perform any DB write or role mutation
- Start Docker, runtime, replay, or backfill

Operator repair path (separate GO):

1. Load `CDB_READONLY_PASSWORD` from the canonical secret store (not into repo/chat).
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

## 8. Verdict

**`HOLD_READONLY_ACCESS_UNAVAILABLE`**

Why this verdict (and not a data verdict):

- The inventory script fail-closed at PostgreSQL authentication.
- No cluster inventory or extraction attempt reached `correlation_ledger`.
- Therefore this slice cannot honestly claim `HOLD_NO_VALID_WINDOWS_READONLY`, `REQUIRES_RUNTIME_GO_FOR_FRESH_PAPER`, or `WINDOW_EXTRACTED_*` from live DB evidence.

What remains true from prior repo-backed evidence:

- ARVP Phase A §5.2.4 (`regime_segments`) is still **NOT MET** (#2974, #3219).
- Window bank remains 3 windows with **regime_segments unavailable** on all (#3219).
- #3343 PB1-only readonly expansion was exhausted under a working readonly session (2026-06-19).

**#3742 stays OPEN** until either:

1. Readonly access is repaired and the inventory script completes, or
2. Control explicitly parks the slice with a separate decision.

---

## 9. Operator Follow-Up (Out of #3742 Write Scope)

| Step | Owner | Scope |
|------|-------|-------|
| Repair `cdb_readonly` login | Operator / separate GO | `operator_create_readonly_login.sql` |
| Verify privileges | Operator | `verify_privileges.sql` |
| Re-run inventory | #3742 continuation | `scripts/arvp_3742_natural_paper_window_inventory.py` |
| If DB still has no valid windows | Future slice | `REQUIRES_RUNTIME_GO_FOR_FRESH_PAPER` under #1784 |

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
- No secrets in issues, PRs, logs, or repo files

---

## 11. Restunsicherheiten

1. Whether `cdb_readonly` role exists in the live DB was not verified inside this slice (connect failed first).
2. Whether a successful repair would change the prior #3343/#3219 data-negative picture is unknown until inventory re-run.
3. Even with repaired readonly access and new windows, `regime_segments` still require replay/compare pipeline work — not solved by extraction alone.

---

## 12. Status

**`HOLD_READONLY_ACCESS_UNAVAILABLE` — evidence documented; issue remains OPEN pending operator readonly repair and inventory re-run.**
