# LR-050 Venue Audit — Broker / Exchange / Crypto Paths

- **Control:** `LR-050` (P5 Canary Echtgeld / Live-Kapital)
- **GitHub issue:** [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527)
- **Document role:** Repo-backed inventory of venue/broker/exchange integration paths; mode separation; secret **names** and permission boundaries; conservative canary-path **candidate** (not activation)
- **Last updated:** 2026-06-04
- **Verdict authority (unchanged):** [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)

## Safety boundaries (read first)

| Rule | Status |
|------|--------|
| Global `LR-050` verdict | **NO-GO** until separate explicit Human Approval |
| This document authorizes live trading | **No** — kein Live-Go |
| This document authorizes real-money exposure | **No** — kein Echtgeld-Go |
| Automatic activation / auto-live | **Forbidden** — No auto-live |
| Board stage `trade-capable` | **Not** live-capital authorization (orthogonal to LR) |
| Any venue marked live-ready here | **No** — while [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532), [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533), [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) remain OPEN |
| Secrets in this document | **None** — names and classes only |
| Broker/exchange calls via this document | **None** |

**MEXC** appears below only as the **sole repo-backed exchange integration path**. That is **not** a designation as the approved LR-050 canary venue and **not** live-ready.

---

## 1. Scope and non-goals

### In scope

- Inventory of broker/exchange/crypto venue surfaces found in the working repo (code, compose references, config names, contracts).
- Separation of mock / paper / sandbox / testnet / live (and `unknown` where not provable from repo).
- Connector-type classification: REST, WebSocket, SDK, CCXT, custom client.
- Secret/permission **requirements** (names only; read-only vs trading; forbidden withdrawal/transfer/admin).
- Cross-links to LR-050 sibling gates (Human Approval, Risk Limits, Kill-Switch, Observability, Secrets Readiness).
- Handoff expectations for [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) (Canary Plan) and [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) (Dry-run Proof).

### Non-goals

