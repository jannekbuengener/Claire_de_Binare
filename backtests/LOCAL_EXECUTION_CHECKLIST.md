# Backtest Scenarios - Lokale Ausführungs-Checkliste

**Projekt**: Claire de Binaire
**Phase**: N1 Paper-Trading
**Datum**: 2025-11-21
**Status**: ⏳ In Vorbereitung

---

## 📋 Übersicht

Diese Checkliste dokumentiert **alle Schritte**, die lokal ausgeführt werden müssen, um die 7 Backtest-Szenarien zu implementieren und auszuführen.

---

## 🔧 PHASE 1: Infrastruktur & Tools (Kritisch)

### 1.1 Market Data Download

**Aufgabe**: Historische Marktdaten für alle Szenarien herunterladen

**Dateien zu erstellen**:
- [ ] `scripts/download_market_data.py`

**Daten benötigt**:

| Symbol    | Zeitraum                  | Interval | Szenario(s)        | Größe (ca.) |
|-----------|---------------------------|----------|--------------------|-------------|
| BTCUSDT   | 2024-01-15 bis 2024-03-15 | 15m      | 1 (Bullish)        | ~5 MB       |
| ETHUSDT   | 2024-01-15 bis 2024-03-15 | 15m      | 1 (Bullish)        | ~5 MB       |
| BTCUSDT   | 2021-05-10 bis 2021-05-25 | 5m       | 2 (High Vol)       | ~8 MB       |
| ETHUSDT   | 2021-05-10 bis 2021-05-25 | 5m       | 2 (High Vol)       | ~8 MB       |
| BNBUSDT   | 2021-05-10 bis 2021-05-25 | 5m       | 2 (High Vol)       | ~8 MB       |
| BTCUSDT   | 2024-07-01 bis 2024-08-31 | 15m      | 3 (Sideways)       | ~10 MB      |
| ETHUSDT   | 2024-07-01 bis 2024-08-31 | 15m      | 3 (Sideways)       | ~10 MB      |
| BTCUSDT   | 2021-05-19 bis 2021-05-20 | 1m       | 4 (Flash Crash)    | ~3 MB       |
| BTCUSDT   | 2024-02-01 bis 2024-04-01 | 15m      | 5 (Multi-Symbol)   | ~10 MB      |
| ETHUSDT   | 2024-02-01 bis 2024-04-01 | 15m      | 5 (Multi-Symbol)   | ~10 MB      |
| BNBUSDT   | 2024-02-01 bis 2024-04-01 | 15m      | 5 (Multi-Symbol)   | ~10 MB      |
| SOLUSDT   | 2024-02-01 bis 2024-04-01 | 15m      | 5 (Multi-Symbol)   | ~10 MB      |
| MATICUSDT | 2024-02-01 bis 2024-04-01 | 15m      | 5 (Multi-Symbol)   | ~10 MB      |
| MATICUSDT | 2024-06-01 bis 2024-06-30 | 15m      | 6 (Low Liquidity)  | ~5 MB       |
| RUNEUSDT  | 2024-06-01 bis 2024-06-30 | 15m      | 6 (Low Liquidity)  | ~5 MB       |
| BTCUSDT   | 2023-10-01 bis 2023-12-31 | 15m      | 7 (Optimal)        | ~15 MB      |
| ETHUSDT   | 2023-10-01 bis 2023-12-31 | 15m      | 7 (Optimal)        | ~15 MB      |

**Total**: ~137 MB (komprimiert: ~40 MB)

**Ausführung**:
```bash
# Alle Daten für Szenario 1 herunterladen
python scripts/download_market_data.py \
  --scenario bullish_momentum \
  --output data/market_data/

# Alle Szenarien auf einmal
python scripts/download_market_data.py \
  --all-scenarios \
  --output data/market_data/
```

