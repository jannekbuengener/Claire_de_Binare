# ARVP #3086: MEXC Same-Venue Candle Acquisition Decision

**Decision Date:** 2026-06-09
**Decision:** **DECISION_COMPLETE_EXECUTION_SPLIT**
**Status:** DONE_MERGED_HOLD_EXECUTE_BLOCKER
**Issue:** #3086 remains OPEN until real MEXC same-venue dataset is delivered

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `gh issue view` (x6), `gh pr view` (x2), `gh pr list`, `git fetch/status/rev-parse`, `rg` across repo |
| `records_or_results` | 8 live GitHub queries; 4 evidence docs; DB schema; MEXC WS client + candles service + db_writer code |
| `repo_crosscheck` | `candle_continuity.py`, `mexc_v3_client.py`, `candles/service.py`, `db_writer/db_writer.py`, `schema.sql`, `dataset_spec.json` |
| `impact_on_plan` | Persistent MEXC candle capture pipeline already designed and implemented; acquisition is activation not construction |
| `limitations` | Cannot verify DB contents (no DB access in this slice); no SurrealDB/Context Brain evidence used |

---

## Bootloader / Read-Order

- `AGENTS.md` root pointer → `agents/AGENTS.md` canonical registry ✅
- `knowledge/governance/CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md` ✅
- `docs/runbooks/CONTROL_REGISTER.md`: Board `trade-capable`, LR NO-GO ✅
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`: LR verdict NO-GO ✅
- Git truth: HEAD `696f3d7` == `origin/main`, clean worktree ✅

---

## Problem Statement

The #3028 paper reference window (2026-06-06) uses Binance 1m candles (`venue_mismatch=true`,
source: `binance_spot_api_v3_klines`). This venue mismatch confounds drift classification and
limits aggregate certainty for the ARVP calibration batch to `limited`.

MEXC's public klines API (`/api/v3/klines`) only retains ~2.5 days of 1m candle history, as
confirmed by #3083 / PR #3085. The #3028 window is ~60 hours before the earliest available
MEXC public kline.

A viable acquisition strategy for MEXC same-venue 1m candle data beyond public klines retention
is needed to document the path forward and either close #3086 as a plan issue or leave it open
with an explicitly named execute blocker.

---

## Repo/Data Inventory

### Existing MEXC Candle Persistence Pipeline (ALREADY BUILT)

The runtime stack contains a complete persistent MEXC candle capture chain:

```
MEXC Spot V3 WebSocket (services/ws/mexc_v3_client.py)
  → protobuf-decoded aggregated deals via Redis PubSub
  → Candles Service (services/candles/service.py) aggregates → 1m OHLCV
  → Redis Stream (stream.candles_1m) with maxlen=100000
  → DB Writer daemon (services/db_writer/db_writer.py, _candle_stream_worker)
    → Postgres candles_1m table (infrastructure/database/schema.sql:232)
    → Provenance in candle_backfill_imports (schema.sql:268)
```

Key components:
| Component | File | Role |
|-----------|------|------|
| MEXC WS Client | `services/ws/mexc_v3_client.py` | Connects `wss://wbs-api.mexc.com/ws`, decodes protobuf public.aggre.deals |
| Candles Service | `services/candles/service.py` | Aggregates raw trades into 1m candles, emits to `stream.candles_1m` |
| DB Writer | `services/db_writer/db_writer.py:873` | Daemon thread: XREAD from `stream.candles_1m`, INSERT into `candles_1m` |
| DB Table | `infrastructure/database/schema.sql:232` | `candles_1m` with UNIQUE(symbol, ts_ms), all required OHLCV columns |
| Provenance Table | `infrastructure/database/schema.sql:268` | `candle_backfill_imports` with source, checksum, payload |

### Existing Offline Backfill Tools

| Component | File | Role |
|-----------|------|------|
| MEXC parser | `candle_continuity.py:273` | `parse_mexc_kline` — 8-field MEXC kline → `CandleRow` |
| MEXC fetcher | `candle_continuity.py:355` | `fetch_mexc_klines` — paginate public `/api/v3/klines` |
| MEXC CLI | `candle_continuity.py:653` | `backfill-mexc` subcommand with `--apply` for DB insert |

