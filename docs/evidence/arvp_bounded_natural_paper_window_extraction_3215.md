# ARVP Bounded Natural-Paper Window Extraction — #3215

Status Class: Scoped evidence / extraction-route decision
Issue: #3215
Parent: #1900
Control Refs: #2985, #2977, #3212, #3214
Live-Readiness: NO-GO
Echtgeld: not authorized

---

## 1. Brain Evidence Block

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - read: AGENTS.md, agents/AGENTS.md, canonical read-order files
  - read: docs/evidence/arvp_window_bank_inventory_3212.md
  - read: docs/governance/arvp_paper_reference_contract.md
  - read: docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md
  - read: knowledge/governance/ARVP_PRODUCT_INTENT.md
  - read: docs/evidence/arvp_readonly_preflight_2967_closeout.md
  - read: docs/evidence/arvp_window_bank_2961_extraction_2026-06-04.md
  - read: core/replay/paper_reference_window_export.py
  - read: services/validation/paper_reference_window_runner.py
  - read: core/replay/replay_vs_paper_compare.py
  - grep: paper_reference_window, readonly, DSN, correlation_ledger, regime_segments, runner/exporter surfaces
  - bash: git status -sb; git rev-parse HEAD; git rev-parse origin/main; gh issue/pr views
records_or_results:
  - HEAD == origin/main == a4e3a04be67ae29acb0dd1062591e29d69e9fce5 at session start
  - #3215 OPEN; #3212 CLOSED; #3214 MERGED; #2985 OPEN; #1900 OPEN; #2977 OPEN/BLOCKED
  - runner requires POSTGRES_READONLY_PASSWORD_DSN and cdb_readonly identity/privilege checks
  - exporter is fail-closed on SIGNAL-anchor integrity, event shape, strategy match, and paper_ qualification
repo_crosscheck:
  - docs/evidence/arvp_window_bank_inventory_3212.md
  - docs/evidence/arvp_readonly_preflight_2967_closeout.md
  - docs/evidence/arvp_window_bank_2961_extraction_2026-06-04.md
  - core/replay/paper_reference_window_export.py
  - services/validation/paper_reference_window_runner.py
  - core/replay/replay_vs_paper_compare.py
impact_on_plan:
  - the guarded extraction route is clear enough to document exactly
  - current-session safe access is not attested without secret-backed runtime configuration
  - fail-closed plan is safer than an unsafe or secret-dependent extraction attempt
limitations:
  - no DB-/MCP-/SurrealDB-backed read executed in this slice
  - no env/secret inspection performed
  - no current-session proof that POSTGRES_READONLY_PASSWORD_DSN is available to this agent shell
```

---

## 2. Bootloader-/Read-Order-Evidence

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
- LR remains NO-GO.
- Board stage `trade-capable` is not Live-Go.
- No secret search or output is permitted in this slice.

---

## 3. Live-Lage

| Item | Status |
|---|---|
| Branch at session start | `main` |
| HEAD / origin/main | `a4e3a04be67ae29acb0dd1062591e29d69e9fce5` / equal |
| Working tree | foreign untracked surfaces `.opencode/plans/`, `docs/decisions/`; untouched |
| #3215 | OPEN |
| #3212 | CLOSED |
| PR #3214 | MERGED |
| #2985 | OPEN |
| #1900 | OPEN |
| #2977 | OPEN / BLOCKED |
| Open PRs | Dependabot-only |
| LR verdict | NO-GO |
| Board stage | `trade-capable` (not Live-Go) |

No live-truth conflict was found.

---

## 4. #3212 Source Decision

Source artifact: `docs/evidence/arvp_window_bank_inventory_3212.md`

Source decision:

- `WINDOW_BANK_INSUFFICIENT_NEEDS_BOUNDED_DATA_ACQUISITION`

Inherited truth from `#3212` / PR `#3214`:

- current repo-backed 2-window bank exists
- both current windows remain `regime_segments = unavailable`
- A2 Replay-vs-Paper Batch Compare = PASS on current bank
- A3 Calibration + Drift Classification = WARN
- A4 Regime Interpretation = FAIL
- no Candidate #4
- no PB1/RMR/Momentum rescue
- LR remains NO-GO