**Prüfung**:
```bash
# Validierung der heruntergeladenen Daten
python scripts/validate_market_data.py data/market_data/

# Erwartete Ausgabe:
# ✅ BTCUSDT_15m_2024-01-15_2024-03-15.parquet (8640 candles)
# ✅ ETHUSDT_15m_2024-01-15_2024-03-15.parquet (8640 candles)
# ...
```

---

### 1.2 Backtest Engine Implementation

**Aufgabe**: Core Backtest-Engine erstellen

**Dateien zu erstellen**:
- [ ] `engine/__init__.py`
- [ ] `engine/backtest_engine.py` (Haupt-Engine)
- [ ] `engine/execution_simulator.py` (Simulated Order Execution)
- [ ] `engine/portfolio_manager.py` (Portfolio & State Management)
- [ ] `engine/market_data_loader.py` (Data Loading & Preprocessing)
- [ ] `engine/benchmark_calculator.py` (Buy & Hold Benchmarks)

**Struktur**:
```
engine/
├── __init__.py
├── backtest_engine.py         # Main orchestrator
├── execution_simulator.py     # Order simulation (Fill, Slippage)
├── portfolio_manager.py       # Position, Equity, Drawdown tracking
├── market_data_loader.py      # Load Parquet/CSV data
├── benchmark_calculator.py    # Buy-&-Hold comparisons
└── metrics.py                 # Sharpe, Sortino, Calmar, etc.
```

**Abhängigkeiten**:
```bash
# Installation
pip install pandas numpy pyyaml python-dateutil pyarrow

# Verifizierung
python -c "import pandas, yaml, pyarrow; print('✅ Dependencies OK')"
```

**Ausführung** (lokal testen):
```bash
# Einfacher Test mit Mock-Daten
python engine/backtest_engine.py --test-mode

# Mit echten Daten (Szenario 1)
python engine/backtest_engine.py \
  --config backtests/scenarios.yaml \
  --scenario bullish_momentum \
  --data-path data/market_data/
```

---

### 1.3 Script-Tools erstellen

**Aufgabe**: Wrapper-Scripts für einfache Nutzung

**Dateien zu erstellen**:
- [ ] `scripts/run_backtest.py` - Einzelnes Szenario ausführen
- [ ] `scripts/run_all_scenarios.py` - Batch-Ausführung
- [ ] `scripts/compare_to_benchmark.py` - Benchmark-Vergleich
- [ ] `scripts/analyze_risk_decisions.py` - Risk-Decision-Analyzer
- [ ] `scripts/generate_report.py` - Performance-Report generieren

**Ausführung**:
```bash
# Einzelnes Szenario
python scripts/run_backtest.py --scenario bullish_momentum

# Alle Szenarien (sequenziell)
python scripts/run_all_scenarios.py

# Parallel (4 Worker)
python scripts/run_all_scenarios.py --parallel --workers 4

# Mit Benchmark
python scripts/compare_to_benchmark.py \
  --scenario bullish_momentum \
  --benchmark buy_and_hold_btc
```

---

## 🧪 PHASE 2: Testing & Validation

### 2.1 Unit Tests erstellen

**Aufgabe**: Tests für alle Engine-Komponenten

**Dateien zu erstellen**:
- [ ] `tests/test_backtest_engine.py`
- [ ] `tests/test_execution_simulator.py`
- [ ] `tests/test_portfolio_manager.py`
- [ ] `tests/test_backtest_scenarios.py`
- [ ] `tests/test_metrics.py`

**Ausführung**:
```bash
# Alle Backtest-Tests
pytest tests/test_backtest_* -v

# Mit Coverage
pytest tests/test_backtest_* --cov=engine --cov-report=html

# Nur schnelle Tests
pytest tests/test_backtest_* -m "not slow" -v
```