### #3028 Window Status

| Property | Value |
|----------|-------|
| Window ID | `0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab` |
| Timeframe | 2026-06-05T20:28:00 to 2026-06-06T00:31:00 UTC |
| Candles | 244 (Binance, venue_mismatch=true) |
| Source | `binance_spot_api_v3_klines` |
| Venue match | `false` — Binance is not original paper-trade venue |
| Regime note | All `regime_id=0` (Binance klines lack regime data); original MEXC paper used `regime_id=2` |

### What Does NOT Exist

- MEXC same-venue candles for the #3028 window (outside ~2.5 day public klines retention)
- Any external provider or premium API integration
- Any method to retroactively recover MEXC data beyond the public klines retention window
  without external purchase or credentials

---

## Acquisition Option Matrix

### Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Retroactive #3028 | Critical | Can the #3028 window be backfilled? |
| Future windows | High | Can future comparison windows get same-venue data? |
| Requires secrets | Blocker | API keys or credentials needed? |
| Requires purchase | Blocker | $/€ cost? |
| Governance compliance | Hard gate | Within CDB_AGENT_POLICY and safety boundaries? |
| Implementation effort | Moderate | Is the code already built? |
| Data quality | High | Real MEXC venue-matched 1m OHLCV? |
| Provenance | High | Deterministic, auditable source? |

### Option Matrix

| # | Option | Retro #3028 | Future | Secrets? | Purchase? | Gov OK? | Effort | Quality | Viability |
|---|--------|:-----------:|:------:|:--------:|:---------:|:-------:|:------:|:-------:|-----------|
| A | MEXC public klines (backfill CLI) | ❌ | ✅ | No | No | ✅ | Built | Real MEXC | **VIABLE** (future only) |
| B | Persistent runtime capture (WS → DB) | Unknown | ✅ | Yes (SECRETS_PATH) | No | ✅ | Built | Real MEXC | **VIABLE** (future only) |
| C | Premium MEXC API (deeper history) | Possibly | Yes | Yes | Yes ($) | ❌ Forbidden | Unbuilt | Real MEXC | **BLOCKED** |
| D | External historical data provider | Possibly | N/A | Possibly | Yes ($) | Research only | Unbuilt | Real MEXC | **RESEARCH** |
| E | Synthetic / Binance ersatz | N/A | N/A | N/A | N/A | ❌ REJECT | N/A | Fake | **REJECTED** |
| F | Fractal / MEXC adapter | Unclear | Unclear | Yes | Unknown | ❌ No code | Unbuilt | Unclear | **UNPROVEN** |

### Detailed Option Assessments

#### Option A: MEXC Public Klines API (`backfill-mexc` CLI)

- Status: Code delivered via PR #3085
- Retention: ~2.5 days of 1m candles
- Auth: None (public endpoint)
- Gap: #3028 window (2026-06-06) is 60+ hours outside retention
- Viable for: Windows within ~60 hours of query time
- Not viable for: Historic windows (pre-2026-06-08)
- Evidence: `docs/evidence/arvp_mexc_backfill_3083.md`

#### Option B: Persistent Runtime Capture (Existing Pipeline)

- Status: Full pipeline designed, implemented, and integrated
- How it works:
  1. Start BLUE+RED stack (`make docker-up`)
  2. MEXC WS client connects, receives real-time aggregated deals
  3. Candles service aggregates into 1m candles
  4. DB Writer persists to `candles_1m`
  5. `DBBackedDatasetProvider` (core/replay/dataset_provider.py) queries `candles_1m` for replay windows
- Prerequisite: Running Docker stack with `SECRETS_PATH` containing MEXC API key
- Data quality: Real MEXC same-venue 1m candles, cadence-enforced, deterministic
- Provenance: `ingested_at` timestamp, `candle_backfill_imports` records
- Caveats:
  - Requires stack runtime (forbidden in this slice)
  - Cannot retroactively fill #3028 unless the stack was running at that time
  - Gap-safe cursor persistence is a known limitation (db_writer:882)

#### Option C: Premium MEXC API

