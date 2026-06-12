# External MEXC Historical Provider Research for #3092

**Decision Date:** 2026-06-12
**Issue:** #3092
**Scope:** Research-only evaluation of external providers for retroactive MEXC BTCUSDT spot 1m candle coverage for the #3028 window
**Decision:** **NO_PURCHASE_RECOMMENDED** under current session boundaries

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `git status -sb`, `git rev-parse`, `gh issue view`, `gh pr list`, `rg`, `webfetch` against official public provider docs/pricing pages |
| `records_or_results` | Live GitHub issue state for #3092/#3086/#3028/#3083; repo evidence for #3028 window; official public provider pages for Tardis.dev, Kaiko, CoinAPI, CryptoDataDownload |
| `repo_crosscheck` | `docs/evidence/arvp_mexc_same_venue_acquisition_3086.md`, `docs/evidence/arvp_signal_reproduction_gap_3057_after_2980.md`, `artifacts/candles/3028_window/dataset_spec.json` |
| `impact_on_plan` | Provider evaluation is pinned to the full replay dataset window, not just the inner paper event window; no provider is actionable without leaving current no-purchase/no-signup/no-credential boundaries |
| `limitations` | No DB-backed evidence used; no provider account, API key, trial, or download was used; Kaiko and CoinAPI pair-level MEXC BTCUSDT coverage could not be fully proven from static public pages alone |

---

## Scope and Non-goals

### In scope

- Evaluate official public evidence for external MEXC historical data providers.
- Judge whether a provider could plausibly cover the #3028 full dataset window.
- Document data shape, provenance posture, pricing/access model, and governance implications.
- Produce a ranked recommendation for #3086 Option D only.

### Non-goals

- No purchase or subscription.
- No signup or free-trial activation.
- No API key or credential use.
- No actual data download.
- No code, runtime, DB, Docker, or MCP mutation.
- No #3091 execution work.
- No LR or Echtgeld status change.

---

## #3028 Window Requirements

### Required evaluation target

- **Market:** MEXC spot `BTCUSDT`
- **Granularity:** `1m` candles
- **Full dataset window:** `2026-06-05T20:28:00Z` to `2026-06-06T00:31:00Z`
- **Inner paper event window:** `2026-06-06T00:28:12.551Z` to `2026-06-06T00:30:12.814Z`

### Evaluation rule

Provider viability is judged against the **full dataset window** above. The inner paper event window is context only and is not enough for a replacement replay dataset.

### Repo-backed context

- Current replay dataset is `Binance`, not MEXC.
- `artifacts/candles/3028_window/dataset_spec.json` marks `venue_mismatch=true`.
- `docs/evidence/arvp_mexc_same_venue_acquisition_3086.md` records the same full dataset window and states that no retroactive same-venue MEXC dataset exists in-repo today.
- `#3083` / PR `#3085` established that MEXC public klines retention is too short for this window.

---

## Provider Evaluation Matrix

