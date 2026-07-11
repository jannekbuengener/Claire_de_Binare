# Binance Historical Source Probe — Issue #3990

**Date:** 2026-07-11  
**Issue:** [#3990](https://github.com/jannekbuengener/Claire_de_Binare/issues/3990)  
**Branch:** `feat/3990-binance-historical-source-probe`  
**Verdict:** `BINANCE_HISTORICAL_SOURCE_PROBE_PASS`  
**LR:** NO-GO (unchanged)

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `context_tool_status` | `available` |
| `context_trust_level` | `none` |
| `records_found` | `none` |
| `tools_or_queries` | `cdb_context_briefing`, `gh issue/pr view`, live Binance Data Vision + REST probes, `pytest`, `strategy_replay_runner` |
| `records_or_results` | briefing `a10b2421df1d498c` with `records_found=none`; live probe JSON at `artifacts/.../probe_result.json` |
| `repo_crosscheck` | `tools/market_data/mexc_historical_probe.py`, `core/replay/dataset_spec.py`, `assign_regime_to_mexc_3091.py`, PR #3992 MEXC BLOCKED verdict |
| `impact_on_plan` | MEXC 1m blocked → Binance official monthly archive viable for cross-venue research corpus |
| `limitations` | No SurrealDB records; Binance evidence is not MEXC same-venue execution evidence |

---

## Scope

Exactly one full calendar month **BTCUSDT Spot 1m** from official Binance public data. Cross-venue research probe only — no full-history import, no replay campaign, no raw/normalized bulk in Git.

**Central message:**

```text
MEXC official 1m archive is unavailable.
Binance official 1m history is used as the broad historical
research corpus. MEXC data remains the later same-venue
confirmation layer.
```

---

## Source Discovery

| Check | Status |
|-------|--------|
| Official portal | `proven` — https://www.binance.com/en/landing/data |
| Official repository | `proven` — https://github.com/binance/binance-public-data |
| Data Vision host | `proven` — https://data.binance.vision |
| Spot BTCUSDT 1m monthly | `proven` — `BTCUSDT-1m-2026-06.zip` |
| Official `.CHECKSUM` | `proven` |
| Account / purchase | `not_required` |
| Download path used | **monthly** (not daily) |

---

## Probe Month

| Field | Value |
|-------|-------|
| Requested | `2026-06-01T00:00:00Z` → `2026-06-30T23:59:00Z` |
| Expected candles | `43200` |
| Actual candles | `43200` |
| Missing minutes | `0` |
| Longest contiguous island | `43200` |
| Duplicates | `0` identical / `0` conflicting |

---

## Download Evidence

| Field | Value |
|-------|-------|
| Source URL | `https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2026-06.zip` |
| Original filename | `BTCUSDT-1m-2026-06.zip` |
| File size | `2092027` bytes |
| Official checksum SHA-256 | `c8e1d5e70b766dd2312fc9cd7085785bb25708e27e75c21a5a5aaba61a6d07f5` |
| Local SHA-256 | `c8e1d5e70b766dd2312fc9cd7085785bb25708e27e75c21a5a5aaba61a6d07f5` |
| Checksum verified | `true` |
| Archive format | ZIP → `BTCUSDT-1m-2026-06.csv` |
| Downloaded at UTC | `2026-07-11T11:59:23Z` |
| Repo source SHA | `2e2fc4db` (at probe time) |

---

## Schema

| Field | Value |
|-------|-------|
| Header present | `false` |
| Columns | `open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore` |
| Open-time unit | `microseconds` |
| Close-time unit | `microseconds` |
| Canonical output | `ts_ms` (UTC milliseconds) |
| Normalized hash | `3d135af4952023228715000b8bf1ed69b52243eb861d1409b41364a210964341` |

---

## Quality Verdict

`STRICT_COMPLETE`

- Monotonic timestamps: yes  
- OHLC invariants: pass  
- Future rows: 0  
- Second parser hash: stable  

---

## REST Crosscheck

| Sample | Result |
|--------|--------|
| Month start (`1780272000000`) | all fields `exact_match` (5 candles) |
| Month middle (`1781568000000`) | all fields `exact_match` (5 candles) |
| Month end (`1782863940000`) | last archive candle `exact_match`; REST continues past archive end (expected) |

REST used for crosscheck only — not as second dataset.

---

## ARVP Compatibility

| Check | Result |
|-------|--------|
| `FileBackedDatasetProvider` | PASS — 43200 candles loaded |
| `strategy_replay_runner --dry-run` | PASS |
| Venue | `binance` (`venue_match=false`) |
| Evidence class | `historical_cross_venue_research` |
| `ranking_ready` | `false` |

---

## Regime Enrichment

| Item | Value |
|------|-------|
| Method | offline ADX/ATR (`tools/market_data/assign_regime_offline.py`) |
| Warmup | 240 candles considered |
| Status | PASS |
| Distribution | TREND: 16, HIGH_VOL_CHAOTIC: 43184 |
| Deterministic | yes (second run identical) |
| Output | `artifacts/market_data/enriched/binance/spot/BTCUSDT/1m/2026-06/` |

---

## Replay Probe

Campaign root: `artifacts/replay_reports/binance_probe_3990/2026-06/`

| Strategy | Scenarios | Exit | Group ID |
|----------|-----------|------|----------|
| `donchian_breakout_v1` | baseline, pessimistic_execution, feed_gap | 0 | `arvp_binance_probe_3990_donchian_breakout_v1_202606` |
| `breakout_trend_filter_v1` | baseline, pessimistic_execution, feed_gap | 0 | `arvp_binance_probe_3990_breakout_trend_filter_v1_202606` |

`primary_breakout_v1` not executed in this slice (Pack-A strategies sufficient; cross-venue lab scope).

---

## Cross-Venue Boundaries

| Allowed | Not allowed |
|---------|-------------|
| `controlled_lab_evidence` | `mexc_same_venue` |
| `historical_cross_venue_research` | `natural_paper_evidence` |
| `venue=binance` | `live_evidence` |
| `target_validation_venue=mexc` | `promotion_ready` |
| | `ranking_ready=true` |

---

## License / Data Retention

| Policy | Value |
|--------|-------|
| `raw_data_git_policy` | `DO_NOT_COMMIT` |
| `normalized_data_git_policy` | `DO_NOT_COMMIT` |
| `metadata_and_hashes_git_policy` | `ALLOWED` |
| Redistribution | `LEGAL_REVIEW_REQUIRED` |

---

## Final Decision

`BINANCE_HISTORICAL_SOURCE_PROBE_PASS`

### Required next human gate

```text
HISTORICAL-DATA-GO #3990 Binance BTCUSDT 1m full archive import
```

Do **not** start full archive import without this gate. LR remains NO-GO.

---

## Delivered Code

- `tools/market_data/historical_common.py`
- `tools/market_data/assign_regime_offline.py`
- `tools/market_data/binance_historical_probe.py`
- `tests/unit/market_data/test_binance_historical_probe.py`
- Fixtures under `tests/fixtures/market_data/`

## Validation

```bash
pytest -q tests/unit/market_data/test_binance_historical_probe.py
python -m tools.market_data.binance_historical_probe --month 2026-06
python -m services.validation.strategy_replay_runner --dry-run --input-candles artifacts/market_data/normalized/binance/spot/BTCUSDT/1m/2026-06/candles.jsonl --strategy-id donchian_breakout_v1 --adapter-id donchian_breakout_runner_v1
```

---

## Non-goals

- Full Binance history since 2017
- Full MEXC history
- Window bank / vacation queue expansion
- Issue #3990 close (broader dataset-bank scope remains)
