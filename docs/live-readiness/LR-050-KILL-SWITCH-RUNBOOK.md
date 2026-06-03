# LR-050 Kill-Switch Runbook — Stop and Halt Controls for First Live-Capital Canary

- **Control:** `LR-050` (P5 Canary Echtgeld / Live-Kapital)
- **GitHub issue:** [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529)
- **Document role:** Repo-backed SSOT for manual and automatic stop paths, recovery, auto-live exclusion, and verification matrix (**gate definition only — not activation**)
- **Last updated:** 2026-06-03
- **Companion:** [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md), [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md), [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md)
- **Verdict authority (unchanged):** [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)

## Safety boundaries (read first)

| Rule | Status |
|------|--------|
| Global `LR-050` verdict | **NO-GO** until separate explicit Human Approval |
| This document authorizes live trading | **No** — kein Live-Go |
| This document authorizes real-money exposure | **No** — kein Echtgeld-Go |
| Merge of PR that adds this document | **Documentation only** — ersetzt **niemals** Human Approval |
| Automatic activation / auto-live | **Forbidden** — No auto-live |
| Board stage `trade-capable` | **Not** live-capital authorization (orthogonal to LR) |
| Runtime actions via this document | **None** — no container stop, no Kill Switch activation, no orders |

**Terminology (do not conflate):**