| provider | mexc_spot_coverage | btcusdt_symbol_proof | 1m_ohlcv_support | 3028_window_coverage | data_format | provenance_quality | pricing_access_model | signup_key_purchase_required | repo_backed_evidence_fit | governance_risk | recommendation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Kaiko` | `unknown on static public docs; exchange/instrument lookup path documented` | `unknown on static public docs; docs say to verify via exchange+instrument reference data` | `yes; official OHLCV endpoint supports minute intervals and trade-based OHLCV` | `plausible if MEXC spot BTCUSDT is covered, but not publicly proven in this slice` | `REST JSON; stream; cloud delivery` | `high` | `quote-based / contact sales` | `yes` | `medium after separate procurement and symbol verification` | `high` | `maybe` |
| `CoinAPI` | `unknown from accessible public proof` | `unknown from accessible public proof` | `yes; historical OHLCV, trade data, and flat files are publicly advertised` | `plausible if MEXC symbol exists, but not publicly proven in this slice` | `REST, WebSocket, flat files, gz CSV` | `high` | `published paid tiers plus free credits` | `yes` | `medium after separate procurement and symbol verification` | `high` | `maybe` |
| `CryptoDataDownload` | `not publicly proven; public exchange catalog omits MEXC and /data/mexc/ is 404` | `not proven` | `yes for supported exchanges` | `not plausible from public proof for MEXC` | `CSV/XLSX downloads; API JSON/CSV/XLSX` | `medium` | `free tier plus paid Plus/API/PRO tiers` | `not needed for some free data, but MEXC proof is absent` | `low for this issue because MEXC coverage is not publicly evidenced` | `medium` | `rejected` |
| `Tardis.dev` | `not publicly proven; official docs query could not find MEXC spot support` | `not proven` | `no precomputed provider-side 1m OHLCV; aggregation is client-side from tick data` | `not plausible from public proof` | `NDJSON raw replay, tick-level CSV datasets, client-side computed OHLCV` | `high for supported exchanges` | `API key via order; limited unauthenticated access only for first day of each month` | `yes` | `low for this issue because data shape and exchange proof do not fit the required retroactive file-backed candle need` | `high` | `rejected` |

---

## Provider Notes

### 1. Kaiko

**What is publicly proven**

- Official OHLCV endpoint documentation supports historical OHLCV for a specific exchange/instrument and accepts minute intervals such as `1m`.
- Official API-key documentation states that requests require an `X-Api-Key` and instructs users to contact `support@kaiko.com` if they do not have one.
- Official pricing page says plans are custom/quote-based depending on assets, granularity, history, and usage.

**What is not publicly proven in this slice**

- Static public docs do not directly prove `MEXC spot BTCUSDT` coverage.
- Official docs instead point to exchange-code and instrument-code lookup flows or the Instrument Explorer to verify exact pair coverage.
- This session did not perform authenticated lookup, signup, or any live provider-side query.

**Why it is still ranked highest**

- Kaiko has the strongest public proof of provider-side `1m` OHLCV support tied to exchange/instrument identifiers.
- Its public docs explicitly define the path needed to confirm exact pair coverage.
- That makes Kaiko the most defensible procurement/contact candidate, even though this turn cannot prove the exact MEXC pair.

**Sources retrieved 2026-06-12**

- `https://docs.kaiko.com/rest-api/data-feeds/level-1-and-level-2-data/level-1-aggregations/trade-count-ohlcv-and-vwap/ohlcv-only.md`
- `https://docs.kaiko.com/getting-started/about-the-developer-hub.md?ask=Does Kaiko provide historical MEXC spot BTCUSDT 1 minute OHLCV or trade data, and would access require signup, trial, or enterprise contact?`
- `https://www.kaiko.com/about-kaiko/pricing-and-contracts`
- `https://docs.kaiko.com/getting-started/about-the-developer-hub.md?ask=Is BTCUSDT on MEXC spot covered?`

**Limitations**

- Public static docs alone do not justify a `viable` verdict.
- Exact MEXC pair coverage remains `unknown` until a separate human-approved verification step is taken.

### 2. CoinAPI

**What is publicly proven**

- Official Market Data API product page advertises historical OHLCV, trades, quotes, order books, metadata, and broad exchange coverage.
- Official Flat Files product page advertises downloadable historical OHLCV/trades/order books with exchange- and symbol-level files.
- Official pricing page publishes a real paid access surface with free credits, metered access, and paid startup/streamer/pro tiers.

**What is not publicly proven in this slice**

- No accessible public page in this slice directly proved `MEXC spot BTCUSDT` coverage.
- Some `docs.coinapi.io` surfaces were not publicly retrievable from this environment, so pair-level proof stayed incomplete.

**Why it remains a procurement candidate**

- CoinAPI publicly proves the right general data shape: historical OHLCV plus bulk historical delivery.
- Unlike Tardis, the provider-side offering includes prebuilt OHLCV and flat-file workflows.
- That makes it a plausible second procurement/contact candidate even though exact pair proof is missing.

**Sources retrieved 2026-06-12**

- `https://www.coinapi.io/products/market-data-api`
- `https://www.coinapi.io/products/flat-files`
- `https://www.coinapi.io/products/market-data-api/pricing`

**Limitations**

- Public proof in this slice is product-level, not pair-level.
- Exact MEXC spot BTCUSDT coverage remains `unknown`.

### 3. CryptoDataDownload

**What is publicly proven**

- Official home, data, and services pages advertise free or paid historical `1m` OHLCV for supported exchanges and a programmatic API.
- Public exchange catalog pages list supported exchanges by region.

**What blocks it for #3092**

- The public exchange catalog does not list MEXC.
- The direct path `https://www.cryptodatadownload.com/data/mexc/` returns `404`.
- No public page in this slice proves MEXC spot coverage, let alone exact `BTCUSDT` support.

**Sources retrieved 2026-06-12**

- `https://www.cryptodatadownload.com/`
- `https://www.cryptodatadownload.com/data/`
- `https://www.cryptodatadownload.com/services/`
- `https://www.cryptodatadownload.com/data/mexc/`

**Limitations**

- Public catalog absence is not the same as a contractual denial.
- It is still sufficient to reject the provider for this repo-backed research decision because no public MEXC proof is available.

### 4. Tardis.dev

**What is publicly proven**

