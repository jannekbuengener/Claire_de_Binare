# MEXC Historical Source Probe — Issue #3990

**Date:** 2026-07-11  
**Issue:** [#3990](https://github.com/jannekbuengener/Claire_de_Binare/issues/3990)  
**Branch:** `feat/3990-mexc-historical-source-probe`  
**Verdict:** `MEXC_HISTORICAL_SOURCE_PROBE_BLOCKED`  
**LR:** NO-GO (unchanged)

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `cdb_context_briefing`, `gh issue view` (10 issues), `gh pr list`, `git fetch/status`, live `file-svc` + CloudFront + REST probes, `pytest tests/unit/market_data/` |
| `records_or_results` | Context briefing `065e96647cea7006` with `records_found=none`, `operator_trust_level=LOW`; live discovery JSON at `artifacts/market_data/normalized/mexc/spot/BTCUSDT/1m/2026-06/source_discovery.json` |
| `repo_crosscheck` | `scripts/replay/candle_continuity.py`, `core/replay/dataset_spec.py`, `core/replay/dataset_provider.py`, `artifacts/candles/mexc_strict_window_3091/dataset_spec.json`, `docs/evidence/arvp_mexc_backfill_3083.md` |
| `impact_on_plan` | Official historical archive cannot satisfy 1m probe month; REST retention cannot backfill June 2026; next gate is human decision on alternate official/non-archive path |
| `limitations` | No SurrealDB-backed brain records; no full-month 1m download performed because source lacks Min1 partition; legal redistribution remains `LEGAL_REVIEW_REQUIRED` |
| `context_brain_attempted` | `true` |
| `context_brain_used` | `false` |
| `context_available` | `false` |
| `repo_fallback_used` | `true` |
| `repo_fallback_reason` | `insufficient_evidence` |
| `context_tool_status` | `available` |
| `context_trust_level` | `none` |
| `records_found` | `none` |

---

## Scope

Bounded source-and-import probe for exactly one BTCUSDT spot month (`2026-06`), 1m granularity, using official MEXC surfaces only. No full-history import, no replay campaign, no regime enrichment over full history.

---

## Source Discovery

| Check | Status |
|-------|--------|
| Official portal | `proven` — https://www.mexc.com/market-data-download |
| Spot support | `proven` |
| BTCUSDT support | `proven` — symbol_id `2fb942154ef44a4ab2ef98c8afb6a4a7` |
| Listing API | `proven` — `GET /file-svc/history/download?filePath=...` |
| CDN download | `proven` — `https://d2s4an60yebwep.cloudfront.net/SPOT2/kline/...` |
| CSV format | `proven` — header `open_time,open,high,low,close,volume,amount,close_time` |
| Account / purchase | `proven` not required |
| Automation | `proven` via `tools/market_data/mexc_historical_probe.py` |
| 1m archive partition (`Min1`) | `blocked` — not present in monthly or daily listings |
| Finest archive interval | `proven` — `Min5` |
| June 2026 monthly archive | `proven` at `Min5` as `BTC_USDT-Min5-2026-06-01.csv` |
| REST `/api/v3/klines` 1m for June 2026 | `blocked` — empty retention window |
| Checksums | `not_proven` |
| Redistribution / commit rights | `not_proven` / `LEGAL_REVIEW_REQUIRED` |

### Verified monthly intervals (BTCUSDT)

`Day1`, `Hour4`, `Hour8`, `Min15`, `Min30`, `Min5`, `Min60`, `Month1`, `Week1`

### Verified daily intervals (BTCUSDT)

`Day1`, `Hour4`, `Hour8`, `Min15`, `Min30`, `Min5`, `Min60`

---

## Probe Month

| Field | Value |
|-------|-------|
| Requested | `2026-06-01T00:00:00Z` → `2026-06-30T23:59:00Z` |
| Expected 1m candles | `43200` |
| Official 1m archive file | **not found** |
| Nearest official monthly file | `BTC_USDT-Min5-2026-06-01.csv` (5m, not in probe scope) |

---

## Download Evidence

No raw 1m month was downloaded because the official archive exposes no `Min1` partition. Tool fail-closed before substitute-interval download.

Reference only (not used as probe deliverable):

| Field | Value |
|-------|-------|
| Sample URL | `https://d2s4an60yebwep.cloudfront.net/SPOT2/kline/2fb942154ef44a4ab2ef98c8afb6a4a7/monthly/Min5/BTC_USDT-Min5-2026-06-01.csv` |
| Sample size | `1786116` bytes |
| Sample schema | CSV, ms timestamps, no `trade_count` column |

---

## REST Crosscheck

| Sample point | Result |
|--------------|--------|
| Month start (`1780272000000`) | `RETENTION_UNAVAILABLE` |
| Month middle | `RETENTION_UNAVAILABLE` |
| Month end | `RETENTION_UNAVAILABLE` |

REST retention does not cover June 2026; this is not treated as an archive defect.

---

## ARVP Compatibility

| Check | Result |
|-------|--------|
| Normalized field contract | Defined in probe tool (`ts_ms`, OHLCV, provenance fields) |
| `FileBackedDatasetProvider` | Requires strict 1m cadence; compatible once valid 1m month exists |
| `strategy_replay_runner --dry-run` | Not executed on full month — no valid 1m month acquired |
| `regime_id` | Correctly classified as not enriched / blocked for full-history enrichment |

Existing ARVP datasets (`mexc_strict_window_3091`) remain WS-capture based, not historical-archive based.

---

## Regime Plan

| Item | Status |
|------|--------|
| Applicability of `assign_regime_to_mexc_3091.py` | `proven` technically applicable to normalized 1m JSONL once available |
| Warmup requirement | `240` candles (repo convention) |
| Derived fields | `regime_id` via offline ADX/ATR mirror |
| `primary_breakout_v1` readiness | Blocked until valid 1m month + regime enrichment |

---

## License / Data Retention

| Use | Assessment |
|-----|------------|
| Internal research | Allowed to document metadata/hashes in repo |
| Storage / normalization | Local artifacts only; no git commit of raw/normalized bulk |
| Redistribution / publication | `LEGAL_REVIEW_REQUIRED` |
| Git policy | `raw_data_git_policy=DO_NOT_COMMIT`, `normalized_data_git_policy=DO_NOT_COMMIT`, `metadata_and_hashes_git_policy=ALLOWED` |

---

## Quality Verdict

`SOURCE_UNAVAILABLE` for requested `1m` month via official historical download.

---

## Final Decision

`MEXC_HISTORICAL_SOURCE_PROBE_BLOCKED`

Reason: Official MEXC historical market data download does not publish BTCUSDT spot `1m` (`Min1`) archives. Finest proven archive interval is `Min5`. Public REST `1m` retention does not cover June 2026.

### Required next human gate

```text
HISTORICAL-DATA-GO #3990 MEXC BTCUSDT 1m full archive import
```

This gate is for choosing the next official/non-archive strategy (e.g. sustained WS/DB capture accumulation, paid external provider outside this slice, or acceptance of coarser official archive) — not live/LR/paper go.

---

## Delivered Code

- `tools/market_data/mexc_historical_probe.py`
- `tests/unit/market_data/test_mexc_historical_probe.py`
- Fixtures under `tests/fixtures/market_data/`

## Validation

```bash
pytest -q tests/unit/market_data/test_mexc_historical_probe.py
python -m tools.market_data.mexc_historical_probe --discover-only
```

---

## Non-goals

- Full history since 2023
- Binance / CoinAPI / Kaiko purchase
- Vacation replay campaign
- Regime enrichment over complete history
- Issue #3990 close — scope remains broader than this probe