This issue therefore focuses only on the next bounded data/extraction route.

---

## 5. Guarded Extraction Route

### 5.1 Existing guarded route on main

The repo-backed extraction route already exists and is bounded:

1. `services/validation/paper_reference_window_runner.py`
   - requires explicit `--strategy-id`, `--symbol`, `--start-ts-ms`, `--end-ts-ms`
   - default output path: `artifacts/paper_reference_windows/paper_reference_window.json`
   - requires secret-managed env `POSTGRES_READONLY_PASSWORD_DSN`
   - verifies identity: `current_user == session_user == cdb_readonly`
   - verifies privileges: `SELECT=true`, `INSERT=false`, `UPDATE=false`, `DELETE=false`

2. `core/replay/paper_reference_window_export.py`
   - fail-closed exporter from `public.correlation_ledger`
   - validates:
     - event type set limited to `SIGNAL`, `DECISION`, `ORDER`, `FILL`
     - event timestamps inside window
     - payload strategy match
     - SIGNAL-anchor chain integrity
     - paper qualification via `paper_` ORDER/FILL
     - bot/config homogeneity guards

3. `core/replay/replay_vs_paper_compare.py`
   - current consumer for downstream compare/calibration
   - validates symbol/strategy/timestamp consistency on the generated artifact
   - accepts `events` and optional `causal_context_events`

### 5.2 Exact bounded operator/agent route

The smallest existing bounded route is:

1. operator ensures secret-managed readonly DSN is already set in the execution shell
2. agent runs the existing guarded runner with explicit window bounds and output path
3. runner self-verifies readonly identity and privileges before any query
4. exporter emits contract-shaped JSON under `artifacts/paper_reference_windows/`
5. downstream comparison/calibration/regime tooling can consume the generated artifact

### 5.3 Canonical command shape

```bash
python -m services.validation.paper_reference_window_runner \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --start-ts-ms <START_TS_MS> \
  --end-ts-ms <END_TS_MS> \
  --causal-lookup-start-ms <CAUSAL_LOOKUP_START_MS> \
  --causal-lookup-end-ms <CAUSAL_LOOKUP_END_MS> \
  --output artifacts/paper_reference_windows/paper_reference_window_3215_candidate_<slug>.json \
  --extracted-by issue3215_bounded_window_extraction
```

Notes:

- Secret values are never placed on the command line.
- The runner reads only `POSTGRES_READONLY_PASSWORD_DSN` from the host environment.
- `bot_id` / `config_hash` filters are optional and only usable if already known from repo-backed evidence or operator context.

---

## 6. Read-only Access Assessment

### 6.1 Code-level safety

The existing route is technically safe and fail-closed:

- readonly login required: `cdb_readonly`
- explicit privilege probe against `public.correlation_ledger`
- no write path in the runner
- DB mutation is impossible through the runner route
- output is file-only under the allowed artifact path

### 6.2 Historical repo-backed validation

Historical repo-backed evidence says the route was validated previously:

- `docs/evidence/arvp_readonly_preflight_2967_closeout.md`
  - `cdb_readonly` role historically existed
  - secret-managed readonly DSN was historically set
  - runner extraction was historically validated via `#2969` / `#3028`

### 6.3 Current-session access decision

Current-session safe access is **not attested** for this agent shell.

Reason:

- the runner depends on `POSTGRES_READONLY_PASSWORD_DSN`
- this slice explicitly forbids env/secret reads, secret search, or secret output
- no pre-approved host-side proof was supplied in this session that the env is present and valid
- invoking extraction without that attestation would rely on hidden secret state that this slice is not allowed to inspect or normalize

### 6.4 Current-session verdict

- guarded route exists: **yes**
- historically validated: **yes**
- current-session safe readonly access attested without secret handling: **no**

Therefore this slice does **not** execute the runner.

---

## 7. paper_reference_window.v1 Contract Requirements

The extraction target must satisfy the repo-backed main reality below.

### 7.1 Required window semantics

