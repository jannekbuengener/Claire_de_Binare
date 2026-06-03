# LR-050 Dry-Run Proof — Docs-Only Evidence Contract (No Runtime Execution)

- **Control:** `LR-050` (P5 Canary Echtgeld / Live-Kapital)
- **GitHub issue:** [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533)
- **Document role:** Repo-backed **docs-only** proof contract and gate matrix for a **future** live-path dry-run — **not** runtime evidence, **not** activation
- **Last updated:** 2026-06-04
- **Companion:** [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md), [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md), [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md)
- **Verdict authority (unchanged):** [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)

## Status banner (this delivery)

| Label | Value |
|-------|--------|
| **Proof type** | `dry_run_proof_contract` |
| **Evidence mode** | `docs_only` |
| **Runtime** | **runtime evidence not executed** — kein echter Dry-run wurde ausgeführt |
| **Live authorization** | `not live` — kein Live-Go |
| **Human approval** | `not approved` — kein Echtgeld-Go; ersetzt **nicht** Human Approval ([#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534)) |
| **Orders** | `no order placement` — keine Order wurde gesendet (in diesem Slice; nicht runtime-bewiesen) |
| **Secrets** | keine Secrets wurden gelesen oder ausgegeben in der Erstellung dieses Dokuments |
| **Global LR** | **LR remains NO-GO** |
| **Auto-live** | **Forbidden** — No auto-live |

**Acceptance for [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) (docs slice):** This file closes the **planning/contract** deliverable only. **Runtime dry-run evidence** remains `blocker_before_live` until a separate **Runtime-GO** slice executes stack checks without violating safety boundaries.

---

## Safety boundaries (read first)

| Rule | Status |
|------|--------|
| Global `LR-050` verdict | **NO-GO** until separate explicit Human Approval |
| This document authorizes live trading | **No** — kein Live-Go |
| This document authorizes real-money exposure | **No** — kein Echtgeld-Go |
| Runtime dry-run executed via this issue | **No** — docs-only proof contract |
| Exchange / broker API calls via this document | **None** — forbidden |
| API key validation against live venue | **None** — forbidden |
| Secret values read/logged in this document | **None** |
| Orders sent during authoring of this document | **None** |
| Merge of PR that adds this document | **Documentation only** — ersetzt **niemals** Human Approval |
| Board stage `trade-capable` | **Not** live-capital authorization (orthogonal to LR) |

---

## 1. Scope and non-goals

### In scope

- Define how the **future** live execution path can be exercised **without order placement**, as a **proof contract** backed by repo code and sibling LR-050 SSOTs.
- Provide a **Proof-Matrix** with per-item status, expected signals, and fail-closed behavior.
- Hand off unresolved proof to [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) (Final Reconcile).

### Non-goals (explicit — keine Überbehauptung)

- **Keine Runtime-Evidence in diesem Slice** — kein Stack-Start, kein Docker, kein Service-Restart.
- **Keine echte Orderfreiheit runtime-bewiesen** — Code-Pfade sind beschrieben, nicht am laufenden System verifiziert.
- **Keine Venue-Auth bewiesen** — keine Live-Key-Validation, keine Balance-/Account-Abfrage.
- **Kein Receiver Proof bewiesen** — keine Alertmanager-/Webhook-Tests ([#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531)).
- **Kein Live-Pfad freigegeben** — LR bleibt NO-GO; Issue/PR-Merge ersetzt nicht Human Approval.
- Keine Änderung an Services, Core, Compose, Env, Secrets, `LR-AUDIT-STATUS`, oder `ROADMAP.yaml`.

---

## 2. Dry-run safety invariants (repo-backed)

These invariants describe **required conditions** for a safe non-sending path on `cdb_execution`. They are **contract definitions**; satisfying them at runtime requires a **future** operator drill under Runtime-GO.

### 2.1 Canonical non-send predicates

For **real** exchange submission to be blocked on the active execution path, repo-backed **non-send predicates** are only:

| Mechanism | Env / code | Non-send effect |
|-----------|------------|-----------------|
| Mock adapter | `MOCK_TRADING=true` (default) | `resolve_execution_adapter_id` → `MOCK_BUILTIN` — no live MEXC adapter factory with credentials |
| Dry-run executor | `DRY_RUN=true` (default) | `LiveExecutor(dry_run=True)` — **no** `MexcClient`; `execute_order` returns `DRY_RUN_*` without `place_*` |

`MEXC_TESTNET` is **not** a non-send predicate (see §2.2).

**Must be evidenced explicitly in any future runtime dry-run pack:**

- `DRY_RUN=true` — log line `DRY RUN MODE` / `orders logged but not executed` or config dump showing `DRY_RUN=True`.
- **And** either `MOCK_TRADING=true` **or** confirmed `MOCK_BUILTIN` adapter selection — log `Using execution adapter: mock_builtin` (exact adapter id per repo).

Do **not** treat `MEXC_TESTNET=true` alone as proof of non-send or sandbox isolation.

### 2.2 `MEXC_TESTNET=true` — startup gate bypass only (not proven sandbox)

[`services/execution/service.py`](../../services/execution/service.py) `_require_live_confirmation()` treats `MEXC_TESTNET=true` like `MOCK_TRADING` / `DRY_RUN`: it **skips** the `CONFIRM_LIVE_TRADING` exit when all three are not simultaneously off. That is a **process startup** convenience, **not** proof that orders cannot be sent.

When `MOCK_TRADING=false` and `DRY_RUN=false` but `MEXC_TESTNET=true`:

- Startup can proceed without `CONFIRM_LIVE_TRADING=true`.
- [`LiveExecutor`](../../services/execution/live_executor.py) still constructs `MexcClient` and may call `place_market_order` / `place_limit_order`.
- [`core/clients/mexc.py`](../../core/clients/mexc.py) sets `base_url = "https://contract.mexc.com"` when `testnet=True` (comment: “Testnet URL”). The repo does **not** independently verify that this URL is an isolated sandbox, non-mainnet, or non-live-capital endpoint ([#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) — Venue Audit).

**Invariants (fail-closed for #2535 / operator evidence):**

- `MEXC_TESTNET=true` **does not** prove “no order placement”.
- `MEXC_TESTNET=true` **does not** prove “only testnet” or safe venue isolation — treat as **`blocker_before_live`** until venue endpoint is repo- or operator-verified.
- For future Runtime-GO dry-run evidence, **`DRY_RUN` and/or `MOCK_TRADING`** are the required non-send predicates; do not classify an exchange-capable path (`MOCK_TRADING=false`, `DRY_RUN=false`) as safely isolated based on `MEXC_TESTNET` alone.

[`core/config/trading_mode.py`](../../core/config/trading_mode.py) `TradingMode.STAGED` maps to `DRY_RUN: False`, `MOCK_TRADING: False`, `MEXC_TESTNET: True` — that combination is **exchange-capable** in code terms, not dry-run.

### 2.3 `TRADING_MODE=staged` is not dry-run

The active **`cdb_execution` runtime SSOT** is explicit env resolution in [`services/execution/config.py`](../../services/execution/config.py) (`MOCK_TRADING`, `DRY_RUN`, `MEXC_TESTNET`, secrets via `read_secret`).

`TRADING_MODE` is **only logged** at startup in `service.py` (`main()`); it is **not** imported to set `DRY_RUN` / `MOCK_TRADING` on the execution service path.

**Invariant:** Setting `TRADING_MODE=staged` (or `paper` / `live`) without matching execution env flags does **not** establish dry-run.

### 2.4 Mainnet / live-capital activation tuple (forbidden in this slice)

Mainnet real-money path requires **all** of the following simultaneously (repo-backed gate):

| Flag | Required value for mainnet send path |
|------|--------------------------------------|
| `MOCK_TRADING` | `false` |
| `MEXC_TESTNET` | `false` |
| `DRY_RUN` | `false` |
| `CONFIRM_LIVE_TRADING` | `true` |

Without `CONFIRM_LIVE_TRADING=true`, startup calls `_require_live_confirmation()` → `sys.exit(1)` when all three safety nets are off.

**This slice sets none of these** and does not document operator steps to toggle them.

### 2.5 Predicate mapping (`real_money` / `dry_run`)

Issue language uses `real_money=false` or `dry_run=true`. Repo order path uses:

- `DRY_RUN` env → `config.DRY_RUN` → `LiveExecutor.dry_run`
- `MOCK_TRADING` env → mock adapter (no venue send)
- No production env key named `real_money` on the execution order path in repo grep scope

**Contract mapping:** `real_money=false` **means** at least one non-send mechanism in §2.1 is active; **prefer** `DRY_RUN=true` **and** mock or dry-run executor branch for future runtime proof.

---

## 3. Proof matrix

Legend for **status**:

| Status | Meaning |
|--------|---------|
| `docs_only` | Mechanism defined in repo/docs; **not** runtime-proven in #2533 |
| `ready_for_future_runtime_dry_run` | Checklist-ready under separate Runtime-GO; expected log/artifact named |
| `blocker_before_live` | Mandatory proof missing before live-capital Human GO |
| `forbidden` | Out of scope for any dry-run slice (exchange call, secret value export, live order) |

| Proof item | Source / mechanism | Expected dry-run signal | docs-only | runtime dry-run | secret value | exchange call | Status | Expected evidence artifact | Fail-closed behavior |
|------------|-------------------|-------------------------|-----------|-----------------|--------------|---------------|--------|---------------------------|----------------------|
| **Config resolution (execution SSOT)** | [`services/execution/config.py`](../../services/execution/config.py) — defaults `MOCK_TRADING=true`, `DRY_RUN=true`, `MEXC_TESTNET=true` | Future drill: confirm `DRY_RUN=true` **and** `MOCK_TRADING=true` (or mock adapter log); `MEXC_TESTNET` alone insufficient | yes | yes | no | no | `docs_only` | Redacted config snapshot (names only) | `DRY_RUN=false` + `MOCK_TRADING=false` → **unsafe** even if `MEXC_TESTNET=true` |
| **MEXC_TESTNET venue isolation (unproven)** | [`core/clients/mexc.py`](../../core/clients/mexc.py) `testnet` → `contract.mexc.com` | Must not be cited as sandbox proof | yes | yes | no | yes (if misread as safe) | `blocker_before_live` | Venue Audit #2527 endpoint verification | Treat as **unproven**; use `DRY_RUN`/mock for non-send proof |
| **BLUE compose default (reference)** | [`infrastructure/compose/compose.blue.yml`](../../infrastructure/compose/compose.blue.yml) `MOCK_TRADING: "true"` for `cdb_execution` | Service starts with mock unless overridden | yes | yes | no | no | `docs_only` | Operator records effective compose overlay | Override to `false` without `DRY_RUN` → **blocker_before_live** |
| **Adapter selection** | [`core/contracts/external_adapter_registry.py`](../../core/contracts/external_adapter_registry.py) `default_execution_adapter_id(mock_trading=…)` | Log: mock_builtin vs mexc_builtin | yes | yes | no | no | `docs_only` | Startup log excerpt | `MEXC_BUILTIN` + `DRY_RUN=false` → exchange-capable path |
| **`_require_live_confirmation` gate** | [`services/execution/service.py`](../../services/execution/service.py) | Process exits if mainnet tuple without `CONFIRM_LIVE_TRADING=true` | yes | partial | no | no | `docs_only` | Exit code 1 + CRITICAL log (future negative test only with Runtime-GO) | Fail-closed exit — no silent live |
| **`LiveExecutor` dry_run branch** | [`services/execution/live_executor.py`](../../services/execution/live_executor.py) — `client=None`, `DRY_RUN_*` result | Log: `DRY RUN MODE`, `Would execute`, no HTTP to MEXC | yes | yes | no | no | `ready_for_future_runtime_dry_run` | Log lines + `order_results` with `DRY_RUN_` prefix | If `place_market_order` invoked → **halt** |
| **Venue client init (no call)** | [`core/clients/mexc.py`](../../core/clients/mexc.py) — `ValueError` if keys missing; skipped when `dry_run=True` | No client object when dry_run | yes | yes | no | no | `docs_only` | Log: no `MEXC Client initialized in LIVE mode` | Client init in dry_run config → misconfiguration |
| **Auth / secret load (no value)** | [`core/secrets.py`](../../core/secrets.py) `read_secret`; `validate_all_auth` at startup | Logs: secret loaded / missing — **never** values | yes | yes | no | no | `docs_only` | Log redaction review; secret **presence** bit only | Missing creds + `DRY_RUN=false` → `RuntimeError` at init |
| **Order build / publish path (risk)** | [`services/risk/service.py`](../../services/risk/service.py) order publish to `TOPIC_ORDERS` | Approved orders appear on Redis channel; blocked → `blocked_decisions` | yes | yes | no | no | `ready_for_future_runtime_dry_run` | Redis tap or DB `blocked_decisions` row | Risk block → execution must not send |
| **Risk Gate — kill-switch** | `core.safety.kill_switch` + risk `_kill_switch_gate` | Block reason in logs/DB | yes | yes | no | no | `blocker_before_live` | Kill-switch drill evidence ([#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529)) | Active kill-switch → no forward |
| **Risk Gate — allocation ≤ 0** | risk `_allocation_allowed` | `allocation_pct <= 0` blocks | yes | yes | no | no | `docs_only` | Allocation stream state snapshot | Fail-closed block |
| **Risk Gate — limits / exposure** | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) | Canary values `TBD_BLOCKER_BEFORE_LIVE` | yes | partial | no | no | `blocker_before_live` | Limit proof per #2528 | Over-limit → block |
| **Execution Gate — shadow** | `process_order` shadow branch | `SHADOW_BLOCKED`, zero execution | yes | yes | no | no | `ready_for_future_runtime_dry_run` | `order_results` REJECTED shadow | Shadow must block sends |
| **Execution Gate — kill-switch (defense)** | `process_order` execution kill-switch | `KILL_SWITCH_BLOCKED` | yes | yes | no | no | `ready_for_future_runtime_dry_run` | Rejected result published | Fail-closed |
| **Execution Gate — bot shutdown** | `process_order` shutdown sets | `SHUTDOWN_*` rejected | yes | yes | no | no | `docs_only` | Shutdown stream evidence | Blocks new orders |
| **Order path end-to-end (paper)** | [`tests/e2e/test_paper_trading_p0.py`](../../tests/e2e/test_paper_trading_p0.py) | CI/lab path only — **not** LR-050 runtime proof | yes | yes | no | no | `ready_for_future_runtime_dry_run` | E2E log under Runtime-GO | Test failure → do not claim dry-run |
| **Observability / receiver** | [LR-050-OBSERVABILITY-GATES.md](./LR-050-OBSERVABILITY-GATES.md) | Operator receipt / route proof | yes | no | no | no | `blocker_before_live` | Receiver proof artifact ([#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531)) | No alert path → no live GO |
| **Venue permissions / audit** | [LR-050-VENUE-AUDIT.md](./LR-050-VENUE-AUDIT.md) | Venue SSOT complete | yes | no | no | no | `blocker_before_live` | #2527 closure evidence | Venue unclear → NO-GO |
| **Live API key validation** | N/A | N/A | no | no | yes | yes | `forbidden` | None in #2533 | Attempt → stop |
| **Place order on mainnet** | MEXC `place_*` when not dry_run | Real fill | no | no | yes | yes | `forbidden` | None | **Halt** — incident |

---

## 4. Path sections (contract detail)

### 4.1 Config resolution

**SSOT:** [`services/execution/config.py`](../../services/execution/config.py)

| Variable | Default if unset | Role |
|----------|------------------|------|
| `MOCK_TRADING` | `true` | Mock vs MEXC builtin adapter |
| `DRY_RUN` | `true` | LiveExecutor logs only |
| `MEXC_TESTNET` | `true` | Selects `contract.mexc.com` in client — **not** verified sandbox; not a non-send flag |
| `MEXC_API_KEY` / `MEXC_API_SECRET` | via `read_secret` (empty allowed when dry) | Required only when `DRY_RUN=false` and MEXC path |
| `CONFIRM_LIVE_TRADING` | unset | Required `true` for mainnet tuple |

**Not authoritative for execution:** `TRADING_MODE` (log only). [`core/config/trading_mode.py`](../../core/config/trading_mode.py) is legacy/helper for other tooling — do not use `TRADING_MODE=staged` as dry-run proof.

### 4.2 Venue client initialization (no secret / no exchange call in #2533)

- `DRY_RUN=true` → `LiveExecutor` sets `self.client = None` — **no** `MexcClient` construction.
- `DRY_RUN=false` + missing keys → init `RuntimeError` before subscribe loop (fail-closed).
- Future runtime dry-run: confirm logs contain dry-run banner and **absence** of `place_market_order` / `place_limit_order` log success.

### 4.3 Auth path (no secret output)

- Secrets loaded via [`read_secret`](../../core/secrets.py) — never logs values.
- Startup [`validate_all_auth`](../../services/execution/service.py) — connectivity checks; evidence = pass/fail lines only.
- Cross-ref: [LR-050-SECRETS-READINESS.md](./LR-050-SECRETS-READINESS.md) — **forbidden** to read secret files for #2533 evidence.

### 4.4 Order-builder dry-run

Repo terminology:

- **Risk:** builds order payload + metadata (`_build_order_metadata`, timing metadata) and publishes to Redis `orders` topic when gates pass.
- **Execution:** `process_order` parses `Order`, applies shadow/kill-switch/shutdown, delegates to adapter `execute` / `execute_order`.

**Docs-only proof:** code review + unit tests. **Runtime proof:** inject synthetic approved order under `MOCK_TRADING=true` **and** `DRY_RUN=true`, assert result id prefix `DRY_RUN_` or mock fill — **requires Runtime-GO**.

### 4.5 Risk Gate dry-run

See [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) (Risk Gate) and [LR-050-KILL-SWITCH-RUNBOOK.md](./LR-050-KILL-SWITCH-RUNBOOK.md).

- Mechanisms exist in code (`docs_only` for canary enforcement).
- Numeric canary limits remain `TBD_BLOCKER_BEFORE_LIVE`.
- Runtime drill: force kill-switch / zero allocation and verify **no** `order_results` fill on venue.

### 4.6 Execution Gate dry-run

Distinguish:

| Gate type | Example | Sends to venue? |
|-----------|---------|-----------------|
| **Safe mode** | `MOCK_TRADING`, `DRY_RUN` | No (when configured true) |
| **Halt gate** | kill-switch, shadow, shutdown | No — rejected result |

Mock/dry-run modes are **not** substitutes for kill-switch verification ([#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529)).

### 4.7 Observability (no receiver test)

Per [LR-050-OBSERVABILITY-GATES.md](./LR-050-OBSERVABILITY-GATES.md):

- Receiver proof = `blocker_before_live`.
- This slice performs **no** Alertmanager test fire, **no** webhook drill.

---

## 5. Runtime dry-run evidence — explicit blocker

| Item | Status |
|------|--------|
| Operator stack dry-run | **Not executed** in #2533 |
| Proof pack for #2533 (this file) | `docs_only` contract |
| Follow-up | Separate issue or Runtime-GO slice: `ready_for_future_runtime_dry_run` rows in §3 |

**Minimum future runtime pack (non-exhaustive):**

1. Explicit Runtime-GO from operator.
2. Confirm `DRY_RUN=true` and `MOCK_TRADING=true` (or equivalent non-send path).
3. Inject test order; capture logs + `order_results` / stream without MEXC HTTP.
4. Attach redacted evidence under `reports/` or issue comment — **no** secret values.

Until then: **runtime dry-run evidence remains `blocker_before_live`** for [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535).

---

## 6. Handoff to #2535 (Final Reconcile)

### 6.1 Delivered by #2533 (this document)

- `dry_run_proof_contract` SSOT with safety invariants §2.
- Full proof matrix §3 with honest `docs_only` / `blocker_before_live` / `forbidden` labels.
- Explicit statement: **runtime evidence not executed**.

### 6.2 Remains for #2535 / other issues (not closed by #2533)

| Blocker | Owner |
|---------|--------|
| Runtime dry-run log/evidence pack | Future Runtime-GO / follow-up |
| Venue audit complete | [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) — Venue Audit |
| Risk limit values + proof | [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528) — Risk Gate |
| Kill-switch verified | [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) |
| Secrets readiness proof | [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530) |
| Observability receiver proof | [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) |
| Canary plan alignment | [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) — Canary Plan |
| Human approval wording | [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534) |

**#2535** must **not** upgrade LR verdict to GO; at most `ready-for-human-live-approval` if all child evidence supports it.

---

## 7. Related documents

- [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) — Decision Pack ([#2526](https://github.com/jannekbuengener/Claire_de_Binare/issues/2526))
- [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) — Human Approval ([#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534))
- [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) — Risk Gate ([#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528))
- [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) — Kill-switch ([#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529))
- [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) — Secrets ([#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530))
- [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) — Observability ([#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531))
- [`LR-050-VENUE-AUDIT.md`](./LR-050-VENUE-AUDIT.md) — Venue Audit ([#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527))
- [`LR-050-CANARY-PLAN.md`](./LR-050-CANARY-PLAN.md) — Canary Plan ([#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532); plan_only)

---

## 8. Closing statement

Delivery of this document satisfies [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) as a **docs-only dry-run proof contract**. It does **not**:

- Execute runtime dry-run (**runtime evidence not executed**).
- Prove order-freedom on a live stack.
- Validate venue credentials or exchange connectivity.
- Grant live-capital GO, Echtgeld-Go, or Auto-Live.
- Change global **LR remains NO-GO**.
