# LR-050 Risk Limits — Hard Gate Parameters for First Live-Capital Canary

- **Control:** `LR-050` (P5 Canary Echtgeld / Live-Kapital)
- **GitHub issue:** [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528)
- **Document role:** Repo-backed SSOT for hard capital, order, exposure, loss, and stop limits as **prüfbare Gate-Parameter** (structure + enforceability; not activation)
- **Last updated:** 2026-06-03
- **Companion:** [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md), [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md)
- **Verdict authority (unchanged):** [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)

## Safety boundaries (read first)

| Rule | Status |
|------|--------|
| Global `LR-050` verdict | **NO-GO** until separate explicit human live approval |
| This document authorizes live trading | **No** — kein Live-Go |
| This document authorizes real-money exposure | **No** — kein Echtgeld-Go |
| Merge of PR that adds this document | **Documentation only** — ersetzt **niemals** Human Approval |
| Automatic activation / auto-live | **Forbidden** — No auto-live |
| Board stage `trade-capable` | **Not** live-capital authorization (orthogonal to LR) |
| Concrete canary USDT/symbol values in this doc | **Not** invented — `TBD_BLOCKER_BEFORE_LIVE` where not repo-backed for canary |

---

## 1. Scope and non-goals

### In scope

- Define every limit required by [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528) as a **gate parameter** with value (or `TBD_BLOCKER_BEFORE_LIVE`), source, technical enforceability, fail-closed behavior, and proof hook.
- Map existing repo enforcement mechanisms to canary gates without treating generic dev defaults as canary approval.
- Hand off unresolved values to [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) (Canary Plan) and [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) (Dry-run Proof).

### Non-goals

- No runtime, service, compose, or env changes.
- No live activation, orders, secrets, or API keys.
- No change to [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md).
- No replacement of [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) (kill-switch verification) or [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) (observability gates).

---

## 2. Related documents and dependencies