- Likely endpoint: MEXC offers authenticated endpoints with deeper history for VIP tiers
- Blocker: Requires purchase, credentials, and API key usage
- Governance: Forbidden in this slice (no purchase, no credentials, no API keys)
- Status: BLOCKED — no execute in this issue; can be reconsidered in a future slice
  with explicit human approval

#### Option D: External Historical Data Provider

- Candidates (research, not recommendation):
  - Tardis.dev — historical crypto market data (MEXC spot coverage TBD)
  - Kaiko — institutional-grade historical crypto data
  - CoinAPI — unified crypto market data API
  - CryptoDataDownload — bulk CSV exports
- Status: Research candidate only — no evaluation, no purchase, no signup
- Separate research issue recommended

#### Option E: Synthetic / Binance ersatz

- Rejected per ARVP decision rules: "Keine unechte same-venue Behauptung"
- Binance data is explicitly `venue_mismatch=true` and cannot substitute for MEXC
- Synthetic data would violate the core ARVP principle of calibration against reality

#### Option F: Fractal / MEXC Adapter

- No existing code, no established path, no evidence of feasibility
- Too speculative for a decision document

---

## Decision

### Primary Acquisition Route: Option B (Persistent Runtime Capture)

The persistent MEXC candle capture pipeline already exists in the repo:

| Component | Status |
|-----------|--------|
| MEXC WS client (protobuf) | ✅ Built (`mexc_v3_client.py`) |
| Candles 1m aggregator | ✅ Built (`candles/service.py`) |
| Redis Stream emission | ✅ Built (`stream.candles_1m`) |
| DB Writer persistence | ✅ Built (`db_writer/db_writer.py`) |
| DB Schema (`candles_1m`) | ✅ Built (`schema.sql:232`) |
| Provenance tracking | ✅ Built (`candle_backfill_imports`) |
| Replay dataset provider | ✅ Built (`dataset_provider.py`) |

**The acquisition strategy is activation, not construction.**

### Fallback Route: Option A (Public Klines CLI)

For windows within the ~2.5 day retention window, `backfill-mexc` in `candle_continuity.py`
provides same-venue data without requiring the full runtime stack. Usable for:

- Quick, targeted window backfills
- Testing and validation without stack startup
- Windows captured within 60 hours of the query time

### Retroactive #3028: Option D (External Provider Research)

The #3028 window (2026-06-06) cannot be retroactively filled without external purchase.
Option D (external historical data provider) is the only plausible route, but requires:

- Research into provider MEXC spot coverage
- Purchase decision (out of scope for this slice)
- Separate research issue recommended

### Rejected Options

- **Option C (Premium API):** Requires purchase + credentials — forbidden in this slice
- **Option E (Synthetic/Binance):** Anti-pattern — violates same-venue requirement
- **Option F (Fractal/Adapter):** No code exists — speculative

---

## Status for Issue #3086

### Verdict: **DECISION_COMPLETE_EXECUTION_SPLIT**

| Criterion | Status |
|-----------|--------|
| Acquisition strategy documented | ✅ This document |
| Viable route identified | ✅ Option B (primary) + Option A (fallback) |
| Execution blocker named | ✅ Real MEXC same-venue dataset not yet delivered |
| Retroactive #3028 path identified | ✅ Option D (research) |
| Synthetic/ersatz rejected | ✅ Option E explicitly rejected |
| No credentials or purchase | ✅ Confirmed (docs-only slice) |
| Real dataset delivered | ❌ **Not yet** — #3086 remains OPEN |

**#3086 remains OPEN** until a real MEXC same-venue dataset is delivered for at least one comparison-grade window, or the issue is explicitly superseded.

---

## Follow-up Mapping

| Follow-up | Type | Scope |
|-----------|------|-------|
| Persistent MEXC capture execute | Execute | Validate existing WS → candles → db_writer pipeline; produce file-backed MEXC same-venue dataset for future windows |
| External provider research | Research | Survey MEXC historical data providers for #3028 backfill; no purchase, no credentials |
| #3087 comment | Informational | Note that future-window MEXC capture may be directly relevant to regime_segments blocker |

---

## Related Issue Status

