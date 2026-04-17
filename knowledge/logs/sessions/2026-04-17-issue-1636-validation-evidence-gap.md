# Session Log: 2026-04-17 — Issue #1636 Validation Evidence Gap

**Date:** 2026-04-17  
**Issue:** [#1636](https://github.com/jannekbuengener/Claire_de_Binare/issues/1636)  
**Topic:** primary_breakout_v1 — Evidence- und Evaluationslücken nach erstem deterministischen Offline-Backtest  
**main @ session start:** `8f7a8ebbb94c63f95b9df1ea4fb24a0ba620da5a`  
**Repo delta:** none (no new PRs, no code changes — local-only artifact)

---

## Befund

Zwei Tracks in #1636 separat untersucht.

### Track 1 — Period-Window-Semantik: ERLEDIGT

PR #1707 (`d456770e`, gemerged 2026-04-16) hat den Fix vollständig umgesetzt:
- Runner (`strategy_backtest_runner.py`) gibt alle 4 `dataset_summary`-Felder aus:
  - `requested_period_start_ts_ms` / `requested_period_end_ts_ms`
  - `period_start_ts_ms` / `period_end_ts_ms`
- Schema (`strategy_validation_report_v1.schema.json`) validiert alle 4 Felder
- Test `test_primary_breakout_backtest_runner_period_window_semantics` prüft den Offset
- 8/8 Unit-Tests pass

### Track 2 — Zweiter deterministischer Run: TEILWEISE ERFÜLLT, Blocker offen

Re-Run des originalen 420-Candle-Datensatzes mit aktuellem Runner:

| Feld | Wert |
|---|---|
| `run_id` | `bt-1ab5a47c6449f860` |
| `code_commit` | `8f7a8ebbb94c63f95b9df1ea4fb24a0ba620da5a` |
| `requested_period_start_ts_ms` | `1700000000000` |
| `requested_period_end_ts_ms` | `1700025140000` |
| `period_start_ts_ms` | `1700014400000` |
| `period_end_ts_ms` | `1700025140000` |
| Warmup-Offset | `14.400.000 ms = 240 Candles` |
| `candles_total` | `420` |
| `dataset_sha256` | `9e2448bb9d3a0a5a45bd64e0696c11b92322905a1b2aff67f304480fe65bc43f` |
| Schema-Validation | PASS |
| Determinismus | PASS |
| Gate | FAIL (1 Trade; `min_closed_trades_total`, `min_profit_factor`, `min_expectancy_r` verletzt) |

Artefakte: `artifacts/backtests/primary_breakout_v1/20260417-121042/` (local-only)

### Warum kein synthetisches all-winner Dataset als Closure-Evidence

Synthetic 25-Cycle-Datensatz mit 100% Win-Rate und `max_drawdown_r=0` wurde entworfen und
arithmetisch verifiziert (rubber-duck: Trigger-Arithmetik korrekt). Aber:
- Kein belastbarer Evaluationsanker: `win_rate=1.0`, `profit_factor=∞` ist kein sinnvoller Baseline-Wert
- Für #1636-Closure-Evidence nicht akzeptabel (rubber-duck-Urteil: fake-fix-adjacent)

---

## Aktiver Blocker für Track 2

Kein realer BTCUSDT-1m-Datensatz lokal verfügbar. 420 synthetische Candles → immer
nur 1 Trade, unabhängig vom Code-Stand.

**Nächster konkreter Trigger:** Realen BTCUSDT-1m-Datensatz bereitstellen
(≥5.000 Candles, ≥20 erwartbare Breakout-Signale) → Runner ausführen → Gate auswerten.

---

## Artefakte / Dateien

- `artifacts/backtests/primary_breakout_v1/20260417-121042/results.json` — schema-valid, local-only
- `CURRENT_STATUS.md` — Session-Ledger-Eintrag ergänzt
- Issue-Kommentar: https://github.com/jannekbuengener/Claire_de_Binare/issues/1636#issuecomment-4267860877