| Term | Meaning in this repo |
|------|----------------------|
| **File Kill Switch** | Persistent state file (`CDB_KILL_SWITCH_STATE_FILE`); global HALT via [`core/safety/kill_switch.py`](../../core/safety/kill_switch.py) |
| **Circuit Breaker (in-memory)** | `risk_state.circuit_breaker_active` set by `check_drawdown_limit()` in [`services/risk/service.py`](../../services/risk/service.py) — blocks signals; **does not** write the file Kill Switch |
| **Circuit Breaker (module)** | [`services/risk/circuit_breakers.py`](../../services/risk/circuit_breakers.py) — standalone thresholds; **not imported** in production `process_signal` path |
| **Risk-service halt** | Signal blocked before order creation (kill-switch gate, drawdown, exposure, `decide_trade` BLOCK, bot shutdown) |
| **Execution-service halt** | Order rejected in `process_order()` (kill-switch, shadow, bot shutdown, trace contract) |
| **Alert-triggered halt** | Operator/policy response per [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) ([#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531)) |
| **Safe execution mode (not halt)** | `MOCK_TRADING`, `DRY_RUN`, `MEXC_TESTNET` — reduce real mainnet capital exposure; **do not** REJECT orders in `process_order()`; `MockExecutor` / `LiveExecutor` dry-run may return **FILLED** simulated results |

---

## 1. Scope and non-goals

### In scope

- Document every stop/halt path required by [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) with source file/symbol evidence, enforceability, verification method, and fail-closed behavior.
- Define Recovery after halt and Auto-Live exclusion gates.
- Hand off runtime proof requirements to [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) (dry-run) and [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) (alert abort matrix).

### Non-goals

- No runtime, service, compose, env, or secret changes.
- No container/service stop execution in this deliverable.
- No change to [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md).
- No replacement of [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) observability deliverables or [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) dry-run evidence.

---

## 2. Related documents

| Document / issue | Relationship |
|------------------|--------------|
| [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) | Planning context; §6 Stop/Kill references this SSOT |
| [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) | GO block `Stop/kill rules:` must reference this file after #2529 closes; REVOKED §9.1 triggers halt |
| [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) | Numeric limits; stop rows defer verification proof to this runbook |
| [`LR-050-VENUE-AUDIT.md`](./LR-050-VENUE-AUDIT.md) | Venue paths; `MOCK_TRADING` / `DRY_RUN` / `MEXC_TESTNET` are safe modes ([#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527)) |
| [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) | Post-halt credential rotation / revocation ([#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530)) |
| [`docs/operations/KILL_SWITCH_OPERATOR_CHECKLIST.md`](../operations/KILL_SWITCH_OPERATOR_CHECKLIST.md) | Operator HTTP toggle flows (`:8002`); **does not** prove end-to-end order stop alone |
| [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) | Alert-triggered halt / abort vs investigate matrix |
| [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) | Live-path dry-run proof without order placement |
| [`governance/p5_canary_readiness.yaml`](../../governance/p5_canary_readiness.yaml) | P5 governance abort when observability unevaluable |

---

## 3. Enforceability legend

| Tag | Meaning |
|-----|---------|
| `enforceable_now` | Mechanism exists in repo (code, compose default, or operator runbook); verifiable without new implementation |
| `docs_only` | Policy or partial wiring documented; not fully proven on LR-050 canary path |
| `blocker_before_live` | Concrete canary proof or fix mandatory before live-capital Human GO |

**Runtime action required:** `yes` = needs separate explicit Runtime-GO (stack up, operator drill, E2E). This deliverable performs **no** such actions.

---

## 4. Manual stop paths

### 4.1 Operator halt (File Kill Switch — MANUAL)

| Field | Detail |
|-------|--------|
| **Mechanism** | `POST /kill-switch/activate` on Risk service (`127.0.0.1:8002`); writes persistent state via [`core/safety/kill_switch.py`](../../core/safety/kill_switch.py) `KillSwitchReason.MANUAL` |
| **State file** | `CDB_KILL_SWITCH_STATE_FILE` (Compose BLUE: `/app/kill_switch/.cdb_kill_switch.state`, shared volume `kill_switch_state` on `cdb_risk` + `cdb_execution`) |
| **Effect** | Risk `_kill_switch_gate()` blocks signals; Execution `process_order()` rejects orders (defense-in-depth) |
| **Operator reference** | [`KILL_SWITCH_OPERATOR_CHECKLIST.md`](../operations/KILL_SWITCH_OPERATOR_CHECKLIST.md) |
| **Deactivation** | `POST /kill-switch/deactivate` requires `operator` + `justification`; **not** a substitute for Human REVOKED text |

### 4.2 Service / container stop (documented only)

| Field | Detail |
|-------|--------|
| **Mechanism** | Documented operator paths: `make docker-down`, `docker compose -f infrastructure/compose/compose.blue.yml down` (see [`AGENTS.md`](../../AGENTS.md) Docker section) |
| **Effect** | Stops order flow by stopping processes — coarse halt, not a trading-governance gate |
| **This deliverable** | **Not executed.** Requires separate Runtime-GO to run or verify. |

### 4.3 Capital-safe execution modes (not halt gates)

These env/config flags are **Auto-Live / mainnet-capital guards**, not upstream halt gates in `process_order()`. Orders that pass Risk and Execution halt checks may still flow through execution and produce **simulated or dry-run FILLED results** — that is **not** proof that order flow was stopped.

| Env / config | Service | Default (repo) | Role |
|--------------|---------|----------------|------|
| `MOCK_TRADING` | Execution [`services/execution/config.py`](../../services/execution/config.py) | `"true"` | Selects mock adapter ([`MockExecutor`](../../services/execution/mock_executor.py)) — simulates fills; **no** upstream REJECT |
| `DRY_RUN` | Execution config + [`LiveExecutor._create_dry_run_result()`](../../services/execution/live_executor.py) | `"true"` | Live adapter path may return **FILLED** dry-run results; **no** upstream REJECT |
| `MEXC_TESTNET` | Execution config | `"true"` | Testnet routing — not a `process_order()` reject gate |
| `CONFIRM_LIVE_TRADING` | Execution [`_require_live_confirmation()`](../../services/execution/service.py) | unset / not `"true"` | **Startup gate only:** `sys.exit(1)` if MOCK/DRY_RUN/TESTNET all false — not a per-order halt |
| Compose BLUE | [`compose.blue.yml`](../../infrastructure/compose/compose.blue.yml) `cdb_execution` | `MOCK_TRADING: "true"` | Canonical stack default — **No auto-live** on mainnet |

**Note:** `LIVE_TRADING_CONFIRMED` is **not** a repo env name. Live confirmation uses **`CONFIRM_LIVE_TRADING=true`**.

**Distinction for #2533 dry-run evidence:** Simulated/dry-run **FILLED** results prove **no real mainnet execution**, not that halt gates blocked order flow. Halt proof requires reject paths (shadow, File Kill Switch, bot shutdown) or explicit operator halt (§4.1).

Setting `MOCK_TRADING="false"` without valid Human GO per [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) §4 is **fail-closed** policy violation.

---

## 5. Automatic stop paths

### 5.1 Risk-service halt (signal layer)

| Path | Source | Fail-closed behavior |
|------|--------|----------------------|
| File Kill Switch gate | `_kill_switch_gate()` → `get_kill_switch_details(create_if_missing=False)` | Eval error → block (`KILL_SWITCH_UNEVALUABLE`); active → block |
| Drawdown / in-memory Circuit Breaker | `check_drawdown_limit()` → `risk_state.circuit_breaker_active = True` | Daily loss over cap → block signal + CRITICAL alert + `emit_bot_shutdown()` (once) |
| Exposure / cooldown / risk_off | `check_exposure_limit()`, allocation `cooldown_until`, `risk_off_active` | Over limit or active cooldown → block |
| Decision contract / `decide_trade()` | `DECISION_THRESHOLDS` in [`services/risk/service.py`](../../services/risk/service.py) | Default **BLOCK** unless explicit ALLOW |
| Bot shutdown stream | `emit_bot_shutdown()` → Execution listens, sets `bot_shutdown_active` | Blocks new orders (global or per strategy/bot) |

### 5.2 File Kill Switch (automatic reasons — enum only)

[`KillSwitchReason`](../../core/safety/kill_switch.py) includes `CIRCUIT_BREAKER`, `RISK_LIMIT`, `SYSTEM_ERROR`, `EXCHANGE_ERROR`, `AUTH_FAILURE`. **No production caller** in `services/risk/service.py` was found that auto-invokes `activate_kill_switch()` on drawdown. Drawdown uses in-memory CB + bot shutdown, **not** file Kill Switch.

### 5.3 Circuit Breaker (two concepts)

1. **Wired (in-memory):** `check_drawdown_limit()` / Layer 1 in `process_signal` — metric `circuit_breaker_active` on `/metrics`.
2. **Unwired module:** [`services/risk/circuit_breakers.py`](../../services/risk/circuit_breakers.py) (`CircuitBreaker.check_breakers()`) — unit tests only; thresholds (e.g. 15% drawdown, 60 orders/min) must **not** be read as live protection.

Prometheus alert [`CircuitBreakerTriggered`](../../infrastructure/monitoring/alerts.yml) fires on `circuit_breaker_active == 1` (in-memory metric), **not** on `risk_kill_switch_active` (file state).

### 5.4 Alert-triggered halt

| Status | Detail |
|--------|--------|
| **Policy** | Fail-closed: monitoring unevaluable → no new risk-on; operator manual halt |
| **Repo today** | Critical alerts defined (e.g. `ServiceDown`, `CircuitBreakerTriggered`, `DatabaseConnectionLost`); canary matrix → [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) |
| **Enforceability** | `docs_only` until operator receiver proof per observability SSOT |

### 5.5 Data gaps / stale data

| Mechanism | Source | Thresholds (generic — not canary approval) |
|-----------|--------|---------------------------------------------|
| Staleness | `decide_trade()` in [`services/risk/service.py`](../../services/risk/service.py) | `DECISION_THRESHOLDS["staleness_s_max"]` = **5.0** s |
| Data silence | same | `DECISION_THRESHOLDS["data_silence_s_max"]` = **30.0** s |
| Missing timestamps | same | `staleness_s is None` → conservative block path |

Canary-specific tuning remains `blocker_before_live` until [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532).

### 5.6 Unexpected fill rate

| Status | Detail |
|--------|--------|
| **Repo today** | No dedicated fill-rate gate in risk service config |
| **Policy** | Fail-closed until [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) defines abort/investigate rules; operator REVOKED + manual Kill Switch |
| **Enforceability** | `docs_only`; `blocker_before_live` for canary |

---

## 6. Execution-service halt behavior

[`services/execution/service.py`](../../services/execution/service.py) `process_order()` — **halt gates** (order REJECTED before executor):

| Order | Gate | Result |
|-------|------|--------|
| 1 | Trace contract (`TRACE_CONTRACT_V1_ENABLED`, Compose `"1"`) — missing `decision_id` | REJECTED |
| 2 | `run_mode == "shadow"` | REJECTED (`shadow_blocked`) |
| 3 | File Kill Switch (`get_kill_switch_details`) | REJECTED; eval exception → fail-closed active |
| 4 | Bot shutdown (`bot_shutdown_active`, blocked strategy/bot IDs) | REJECTED |

**Not halt gates** (order may proceed to executor after gates above pass):

| Mode | Behavior | Proof implication (#2533) |
|------|----------|---------------------------|
| `MOCK_TRADING=true` | `MockExecutor.execute_order()` — simulated latency/fills | FILLED mock results ≠ halt; proves no live adapter call |
| `DRY_RUN=true` (MEXC path) | `LiveExecutor._create_dry_run_result()` — **FILLED** dry-run payload | FILLED dry-run ≠ halt; proves no exchange submission |
| `MEXC_TESTNET=true` | Testnet routing at adapter init | Not mainnet capital; not a REJECT gate |

`CONFIRM_LIVE_TRADING` is evaluated at **service startup** only (`_require_live_confirmation()`); it does not REJECT individual orders.

Defense-in-depth: Risk may block before Execution; Execution re-checks File Kill Switch independently.

---

## 7. Recovery after halt

### 7.1 Preconditions before resuming trading

| # | Check | Evidence |
|---|-------|----------|
| 1 | File Kill Switch **inactive** | `GET /kill-switch` → `active: false` or checklist precheck ([`KILL_SWITCH_OPERATOR_CHECKLIST.md`](../operations/KILL_SWITCH_OPERATOR_CHECKLIST.md)) |
| 2 | In-memory circuit breaker cleared | Risk `/status` → `circuit_breaker: false` (or operator attestation after root-cause fix) |
| 3 | Bot shutdown cleared | Execution no longer in shutdown state; Redis stream quiesced |
| 4 | Human authorization | Valid GO block §4 in [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) still in force; if REVOKED issued → **NO-GO**, no resume |
| 5 | Monitoring | [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) gates satisfied before live-capital GO |
| 6 | Config | `MOCK_TRADING` / execution mode match approved canary plan ([#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532)); no silent `MOCK_TRADING="false"` |

### 7.2 Evidence to retain

- UTC timestamp, operator name, halt reason
- Kill Switch GET response (active + inactive)
- REVOKED text if Human Approval withdrawn ([`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) §9.1)
- Incident summary for [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) reconcile

### 7.3 Wiederaufnahme blockiert ohne Human Approval

- Kill Switch deactivation alone **does not** grant live-capital authorization.
- Global verdict remains **NO-GO** per [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md) until explicit GO per Human Approval §4.
- Issue/PR merge (including this runbook) **does not** replace Human Approval.

---

## 8. Auto-Live exclusion

| Gate | Mechanism |
|------|-----------|
| LR verdict | [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md) — **NO-GO** |
| Human Approval | Only exact §4 GO on #2535 (or delegated handoff); REVOKED ends authorization |
| Compose default | `MOCK_TRADING: "true"` on `cdb_execution` |
| Startup safety | `CONFIRM_LIVE_TRADING=true` required only when MOCK/DRY_RUN/TESTNET all false |
| Issue/PR/CI | Close #2529, green CI, merge — **no** Live-Go, kein Echtgeld-Go, No auto-live |
| Board stage | `trade-capable` orthogonal — not LR-GO ([`CONTROL_REGISTER.md`](../runbooks/CONTROL_REGISTER.md)) |
| Agent/session GO | Invalid per Human Approval §8 |
| `DELIVERY_APPROVED.yaml` | Human-controlled; agents must not modify ([`AGENTS.md`](../../AGENTS.md)) |

---

## 9. Prüfbarkeits-Matrix (Stop paths)

| control | source/mechanism | enforceability | verification method | runtime action required | blocker status | fail-closed behavior |
|---------|------------------|----------------|---------------------|-------------------------|----------------|----------------------|
| Operator manual halt (File Kill Switch) | `POST /kill-switch/activate`; [`core/safety/kill_switch.py`](../../core/safety/kill_switch.py); shared `CDB_KILL_SWITCH_STATE_FILE` | `enforceable_now` | Unit: `tests/unit/safety/test_kill_switch.py`, `tests/unit/risk/test_kill_switch_endpoints.py`; HTTP checklist | yes (Runtime-GO for live drill) | OPEN until #2533 dry-run + optional E2E | Active → Risk block + Execution REJECTED; read error → active (KS core) / unevaluable (Risk gate) |
| Kill Switch deactivate | `POST /kill-switch/deactivate` | `enforceable_now` | Same endpoints tests; operator checklist | yes | Recovery requires Human GO still valid | Deactivate without GO does not authorize live capital |
| Service/container stop | `make docker-down` / compose down | `docs_only` | Documented in AGENTS.md; not executed here | yes | Coarse halt; not a governance SSOT | Process stop → no orders; no substitute for Kill Switch audit |
| `MOCK_TRADING` / `DRY_RUN` / `MEXC_TESTNET` (safe modes) | [`services/execution/config.py`](../../services/execution/config.py); Compose `MOCK_TRADING: "true"`; not `process_order()` reject gates | `enforceable_now` (config); **not halt gates** | Read compose + config; code paths in `MockExecutor` / `LiveExecutor` dry-run | no | Default prevents **real mainnet** execution; order flow may continue with simulated FILLED results | Simulated/dry-run fills **must not** be read as halt proof (#2533) |
| `CONFIRM_LIVE_TRADING` startup gate | [`services/execution/service.py`](../../services/execution/service.py) `_require_live_confirmation()` | `enforceable_now` | Code read; startup test optional Runtime-GO | yes (if testing live startup path) | `blocker_before_live` if operator disables all safe modes without GO | Missing `CONFIRM_LIVE_TRADING=true` → `sys.exit(1)` at startup; not per-order REJECT |
| Risk File Kill Switch gate | `_kill_switch_gate()` in [`services/risk/service.py`](../../services/risk/service.py) | `enforceable_now` | Unit coverage indirect; #2533 dry-run | no (unit); yes (E2E) | E2E order-flow proof → `blocker_before_live` | Eval failure → block signal |
| Risk drawdown halt (in-memory CB) | `check_drawdown_limit()`; `risk_state.circuit_breaker_active` | `enforceable_now` | `tests/unit/risk/test_service.py`; metric `circuit_breaker_active` | no | Does not set file KS; canary threshold TBD | Over drawdown → block + alert + bot shutdown |
| Risk `decide_trade()` BLOCK | `DECISION_THRESHOLDS`, staleness/silence | `enforceable_now` (generic thresholds) | Risk unit tests; #2533 | no | Canary tuning `blocker_before_live` | Missing/ stale data → BLOCK |
| Risk exposure / cooldown halt | `check_exposure_limit()`, `cooldown_until` | `enforceable_now` | `tests/unit/risk/test_service.py` | no | Session caps TBD #2532 | Over limit / cooldown → block |
| Risk bot shutdown | `emit_bot_shutdown()` Redis stream | `enforceable_now` (code) | Partial; full flow `blocker_before_live` | yes (Runtime-GO) | E2E shutdown proof open | Execution rejects new orders |
| Circuit Breaker module (unwired) | [`services/risk/circuit_breakers.py`](../../services/risk/circuit_breakers.py) | `docs_only` | `tests/unit/risk/test_circuit_breakers.py` only | no | Must not be claimed as live protection | N/A in production path |
| Execution Kill Switch gate | `process_order()` KS check | `enforceable_now` | `tests/unit/services/test_execution_shadow_gate.py`; E2E `tests/e2e/test_kill_switch_live.py` (`E2E_RUN=1`) | yes (E2E) | Canary E2E proof → #2533 / Runtime-GO | Active or eval error → REJECTED |
| Execution shadow gate | `run_mode == "shadow"` | `enforceable_now` | `test_execution_shadow_gate.py` | no | — | REJECTED |
| Execution bot shutdown gate | `bot_shutdown_active` / blocked IDs | `enforceable_now` (code) | Integration partial | yes (Runtime-GO) | Full proof `blocker_before_live` | REJECTED |
| Trace contract gate | `TRACE_CONTRACT_V1_ENABLED` | `enforceable_now` | Contract tests | no | — | Missing decision_id → REJECTED |
| Alert-triggered halt | [`infrastructure/monitoring/alerts.yml`](../../infrastructure/monitoring/alerts.yml); policy → #2531 | `docs_only` | Alert rules exist; receiver/abort matrix missing | yes (#2531) | `blocker_before_live` before live GO | Unevaluable monitoring → operator halt, stay NO-GO |
| Unexpected fill rate halt | Policy → #2531 | `docs_only` | No dedicated gate in risk config | yes (#2531) | `blocker_before_live` | Fail-closed until matrix exists |
| P5 soak precheck `kill_switch_precheck_inactive` | [`infrastructure/scripts/soak_gate_eval.py`](../../infrastructure/scripts/soak_gate_eval.py) reads `risk_state.circuit_breaker`, **not** file KS | `blocker_before_live` | `tests/unit/scripts/test_soak_gate_eval.py` | no | Precheck can pass while file KS active — gap | Misleading PASS if only CB flag checked |
| Prometheus `risk_kill_switch_active` | `/metrics` gauge; read failure → **0** | `blocker_before_live` | `test_metrics_endpoint` if present | no | Metric fail-open on read error vs order gates fail-closed | Do not rely on metric alone for halt proof |

---

## 10. Handoff to [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) — Dry-run Proof

### 10.1 Dry-run (no Runtime-GO required where read-only)

- Config resolution: document `MOCK_TRADING`, `DRY_RUN`, `MEXC_TESTNET`, `CDB_KILL_SWITCH_STATE_FILE` without changing stack.
- `GET /kill-switch` precheck read-only (inactive before canary).
- Risk gate simulation: verify BLOCK/DENY paths with test values; `real_money=false` / `dry_run=true` in evidence artifact.
- Execution **halt** gates: confirm shadow / File Kill Switch / bot shutdown **REJECT** paths via unit/integration tests — **no live order**.
- **Do not** treat mock or dry-run **FILLED** results as halt proof; they only attest no real mainnet submission (§4.3, §6).

### 10.2 Runtime-GO only (separate explicit approval)

- Operator activate/deactivate drill with running BLUE stack (`POST /kill-switch/activate`).
- E2E: `tests/e2e/test_kill_switch_live.py` with `E2E_RUN=1` — Risk POST → Execution block.
- Container stop drill (`make docker-down`) — document outcome only under Runtime-GO.
- Alert firing → operator halt workflow after #2531 deliverable.

---

## 11. Acceptance mapping (Issue #2529)

| #2529 acceptance criterion | Section |
|----------------------------|---------|
| Stop-/Kill-Switch-Runbook liegt vor | This document |
| Mindestens ein manueller Stop-Pfad dokumentiert | §4.1 Operator halt |
| Automatische Halt-Bedingungen dokumentiert | §5 |
| Auto-Live bleibt ausgeschlossen | §8 |
| Kein echter Live-Test ohne separates Human-Go | Safety boundaries; §10.2 Runtime-GO split |
| Recovery nach Halt | §7 |
| Nachweis-Matrix | §9 |

---

## 12. Restunsicherheiten

1. **`soak_gate_eval.py` precheck gap:** `kill_switch_precheck_inactive` checks in-memory `circuit_breaker`, not `GET /kill-switch` or file state — can diverge from File Kill Switch.
2. **Drawdown does not activate file Kill Switch:** Automatic file KS reasons exist in enum but are not wired from `check_drawdown_limit()`.
3. **`risk_kill_switch_active` metric:** Reports `0` on read failure (not fail-closed like order gates).
4. **`MOCK_TRADING` / `DRY_RUN` safe modes:** Simulated or dry-run FILLED results are not halt proof — distinguish from REJECT gates (§4.3, §6).
5. **`KILL_SWITCH_OPERATOR_CHECKLIST.md`:** Does not prove end-to-end order-flow stop under live runtime (stated in checklist Limits §83–87).
6. **Alert / fill-rate abort:** Deferred to [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531); policy here is fail-closed only.

Closing [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) via PR merge delivers **gate definition and verification matrix** only. It does **not** grant live-capital GO, clear `LR-050`, or replace #2531/#2533 runtime proof.

---

## Related documents

- [`README.md`](./README.md) — live-readiness index
- [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) — decision pack ([#2526](https://github.com/jannekbuengener/Claire_de_Binare/issues/2526))
- [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) — numeric limits ([#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528))
- [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) — Human Approval ([#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534))
- [`LR-050-CANARY-PLAN.md`](./LR-050-CANARY-PLAN.md) — integration plan ([#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532); plan_only)
- [`LR-050-DRY-RUN-PROOF.md`](./LR-050-DRY-RUN-PROOF.md) — dry-run proof contract ([#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533); docs_only)
- [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md) — global NO-GO (unchanged)