- No HTTP/WebSocket/API calls, no API-key validation, no balance/account queries, no orders.
- No changes to services, core, compose, env, secrets stores, runtime, or [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md).
- No claim that testnet/sandbox endpoints are operationally correct (only what the repo configures).
- No observability/alert/receiver matrix (see [LR-050-OBSERVABILITY-GATES.md](./LR-050-OBSERVABILITY-GATES.md) / #2531).

---

## 2. Related documents

| Document / issue | Relationship |
|------------------|--------------|
| [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) | Planning context; §3 venue row → this SSOT |
| [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) | Gate #1 — venue SSOT must be CLOSED before live-capital GO |
| [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) | Allowed symbols TBD until venue inventory ([#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528)) |
| [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) | Halt paths; `MOCK_TRADING` / `DRY_RUN` / `MEXC_TESTNET` are safe modes, not venue GO |
| [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) | Credential names; venue permissions deferred here until this audit |
| [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) | Monitoring gates ([#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531)) |
| [`knowledge/contracts/EXTERNAL_ADAPTERS.md`](../../knowledge/contracts/EXTERNAL_ADAPTERS.md) | Adapter boundary spec |
| [`core/contracts/external_adapter_registry.py`](../../core/contracts/external_adapter_registry.py) | `mock_builtin` / `mexc_builtin` registry |

---

## 3. Venue inventory (repo-backed only)

### 3.1 Exchanges / venues found

| Venue | Status in repo | Primary integration |
|-------|----------------|---------------------|
| **MEXC** | **Only production-path exchange** wired in `core/` and `services/` | Custom REST (`requests` + HMAC) + WebSocket V3 protobuf |
| Other named exchanges (e.g. Binance-shaped parsers) | **Tests/scripts only** — not an execution or MD production venue | e.g. `tests/unit/scripts/test_candle_continuity.py` (`parse_binance_kline`) |
| CCXT | **Not** in `services/execution/requirements.txt` or active execution import graph | Mentioned in `tools/test_pack/README.md` (emulator) and archived deep-lab docs only |

No second exchange client exists under [`core/clients/`](../../core/clients/) (only [`mexc.py`](../../core/clients/mexc.py)).

### 3.2 Components by layer

| Layer | Component | Path / symbol | Transport | Notes |
|-------|-----------|---------------|-----------|-------|
| Market data | `cdb_ws` stub mode | [`services/ws/service.py`](../../services/ws/service.py) | none | `WS_SOURCE=stub` (default) — health/metrics only |
| Market data | `cdb_ws` MEXC WS V3 | [`services/ws/mexc_v3_client.py`](../../services/ws/mexc_v3_client.py), `MexcV3Client` | WebSocket protobuf | `WS_URL = wss://wbs-api.mexc.com/ws` (repo constant) |
| Market data | MEXC proto gen | [`services/ws/mexc_proto_gen/`](../../services/ws/mexc_proto_gen/) | — | Generated protobuf bindings |
| Execution (active) | `MockExecutor` | [`services/execution/mock_executor.py`](../../services/execution/mock_executor.py) | in-process | Via `mock_builtin` / `MOCK_TRADING=true` |
| Execution (active) | `LiveExecutor` | [`services/execution/live_executor.py`](../../services/execution/live_executor.py) | REST via `MexcClient` | Via `mexc_builtin` when `MOCK_TRADING=false` |
| Execution (REST client) | `MexcClient` | [`core/clients/mexc.py`](../../core/clients/mexc.py) | REST custom | `testnet` flag switches `base_url` in code |
| Execution (shim) | `services.execution.mexc_client` | [`services/execution/mexc_client.py`](../../services/execution/mexc_client.py) | — | Deprecated re-export to `core.clients.mexc` |
| Execution (legacy file) | `MexcExecutor` | [`services/execution/mexc_executor.py`](../../services/execution/mexc_executor.py) | REST custom | **Not** referenced by [`services/execution/service.py`](../../services/execution/service.py) active path |
| Risk | `RealBalanceFetcher` | [`services/risk/balance_fetcher.py`](../../services/risk/balance_fetcher.py) | REST | `MEXC_BASE_URL` default `https://contract.mexc.com` |
| Risk | `MexcClient` shim | [`services/risk/mexc_client.py`](../../services/risk/mexc_client.py) | — | Re-export to `core.clients.mexc` |
| Adapter registry | `mock_builtin`, `mexc_builtin` | [`core/contracts/external_adapter_registry.py`](../../core/contracts/external_adapter_registry.py) | — | `default_execution_adapter_id(mock_trading=…)` |
| Trading mode SSOT | `TradingMode` PAPER / STAGED / LIVE | [`core/config/trading_mode.py`](../../core/config/trading_mode.py) | — | `get_legacy_config()` maps env bundles |
| Paper engine (local) | `PaperTradingEngine` | [`services/execution/paper_trading.py`](../../services/execution/paper_trading.py) | none | Separate from `cdb_execution` adapter path |
| Test / lab | MEXC testnet integration test | [`tests/integration/test_mexc_testnet.py`](../../tests/integration/test_mexc_testnet.py) | REST | Opt-in `CDB_EXTERNAL_TESTS=1` — **not** runtime default |
| Test / lab | ccxt-compatible emulator | [`tools/test_pack/README.md`](../../tools/test_pack/README.md) | — | Lab tooling; not BLUE/RED runtime |

### 3.3 Mode separation (repo configuration)

| Mode label | Repo mechanism | Evidence | Default in canonical operator stack |
|------------|----------------|----------|-------------------------------------|
| **mock** | `MOCK_TRADING=true` → `MockExecutor` / `mock_builtin` | [`services/execution/config.py`](../../services/execution/config.py), [`compose.blue.yml`](../../infrastructure/compose/compose.blue.yml) `cdb_execution` | **true** |
| **paper** | `TradingMode.PAPER`; `MOCK_TRADING` + `DRY_RUN` in `get_legacy_config(PAPER)` | [`core/config/trading_mode.py`](../../core/config/trading_mode.py) | Aligned with safe defaults |
| **dry-run** (no venue send) | `DRY_RUN=true` → `LiveExecutor` with `client=None`, simulated FILLED | [`live_executor.py`](../../services/execution/live_executor.py) | **true** in `.env.example` |
| **testnet (exchange-touch)** | `MEXC_TESTNET=true` with real executor (`MOCK_TRADING=false`, `DRY_RUN=false`) | `config.py`, `trading_mode.py` | Not default; see STAGED row below |
| **STAGED bundle** (documented only) | `get_legacy_config(STAGED)` → `MOCK_TRADING=false`, **`DRY_RUN=false`**, `MEXC_TESTNET=true` | [`core/config/trading_mode.py`](../../core/config/trading_mode.py) | **Not** applied by `cdb_execution` today (see below) |
| **`TRADING_MODE` env** | Logged at startup only in `cdb_execution` | [`services/execution/service.py`](../../services/execution/service.py) ~964–967 | **Does not** set `MOCK_TRADING` / `DRY_RUN` / `MEXC_TESTNET` |
| **live** (mainnet-capable) | `MOCK_TRADING=false` + `DRY_RUN=false` + `MEXC_TESTNET=false` + `CONFIRM_LIVE_TRADING=true` | [`service.py`](../../services/execution/service.py) `_require_live_confirmation()`, [`config.py`](../../services/execution/config.py) | **Not** default; fail-closed; `LIVE_TRADING_CONFIRMED` checked in `trading_mode.py` for mode parsing elsewhere |
| **sandbox** | No `sandbox` mode string or dedicated env in `services/` | repo search | Mark **unknown** / not implemented as distinct mode |

**Effective flags on `cdb_execution` (repo-backed):** [`services/execution/config.py`](../../services/execution/config.py) reads `MOCK_TRADING`, `DRY_RUN`, and `MEXC_TESTNET` **directly from env** (defaults `true` / `true` / `true`). [`services/execution/service.py`](../../services/execution/service.py) logs `TRADING_MODE` but **does not** call `get_legacy_config()` — repo search shows `get_legacy_config` is used in [`core/config/trading_mode.py`](../../core/config/trading_mode.py) and **unit tests only**, not in `services/` production code.

**Fail-closed for #2532 / #2533:** Operators must set **explicit** `MOCK_TRADING`, `DRY_RUN`, and `MEXC_TESTNET` for the intended path. Setting only `TRADING_MODE=staged` (or `paper` / `live`) **does not** change execution behavior today. The STAGED/PAPER/LIVE rows in `get_legacy_config()` are **documented bundles** for planning and tests — not the active runtime mapper.

**Dry-run proof (#2533):** require **explicit** `DRY_RUN=true` (and log evidence from `config.DRY_RUN`) — **not** inferring dry-run from `TRADING_MODE` or from the STAGED bundle table alone.

**Repo inconsistency (document, not externally verified):** [`core/clients/mexc.py`](../../core/clients/mexc.py) uses `https://contract.mexc.com` when `testnet=True` and `https://api.mexc.com` when live; [`services/execution/config.py`](../../services/execution/config.py) default `MEXC_BASE_URL` is `https://contract.mexc.com`. [`services/ws/mexc_v3_client.py`](../../services/ws/mexc_v3_client.py) always uses spot WS `wss://wbs-api.mexc.com/ws` regardless of `MEXC_TESTNET`. Treat operational testnet/sandbox correctness as **TBD_BLOCKER_BEFORE_LIVE**.

### 3.4 Connector-type assessment

| Type | MEXC path in repo | CCXT / other |
|------|-------------------|--------------|
| **Custom REST client** | **Yes** — `MexcClient` (`requests` + HMAC-SHA256) | — |
| **WebSocket** | **Yes** — `MexcV3Client` + protobuf (`websockets` lib) | — |
| **Exchange SDK** | **No** dedicated MEXC official SDK dependency in service `requirements.txt` | — |
| **CCXT** | **No** on active execution/MD path | Lab emulator mention only |

---

## 4. Connector / mode matrix

Columns: **LR-050 canary** = `ready` | `TBD_BLOCKER_BEFORE_LIVE` | `forbidden` | `docs_only`

| path/component | mode | order-capable | market-data-capable | requires secrets | LR-050 canary | evidence | blocker / limitation |
|----------------|------|---------------|---------------------|------------------|---------------|----------|----------------------|
| `cdb_execution` + `MockExecutor` | mock / paper | yes (simulated) | no | no | docs_only | `mock_executor.py`, `MOCK_TRADING` default | Not Echtgeld canary; no venue connectivity proof |
| `cdb_execution` + `LiveExecutor` + `DRY_RUN=true` | dry-run | path exists; no exchange send | no | yes if credentials loaded | TBD_BLOCKER_BEFORE_LIVE | `live_executor.py`, `service.py` | #2533 must prove dry-run; FILLED dry-run ≠ halt |
| `cdb_execution` + `LiveExecutor` + `MEXC_TESTNET=true` | testnet | yes if `DRY_RUN=false` and creds present | no | yes | TBD_BLOCKER_BEFORE_LIVE | `core/clients/mexc.py`, `config.py` | Testnet URL semantics unproven; #2532/#2533 |
| `cdb_execution` + `LiveExecutor` mainnet | live | yes | no | yes | forbidden | `_require_live_confirmation()`, `CONFIRM_LIVE_TRADING` | Inventory only; needs Human Approval + closed child gates |
| `cdb_execution` + `mexc_builtin` adapter | follows env above | yes (via executor) | no | yes on live path | TBD_BLOCKER_BEFORE_LIVE | `external_adapter_registry.py` | Same as LiveExecutor path |
| `cdb_execution` + `MexcExecutor` (legacy module) | live/testnet per config | yes (code present) | no | yes | docs_only | `mexc_executor.py` | Not wired in active `service.py` init |
| `cdb_ws` + `WS_SOURCE=stub` | mock (no external) | no | no | no | docs_only | `services/ws/service.py` | Default; no live MD feed |
| `cdb_ws` + `WS_SOURCE=mexc_pb` | live (public WS URL in repo) | no | yes | typically no for public stream | TBD_BLOCKER_BEFORE_LIVE | `mexc_v3_client.py` | WS endpoint not tied to `MEXC_TESTNET`; may be production feed |
| `cdb_risk` + `RealBalanceFetcher` | live/testnet per `MEXC_BASE_URL` / creds | no | no (balance read) | yes | TBD_BLOCKER_BEFORE_LIVE | `balance_fetcher.py`, `risk/service.py` | Balance fetch is exchange call — out of scope for this audit run; gated for canary |
| `core.clients.MexcClient` REST | testnet or live per `testnet` arg | yes (API methods) | yes (ticker/account) | yes | TBD_BLOCKER_BEFORE_LIVE | `core/clients/mexc.py` | Shared by execution + risk |
| `get_legacy_config(STAGED)` (doc/test only) | testnet bundle | yes if equivalent env set | no | yes | docs_only | `trading_mode.py`; not wired in `cdb_execution` | #2532 must set explicit env, not `TRADING_MODE` alone |
| `TRADING_MODE` on `cdb_execution` | unknown (not mapped) | follows `MOCK_TRADING`/`DRY_RUN` env | no | no | docs_only | `service.py` log line | Informational log only |
| `get_legacy_config(LIVE)` (doc/test only) | live bundle | yes if equivalent env set | no | yes | forbidden | `trading_mode.py` | Real money; explicit env + Human Approval |
| `tests/integration/test_mexc_testnet.py` | testnet (opt-in external) | unknown | unknown | yes (test env) | docs_only | `test_mexc_testnet.py` | Requires `CDB_EXTERNAL_TESTS=1`; not CI default |
| `tools/test_pack` ccxt emulator | mock/lab | unknown | unknown | unknown | docs_only | `tools/test_pack/README.md` | Not production runtime |
| **sandbox** (distinct mode) | sandbox | unknown | unknown | unknown | TBD_BLOCKER_BEFORE_LIVE | not found in `services/` | No repo-backed sandbox mode |
| Passphrase-based venue auth | unknown | — | — | unknown | TBD_BLOCKER_BEFORE_LIVE | not in MEXC client code | Venue-dependent; unproven in repo |
| IP allowlist / account binding | unknown | — | — | unknown | TBD_BLOCKER_BEFORE_LIVE | no repo SSOT for egress IP | Operator + #2532 |
| Withdrawal / transfer / admin API use | forbidden | — | — | — | forbidden | LR-050 policy; [LR-050-SECRETS-READINESS.md](./LR-050-SECRETS-READINESS.md) §6 | Must not be enabled on canary keys |

**No row is marked `ready` for LR-050 live-capital canary** while #2532, #2533, and #2535 are OPEN.

---

## 5. Secret and permission requirements (names only)

Cross-reference: [LR-050-SECRETS-READINESS.md](./LR-050-SECRETS-READINESS.md). This section adds **venue-path inventory** only.

### 5.1 Repo-found secret names (not canary-venue designation)

| Secret file / env name | Used by (repo) | Canary note |
|------------------------|----------------|-------------|
| `mexc_api_key` / `MEXC_API_KEY` | execution config, risk balance, compose mounts | Permission scope **TBD_BLOCKER_BEFORE_LIVE** |
| `mexc_api_secret` / `MEXC_API_SECRET` | same | same |
| `MEXC_TRADE_API_KEY.txt` / `MEXC_TRADE_API_SECRET.txt` | `.env.example`, knowledge docs | **Not** loaded in `services/execution/config.py` — which key set for canary **TBD_BLOCKER_BEFORE_LIVE** |
| `MEXC_BASE_URL` | env override | Default `https://contract.mexc.com` in execution config |
| `MEXC_TESTNET` | env boolean | Default `true` in `.env.example` |
| `MOCK_TRADING`, `DRY_RUN` | execution | Safe-mode defaults `true` |
| `CONFIRM_LIVE_TRADING` | execution startup gate | Required for mainnet path when safe modes off |
| `LIVE_TRADING_CONFIRMED` | `trading_mode.py` | Required for `TRADING_MODE=live` |
| `EXECUTION_ADAPTER_ID` | optional override | `mock_builtin` / `mexc_builtin` |

### 5.2 Permission classes (policy)

| Class | LR-050 stance | Proof owner |
|-------|---------------|-------------|
| Read-only API (balances, market metadata) | Allowed for **pre-GO** discovery only; not a GO substitute | #2533 dry-run (no secret values in logs) |
| Trading API (place/cancel on approved scope) | **Forbidden** until Human Approval + #2532 plan | #2532, #2534 |
| Withdrawal | **forbidden** | venue dashboard + #2532 |
| Transfer / subaccount-admin | **forbidden** | #2532 |
| Key-management / admin API | **forbidden** | #2532 |
| Passphrase | **TBD_BLOCKER_BEFORE_LIVE** (not in MEXC client) | #2532 if venue requires |
| IP allowlist / egress binding | **TBD_BLOCKER_BEFORE_LIVE** | #2532 + operator |
| Account / subaccount binding | **TBD_BLOCKER_BEFORE_LIVE** | #2532 |

---

## 6. Safety and control requirements (mandatory gates)

None of the following are satisfied by this venue inventory alone. They remain **mandatory** for any future live-capital canary:

| Gate | SSOT |
|------|------|
| Human Approval (exact GO/REVOKE) | [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md) — [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534) |
| Hard risk limits (numeric caps) | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) — [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528) |
| Kill-switch / halt | [LR-050-KILL-SWITCH-RUNBOOK.md](./LR-050-KILL-SWITCH-RUNBOOK.md) — [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) |
| Secrets readiness | [LR-050-SECRETS-READINESS.md](./LR-050-SECRETS-READINESS.md) — [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530) |
| Observability / receiver proof | [LR-050-OBSERVABILITY-GATES.md](./LR-050-OBSERVABILITY-GATES.md) — [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) |

**Issue/PR merge does not replace Human Approval.**

---

## 7. Recommendation (conservative)

### 7.1 Preferred later canary path (candidate only)

If, after [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532), [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533), [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534), and [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535), a controlled live-capital canary is still desired:

**Recommended controlled path (documentation only):**

1. **Venue candidate:** MEXC — **only** because it is the only integrated execution venue in repo; **not** pre-approved as canary venue.
2. **Pre-live-capital steps (no Echtgeld-Go):** remain on `MOCK_TRADING=true` / shadow / paper paths for system proof.
3. **[#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) dry-run proof (non-destructive):** set and evidence **explicit** env on `cdb_execution`: `DRY_RUN=true` (and typically `MOCK_TRADING=false` if exercising `LiveExecutor`), with log proof from startup (`config.DRY_RUN`). **`TRADING_MODE` alone changes nothing** on the active execution path (§3.3).
4. **Later testnet exchange-touch (still gated, not #2533 dry-run):** set **explicit** env (not `TRADING_MODE` alone): `MOCK_TRADING=false`, `MEXC_TESTNET=true`, `DRY_RUN=false` — aligns with the **documented** STAGED bundle in `get_legacy_config(STAGED)` but must be operator-set until/unless execution wires `TRADING_MODE` → legacy config; only after Human GO + #2532 scope; **never** imply mainnet from defaults.
5. **Mainnet / real-money path:** `MEXC_TESTNET=false`, `DRY_RUN=false`, `CONFIRM_LIVE_TRADING=true`, `LIVE_TRADING_CONFIRMED=yes` — **forbidden** until explicit Human Approval per [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md).

### 7.2 Clear blockers (fail-closed)

| Blocker | Owner |
|---------|-------|
| Global LR **NO-GO** | [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md) |
| No venue marked live-ready in this audit | This doc + open #2532/#2533/#2535 |
| Testnet/sandbox not repo-proven end-to-end | #2533 |
| `MEXC_TRADE_*` vs `MEXC_*` key split unresolved | #2532 + [LR-050-SECRETS-READINESS.md](./LR-050-SECRETS-READINESS.md) |
| WS MD URL vs execution testnet flag alignment | #2532 / #2533 |
| Venue permission model, IP allowlist, account binding | #2532 |
| Allowed symbols / notional caps | #2528, #2532 |
| Dry-run evidence (`real_money=false` / `config.DRY_RUN`; not `TRADING_MODE` alone) | #2533 |
| `TRADING_MODE` not mapped to execution env in `cdb_execution` | #2532 / #2533 (explicit flags) |
| Observability receiver proof | #2531 |
| Final LR reconcile | #2535 |

### 7.3 What this audit does **not** grant

- **No Live-Go**, **no Echtgeld-Go**, **No auto-live**.
- Existence of `LiveExecutor` and mainnet-capable config is **inventory only**, not authorization.

---

## 8. Handoff

### 8.1 To [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) (Canary Plan)

Must concretize (using this SSOT, not replacing it):

- Confirm or reject **MEXC** as canary venue (only repo-backed option today).
- Symbol list and order types.
- Which credential file set (`MEXC_*` vs `MEXC_TRADE_*`).
- Testnet vs mainnet scope; set **explicit** `MEXC_TESTNET`, `DRY_RUN`, `MOCK_TRADING` on `cdb_execution` (do not rely on `TRADING_MODE` alone); align `WS_SOURCE`.
- Capital limits from [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md).
- Venue dashboard permissions (trade-only; withdrawal/transfer/admin **forbidden**).
- IP allowlist / account binding if required by venue.

### 8.2 To [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) (Dry-run Proof)

Repo-backed checks to evidence **without** order placement:

- Config resolution from **effective execution env**: `MOCK_TRADING`, `DRY_RUN`, `MEXC_TESTNET`, `EXECUTION_ADAPTER_ID` ([`services/execution/config.py`](../../services/execution/config.py)).
- Log line: `TRADING_MODE` value at startup ([`service.py`](../../services/execution/service.py)) — must **not** be treated as the source of truth for flags unless a future wiring change applies `get_legacy_config()`.
- **Fail-closed:** `TRADING_MODE=staged` (or any `TRADING_MODE`) **without** matching explicit env does **not** prove STAGED or dry-run behavior on `cdb_execution` today.
- Require explicit `DRY_RUN=true` in env for non-destructive dry-run proof.
- `LiveExecutor(dry_run=True)` / adapter init without exchange submit.
- Risk gate behavior on dry-run path.
- Logs attest `real_money=false` / dry-run / no live mainnet bundle.
- No secret values in output.

### 8.3 To [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) (Final reconcile)

Before any `ready-for-human-live-approval` state:

- #2527 CLOSED with this SSOT reviewed.
- No matrix row promoted to `ready` without #2532/#2533 evidence.
- All `TBD_BLOCKER_BEFORE_LIVE` items either closed with proof or accepted as continued **NO-GO**.

---

## 9. Restunsicherheiten (explicit)

| Topic | Status |
|-------|--------|
| MEXC testnet REST/WS endpoints match exchange documentation | **Not proven** (repo code only) |
| `MEXC_TRADE_*` secrets purpose and wiring | **Not proven** in execution service |
| `MexcExecutor` legacy module | Present; **not** active service wiring |
| CCXT in production | **Not found** on active path |
| Distinct **sandbox** mode | **Not found** in services |
| `TRADING_MODE` → `get_legacy_config()` on `cdb_execution` | **Not wired** — env flags are SSOT for execution runtime |
| Public WS feed vs execution testnet alignment | **Unproven** |

---

## 10. Acceptance mapping (#2527)

| Acceptance criterion | Met by |
|---------------------|--------|
| Venue inventory documented | §3–§4 |
| Preferred canary path or clear blocker | §7 (candidate + blockers) |
| Live/Paper/Mock modes separated | §3.3, §4 |
| No broker/exchange call in delivery | Audit method (repo read-only) |
| No secrets read or posted | §5, safety table |
