# LR-050 Venue Endpoint Semantics — Repo + Official-Doc Verification (#2979)

- **Control:** `LR-050` (P5 Canary Echtgeld / Live-Kapital)
- **GitHub issue:** [#2979](https://github.com/jannekbuengener/Claire_de_Binare/issues/2979) — `[LR-050][VENUE] Verify MEXC venue/testnet/mainnet endpoint semantics`
- **Document role:** Repo-backed **and** official-public-doc-backed verification of MEXC venue / testnet / mainnet REST + WebSocket endpoint semantics. Documentation-only evidence artifact.
- **Reconcile date:** 2026-07-03
- **Repo anchor:** `origin/main` @ `b758edd16c131206d4de64c47a5158c4eb6ffb5e`
- **Verdict authority (unchanged):** [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)
- **Upstream inventory (not duplicated here):** [`LR-050-VENUE-AUDIT.md`](./LR-050-VENUE-AUDIT.md) (#2527), [`LR-050-DRY-RUN-PROOF.md`](./LR-050-DRY-RUN-PROOF.md) (#2533), [`LR-050-FINAL-RECONCILE.md`](./LR-050-FINAL-RECONCILE.md) §4 (#2535)

## Safety boundaries (read first)

| Rule | Status |
|------|--------|
| Global `LR-050` verdict | **NO-GO** — fail-closed |
| This document authorizes live trading | **No** — kein Live-Go |
| This document authorizes real-money exposure | **No** — kein Echtgeld-Go |
| Automatic activation / auto-live | **Forbidden** — No auto-live |
| Board stage `trade-capable` | **Not** live-capital authorization (orthogonal to LR) |
| Credentials / secret values in this document | **None** — names and classes only |
| Exchange / venue API called with auth during authoring | **None** |
| Orders (test, real, or proof) placed | **None** |
| Runtime / Docker / stack change via this document | **None** |
| Closing #2979 | Documentation gate only — does **not** clear the live-capital blocker or Human Approval |

---

## 1. Purpose / Scope / Non-Goals

### 1.1 Purpose

Answer, with repo evidence cross-checked against **official public MEXC documentation** (no account access, no credentials):

1. Which MEXC/venue endpoints the repo actually configures.
2. Which mainnet REST/WebSocket semantics are officially documented.
3. Whether a testnet/sandbox semantic is officially documented, or `NOT_FOUND` / `INCONCLUSIVE`.
4. Whether `MEXC_TESTNET` guarantees a non-sending venue, or is only a configuration signal.
5. Which no-send proofs already exist (#2978), and what remains for #2979.

### 1.2 Scope

- Repo endpoint/venue configuration semantics (env names, base URLs, transports).
- Official-public-doc semantics for MEXC Spot REST + WebSocket, testnet/sandbox, rate limits, symbol naming, order format.
- Reconciliation of repo values vs official semantics.
- No-send boundary clarification for `MEXC_TESTNET`.

### 1.3 Non-Goals

- No credentials read, no secret values, no API key validation.
- No authenticated exchange/venue API calls; no account/balance queries; no orders (including `POST /api/v3/order/test`).
- No runtime, Docker/compose, or service changes.
- No modification of [`LR-050-FINAL-RECONCILE.md`](./LR-050-FINAL-RECONCILE.md), [`LR-050-BLOCKER-REFRESH-MATRIX-2026-07-03.md`](./LR-050-BLOCKER-REFRESH-MATRIX-2026-07-03.md), or `LR-*-STATE.yaml`.
- No change to global LR verdict. **LR remains NO-GO.**
- Does not define canary parameters (#2976), secrets/IP/account binding (#2983), or roadmap (#2985).

---

## 2. Repo semantics (repo-backed)

### 2.1 Env / config names

| Name | Where | Default | Role |
|------|-------|---------|------|
| `MOCK_TRADING` | [`services/execution/config.py`](../../services/execution/config.py) L25 | `true` | Mock adapter (`mock_builtin`) vs real executor |
| `DRY_RUN` | [`services/execution/config.py`](../../services/execution/config.py) L26-28 | `true` | `LiveExecutor` logs only, no venue send |
| `MEXC_TESTNET` | [`services/execution/config.py`](../../services/execution/config.py) L22 | `true` | Selects `MexcClient(testnet=…)` base URL; **not** a non-send flag (see §5) |
| `MEXC_BASE_URL` | [`services/execution/config.py`](../../services/execution/config.py) L21; [`services/risk/balance_fetcher.py`](../../services/risk/balance_fetcher.py) L32 | `https://contract.mexc.com` | Explicit base-URL override; default points at deprecated futures host (see §4) |
| `MEXC_API_KEY` / `MEXC_API_SECRET` | [`services/execution/config.py`](../../services/execution/config.py) L19-20 | via `read_secret` | Required only when `DRY_RUN=false` on MEXC path (names only) |
| `CONFIRM_LIVE_TRADING` | [`services/execution/service.py`](../../services/execution/service.py) L993 | unset | Required `true` for mainnet tuple |
| `LIVE_TRADING_CONFIRMED` | [`core/config/trading_mode.py`](../../core/config/trading_mode.py) L95 | unset | Required `yes` for `TRADING_MODE=live` parsing |
| `TRADING_MODE` | [`services/execution/service.py`](../../services/execution/service.py) L1015-1016 | `(unset)` | **Logged only** on `cdb_execution`; not mapped to flags |
| `WS_SOURCE` / `WS_URL` | [`services/ws/mexc_v3_client.py`](../../services/ws/mexc_v3_client.py) L30 | `wss://wbs-api.mexc.com/ws` | Public spot WS feed; not tied to `MEXC_TESTNET` |

### 2.2 Endpoint / venue fundstellen

| Component | Path / symbol | Transport | Base URL in repo |
|-----------|---------------|-----------|------------------|
| REST client (shared) | [`core/clients/mexc.py`](../../core/clients/mexc.py) `MexcClient` | REST (`requests` + HMAC-SHA256) | `testnet=False` → `https://api.mexc.com` (L60); `testnet=True` → `https://contract.mexc.com` (L57, comment "Testnet URL") |
| REST spot endpoints used | `MexcClient` | REST | `/api/v3/account` (L99), `/api/v3/order` (L158, L206, L252), `/api/v3/ticker/price` (L282) |
| Execution config | [`services/execution/config.py`](../../services/execution/config.py) | — | `MEXC_BASE_URL` default `https://contract.mexc.com` (L21) |
| Risk balance fetcher | [`services/risk/balance_fetcher.py`](../../services/risk/balance_fetcher.py) | REST | `MEXC_BASE_URL` default `https://contract.mexc.com` (L32); calls `/api/v3/ticker/price` (L69) |
| WebSocket market data | [`services/ws/mexc_v3_client.py`](../../services/ws/mexc_v3_client.py) `MexcV3Client` | WebSocket protobuf | `wss://wbs-api.mexc.com/ws` (L30) |
| Trading-mode helper (legacy) | [`core/config/trading_mode.py`](../../core/config/trading_mode.py) `get_legacy_config` | — | Bundle table only; **not** wired into `cdb_execution` runtime |

**Key repo behavior:** `cdb_execution` resolves `MOCK_TRADING`, `DRY_RUN`, `MEXC_TESTNET` **directly from env** ([`config.py`](../../services/execution/config.py)); `TRADING_MODE` is only logged ([`service.py`](../../services/execution/service.py) L1015-1016). Startup gate [`_require_live_confirmation()`](../../services/execution/service.py) L979-1004 returns early when `MOCK_TRADING or DRY_RUN or MEXC_TESTNET` is set (L988); only if all three are off does it require `CONFIRM_LIVE_TRADING=true` (else `sys.exit(1)`).

### 2.3 What `DRY_RUN=true` and `MOCK_TRADING=true` prove — and what they do not

**They prove (repo + runtime evidence):**

- `MOCK_TRADING=true` → `mock_builtin` adapter; no live MEXC adapter factory with credentials.
- `DRY_RUN=true` → `LiveExecutor(dry_run=True)` with `client=None`; `execute_order` returns a `DRY_RUN_*` result without calling `place_market_order` / `place_limit_order`.
- Runtime confirmation: [`reports/lr050/dry_run_proof/2026-07-03/manifest.json`](../../reports/lr050/dry_run_proof/2026-07-03/manifest.json) — `result: PASS`, `dry_run: true`, `mock_trading: true`, `mock_builtin_adapter: true`, `no_venue_client_init: true`, `no_place_order_logs: true` (repo head `a90037fb`, merged PR [#3713](https://github.com/jannekbuengener/Claire_de_Binare/pull/3713), #2978).

**They do not prove:**

- Venue endpoint correctness (which host the client would talk to when sending).
- That `MEXC_TESTNET=true` isolates or blocks sends (see §5).
- Any live-capital readiness, canary parameters, or Human Approval.

---

## 3. Official-doc-backed semantics (public docs only, no secrets)

Sources are official MEXC public documentation, read without credentials or account access. See §10 for URLs.

### 3.1 Mainnet Spot REST

| Item | Official semantics | Source |
|------|--------------------|--------|
| Spot REST base endpoint | `https://api.mexc.com` | MEXC Spot API docs (apidocs spot_v3; api-docs/spot-v3 introduction) |
| Spot order endpoint | `POST /api/v3/order` (params: `symbol`, `side`, `type`, `quantity`[, `price`, `timeInForce`], `timestamp`, `signature`; header `X-MEXC-APIKEY`) | MEXC Spot API docs |
| Test-order endpoint | `POST /api/v3/order/test` — validates without submitting to the matching engine; **not** a separate sandbox | MEXC Spot API docs (Test New Order) |
| Symbol naming | Concatenated, e.g. `BTCUSDT` (no separator) | MEXC Spot API docs |
| REST rate limit | `429` on exceed; keyed endpoints limited per account, non-keyed per IP | MEXC Spot API docs |
| API key IP whitelist | Optional; if no whitelist added, key valid for 90 days | MEXC Spot API introduction |

Repo's live (`testnet=False`) base URL `https://api.mexc.com` and the spot `/api/v3/*` paths **match** the official mainnet spot semantics.

### 3.2 Mainnet Spot WebSocket

| Item | Official semantics | Source |
|------|--------------------|--------|
| Spot WS base endpoint | `ws://wbs-api.mexc.com/ws` (protobuf push format) | MEXC Spot API docs (Websocket Market/User Data Streams) |
| Connection lifetime | Each connection valid ≤ 24h; ping/pong keepalive | MEXC Spot API docs |
| Subscription limit | ≤ 30 streams per single connection; WS access limited to 100/s | MEXC Spot API docs |
| Protobuf definitions | `https://github.com/mexcdevelop/websocket-proto` | MEXC Spot API docs |

Repo WS URL `wss://wbs-api.mexc.com/ws` ([`mexc_v3_client.py`](../../services/ws/mexc_v3_client.py) L30) targets the **same host/path** as the official spot WS base (repo correctly uses the secure `wss://` scheme). The repo WS feed is a **public spot** stream and is **not** switched by `MEXC_TESTNET`.

### 3.3 Testnet / Sandbox

| Item | Official semantics | Source |
|------|--------------------|--------|
| Spot API sandbox / testnet | **Not offered.** "MEXC API connects directly to the live trading environment. We don't currently offer a sandbox or test environment." | MEXC API overview |
| Futures Demo Trading ("testnet") | Web-based demo only; supports 4 futures pairs (USDT-M `BTCUSDT`, `ETHUSDT`; COIN-M `BTCUSD`, `ETHUSD`); demo prices may differ from live; generally no programmatic Spot API access | MEXC Futures demo announcement |
| `contract.mexc.com` | Former **MEXC Futures** access domain; officially superseded by `https://api.mexc.com`, with support for the original domain **discontinued from 2026-01-19** | MEXC API updates announcement; MEXC Futures integration guide; corroborated by ccxt/ccxt #27838 |

**Conclusion:** There is **no official MEXC Spot API testnet/sandbox**. A testnet exists only as a **web-based Futures demo**, which is not the repo's spot REST/WS path.

---

## 4. Reconciliation — repo config vs official semantics

| Repo location | Repo value | Official semantics | Verdict |
|---------------|-----------|--------------------|---------|
| [`core/clients/mexc.py`](../../core/clients/mexc.py) L60 (live) | `https://api.mexc.com` + spot `/api/v3/*` | Spot REST base `https://api.mexc.com` | **Correct** (mainnet spot) |
| [`services/ws/mexc_v3_client.py`](../../services/ws/mexc_v3_client.py) L30 | `wss://wbs-api.mexc.com/ws` | Spot WS base `ws(s)://wbs-api.mexc.com/ws` | **Correct** (mainnet spot WS) |
| [`core/clients/mexc.py`](../../core/clients/mexc.py) L57 (testnet) | `https://contract.mexc.com` labeled "Testnet URL", still using spot `/api/v3/*` | `contract.mexc.com` = former **Futures** host, **deprecated since 2026-01-19**; **no** spot testnet exists | **Incorrect / stale label** — not a real spot testnet; deprecated host; wrong API family for spot paths |
| [`services/execution/config.py`](../../services/execution/config.py) L21 (`MEXC_BASE_URL` default) | `https://contract.mexc.com` | deprecated futures host | **Stale default** |
| [`services/risk/balance_fetcher.py`](../../services/risk/balance_fetcher.py) L32 + L69 | `https://contract.mexc.com` + spot `/api/v3/ticker/price` | deprecated futures host + spot path | **Stale default + family mismatch** |
| [`core/config/trading_mode.py`](../../core/config/trading_mode.py) L203-208 `STAGED` | `MOCK_TRADING=False, DRY_RUN=False, MEXC_TESTNET=True` (labeled "testnet") | No spot testnet; combination is exchange-capable | **Exchange-capable, not dry-run; "testnet" is nominal** |

**Repo finding (code-level, out of scope for this docs gate):** the `testnet=True` branch and the `MEXC_BASE_URL` defaults point at the deprecated `contract.mexc.com` futures host and are labeled "Testnet URL", although MEXC offers no spot testnet. Setting `MEXC_TESTNET=true` today would not route to a safe sandbox; against a discontinued domain it would more likely fail to connect. This is a documentation/verification finding here; the code correction is tracked as a **separate deduplicated follow-up issue** (linked in the delivering PR) and is not fixed in this documentation-only change.

---

## 5. No-Send boundary

`MEXC_TESTNET` alone is **not** a no-send proof, on two independent grounds:

1. **Startup-gate only, not a send blocker.** [`_require_live_confirmation()`](../../services/execution/service.py) L988 treats `MEXC_TESTNET=true` like `MOCK_TRADING` / `DRY_RUN`: it **skips** the `CONFIRM_LIVE_TRADING` exit. With `MOCK_TRADING=false`, `DRY_RUN=false`, `MEXC_TESTNET=true`, [`LiveExecutor`](../../services/execution/live_executor.py) still constructs `MexcClient` and may call `place_market_order` / `place_limit_order` ([`core/clients/mexc.py`](../../core/clients/mexc.py)). This matches [`LR-050-DRY-RUN-PROOF.md`](./LR-050-DRY-RUN-PROOF.md) §2.2 and [`LR-050-FINAL-RECONCILE.md`](./LR-050-FINAL-RECONCILE.md) §4.
2. **No real venue isolation.** Per §3-§4, there is no MEXC spot testnet, and the configured "testnet" host is a deprecated futures domain — so `MEXC_TESTNET=true` provides neither a documented sandbox nor a reliable non-production venue.

**No-send for CDB remains dependent on all of:**

- `DRY_RUN=true`, **and**
- `MOCK_TRADING=true` (or a confirmed `mock_builtin` adapter selection),
- i.e. the mock executor / `mock_builtin` path,
- runtime-evidenced by #2978 ([`reports/lr050/dry_run_proof/2026-07-03/`](../../reports/lr050/dry_run_proof/2026-07-03/manifest.json), PR [#3713](https://github.com/jannekbuengener/Claire_de_Binare/pull/3713)),
- with **no** real order paths exercised.

`TRADING_MODE=staged` is likewise **not** dry-run and not authoritative on the execution path (logged only).

Mainnet activation tuple (repo-backed, forbidden here): `MOCK_TRADING=false` **and** `MEXC_TESTNET=false` **and** `DRY_RUN=false` **and** `CONFIRM_LIVE_TRADING=true` (plus `LIVE_TRADING_CONFIRMED=yes` for `TRADING_MODE=live` parsing).

---

## 6. #2979 Gate decision

**Gate: PASS** — venue / testnet / mainnet endpoint semantics are sufficiently documented by **repo sources + official public MEXC documentation**, which is the docs-based verification path #2979 explicitly permits ("Verification can use MEXC public API docs without account access").

### 6.1 Acceptance-criteria mapping (#2979)

| # | Acceptance criterion | Met by |
|---|----------------------|--------|
| 1 | REST endpoint semantics verified vs MEXC docs | §3.1, §4 — mainnet spot base `https://api.mexc.com` verified; repo live path matches |
| 2 | WebSocket/feed semantics verified | §3.2, §4 — spot WS base `wbs-api.mexc.com/ws` verified; repo path matches |
| 3 | Testnet vs mainnet assumptions documented (order format, rate limits, symbol naming) | §3.1-§3.3 — no spot testnet; futures demo web-only; order format, rate limits, symbol naming documented |
| 4 | `MEXC_TESTNET` documented as **not** non-send proof | §5 — reinforced on two grounds |
| 5 | Evidence redacted of secrets and account identifiers | Whole document — names/classes only |
| 6 | No secrets disclosed in repo | Authoring method — repo read-only + public docs; no credentials |

### 6.2 What PASS does and does not mean

- **Does:** close the #2979 venue-semantics verification gate; establish that repo endpoint config for the mainnet spot path is correct and that `MEXC_TESTNET` is neither a no-send proof nor a real spot testnet.
- **Does not:** clear the live-capital blocker in [`LR-050-FINAL-RECONCILE.md`](./LR-050-FINAL-RECONCILE.md) §3, authorize any canary, grant Human Approval, or change the global verdict. **LR remains NO-GO.** Operator/runtime live-venue confirmation (an actual authenticated connection) is out of scope for #2979 and is not required by its acceptance criteria; it remains a separate future scope if ever pursued.

---

## 7. Dependencies (referenced only — not resolved, not closed)

| Issue | Status | Note |
|-------|--------|------|
| [#2976](https://github.com/jannekbuengener/Claire_de_Binare/issues/2976) Canary caps / symbolset | **OPEN** | Not closed here; canary parameters remain `TBD_BLOCKER_BEFORE_LIVE` |
| [#2983](https://github.com/jannekbuengener/Claire_de_Binare/issues/2983) Secrets / IP / account binding | **OPEN / parked** | Not closed here; S7 IP allowlist not touched |
| [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985) Meta / Live roadmap | **OPEN** | Not closed here; control overview only |
| [#3713](https://github.com/jannekbuengener/Claire_de_Binare/pull/3713) / #2978 dry-run proof | **MERGED** | Runtime no-send evidence referenced in §2.3, §5 |
| [#3714](https://github.com/jannekbuengener/Claire_de_Binare/pull/3714) / #2984 kill-switch drill | **MERGED** | Referenced context |
| [#3717](https://github.com/jannekbuengener/Claire_de_Binare/pull/3717) / #2983 secrets readiness | **MERGED** | INCONCLUSIVE (S7); #2983 stays OPEN |

No LR-wide release is implied. This document does not authorize live capital.

---

## 8. Method / validation (docs-only)

- Repo read-only inspection of the files cited above at `origin/main` `b758edd1`.
- Official MEXC public documentation read via web without credentials, account access, or API calls.
- No authenticated exchange call, no order (including test order), no secret read.
- Redaction review: no IP addresses, no account identifiers, no email addresses, no tokens, no secret values.

---

## 9. Restunsicherheiten (explicit)

- Official docs are a public snapshot (2026-07-03); MEXC may change domains, limits, or demo scope over time.
- No authenticated/live connection was made; this is documentation verification, not an operator live-venue drill.
- The deprecated `contract.mexc.com` "testnet" configuration is a code-level defect tracked as a separate follow-up; it is documented but not fixed here.

---

## 10. Sources

Repo (at `origin/main` `b758edd1`):

- [`core/clients/mexc.py`](../../core/clients/mexc.py), [`services/execution/config.py`](../../services/execution/config.py), [`services/execution/service.py`](../../services/execution/service.py), [`services/risk/balance_fetcher.py`](../../services/risk/balance_fetcher.py), [`services/ws/mexc_v3_client.py`](../../services/ws/mexc_v3_client.py), [`core/config/trading_mode.py`](../../core/config/trading_mode.py)
- [`reports/lr050/dry_run_proof/2026-07-03/manifest.json`](../../reports/lr050/dry_run_proof/2026-07-03/manifest.json)
- [`LR-050-VENUE-AUDIT.md`](./LR-050-VENUE-AUDIT.md), [`LR-050-DRY-RUN-PROOF.md`](./LR-050-DRY-RUN-PROOF.md), [`LR-050-FINAL-RECONCILE.md`](./LR-050-FINAL-RECONCILE.md), [`LR-050-BLOCKER-REFRESH-MATRIX-2026-07-03.md`](./LR-050-BLOCKER-REFRESH-MATRIX-2026-07-03.md)

Official MEXC public documentation (read-only, no credentials):

- MEXC Spot API docs: `https://mexcdevelop.github.io/apidocs/spot_v3_en/`
- MEXC Spot API introduction: `https://www.mexc.com/api-docs/spot-v3/introduction`
- MEXC Spot Test New Order: `https://www.mexc.com/api-docs/spot-v3/spot-account-trade/test-new-order`
- MEXC API overview (sandbox/testnet statement): `https://www.mexc.com/mexc-api`
- MEXC Futures demo trading: `https://www.mexc.com/announcements/article/how-to-access-demo-trading-in-mexc-futures-5705980230169`
- MEXC API updates (`contract.mexc.com` → `api.mexc.com`): `https://www.mexc.com/announcements/api-updates`
- MEXC Futures integration guide / contract docs: `https://www.mexc.com/api-docs/futures/integration-guide`, `https://mexcdevelop.github.io/apidocs/contract_v1_en/`

---

**Closing statement:** This document delivers the #2979 venue endpoint semantics verification as a documentation-only artifact. It does not execute exchange calls, read secrets, place orders, change runtime, or authorize live capital. **LR remains NO-GO. Kein Live-Go. Kein Echtgeld-Go.**