| Document / issue | Relationship |
|----------------|--------------|
| [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) | Planning context; §5 mirrors parameters — values live here |
| [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) | GO block §5 must copy **concrete** values from this SSOT after #2528 closes |
| [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) | Venue — blocks **Allowed Symbols** until closed; SSOT: [LR-050-VENUE-AUDIT.md](./LR-050-VENUE-AUDIT.md) |
| [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) | Kill-switch / stop / halt verification SSOT — [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) |
| [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530) | Secrets / credential readiness SSOT — [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) |
| [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) | Observability SSOT — [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) |
| [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | Canary plan — must reference all limits below |
| [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) | Dry-run — must prove gates block/simulate with `real_money=false` |
| [`services/risk/README.md`](../../services/risk/README.md) | Runtime risk service surface |
| [`docs/operations/KILL_SWITCH_OPERATOR_CHECKLIST.md`](../operations/KILL_SWITCH_OPERATOR_CHECKLIST.md) | Manual stop operator path |
| [`knowledge/playbooks/07_RISK_GUARDS_DRAWDOWN_BREAKER.md`](../../knowledge/playbooks/07_RISK_GUARDS_DRAWDOWN_BREAKER.md) | Drawdown + circuit breaker integration contract |

---

## 3. Enforceability legend

Each limit row uses one or more tags:

| Tag | Meaning |
|-----|---------|
| `enforceable_now` | Mechanism exists in repo today (code, contract, or operator runbook); can be checked without new implementation |
| `docs_only` | Behavior defined here or in a sibling issue; not fully wired as a dedicated canary gate yet |
| `blocker_before_live` | A **concrete canary value** and proof are mandatory before live-capital GO; until then use `TBD_BLOCKER_BEFORE_LIVE` |

**Value status:**

| Status | Meaning |
|--------|---------|
| `TBD_BLOCKER_BEFORE_LIVE` | No fachlich verantwortbarer Canary-Wert im Repo — must be set via #2532 / operator before Human GO |
| *(repo default noted)* | Generic env/code default exists — **not** a canary approval; listed only as enforcement reference |

---

## 4. Canary gate parameters (main matrix)

| Limit | Value (canary) | Source / rationale | Enforceability | Fail-closed behavior | Proof hook |
|-------|----------------|-------------------|----------------|----------------------|------------|
| **Max Notional per Order** | `TBD_BLOCKER_BEFORE_LIVE` | Human GO field `Max notional per order:` — [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) §5; enforcement via `risk_policy.max_notional_usdt` in [`core/contracts/decision_contract_v1.py`](../../core/contracts/decision_contract_v1.py) (`RC_LIMIT_NOTIONAL`) | `enforceable_now` (mechanism); `blocker_before_live` (canary USDT value) | Order evaluation → **BLOCK** / `DECISION_DENY`; reason `RC_LIMIT_NOTIONAL` | Unit: `tests/unit/risk/test_contract_enforcement.py`; dry-run: [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Max Notional session total** | `TBD_BLOCKER_BEFORE_LIVE` | Human GO field `Max notional session total:` — same SSOT; no separate session-notional cap in risk config today — derive in [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) from exposure + order count | `docs_only` (session aggregate); `blocker_before_live` (value) | Treat as **NO-GO** for live until explicit session cap documented and provable | [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) plan + [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Max Gesamt-Exposure** | `TBD_BLOCKER_BEFORE_LIVE` | [`services/risk/config.py`](../../services/risk/config.py) `MAX_TOTAL_EXPOSURE_PCT` / `MAX_EXPOSURE_PCT` (generic default **0.30** — *not* canary approval); runtime: `check_exposure_limit()` in [`services/risk/service.py`](../../services/risk/service.py) | `enforceable_now` (mechanism); `blocker_before_live` (canary cap) | Projected exposure over limit → **BLOCK**; publish to `stream.orders_blocked` | `tests/unit/risk/test_service.py` (exposure); metric `orders_blocked_total`; [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Max Orders per Session** | `TBD_BLOCKER_BEFORE_LIVE` | **Gap:** [`services/risk/circuit_breakers.py`](../../services/risk/circuit_breakers.py) `FREQUENCY` threshold = **60 orders/minute**, not per-session — canary session limit must be defined in [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | `docs_only`; `blocker_before_live` | Until session cap defined: **fail-closed** — do not interpret 60/min as canary approval | [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532), [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Max Daily Loss** | `TBD_BLOCKER_BEFORE_LIVE` | **Wired live path:** `RiskManager.check_drawdown_limit()` + `MAX_DAILY_DRAWDOWN_PCT` in [`services/risk/config.py`](../../services/risk/config.py) (generic default **0.05** — *not* canary approval); decision threshold `daily_drawdown_pct_max` **5.0** in [`services/risk/service.py`](../../services/risk/service.py) `DECISION_THRESHOLDS`. **Not wired in order flow:** standalone `CircuitBreaker.check_breakers()` / `LOSS_LIMIT` in [`services/risk/circuit_breakers.py`](../../services/risk/circuit_breakers.py) (class + unit tests only) | `enforceable_now` (drawdown latch path); `blocker_before_live` (canary USDT/%) | Daily PnL below drawdown cap → **BLOCK** + `circuit_breaker_active` via `check_drawdown_limit()` | `tests/unit/risk/test_service.py`; playbook [`07_RISK_GUARDS_DRAWDOWN_BREAKER.md`](../../knowledge/playbooks/07_RISK_GUARDS_DRAWDOWN_BREAKER.md); [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Max Slippage** | `TBD_BLOCKER_BEFORE_LIVE` | Generic gate: `DECISION_THRESHOLDS["slippage_pct_max"]` = **1.0** (% points) in [`services/risk/service.py`](../../services/risk/service.py) — *not* LR-050 canary approval; canary cap TBD in [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | `enforceable_now` (generic); `blocker_before_live` (canary value) | `slippage_pct` over threshold → **BLOCK** (RC slippage path) | `tests/unit/risk/test_flask_import_guard.py` (market_health); [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Allowed Symbols** | `TBD_BLOCKER_BEFORE_LIVE` | Blocked until venue/symbol inventory from [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527); symbol list in [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | `blocker_before_live` | Order/signal for non-listed symbol → **BLOCK** (operator + config gate; exact check TBD in plan) | [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527), [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) |
| **Trading Window** | `TBD_BLOCKER_BEFORE_LIVE` | No dedicated `TRADING_WINDOW` in [`services/risk/config.py`](../../services/risk/config.py) — define UTC window in [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | `docs_only`; `blocker_before_live` | Outside declared window → **BLOCK** / operator NO-GO (fail-closed until window encoded) | [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) |
| **Cooldown rules** | `TBD_BLOCKER_BEFORE_LIVE` | **Mechanism wired:** `cooldown_until` per allocation in [`services/risk/service.py`](../../services/risk/service.py) (`tests/unit/risk/test_service.py`). **Canary rule (duration/trigger) TBD** — must match Decision Pack `Trading window / cooldown` and be set in [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | `enforceable_now` (field latch); `blocker_before_live` (concrete canary cooldown policy) | Active `cooldown_until` → **BLOCK**; without documented canary rule → **NO-GO** for Human GO | [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532), [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Manual stop rules** | Operator halt (no numeric cap) | [`core/safety/kill_switch.py`](../../core/safety/kill_switch.py) `KillSwitchReason.MANUAL`; operator checklist [`KILL_SWITCH_OPERATOR_CHECKLIST.md`](../operations/KILL_SWITCH_OPERATOR_CHECKLIST.md); verification SSOT [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) ([#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529)) | `enforceable_now` | Kill-switch **ACTIVE** → all trading **halt**; cannot bypass | Runbook §9 matrix; dry-run [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Circuit Breaker** | Canary thresholds `TBD_BLOCKER_BEFORE_LIVE` | **Wired live path:** `check_drawdown_limit()` sets `risk_state.circuit_breaker_active` in [`services/risk/service.py`](../../services/risk/service.py) (`process_signal` Layer 1). **Not wired in order flow:** [`services/risk/circuit_breakers.py`](../../services/risk/circuit_breakers.py) `CircuitBreaker.check_breakers()` (drawdown **15%**, loss **5%**, error rate **10%**, frequency **60/min**) — documented module + unit tests only; `E2E_DISABLE_CIRCUIT_BREAKER` for tests | `enforceable_now` (drawdown latch only); `docs_only` (standalone breaker thresholds); `blocker_before_live` (canary tuning) | Drawdown latch → **BLOCK** + `circuit_breaker_active`; unwired breaker thresholds must **not** be read as live protection until integrated | `tests/unit/risk/test_service.py`; [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529), [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Kill Switch** | ACTIVE = global halt | [`core/safety/kill_switch.py`](../../core/safety/kill_switch.py); SSOT [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md); P5 precheck `kill_switch_precheck_inactive` in `infrastructure/scripts/soak_gate_eval.py` (precheck gap — runbook §9) | `enforceable_now` | `get_kill_switch_state()` true → **no new orders**; fail-closed if state unevaluable (Risk gate) | `GET /kill-switch`; runbook §9; dry-run [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Alertmanager / Prometheus outage** | Policy: fail-closed (no new risk-on) | [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) §8; P5 governance abort: observability unevaluable per [`governance/p5_canary_readiness.yaml`](../../governance/p5_canary_readiness.yaml) | `docs_only` | If monitoring cannot attest health: **halt new live orders**, operator manual stop, keep **NO-GO** | [LR-050-OBSERVABILITY-GATES.md](./LR-050-OBSERVABILITY-GATES.md) |
| **Data gaps (staleness / silence)** | Generic thresholds only (not canary approval) | `DECISION_THRESHOLDS`: `staleness_s_max` **5.0** s, `data_silence_s_max` **30.0** s in [`services/risk/service.py`](../../services/risk/service.py); stale market → block path | `enforceable_now` (generic); `blocker_before_live` (canary tuning) | Staleness/silence over threshold → **BLOCK**; missing timestamps → conservative block | Risk decision unit tests; [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531), [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| **Unexpected fill rate** | `TBD_BLOCKER_BEFORE_LIVE` | Abort/investigate rules for unexpected fills → [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531); no dedicated fill-rate gate in risk service config | `docs_only`; `blocker_before_live` | Fill rate or reject spike beyond plan → **halt** + operator REVOKED path; fail-closed until matrix exists | [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531), [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |

---

## 5. Global fail-closed defaults

1. **Default verdict:** `NO-GO` for live-capital until valid Human GO per [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) §4.
2. **Risk service default:** Signals without explicit **ALLOW** are **BLOCK** ([`services/risk/README.md`](../../services/risk/README.md)).
3. **Ambiguous or unevaluable gate:** Treat as **block** — no order placement, no `MOCK_TRADING="false"`, no inference from CI/PR/issue close.
4. **Kill-switch precedence:** Active kill-switch overrides all other limits.
5. **`TBD_BLOCKER_BEFORE_LIVE`:** Any limit still TBD at Human GO time → **invalid GO** (missing Pflichtfeld).

---

## 6. Handoff to downstream issues

### [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) — Canary Plan (required imports)

The canary plan **must** include, for each row in §4 with `TBD_BLOCKER_BEFORE_LIVE`:

- Concrete numeric/value + unit (USDT, %, count, UTC window).
- Explicit reference to this file (section + limit name).
- Stop criteria tied to **Max Daily Loss**, **Circuit Breaker**, and **Kill Switch** rows.
- Statement that plan publication does **not** activate live trading (kein Live-Go, kein Echtgeld-Go, No auto-live).

### [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) — Dry-run Proof (required demonstrations)

Dry-run evidence **must** show, without live orders:

- Risk gate returns BLOCK/DENY when a limit would be exceeded (simulated or configured test values).
- `real_money=false` and/or `dry_run=true` documented in evidence artifact.
- Kill-switch precheck and exposure/notional paths exercised read-only where possible.
- No secrets in logs or issues.

---

## 7. Acceptance mapping (Issue #2528)

| #2528 acceptance criterion | Section |
|---------------------------|---------|
| Risk limits documented | §4 matrix |
| Limits technically checkable or marked blocker | §3 legend + §4 `Enforceability` column |
| Fail-closed behavior described | §4 `Fail-closed` column + §5 |
| No live-go through this issue | Safety boundaries |
| No Echtgeld-go through this issue | Safety boundaries |

---

## 8. Issue closure note

Closing [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528) via PR merge delivers **gate structure and enforceability mapping** only. It does **not**:

- Set `ready-for-human-live-approval` ([#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535)),
- Grant live-capital GO,
- Replace [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) / [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) deliverables.

Operator checklist gate #2 in [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) §3 may move to **CLOSED + SSOT** once this file is on `main`.

---

## Related documents

- [`README.md`](./README.md) — live-readiness index
- [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) — decision pack ([#2526](https://github.com/jannekbuengener/Claire_de_Binare/issues/2526))
- [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) — human GO/REVOKE ([#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534))
- [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) — stop/halt SSOT ([#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529))
- [`LR-050-CANARY-PLAN.md`](./LR-050-CANARY-PLAN.md) — integration plan ([#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532); plan_only)
- [`LR-050-DRY-RUN-PROOF.md`](./LR-050-DRY-RUN-PROOF.md) — dry-run proof contract ([#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533); docs_only)
- [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md) — global NO-GO (unchanged)