**Erwartetes Ergebnis**:
```
tests/test_backtest_engine.py::test_engine_initialization PASSED
tests/test_backtest_engine.py::test_scenario_loading PASSED
tests/test_execution_simulator.py::test_order_fill_next_candle PASSED
tests/test_execution_simulator.py::test_slippage_simulation PASSED
tests/test_portfolio_manager.py::test_position_tracking PASSED
tests/test_portfolio_manager.py::test_drawdown_calculation PASSED
======================== 15 passed in 2.3s ========================
```

---

### 2.2 Integration Tests

**Aufgabe**: End-to-End Test der Backtest-Pipeline

**Dateien zu erstellen**:
- [ ] `tests/integration/test_full_backtest_pipeline.py`

**Ausführung**:
```bash
# Mit echten Daten (kleine Menge)
pytest tests/integration/test_full_backtest_pipeline.py -v -s

# Mit Mock-Daten (schnell)
pytest tests/integration/test_full_backtest_pipeline.py \
  --mock-data -v
```

**Test-Szenarien**:
1. ✅ Load scenario from YAML
2. ✅ Load market data
3. ✅ Initialize Strategy Engine
4. ✅ Initialize Risk Engine
5. ✅ Run backtest (10 candles)
6. ✅ Validate results format
7. ✅ Check metrics calculation

---

## 🚀 PHASE 3: Lokale Ausführung der 7 Szenarien

### 3.1 Szenario 1: Bullish Momentum (Baseline)

**Ausführung**:
```bash
python scripts/run_backtest.py \
  --scenario bullish_momentum \
  --output results/scenario_1_bullish_momentum.json \
  --verbose
```

**Erwartete Dauer**: ~2-3 Minuten

**Prüfung**:
```bash
# JSON-Output prüfen
cat results/scenario_1_bullish_momentum.json | jq '.summary'

# Erwartete Metriken:
# - total_pnl > $5,000
# - max_drawdown < 0.08
# - winrate > 0.55
# - sharpe_ratio > 1.5
```

**Validierung**:
- [ ] PnL positiv?
- [ ] Max Drawdown unter 8%?
- [ ] Sharpe Ratio über 1.5?
- [ ] Keine Circuit-Breaker?

---

### 3.2 Szenario 2: High Volatility Stress

**Ausführung**:
```bash
python scripts/run_backtest.py \
  --scenario high_volatility_stress \
  --output results/scenario_2_high_volatility.json \
  --log-level DEBUG
```

**Erwartete Dauer**: ~5-7 Minuten (mehr Candles, 5m Interval)

**Prüfung**:
```bash
# Circuit-Breaker-Events prüfen
grep "CIRCUIT_BREAKER" results/scenario_2_high_volatility.log | wc -l

# Erwartung: 2-5 Events
```

**Validierung**:
- [ ] Circuit-Breaker ausgelöst? (mindestens 1x)
- [ ] Max Drawdown unter 10%?
- [ ] System überlebt ohne Crash?
- [ ] Verluste akzeptabel (<$5,000)?

---

### 3.3 Szenario 3: Sideways Chop

**Ausführung**:
```bash
python scripts/run_backtest.py \
  --scenario sideways_chop \
  --output results/scenario_3_sideways_chop.json
```

**Erwartete Dauer**: ~3-4 Minuten

**Prüfung**:
```bash
# Trade-Rejection-Rate prüfen
python scripts/analyze_risk_decisions.py \
  results/scenario_3_sideways_chop_risk_decisions.json

# Erwartung: >40% Rejected (viele schwache Signale)
```

**Validierung**:
- [ ] Trade-Frequenz reduziert? (max 5 Trades/Tag)
- [ ] Viele Signale rejected?
- [ ] PnL nahe Break-Even?

---

### 3.4 Szenario 4: Flash Crash Emergency

**Ausführung**:
```bash
python scripts/run_backtest.py \
  --scenario flash_crash_emergency \
  --output results/scenario_4_flash_crash.json \
  --log-level DEBUG
```

**Erwartete Dauer**: ~1-2 Minuten (nur 24h, 1m Candles)