- Official HTTP API docs provide historical raw exchange-native feeds and require `Authorization: Bearer YOUR_API_KEY` for normal historical access.
- Official data FAQ states that Tardis provides raw tick-level data, not provider-side precomputed OHLCV candles.
- Official docs query could not find evidence that Tardis supports MEXC spot, including `BTCUSDT`.

**Why that is a hard mismatch for #3092**

- The issue needs a retroactive file-backed same-venue candle replacement path.
- Tardis publicly fits raw replay/tick-data workflows, not provider-side precomputed `1m` candle delivery.
- The same public evidence also fails to prove MEXC spot support.

**Sources retrieved 2026-06-12**

- `https://docs.tardis.dev/api/http-api-reference.md`
- `https://docs.tardis.dev/faq/data.md`
- `https://docs.tardis.dev/downloadable-csv-files.md?ask=Does Tardis provide historical MEXC spot BTCUSDT 1m candle or trade data, and does access require an account or API key?`

**Limitations**

- The docs query is still a derived documentation answer, not a commercial contract.
- It is nevertheless strong enough for a `rejected` recommendation under this issue's constraints.

---

## Governance Assessment

### Current session boundary result

No provider is actionable inside the current hard boundaries:

- no purchase
- no signup
- no free trial
- no API key
- no credentials
- no data download

### Consequence

- `Kaiko` and `CoinAPI` are at most **procurement/contact candidates**.
- `CryptoDataDownload` and `Tardis.dev` are not credible public-evidence paths for this issue.
- No provider can produce immediate repo-backed backfill evidence from this session alone.

### Governance call

The truthful research outcome is therefore:

- **research complete**
- **retroactive backfill still blocked operationally**
- **NO_PURCHASE_RECOMMENDED** in this session
- any next step would require a separate human decision on procurement/contact scope

---

## Ranked Recommendation

1. **Kaiko — `maybe`**
   - Best public proof of exchange/instrument-scoped historical `1m` OHLCV.
   - Still not publicly sufficient to prove exact `MEXC spot BTCUSDT` in this slice.
   - Treat as top procurement/contact candidate only.

2. **CoinAPI — `maybe`**
   - Strong public product proof for historical OHLCV/trades/flat files and explicit pricing.
   - Exact MEXC spot BTCUSDT proof not obtained from accessible public docs in this slice.
   - Treat as second procurement/contact candidate only.

3. **CryptoDataDownload — `rejected`**
   - Public exchange catalog does not show MEXC.
   - Direct MEXC data path is `404`.
   - Not defensible as a public-evidence route for `#3092`.

4. **Tardis.dev — `rejected`**
   - Public docs do not prove MEXC spot support.
   - Public product shape is raw tick data, not provider-side precomputed `1m` candle delivery.
   - Not a good fit for the required backfill artifact under this scope.

### Session-level decision language

**NO_PURCHASE_RECOMMENDED.**

This research does not justify purchase, signup, or credential use. If Jannek wants to pursue Option D anyway, the next human decision should be whether to contact `Kaiko` or `CoinAPI` first for exact `MEXC spot BTCUSDT 1m` historical coverage confirmation and commercial terms.

---

## Decision for #3086

`#3086` Option D research is now complete at the public-evidence level.

### What this research proves

- External provider research was missing and is now documented.
- `Kaiko` and `CoinAPI` are the only plausible procurement/contact candidates from current public evidence.
- No provider is publicly proven usable enough to authorize retroactive backfill work within this session.

### What this research does not prove

- It does **not** acquire real MEXC same-venue data.
- It does **not** prove a purchasable provider definitely covers `MEXC spot BTCUSDT` for the full `#3028` window.
- It does **not** close `#3086`.

### Decision statement

- `#3086` stays open.
- `#3091` stays open as the future capture path.
- Option D is now narrowed to a human procurement/contact decision rather than an unbounded research question.

---

## Limitations

- This document uses official public surfaces only.
- No provider account, API key, or authenticated catalog query was used.
- No actual historical files were downloaded or inspected.
- Kaiko public docs define how to verify exact pair coverage but do not provide a static public yes/no proof captured in this slice.
- CoinAPI public product pages prove product shape and pricing, but pair-level MEXC coverage remains unverified from accessible public docs.
- Provider catalogs can change over time; this is a point-in-time research result as of `2026-06-12`.

---

## Safety Boundaries

- LR remains `NO-GO`.
- No Live-Go.
- No Echtgeld-Go.
- No purchase.
- No signup.
- No credentials.
- No data download.
- No runtime, DB, Docker, or MCP mutation.
- No scope growth into `#3091` execution.
