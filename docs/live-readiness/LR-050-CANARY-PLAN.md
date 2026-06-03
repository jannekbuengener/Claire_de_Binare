# LR-050 Canary Plan — First Controlled Live-Capital Integration Plan

- **Control:** `LR-050` (P5 Canary Echtgeld / Live-Kapital)
- **GitHub issue:** [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532)
- **Document role:** Integration plan binding delivered LR-050 SSOTs into one controlled first crypto / real-money canary **procedure shape** — **not activation**, **not executable**
- **Last updated:** 2026-06-04
- **Verdict authority (unchanged):** [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)

## Safety boundaries (read first)

| Rule | Status |
|------|--------|
| **Plan status** | `plan_only` |
| Global `LR-050` verdict | **NO-GO** — LR remains NO-GO |
| Human live-capital approval | **not approved** — requires exact Human Approval from [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) |
| Executability | **not executable** — no operator may treat this document as a start command |
| This document authorizes live trading | **No** — kein Live-Go |
| This document authorizes real-money exposure | **No** — kein Echtgeld-Go |
| Automatic activation / auto-live | **Forbidden** — No auto-live |
| Auto-start | **Forbidden** |
| Board stage `trade-capable` | **Not** live-capital authorization (orthogonal to LR) |
| Issue/PR merge (#2532) | **Documentation only** — does **not** replace Human Approval |
| P5 prestart Human Gate (2026-04-04) | Shadow/prestart only — **not** this live-capital canary |
| Secrets in this document | **None** |
| Orders / runtime mutation via this document | **None** |

**This plan is not startable.** Publication does not clear `LR-050`, does not mark any venue live-ready, and does not satisfy dry-run or final-reconcile gates.

---

## 1. Scope and non-goals

### In scope

- Integrate delivered LR-050 SSOTs (Decision, Human Approval, Risk Limits, Kill-Switch, Secrets, Observability, Venue Audit) into one **human-reviewable** canary plan skeleton.
- Declare operator gates, stop criteria, execution-mode boundaries, and handoffs to [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) (Dry-run Proof) and [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) (Final Reconcile).
- Mark every canary parameter that is not repo-backed for live-capital GO as `TBD_BLOCKER_BEFORE_LIVE`.

### Non-goals

- **No** venue/broker inventory duplication — venue facts live in [`LR-050-VENUE-AUDIT.md`](./LR-050-VENUE-AUDIT.md) ([#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527)); this plan **references** only.
- **No** broker/exchange calls, HTTP/WebSocket calls, API-key validation, balance queries, orders, secret reads, DB writes, Docker/stack commands, or changes to services, compose, env, GitHub secrets, or [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md).
- **No** invention of symbols, notional caps, session duration, operator paging channel, or receiver proof artifacts.

---

## 2. LR-050 SSOT index (integration inputs)

| SSOT | Issue | Role in this plan |
|------|-------|-------------------|
| [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) | [#2526](https://github.com/jannekbuengener/Claire_de_Binare/issues/2526) | Planning context; gate matrix; TBD parameter mirror |
| [`LR-050-VENUE-AUDIT.md`](./LR-050-VENUE-AUDIT.md) | [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) | Venue candidate path only — **not** re-audited here |
| [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) | [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528) | Hard limit names, enforceability, fail-closed |
| [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) | [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) | Stop/halt paths and recovery preconditions |
| [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) | [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530) | Credential classes; forbidden permissions |
| [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) | [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) | Abort/investigate policy; receiver proof definition |
| [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) | [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534) | Exact GO/REVOKE — **separate** gate on [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) |

Open proof/reconcile issues (block live-ready claims):

| Issue | State (planning time) | Blocks |
|-------|----------------------|--------|
| [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) | OPEN | Dry-run Proof; venue-ready claim |
| [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) | OPEN | Final LR reconcile; Human Approval audit channel |

---

## 3. Canary parameters (integration table)

Values are **canary approval** fields for a future Human GO block. Generic repo defaults (e.g. drawdown **0.05**, exposure **0.30**) are **not** canary approval — see [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) §4.

| Parameter | Canary value | SSOT | Notes |
|-----------|--------------|------|-------|
| **Venue** | `candidate_controlled_path`: MEXC (repo-only integrated execution path) | [LR-050-VENUE-AUDIT.md](./LR-050-VENUE-AUDIT.md) §7.1 | **Not** live-ready; **not** approved canary venue while #2533 and #2535 are OPEN |
| **Symbols** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 Allowed Symbols; Venue Audit §8.1 | No repo-backed approved symbol list for canary |
| **Max notional per order** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 | Mechanism `RC_LIMIT_NOTIONAL` exists; canary USDT value TBD |
| **Max notional session total** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 | Session aggregate cap not fully wired — plan value TBD |
| **Max daily loss** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 | Drawdown latch wired; canary %/USDT TBD |
| **Max orders per session** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 | Do not use 60 orders/min as canary approval |
| **Max slippage (canary)** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 | Generic 1.0 % threshold in risk service ≠ canary cap |
| **Trading window (UTC)** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 Trading Window | No `TRADING_WINDOW` in risk config today |
| **Cooldown rules** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 Cooldown | `cooldown_until` wired; canary policy TBD |
| **Canary duration / end time** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md) §5 `Duration (UTC window):` | Required in future GO block |
| **Order types (approved set)** | `TBD_BLOCKER_BEFORE_LIVE` | Venue Audit §8.1; repo mechanism below §5 | See §5 — do not infer approval from code paths alone |
| **Operator notification channel** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-OBSERVABILITY-GATES.md](./LR-050-OBSERVABILITY-GATES.md) §6 | Alertmanager vs Grafana not canonically chosen |
| **Receiver proof (operator receipt)** | `blocker_before_live` | [LR-050-OBSERVABILITY-GATES.md](./LR-050-OBSERVABILITY-GATES.md) §3–§4 | No LR-050 canary receipt artifact on `main` yet |
| **Credential file set (`MEXC_*` vs `MEXC_TRADE_*`)** | `TBD_BLOCKER_BEFORE_LIVE` | [LR-050-SECRETS-READINESS.md](./LR-050-SECRETS-READINESS.md); Venue Audit §7.2 | Which set applies to canary TBD |
| **Venue permissions / IP / account binding** | `TBD_BLOCKER_BEFORE_LIVE` | Venue Audit §7.2; Secrets §7 | Operator + future evidence |

Mirror (non-approving): Decision Pack [§5](./LR-050-DECISION-PACK.md#5-canary-parameter-tbd--nicht-freigebend).

---

## 4. Venue (reference only)

| Rule | Detail |
|------|--------|
| Inventory SSOT | [`LR-050-VENUE-AUDIT.md`](./LR-050-VENUE-AUDIT.md) — full path/mode matrix lives there |
| Repo-found candidate | **MEXC** — sole integrated execution venue in working repo |
| Live-ready | **No** — while [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) and [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) remain OPEN |
| Canary venue approval | **not approved** — candidate path only; confirm/reject MEXC in operator review after #2533/#2535 |
| Withdrawal/transfer/admin API | **forbidden** per Secrets + Venue policy |

This plan does **not** duplicate Venue Audit §3–§4 tables. Operators resolving venue questions must read Venue Audit SSOT.

---

## 5. Order types (repo mechanism vs canary approval)

| Item | Status |
|------|--------|
| **Repo-backed execution types** | [`services/execution/live_executor.py`](../../services/execution/live_executor.py): `MARKET` and `LIMIT` supported on `LiveExecutor` path; other types raise `Unsupported order type` |
| **Approved canary order-type set** | `TBD_BLOCKER_BEFORE_LIVE` — must be named in Human GO `Symbols:` / plan annex and risk symbol gate |
| **Invent new order types** | **Forbidden** in canary scope unless added to repo in a separate approved change |

Paper/mock paths may expose additional types in [`services/execution/paper_trading.py`](../../services/execution/paper_trading.py); those are **not** Echtgeld canary paths.

---

## 6. Execution mode matrix (`cdb_execution` runtime SSOT)

**Fail-closed:** On `cdb_execution`, effective mode is set only by explicit env flags in [`services/execution/config.py`](../../services/execution/config.py): `MOCK_TRADING`, `DRY_RUN`, `MEXC_TESTNET`. `MOCK_TRADING` **defaults to `true`**; [`services/execution/service.py`](../../services/execution/service.py) uses the mock adapter while it remains true. The service logs `TRADING_MODE` but does **not** apply `get_legacy_config()` from [`core/config/trading_mode.py`](../../core/config/trading_mode.py) on the active path (Venue Audit §3.3).

| Phase | Intended flags (operator-set) | Real money / exchange submit? | Proof owner |
|-------|----------------------------|-------------------------------|-------------|
| Shadow / paper / mock default | `MOCK_TRADING=true` (typical compose default) | **No** | Pre-canary ops |
| **#2533 Dry-run Proof** | **Explicit** `DRY_RUN=true`; log `config.DRY_RUN`; typically `MOCK_TRADING=false` if exercising `LiveExecutor` init | **No** exchange submit | [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| `TRADING_MODE=staged` **alone** | **Does not change** `MOCK_TRADING`/`DRY_RUN`/`MEXC_TESTNET` | **Unknown** — treat as **not** dry-run proof | **Forbidden** as #2533 evidence |
| Later testnet exchange-touch | **Explicit** `MOCK_TRADING=false`, `MEXC_TESTNET=true`, `DRY_RUN=false` | Testnet orders possible if creds loaded — **separate** Runtime-GO after Human GO | Not #2533 dry-run |
| Mainnet / live-capital | **Explicit** `MOCK_TRADING=false`, `MEXC_TESTNET=false`, `DRY_RUN=false`, `CONFIRM_LIVE_TRADING=true`, plus Human GO | **Yes** — only after exact Human Approval on #2535; without `MOCK_TRADING=false` the service stays in mock mode | Human Approval + operator |

**TRADING_MODE** is **log/legacy context** on the active execution path unless a future repo change wires `get_legacy_config()` into `cdb_execution` with evidence.

---

## 7. Operator gates (all required before any live-capital window)

| # | Gate | SSOT | Satisfied for live window? |
|---|------|------|----------------------------|
| 1 | Venue path documented | [LR-050-VENUE-AUDIT.md](./LR-050-VENUE-AUDIT.md) — #2527 CLOSED | SSOT yes; **venue not live-ready** while #2533/#2535 OPEN |
| 2 | Risk limits structure | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) — #2528 CLOSED | Structure yes; **canary values** `TBD_BLOCKER_BEFORE_LIVE` |
| 3 | Kill-switch runbook | [LR-050-KILL-SWITCH-RUNBOOK.md](./LR-050-KILL-SWITCH-RUNBOOK.md) — #2529 CLOSED | SSOT yes; dry-run verification → #2533 |
| 4 | Secrets readiness | [LR-050-SECRETS-READINESS.md](./LR-050-SECRETS-READINESS.md) — #2530 CLOSED | Gates defined; venue permission proof `blocker_before_live` |
| 5 | Observability gates | [LR-050-OBSERVABILITY-GATES.md](./LR-050-OBSERVABILITY-GATES.md) — #2531 CLOSED | Policy yes; **receiver proof** `blocker_before_live` |
| 6 | **This canary plan** | This document — #2532 | Delivers integration plan only — **not executable** |
| 7 | Dry-run Proof | [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) | **OPEN** — required before venue-ready / reconcile |
| 8 | Human Approval wording | [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md) — #2534 CLOSED | Wording on `main`; **no GO issued** |
| 9 | Final LR reconcile | [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) | **OPEN** — may set `ready-for-human-live-approval` only if evidence supports; **not GO** |
| 10 | **Exact Human Approval** | [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md) §4 on **#2535** only | **not approved** — separate explicit block; agents/PRs invalid |

---

## 8. Stop criteria (consolidated)

Stop criteria apply during any future approved canary window. **None** grant live GO by themselves. Operator default: **halt new live-capital orders**, invoke kill-switch/runbook, consider REVOKED per Human Approval §9.

### 8.1 Policy classes (Observability Gates)

| Class | Operator action | Reference |
|-------|-----------------|-----------|
| **abort** | Halt new live-capital orders; kill-switch/runbook; consider REVOKED | [LR-050-OBSERVABILITY-GATES.md](./LR-050-OBSERVABILITY-GATES.md) §5 |
| **investigate** | Triage; continue only under explicit Human Approval + written canary constraints | Same |
| **blocker_before_live** | Do not start canary; remain **NO-GO** | Same |

### 8.2 Mandatory stop triggers (plan integration)

| Trigger | Policy class | Primary SSOT |
|---------|--------------|--------------|
| Risk limit breach (notional, exposure, drawdown, slippage, staleness, silence) | **abort** (orders blocked in app) | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4–§5 |
| Kill-switch ACTIVE | **abort** | [LR-050-KILL-SWITCH-RUNBOOK.md](./LR-050-KILL-SWITCH-RUNBOOK.md) |
| Circuit breaker latch (`circuit_breaker_active`) | **abort** | Risk Limits + Observability `CircuitBreakerTriggered` |
| Unexpected fills (rate/count vs plan) | **abort** once thresholds exist; until then **blocker_before_live** | Observability §7.2 |
| Rejected order spike | **investigate** → escalate to halt per plan | Observability §7.2 |
| Shadow/live **mode drift** (approved env ≠ runtime) | **abort** | Observability §7.2; §6 this plan |
| Stale market data / data silence over canary threshold | **abort** (app block); canary alert TBD | Risk Limits §4 |
| Prometheus/Alertmanager outage or unevaluable monitoring | **abort** / manual halt | Observability §8; Risk Limits §4 |
| Receiver failure / no operator receipt proof | **blocker_before_live** before start; **abort** if lost mid-window | Observability §3–§4 |
| Secret/credential incident (leak, wrong key, withdrawal enabled) | **abort** + REVOKED; rotate per Secrets §8 | [LR-050-SECRETS-READINESS.md](./LR-050-SECRETS-READINESS.md) |
| `MOCK_TRADING` / `DRY_RUN` / `MEXC_TESTNET` drift from approved plan | **abort** | Kill-switch runbook §7.1 item 6; §6 this plan |

Numeric thresholds for fills, reject spike, and latency remain `TBD_BLOCKER_BEFORE_LIVE` in this plan — define in operator review or follow-up only with repo-backed evidence.

---

## 9. Final review criteria (before any `ready-for-human-live-approval` or GO)

| Criterion | Required outcome |
|-----------|------------------|
| All §3 parameters still `TBD_BLOCKER_BEFORE_LIVE` | Either closed with repo-backed values + proof **or** global state remains **NO-GO** |
| [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) | **CLOSED** with dry-run evidence: explicit `DRY_RUN=true`, no orders, no secrets in logs, `real_money=false` attested |
| [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) | **CLOSED** with documented verdict: `NO-GO` **or** `ready-for-human-live-approval` only |
| Human live-capital **GO** | **Only** via exact block on [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) per [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md) §4 — **never** via #2532 merge |
| `LR-AUDIT-STATUS` | Updated only through #2535 reconcile scope — **not** by this issue |
| Venue live-ready claim | **Forbidden** until #2533 and #2535 closed and Human GO if applicable |

---

## 10. Handoff — [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) Dry-run Proof

### 10.1 Non-destructive proofs (#2533 may deliver without real orders)

| Check | Evidence expectation |
|-------|---------------------|
| Effective env on `cdb_execution` | `MOCK_TRADING`, `DRY_RUN`, `MEXC_TESTNET`, `EXECUTION_ADAPTER_ID` from config — not inferred from `TRADING_MODE` |
| **Explicit `DRY_RUN=true`** | Startup log shows `config.DRY_RUN`; **`TRADING_MODE=staged` is not Dry-run** |
| `LiveExecutor` / adapter init | Dry-run path without exchange submit ([`live_executor.py`](../../services/execution/live_executor.py)) |
| Risk gates | BLOCK/DENY on simulated exceed; kill-switch precheck where applicable |
| Logs | Attest `real_money=false` / dry-run / no mainnet bundle |
| Secret names only | No API keys, tokens, or values in issues/PRs/logs |
| Alert/monitoring config | Repo file references allowed; **not** operator receiver delivery |

### 10.2 Out of scope for #2533 alone (separate explicit Runtime-GO)

| Check | Why separate |
|-------|--------------|
| Alertmanager/Grafana operator receipt proof | Observability §11 — requires runtime drill |
| ServiceDown / production alert fire | Observability §12 |
| Testnet exchange-touch (`DRY_RUN=false`, `MEXC_TESTNET=true`) | **Not** dry-run — gated post Human GO |
| Live auth success / balance fetch | Secrets §12 — post Human GO |
| Any order placement | **Forbidden** in #2533 |

---

## 11. Handoff — [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) Final Reconcile

#2535 runs **after** #2533 and reviews all child SSOTs. Input artifacts:

| Artifact | Source |
|----------|--------|
| This plan | `LR-050-CANARY-PLAN.md` (#2532) |
| Decision pack | [LR-050-DECISION-PACK.md](./LR-050-DECISION-PACK.md) |
| Venue, risk, kill-switch, secrets, observability, human approval SSOTs | #2527–#2531, #2534 |
| Dry-run evidence bundle | #2533 (path under `reports/` or `docs/evidence/` — TBD by #2533) |
| Operator receiver proof | Future redacted attestation per Observability §4.4 |
| Optional state files | `GO_NO_GO.md`, `LR-050-STATE.yaml` — **only** within #2535 scope |

#2535 may document `ready-for-human-live-approval` **only** if evidence supports it. **GO** for live capital requires a **separate** exact Human Approval block on #2535 — never implied by reconcile or by closing #2532.

---

## 12. Human Approval boundary (repeat)

| Rule | Detail |
|------|--------|
| Who may grant GO | `jannekbuengener` only — [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md) §2 |
| Valid channel | GitHub comment on **#2535** with full GO text — §4 |
| #2532 merge | **Does not** approve, start, or execute canary |
| Agents / CI / Board stage | **Cannot** grant live-capital GO |

---

## 13. Restunsicherheiten

1. All canary numeric caps and symbols remain `TBD_BLOCKER_BEFORE_LIVE`.
2. MEXC testnet/mainnet/WS alignment not operationally proven — Venue Audit §9.
3. Operator paging channel (Alertmanager vs Grafana) undecided — Observability §6.
4. No LR-050 operator receiver receipt artifact on `main`.
5. `TRADING_MODE` not wired to execution env on `cdb_execution`.
6. #2533 and #2535 OPEN — **no venue-ready claim** and **not executable** plan.

---

## 14. Closing statement

Delivery of `LR-050-CANARY-PLAN.md` closes **integration planning** for [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) only.

It does **not**:

- Change global `LR-050` verdict (**NO-GO** remains).
- Grant live-capital GO, Echtgeld-Go, or auto-live.
- Mark MEXC or any path live-ready.
- Replace [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533), [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535), or Human Approval.
- Authorize orders, runtime changes, or secret handling.

**Status:** `plan_only` · **not approved** · **not executable** · LR remains **NO-GO**.

---

## Related documents

- [`README.md`](./README.md) — live-readiness index
- [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) — [#2526](https://github.com/jannekbuengener/Claire_de_Binare/issues/2526)
- [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md) — global NO-GO (unchanged by this issue)
- [`docs/runbooks/CONTROL_REGISTER.md`](../runbooks/CONTROL_REGISTER.md) — Board stage vs LR