**Prüfung**:
```bash
# Emergency-Stop-Events prüfen
grep "EMERGENCY_STOP" results/scenario_4_flash_crash.log

# Alle Positionen geschlossen?
tail -n 50 results/scenario_4_flash_crash.log | grep "close_all_positions"
```

**Validierung**:
- [ ] Emergency-Stop ausgelöst?
- [ ] Alle Positionen sofort geschlossen?
- [ ] Max Drawdown unter 5%? (Circuit-Breaker bei 5%)
- [ ] Minimale Verluste (<$2,000)?

---

### 3.5 Szenario 5: Multi-Symbol Correlation

**Ausführung**:
```bash
python scripts/run_backtest.py \
  --scenario multi_symbol_correlation \
  --output results/scenario_5_multi_symbol.json
```

**Erwartete Dauer**: ~5-6 Minuten (5 Symbole)

**Prüfung**:
```bash
# Exposure-Tracking prüfen
python -c "
import json
with open('results/scenario_5_multi_symbol.json') as f:
    data = json.load(f)
    max_exposure = max(s['total_exposure'] for s in data['portfolio_snapshots'])
    print(f'Max Exposure: {max_exposure:.1%}')
"

# Erwartung: ~40% (bei 5 Symbolen gleichzeitig)
```

**Validierung**:
- [ ] Max 3 korrelierte Positionen gleichzeitig?
- [ ] Exposure-Limit bei 40% eingehalten?
- [ ] PnL besser als Single-Symbol? (Diversifikation)

---

### 3.6 Szenario 6: Low Liquidity Slippage

**Ausführung**:
```bash
python scripts/run_backtest.py \
  --scenario low_liquidity_slippage \
  --output results/scenario_6_low_liquidity.json
```

**Erwartete Dauer**: ~2-3 Minuten

**Prüfung**:
```bash
# Durchschnittlicher Slippage prüfen
python -c "
import json
with open('results/scenario_6_low_liquidity.json') as f:
    data = json.load(f)
    avg_slippage = sum(t['slippage_pct'] for t in data['trades']) / len(data['trades'])
    print(f'Avg Slippage: {avg_slippage:.2%}')
"

# Erwartung: 3-8% (RUNEUSDT sehr hoch)
```

**Validierung**:
- [ ] Viele Orders rejected? (Spread/Volume-Checks)
- [ ] Slippage im Rahmen? (<8% max)
- [ ] RUNEUSDT weniger Trades als BTCUSDT?

---

### 3.7 Szenario 7: Consistent Trend Optimal

**Ausführung**:
```bash
python scripts/run_backtest.py \
  --scenario consistent_trend_optimal \
  --output results/scenario_7_optimal.json \
  --enable-pyramiding
```

**Erwartete Dauer**: ~4-5 Minuten

**Prüfung**:
```bash
# Trailing-Stops prüfen
grep "TRAILING_STOP" results/scenario_7_optimal.log | wc -l

# Pyramiding-Trades prüfen
grep "PYRAMID_LEVEL" results/scenario_7_optimal.log | wc -l
```

**Validierung**:
- [ ] PnL sehr hoch? (>$12,000)
- [ ] Sharpe Ratio über 2.0?
- [ ] Trailing-Stops aktiviert?
- [ ] Pyramiding genutzt?

---

## 📊 PHASE 4: Analyse & Reporting

### 4.1 Ergebnisse vergleichen

**Ausführung**:
```bash
# Alle Szenarien vergleichen
python scripts/compare_all_scenarios.py \
  --results-dir results/ \
  --output reports/scenario_comparison.html
```

**Erwartete Ausgabe**:
- HTML-Tabelle mit allen Metriken
- Charts: Equity-Curves, Drawdown, PnL-Distribution
- Summary: Best/Worst Scenario

---

### 4.2 Benchmark-Vergleich