| Issue | State | Relevance |
|-------|-------|-----------|
| #3083 | CLOSED (HOLD_DATA_UNAVAILABLE) | Confirmed ~2.5 day MEXC klines retention; code infrastructure delivered |
| #3085 | MERGED | MEXC fetch/parse/CLI code in `candle_continuity.py` |
| #2974 | CLOSED (PRODUCT_COMPLETE_BLOCKED) | #3086 is a documented limitation, not a hard blocker |
| #2973 | CLOSED | Drift classification: #3028 venue_mismatch, `limited` certainty |
| #2980 | CLOSED (BLOCKED) | Fill-model fix blocked by signal semantics gap (venue-level) |
| #1900 | OPEN | ARVP north-star; #3086 tracked as data limitation |
| #3028 | (dataset) | venue_mismatch=true, Binance source |

---

## Non-goals

- Live-Go / Echtgeld-Go authorization
- Strategy code changes
- Docker/runtime changes in this slice
- DB mutations in this slice
- Data fetch with credentials in this slice
- Purchase or subscription decisions
- Synthetic or ersatz data creation
- Product-complete claim

---

## Safety Boundaries

| Boundary | Status |
|----------|--------|
| LR remains **NO-GO** | Confirmed |
| Product-complete is NOT Live-Go | Confirmed |
| Board stage `trade-capable` is NOT Live-Go | Confirmed |
| No Echtgeld-Go | Confirmed |
| No credentials in output | Confirmed |
| No purchase or subscription | Confirmed |
| No synthetic or ersatz data | Confirmed |
| No runtime/stack start/stop | Confirmed |
| No Docker/compose changes | Confirmed |
| No live exchange runtime | Confirmed |
| No productive DB writes | Confirmed |
| No API key usage | Confirmed |
| No secrets in output | Confirmed |
| Diff docs-only | Confirmed |

---

## References

- `docs/evidence/arvp_mexc_backfill_3083.md` — MEXC backfill attempt (HOLD_DATA_UNAVAILABLE)
- `docs/evidence/arvp_product_complete_review_2974.md` — Product-complete gate review
- `docs/evidence/arvp_drift_classification_2973_after_2971.md` — Multi-window drift classification
- `docs/evidence/arvp_price_policy_evaluation_3079.md` — Price policy evaluation
- `scripts/replay/candle_continuity.py` — Candle continuity and backfill CLI
- `services/ws/mexc_v3_client.py` — MEXC Spot V3 WebSocket client
- `services/candles/service.py` — 1m candle aggregator service
- `services/db_writer/db_writer.py` — DB Writer with candle persistence daemon
- `infrastructure/database/schema.sql` — DB schema (candles_1m, candle_backfill_imports)
- `core/replay/dataset_provider.py` — DB-backed dataset provider for replay
- `artifacts/candles/3028_window/dataset_spec.json` — #3028 dataset spec (venue_mismatch=true)
- PR #3085 — MEXC code infrastructure (0759cbc)
- PR #3088 — Product-complete review (5ed84bd)

---

## Restunsicherheiten

1. **DB may already contain MEXC candles for the #3028 timeframe** if the stack was running
   during that period. This cannot be verified in this slice (no DB access).
2. **Future-window capture requires the runtime stack** to be active — this is a separate
   operational decision with its own safety gates.
3. **External provider coverage for MEXC spot** is unverified. Option D is purely a research
   direction; no provider has been evaluated.
4. **Candle stream cursor persistence** has a known gap (db_writer.py:882): gap-safe cursor
   persistence is reserved for a follow-up task. Short stack restarts may lose candle entries
   still in the Redis stream.
5. **All evidence is repo+GitHub backed.** No DB/MCP/brain claims were used.

---

## Status

`DONE_MERGED_HOLD_EXECUTE_BLOCKER`

- Acquisition decision documented
- Persistent capture path (Option B) exists as primary route
- Public klines path (Option A) exists as fallback for windows within retention
- External provider research (Option D) is the only retroactive #3028 route
- Real same-venue MEXC dataset NOT YET DELIVERED
- #3086 remains OPEN until data is acquired or explicitly superseded