- `contract_version = arvp_paper_reference_window.v1`
- `strategy_id` non-empty and consistent
- `symbol` non-empty and consistent
- `start_ts_ms_utc < end_ts_ms_utc`
- all event `timestamp_ms` values inside the bounded window

### 7.2 Required event shape

- event set drawn from `SIGNAL`, `DECISION`, `ORDER`, `FILL`
- `payload.strategy_id` present and matching requested strategy
- event-type-specific required fields:
  - SIGNAL: `signal_id`
  - DECISION: `signal_id`, `decision_id`
  - ORDER: `signal_id`, `decision_id`, `order_id`
  - FILL: `signal_id`, `decision_id`, `order_id`, `fill_id`

### 7.3 Required chain / paper qualification

- at least one SIGNAL anchor in-window
- every non-SIGNAL event must map to its SIGNAL anchor
- at least one paper-qualified ORDER (`order_id` starts with `paper_`)
- at least one paper-qualified FILL (`order_id` starts with `paper_`)

### 7.4 Required provenance / extraction metadata on main

Current exporter shape on main emits flattened extraction metadata fields:

- `source_table`
- `source_query_intent`
- `extracted_at_utc`
- `extracted_by`
- optional `causal_context_events`

### 7.5 Fingerprint / downstream readiness

The extracted window itself does not generate compare/calibration fingerprints.
Fingerprints are generated later by downstream compare/calibration/regime stages.

For `#3215`, a successful extraction must still document:

- window path
- exact UTC bounds
- event count
- event-type coverage
- provenance metadata present/absent
- `regime_segments` status after downstream read, if any tooling is applied later

---

## 8. Extraction Attempt or Fail-Closed Plan

### 8.1 Extraction attempt

No extraction attempt was executed in this slice.

Why not:

- current-session secret-backed readonly access was not safely attestable without crossing the no-secret boundary
- the issue contract explicitly prefers fail-closed planning over improvising hidden-secret access

### 8.2 Fail-closed future execution plan

The next safe execution should be:

1. Human/operator confirms that `POSTGRES_READONLY_PASSWORD_DSN` is already configured in the shell where the runner will execute.
2. No secret value is shown, printed, committed, or copied into repo files.
3. Agent runs only the existing guarded runner.
4. Candidate windows are tried in descending evidence value:
   - longer natural-paper windows from the already known BTCUSDT / primary_breakout_v1 paper period
   - prefer widths that plausibly support non-empty `regime_segments`
5. If extraction succeeds:
   - write artifact under `artifacts/paper_reference_windows/`
   - document output in a docs/evidence follow-up
6. If extraction fails with no qualifying windows:
   - record exact bounded failure and query/result criteria

### 8.3 Safe command template

```bash
python -m services.validation.paper_reference_window_runner \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --start-ts-ms <START_TS_MS> \
  --end-ts-ms <END_TS_MS> \
  --causal-lookup-start-ms <CAUSAL_LOOKUP_START_MS> \
  --causal-lookup-end-ms <CAUSAL_LOOKUP_END_MS> \
  --output artifacts/paper_reference_windows/paper_reference_window_3215_candidate_<slug>.json \
  --extracted-by issue3215_bounded_window_extraction
```

### 8.4 Safe result classification

- if one or more contract-valid windows are produced: `EXTRACTED_WINDOW_READY_FOR_REVIEW`
- if route is intact but access still requires secret-managed operator context: `PLAN_READY_FOR_WINDOW_EXTRACTION`
- if readonly access cannot be made available safely: `BLOCKED_NO_SAFE_READONLY_LEDGER_ACCESS`
- if safe access exists but no qualifying windows are found: `BLOCKED_NO_CANDIDATE_WINDOWS_FOUND`

---

## 9. Candidate Window / Planned Window Matrix