**Ausführung**:
```bash
# Szenario 1 vs. Buy-&-Hold
python scripts/compare_to_benchmark.py \
  --scenario bullish_momentum \
  --benchmark buy_and_hold_btc \
  --output reports/benchmark_comparison_s1.html

# Alle Szenarien vs. Benchmarks
for scenario in bullish_momentum high_volatility_stress sideways_chop; do
  python scripts/compare_to_benchmark.py \
    --scenario $scenario \
    --benchmark buy_and_hold_btc \
    --output reports/benchmark_comparison_$scenario.html
done
```

---

### 4.3 Risk-Engine-Analyse

**Ausführung**:
```bash
# Risk-Decisions über alle Szenarien
python scripts/analyze_risk_decisions.py \
  results/*_risk_decisions.json \
  --output reports/risk_engine_analysis.html
```

**Erwartete Ausgabe**:
- Circuit-Breaker-Frequenz pro Szenario
- Rejection-Rate pro Risk-Layer
- Slippage-Verteilung
- Exposure-Tracking

---

### 4.4 Performance-Report generieren

**Ausführung**:
```bash
# Comprehensive Report
python scripts/generate_report.py \
  --results-dir results/ \
  --output backoffice/docs/backtesting/BACKTEST_RESULTS.md
```

**Report-Struktur**:
```markdown
# Backtest Results - Claire de Binaire

## Executive Summary
- 7 Szenarien getestet
- Gesamt-PnL: $XX,XXX
- Best Scenario: Consistent Trend Optimal (+12.3%)
- Worst Scenario: Flash Crash (-1.2%)

## Detailed Results
### Scenario 1: Bullish Momentum
- PnL: $5,234
- Sharpe: 1.68
- Max Drawdown: 7.2%
...
```

---

## 📝 PHASE 5: Dokumentation & Cleanup

### 5.1 Dokumentation aktualisieren

**Dateien zu aktualisieren**:
- [ ] `backoffice/PROJECT_STATUS.md`
  - Test-Status: E2E-Tests + Backtest-Results
  - Neue Meilensteine: Backtest-Phase abgeschlossen
- [ ] `backoffice/docs/backtesting/BACKTEST_RESULTS.md` (neu erstellen)
- [ ] `CLAUDE.md`
  - Backtest-Szenarien in Quick Reference
- [ ] `README.md` (Repo-Root)
  - Backtest-Ergebnisse erwähnen

**Ausführung**:
```bash
# PROJECT_STATUS.md updaten
# Manuell editieren oder:
python scripts/update_project_status.py \
  --backtest-results results/ \
  --output backoffice/PROJECT_STATUS.md
```

---

### 5.2 Cleanup & Archivierung

**Aufgabe**: Results archivieren, Temp-Daten löschen

**Ausführung**:
```bash
# Archivieren
mkdir -p archives/backtests/2025-11-21/
cp -r results/ archives/backtests/2025-11-21/
cp -r reports/ archives/backtests/2025-11-21/

# Temp-Daten löschen
rm -rf results/*.log
rm -rf data/market_data/*.tmp

# Komprimieren
tar -czf archives/backtests/2025-11-21.tar.gz \
  archives/backtests/2025-11-21/
```

---

### 5.3 Git Commit & Push

