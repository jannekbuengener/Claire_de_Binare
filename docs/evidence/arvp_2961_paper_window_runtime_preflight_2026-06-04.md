# ARVP #2961 Paper Window Runtime Preflight — 2026-06-04

Status: Preflight plan only — no runtime start, no DB mutation, no Docker/Compose orchestration; one non-mutating `docker exec cdb_execution printenv` env-read confirmed MOCK_TRADING=true; no secret values, DSNs, or full environment dumps were captured or committed
Parent: #2961 (Phase A1)
Roadmap: `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md` § Phase A1
Extraction HOLD: `docs/evidence/arvp_window_bank_2961_extraction_2026-06-04.md` (merged #2964)
Live-Readiness: **NO-GO** (unchanged)
Echtgeld: **not authorized**

---

## 1. Brain Evidence

```
## Brain Evidence
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - bootloader: AGENTS.md, agents/AGENTS.md (full Read Order), CDB_AGENT_POLICY.md
  - LR SSOTs: LR-AUDIT-STATUS-2026-03-05.md, GO_NO_GO.md
  - ARVP docs: arvp_platform.md, arvp_paper_reference_contract.md
  - Roadmap: ARVP_TO_LIVE_GO_ROADMAP_2026-06.md
  - Evidence: arvp_window_bank_2961_extraction_2026-06-04.md, arvp_calibration_batch_2961_2026-06-04.md, arvp_calibration_pilot_1932_2026-04-26.md
  - Code: services/validation/paper_reference_window_runner.py, core/replay/paper_reference_window_export.py, services/execution/service.py, services/execution/config.py, core/utils/trace_toggle.py
  - Infra: infrastructure/compose/compose.blue.yml, infrastructure/compose/compose.red.yml
  - Live: git fetch/status, gh issue view 2961/1900/1784, gh pr list, docker exec cdb_execution printenv
  - DB readonly: correlation_ledger inventory from extraction audit
records_or_results:
  - _correlation_ledger_order_ids() @ service.py:242 — paper_ prefix logic: when MOCK_TRADING=true, order_id gets paper_ prepended
  - compose.blue.yml: MOCK_TRADING=true, TRACE_CONTRACT_V1_ENABLED=1, USE_REAL_BALANCE=false for cdb_execution
  - Running execution service: MOCK_TRADING=true (confirmed via docker exec)
  - ALLOW_EVIDENCE_DEBT defaults to OFF (os.getenv("ALLOW_EVIDENCE_DEBT", "0") == "1")
  - paper_reference_window_runner.py: requires cdb_readonly user + POSTGRES_READONLY_PASSWORD_DSN
  - correlation_ledger: 1 paper_ ORDER/FILL, 5 MOCK_ ORDER/FILL, 17K SIGNALS, 17K DECISIONS
repo_crosscheck:
  - HEAD = origin/main = a9dd8494
  - #2961 OPEN, #1900 OPEN, #1784 OPEN, 0 open PRs
  - Roadmap Phase A1 correctly describes extraction-first bottleneck
impact_on_plan:
  - Paper-prefix logic is already correct in code — MOCK_TRADING=true → paper_ prefix
  - Bottleneck is not prefix logic, it's that execution produced only 6 ORDER events total
  - New paper trading runtime period needed to produce sufficient ORDER/FILL volume
  - cdb_readonly role required before next extraction can use the runner
limitations:
  - No runtime start performed; preconditions verified by code inspection + live env check
  - correlation_ledger ORDER/FILL volume is an observation, not a diagnostic conclusion
  - Paper phase behavior (#1784) with respect to ORDER volume is a separate concern
```

---

## 2. Live State

| Item | Status |
|------|--------|
| git branch | main |
| HEAD | a9dd8494 == origin/main |
| Open PRs | 0 |
| #2961 | OPEN |
| #1900 | OPEN |
| #1784 | OPEN |
| Docker execution service | Running, healthy, MOCK_TRADING=true |
| Docker postgres | Running, healthy |
| cdb_readonly role | **Not configured** |
| POSTGRES_READONLY_PASSWORD_DSN | **Not set** |

---

## 3. Readonly DB Setup Plan

### 3.1 Goal

Create a dedicated `cdb_readonly` PostgreSQL role with **only** SELECT privileges on `public.correlation_ledger`, to allow safe extraction via `paper_reference_window_runner.py`.

### 3.2 SQL Steps (not executed — explicit Human-GO required)

```sql
-- Step 1: Create readonly login role
CREATE ROLE cdb_readonly WITH LOGIN PASSWORD '<SECRET_VALUE>' 
  CONNECTION LIMIT 2
  VALID UNTIL 'infinity';

-- Step 2: Grant CONNECT to database
GRANT CONNECT ON DATABASE claire_de_binare TO cdb_readonly;

-- Step 3: Grant USAGE on public schema
GRANT USAGE ON SCHEMA public TO cdb_readonly;

-- Step 4: Grant SELECT-only on correlation_ledger (explicit, no table-level INSERT/UPDATE/DELETE)
GRANT SELECT ON public.correlation_ledger TO cdb_readonly;

-- Step 5: Verify no other schema-level privileges
-- (by default, cdb_readonly gets no other schema privileges)

-- Step 6: Ensure default privileges do NOT grant write access
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM cdb_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM cdb_readonly;
```

### 3.3 Verification Commands (readonly, safe)

After the role is created by a human operator:

```bash
# Run the runner — it will self-verify identity and privileges:
# 1. Verify current_user = cdb_readonly and session_user = cdb_readonly
# 2. Verify SELECT=yes, INSERT=no, UPDATE=no, DELETE=no on correlation_ledger
# 3. If either check fails, the runner exits with code 2 and does nothing
python -m services.validation.paper_reference_window_runner \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --start-ts-ms 1700000000000 \
  --end-ts-ms 1800000000000 \
  --extracted-by preflight_verification
# Expected: exit code 0 only if identity+privileges pass; output a window payload
```

### 3.4 Secret/Env Requirements

| Requirement | What to do | What NOT to do |
|-------------|-----------|----------------|
| `POSTGRES_READONLY_PASSWORD_DSN` | Set as environment variable on the host (not in compose, not in repo) | Never commit the DSN, never log it, never include it in GitHub comments |
| `cdb_readonly` password | Generate a strong password, store in the host secrets directory | Never store in repo files, never display in logs/reports |
| DSN format | `postgresql://cdb_readonly:<PASSWORD>@localhost:5432/claire_de_binare?connect_timeout=10` | Never hardcode in Python files, .env, or compose yaml |
| Connection safety | The DSN contains the readonly user credentials — treat as a secret | Never print, commit, or share |

### 3.5 Risk Classification

| Operation | Mutation | Human-GO required | Agent scope |
|-----------|----------|-------------------|-------------|
| CREATE ROLE cdb_readonly | Yes (DB state) | **YES** | **No** |
| GRANT CONNECT, USAGE, SELECT | Yes (grants) | **YES** | **No** |
| Set POSTGRES_READONLY_PASSWORD_DSN env var | No (shell env) | **YES** | **No** — contains secret |
| Run paper_reference_window_runner.py | No (SELECT only) | No (after setup) | Yes |

---

## 4. Paper-Prefix Runtime Preconditions

### 4.1 The prefix Logic (repo-backed)

The function `_correlation_ledger_order_ids()` in `services/execution/service.py:242-271` determines whether correlation_ledger ORDER/FILL events get a `paper_` prefix:

```
if internal_id already starts with "paper_":
  → use internal_id as-is

elif MOCK_TRADING is true:
  if internal_id exists:
    → canonical = "paper_" + internal_id   (e.g. paper_<UUID>)
  elif exchange_order_id exists:
    → canonical = "paper_" + exchange_order_id  (e.g. paper_MOCK_xxxxx)

else (MOCK_TRADING is false):
  → no prefix; use internal_id or exchange_order_id as-is
```

**Key insight**: `MOCK_TRADING=true` → paper_ prefix is **guaranteed** by code. No additional config flag is needed.

### 4.2 Current Compose Configuration for cdb_execution

From `infrastructure/compose/compose.blue.yml` (lines 262-270):

| Env Var | Value | Relevant to paper prefix? |
|---------|-------|--------------------------|
| MOCK_TRADING | "true" | **Yes** — triggers paper_ prefix |
| DRY_RUN | (defaults to "true") | No — only affects order execution, not prefix |
| MEXC_TESTNET | (defaults to "true") | No — only affects exchange endpoint |
| USE_REAL_BALANCE | "false" | No |
| TRACE_CONTRACT_V1_ENABLED | "1" | Indirect — enables strict ID enforcement |

### 4.3 Config Flag Interactions

| Flag | Default | Effect on paper_ prefix | Effect on correlation_ledger writes |
|------|---------|------------------------|-------------------------------------|
| MOCK_TRADING=true | Default | **TRIGGERS paper_ prefix** | Enables writes via MockExecutor |
| DRY_RUN=true | Default | No effect on prefix | Logs order without executing; correlation_ledger writes still happen |
| MEXC_TESTNET=true | Default | No effect on prefix | Routes to testnet; MOCK_TRADING=true prevents real orders anyway |
| ALLOW_EVIDENCE_DEBT | Default OFF (0) | No effect on prefix | When OFF: missing fields raise ValueError → skip correlation write with warning. When ON: missing fields silently skip |
| TRACE_CONTRACT_V1_ENABLED | "1" in compose | No effect on prefix | Enables stricter ID validation in contract layer |

### 4.4 Why Only 1 paper_ Entry Despite MOCK_TRADING=true?

Current correlation_ledger inventory:
- 17,104 SIGNAL events
- 17,121 DECISION events
- 6 ORDER events (1 paper_ + 5 MOCK_)
- 6 FILL events (1 paper_ + 5 MOCK_)

The MOCK_ entries pre-date the `_correlation_ledger_order_ids()` function. The single paper_ entry (`paper_1909_1776991354682`) proves the prefix logic works correctly.

**The bottleneck is ORDER volume, not prefix logic.** The current codebase and compose config are already correctly configured to produce paper_-prefixed correlation_ledger entries. What's needed is a paper trading runtime period that produces a meaningful number of ORDER/FILL events.

### 4.5 Pre-Runtime Proof Path

Before starting a full paper trading period, a minimal smoke/dry-run can prove that new events will be paper_-prefixed:

```
# 1. Verify current configuration (readonly, safe):
docker exec cdb_execution printenv | grep MOCK_TRADING
# Expected: MOCK_TRADING=true

# 2. After runtime is running under Human-GO, verify a new event:
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c \
  "SELECT order_id FROM correlation_ledger WHERE event_type='ORDER' ORDER BY timestamp_ms DESC LIMIT 1;"
# Expected: order_id starts with "paper_"

# 3. Run extraction to verify:
python -m services.validation.paper_reference_window_runner \
  --strategy-id primary_breakout_v1 --symbol BTCUSDT \
  --start-ts-ms <start> --end-ts-ms <end>
```

---

## 5. Runtime-GO Scope

### 5.1 Step Classification

| Step | Type | Who | Gate |
|------|------|-----|------|
| 1. Read preflight report | Read-only | Agent | None |
| 2. Analyze code/config | Read-only | Agent | None |
| 3. Create cdb_readonly role | DB mutation | **Human Operator** | Explicit Human-GO |
| 4. Set POSTGRES_READONLY_PASSWORD_DSN | Shell env | **Human Operator** | Explicit Human-GO |
| 5. Verify readonly identity + privileges | Read-only | Agent (runner) | After step 3+4 done |
| 6. Start paper trading runtime | Runtime start | **Human Operator** | Explicit Human-GO |
| 7. Let runtime produce ORDER/FILL events | Runtime (auto) | System | After step 6 |
| 8. Extract paper reference windows | Read-only DB | Agent (runner) | After step 7 |
| 9. Run ARVP replay/compare/calibrate | Offline replay | Agent | After step 8 |
| 10. Commit evidence | Repo write | Agent | After step 9 |

### 5.2 Stop Rules (applied to all steps)

1. **No Live-Go** — LR-050 stays NO-GO
2. **No Real-Money-Go** — No real capital exposure
3. **No Runtime Start** — without explicit Human-GO per step 6
4. **No Docker orchestration** — No container start/stop/compose without Human-GO. A single non-mutating `docker exec cdb_execution printenv | grep MOCK_TRADING` was used to confirm the running container's MOCK_TRADING=true setting. This command produced a single line (`MOCK_TRADING=true`) and no secret values, DSNs, passwords, tokens, or full environment dumps were committed or reported.
5. **No workflow_dispatch** — without Human-GO
6. **No DB Mutation** — Steps 3+4 are Human-Operator only
7. **No secrets in repo** — Never commit POSTGRES_READONLY_PASSWORD_DSN or passwords
8. **Board stage `trade-capable` does not authorize live capital**

### 5.3 Risk Matrix

| Scenario | Risk | Mitigation |
|----------|------|-----------|
| Runner connects as claire_user (not cdb_readonly) | Write access possible | Runner self-verifies identity + privileges; exits if user != cdb_readonly or if INSERT/UPDATE/DELETE detected |
| cdb_readonly password leaked in logs | Credential exposure | Password is in env var only, never in code. Runner prints only database name + user name, never DSN |
| Postgres not running during extraction | Connection failure | Runner has 10s connect_timeout + fail-closed exit |
| correlation_ledger returns empty result | No paper window | Runner raises PaperReferenceExportError (exit code 2) |
| MOCK_TRADING accidentally set to false | paper_ prefix NOT generated | Compose.blue.yml has MOCK_TRADING=true as default. Pre-runtime verification step confirms the setting |
| ALLOW_EVIDENCE_DEBT=0 skips broken writes | Lost correlation events | This is expected behavior — only well-formed events are persisted. Not a bug, a guard. |
| Paper runtime does not produce orders | No new windows | This happened in the 14-day phase (#1784: many SIGNALS, few ORDERS). The risk service blocks most decisions. This is a strategy calibration concern, not a window extraction concern. |

---

## 6. Proposed Issue Split

**No issues are created.** These are planning suggestions only.

### Issue A: `[ARVP][PREFLIGHT] Create cdb_readonly Postgres role and set POSTGRES_READONLY_PASSWORD_DSN`

- Parent: #2961
- Scope: Execute the SQL from §3.2 (Human-Operator only — DB mutation). Set the DSN env var (Human-Operator only — secret). Verify with runner dry-run.
- Acceptance: `paper_reference_window_runner.py` exits 0 and produces a valid window payload against a known time range.
- Human-GO: Required (DB mutation + secret setup)

### Issue B: `[ARVP][PAPER-RUNTIME] Run staged/shadow paper trading period for correlation_ledger window production`

- Parent: #2961, #1900
- Scope: Start the BLUE stack under `MOCK_TRADING=true`, `DRY_RUN=true`, `MEXC_TESTNET=true` for a duration sufficient to produce 2+ comparison-grade paper reference windows. Monitor ORDER/FILL volume in `correlation_ledger`. Continue until sufficient data exists.
- Duration guidance: Minutes-to-hours. The pilot window was 1 minute and produced 1 ORDER + 1 FILL. Target: windows of 5+ minutes with at least 1 ORDER/FILL each.
- Acceptance: 2+ new comparison-grade windows exist in `correlation_ledger` (verified by readonly SELECT). No live capital exposed.
- Human-GO: Required (Runtime-Start)

### Issue C: `[ARVP][EXTRACTION] Extract comparison-grade paper reference windows from correlation_ledger`

- Parent: #2961
- Scope: Run `paper_reference_window_runner.py` (readonly) against all candidate windows. Commit `paper_reference_window.json` files as repo-backed evidence.
- Depends on: Issue A (cdb_readonly role) + Issue B (runtime data)
- Acceptance: 3+ total comparison-grade windows committed (1 existing pilot + 2+ new)
- Human-GO: Not required (read-only extraction)

### Issue D: `[ARVP][BATCH] Run replay-vs-paper calibration batch across window bank`

- Parent: #2961
- Scope: Run ARVP replay against each window, produce batch comparison + calibration report with per-window drift classification.
- Depends on: Issue C (windows extracted)
- Acceptance: Multi-window calibration report with ranked drift findings per the Phase A3/A5 roadmap
- Human-GO: Not required (offline replay)

---

## 7. Recommended Next Prompt

After this preflight is reviewed:

> #2961 Phase A1: human operator executes Issue A (cdb_readonly role + DSN setup).
> After cdb_readonly is configured: agent verifies runner extracts the existing pilot window successfully.
> If successful: operator decides on Issue B (paper runtime start).
> If not: troubleshoot infrastructure.

---

## 8. Restunsicherheiten

1. **Why the 14-day paper phase (#1784) produced only 6 ORDER events in correlation_ledger**: The extreme signal-to-order ratio (17K:6) suggests the risk service blocks almost all decisions. This is likely strategy design, not a bug — but it means correlation_ledger is not guaranteed to accumulate many ORDER/FILL events even with a long-running paper phase.

2. **Whether current paper trading would produce more orders**: The running execution service has MOCK_TRADING=true and the prefix logic is correct. But order production depends on risk service decisions, which are driven by market conditions and strategy signals. The system may need volatile market conditions to produce orders.

3. **`ALLOW_EVIDENCE_DEBT` interaction**: With default OFF, any correlation_ledger write with missing required fields (order_id, signal_id, etc.) is silently skipped. This could reduce the number of captured events. Setting ALLOW_EVIDENCE_DEBT=1 would make these skips visible but does not fix the root cause.

4. **cdb_readonly role creation is irreversible within a session**: The CREATE ROLE + GRANT steps should be executed by a human operator who has superuser or CREATEROLE privileges on the Postgres instance.

5. **The bottleneck may be risk-service gating, not execution infrastructure**: The high DECISION count (17K) vs ORDER count (6) means most decisions result in blocks, not orders. This is likely intentional strategy behavior but means windows with ORDER/FILL events will be naturally sparse.

---

## 9. Sources

- `AGENTS.md`, `agents/AGENTS.md` (Read Order: items 1-8)
- `knowledge/governance/CDB_AGENT_POLICY.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/live-readiness/GO_NO_GO.md`
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
- `docs/evidence/arvp_window_bank_2961_extraction_2026-06-04.md`
- `docs/governance/arvp_paper_reference_contract.md`
- `docs/evidence/arvp_calibration_batch_2961_2026-06-04.md`
- `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md`
- `services/validation/paper_reference_window_runner.py` (217 lines)
- `core/replay/paper_reference_window_export.py` (377 lines)
- `services/execution/service.py` (§ _correlation_ledger_order_ids, § Phase 8C/8E writes)
- `services/execution/config.py` (MOCK_TRADING, DRY_RUN flags)
- `core/utils/trace_toggle.py` (ALLOW_EVIDENCE_DEBT default)
- `infrastructure/compose/compose.blue.yml` (cdb_execution env, cdb_postgres config)
- Running docker: `cdb_execution` env confirmed MOCK_TRADING=true
- GitHub: #2961 (OPEN), #1900 (OPEN), #1784 (OPEN)