| source | route | symbol | venue | strategy_or_context | candidate_start_ts | candidate_end_ts | target_width | event_count | provenance_status | fingerprint_status | regime_segments_status | contract_status | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `public.correlation_ledger` via `paper_reference_window_runner.py` | existing guarded runner with readonly DSN | BTCUSDT | MEXC paper-side target | `primary_breakout_v1`, longer natural-paper window from known paper period | `TBD_BY_READONLY_QUERY` | `TBD_BY_READONLY_QUERY` | prefer `>= 5m`; 1h aspirational | `unknown in this slice` | route supports exporter provenance fields | downstream only after compare/calibration | must be measured from extracted candidate, never inferred | `unknown until extracted` | strongest bounded next route; no secret values needed in docs, but secret-managed env must exist at execution time |
| historical pilot (`paper_1909_1776991354682`) | already evidenced, not the target of this slice | BTCUSDT | MEXC | narrow pilot anchor | 2026-04-24T00:42:00Z | 2026-04-24T00:43:00Z | 1m | already known narrow chain | historically present | downstream fingerprints already exist | unavailable | not sufficient as new longer candidate | included only as reference anchor, not as a new extraction target |
| historical `#3028` window | already evidenced, not the target of this slice | BTCUSDT | MEXC paper side / Binance replay compare path | committed 2-minute window | 2026-06-06T00:28:12.551Z | 2026-06-06T00:30:12.814Z | 2m0.263s | already known committed chain | present in current exporter shape | downstream fingerprints already exist | unavailable | not sufficient as new longer candidate | included as current-bank reference, not as a new extraction result |

---

## 10. regime_segments Handling

Rules for this slice:

- `regime_segments` must never be inferred.
- A window either produces downstream regime evidence or it does not.
- Longer windows are only a plausibility improvement, not proof.

Current state inherited from `#3212`:

- existing pilot window: `regime_segments = unavailable`
- existing `#3028` window: `regime_segments = unavailable`

Implication for future extraction:

- the only honest goal is to extract a longer comparison-grade natural-paper window that can later be evaluated for `regime_segments`
- this slice cannot claim that a longer window will definitely produce them

---

## 11. A2/A3/A4 Implication

| Workstream | Current implication after this slice |
|---|---|
| A2 Replay-vs-Paper Batch Compare | unchanged; current bank remains usable |
| A3 Calibration + Drift Classification | unchanged; current bank remains WARN-level because certainty is limited |
| A4 Regime Interpretation | unchanged; still FAIL on current bank until at least one longer extracted window later yields usable regime evidence |

This slice does not upgrade any current A2/A3/A4 status. It only makes the next safe execution path explicit.

---

## 12. Decision

**Decision:** `PLAN_READY_FOR_WINDOW_EXTRACTION`

Why:

1. The guarded extraction route is precisely identified and already exists on main.
2. The required command shape, output path, and contract requirements are explicit.
3. Current-session safe readonly access is not attested without crossing the no-secret boundary.
4. A fail-closed execution plan is therefore the correct and bounded result for `#3215`.

This is not:

- a Product-Complete claim
- a Live-Go / Echtgeld-Go step
- a new candidate-family opening
- a strategy rescue path

---

## 13. Required Follow-up

Next safe bounded step after this artifact:

- operator-backed execution of the existing guarded runner in a shell where `POSTGRES_READONLY_PASSWORD_DSN` is already configured and not exposed

If that future execution succeeds, the next expected state would be:

- `EXTRACTED_WINDOW_READY_FOR_REVIEW`

If the route is attempted later and no qualifying windows are found, the honest state becomes:

- `BLOCKED_NO_CANDIDATE_WINDOWS_FOUND`

---

## 14. Stop Rules / Safety

- LR remains NO-GO.
- Board stage `trade-capable` is not Live-Go.
- No Live-Go / Echtgeld-Go.
- No Product-Complete claim.
- No runtime start.
- No Docker/Compose orchestration.
- No workflow dispatch.
- No DB mutation.
- No MCP mutation.
- No secret reading, printing, or dumping.
- No Candidate #4.
- No 5m/15m discovery.
- No PB1/RMR/Momentum rescue.

---

## 15. Restunsicherheiten

1. Historical repo-backed evidence says the readonly route was once validated, but this slice does not prove current-shell availability.
2. A longer extracted window may still fail to produce non-empty `regime_segments`.
3. The current contract doc and current exporter/consumer shape on main are not perfectly aligned.
4. No DB-backed candidate-count claim is made in this slice.

---

## 16. Status

`PLAN_READY_FOR_WINDOW_EXTRACTION`