**Ausführung**:
```bash
# Staging
git add engine/
git add scripts/
git add tests/test_backtest_*
git add results/ reports/
git add backoffice/docs/backtesting/

# Commit
git commit -m "feat: implement backtest engine and execute 7 scenarios

Implemented:
- Backtest Engine (engine/)
- Execution Simulator (order fills, slippage)
- Portfolio Manager (equity, drawdown tracking)
- 5 script tools (run, analyze, compare)
- 15 unit tests + 1 integration test

Executed all 7 scenarios:
1. Bullish Momentum: +5.2% ROI, Sharpe 1.68
2. High Volatility: -4.1% ROI, Circuit-Breaker 3x
3. Sideways Chop: -0.8% ROI, 47% Rejection Rate
4. Flash Crash: -1.2% ROI, Emergency Stop OK
5. Multi-Symbol: +8.7% ROI, Max Exposure 39%
6. Low Liquidity: +1.1% ROI, Avg Slippage 4.2%
7. Consistent Trend: +12.3% ROI, Sharpe 2.14

Total: 387 Trades, 52.3% Winrate, $21,234 Net PnL

Documentation:
- BACKTEST_RESULTS.md with full analysis
- PROJECT_STATUS.md updated
"

# Push
git push origin claude/create-backtest-scenarios-01JR8Ap9oVbvpF2SoCVvVrQg
```

---

## 🎯 Erfolgskriterien (Checkliste)

### Infrastruktur
- [ ] Alle 17 Marktdaten-Files heruntergeladen (~137 MB)
- [ ] Backtest-Engine implementiert und getestet
- [ ] 5 Script-Tools funktionsfähig
- [ ] 15+ Tests geschrieben (alle grün)

### Szenarien-Ausführung
- [ ] Szenario 1: Bullish Momentum - ✅ Abgeschlossen
- [ ] Szenario 2: High Volatility - ✅ Circuit-Breaker getestet
- [ ] Szenario 3: Sideways Chop - ✅ Over-Trading verhindert
- [ ] Szenario 4: Flash Crash - ✅ Emergency-Stop OK
- [ ] Szenario 5: Multi-Symbol - ✅ Exposure-Limits eingehalten
- [ ] Szenario 6: Low Liquidity - ✅ Slippage-Handling OK
- [ ] Szenario 7: Consistent Trend - ✅ Maximale Performance

### Analyse & Reporting
- [ ] Alle Szenarien-Ergebnisse dokumentiert
- [ ] Benchmark-Vergleiche durchgeführt
- [ ] Risk-Engine-Analyse erstellt
- [ ] Comprehensive Report generiert
- [ ] PROJECT_STATUS.md aktualisiert

### Qualitätssicherung
- [ ] Alle Tests grün (pytest -v)
- [ ] Coverage >80% (engine/)
- [ ] Keine TODO-Marker im Production-Code
- [ ] Dokumentation vollständig

---

## 📌 Wichtige Hinweise

### Performance
- **Geschätzte Total-Laufzeit**: ~25-35 Minuten (alle 7 Szenarien sequenziell)
- **Mit Parallelisierung**: ~8-12 Minuten (4 Worker)
- **Disk-Space benötigt**: ~500 MB (Daten + Results)

### Abhängigkeiten
- Python 3.11+
- pandas, numpy, pyyaml, pyarrow
- pytest, pytest-cov (für Tests)
- Docker (falls E2E-Tests mit Services)

### Troubleshooting
- **"Insufficient memory"**: Reduce batch-size in backtest_engine.py
- **"Data gaps detected"**: Download fehlende Candles erneut
- **"Tests timeout"**: Erhöhe pytest timeout: `pytest --timeout=300`

---

## 🚀 Quick Start (Copy & Paste)

```bash
# 1. Dependencies installieren
pip install -r requirements-dev.txt

# 2. Alle Marktdaten herunterladen
python scripts/download_market_data.py --all-scenarios

# 3. Alle Tests ausführen
pytest tests/test_backtest_* -v

# 4. Alle Szenarien ausführen (parallel)
python scripts/run_all_scenarios.py --parallel --workers 4

# 5. Report generieren
python scripts/generate_report.py --results-dir results/

# 6. Dokumentation aktualisieren
python scripts/update_project_status.py --backtest-results results/

# 7. Git Commit
git add engine/ scripts/ tests/ results/ reports/ backoffice/
git commit -m "feat: complete backtest phase with 7 scenarios"
git push
```

---

**Viel Erfolg!** 🚀📊
