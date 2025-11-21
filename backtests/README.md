# Backtest Scenarios - Claire de Binaire

**Version**: 1.0.0
**Datum**: 2025-11-21
**Status**: N1 Paper-Test Ready

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Szenarien im Detail](#szenarien-im-detail)
3. [Verwendung](#verwendung)
4. [Metriken & Interpretation](#metriken--interpretation)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Übersicht

Diese Sammlung enthält **7 realistische Backtest-Szenarien** für die Claire de Binaire Trading-Engine. Jedes Szenario testet spezifische Aspekte der **Strategy-, Risk- und Execution-Layer** unter unterschiedlichen Marktbedingungen.

### Zielsetzung

Die Szenarien dienen dazu:

1. **Strategie-Validierung**: Funktioniert die Momentum-Strategie unter verschiedenen Marktphasen?
2. **Risk-Engine-Testing**: Greifen alle 6 Risk-Schichten korrekt?
3. **Parameter-Tuning**: Optimale Risk-Parameter für verschiedene Volatilitäten finden
4. **Performance-Benchmarking**: Vergleich mit Buy-&-Hold und Equal-Weight-Portfolio
5. **Edge-Case-Detection**: Identifikation von Schwachstellen und Verbesserungspotenzialen

### Szenario-Matrix

| # | Szenario                    | Marktphase      | Volatilität | Hauptfokus                  | Erwartetes Ergebnis |
|---|-----------------------------|--------------------|-------------|------------------------------|---------------------|
| 1 | Bullish Momentum            | Aufwärtstrend      | Moderat     | Baseline-Performance         | Positiv (+5-10%)    |
| 2 | High Volatility Stress      | Crash/Korrektur    | Extrem      | Circuit-Breaker, Drawdown    | Kapitalerhalt       |
| 3 | Sideways Chop               | Range-Bound        | Niedrig     | Over-Trading-Protection      | Break-Even          |
| 4 | Flash Crash Emergency       | Crash (<24h)       | Extrem      | Emergency-Stop-Mechanismen   | Minimale Verluste   |
| 5 | Multi-Symbol Correlation    | Bull-Market        | Moderat     | Portfolio-Exposure-Limits    | Positiv (Diversifiziert) |
| 6 | Low Liquidity Slippage      | Off-Peak/Small-Cap | Moderat     | Slippage-Toleranzen          | Moderate Performance |
| 7 | Consistent Trend Optimal    | Starker Trend      | Moderat     | Maximale Performance         | Sehr Positiv (+12%+) |

---

## Szenarien im Detail

### 🟢 1. Bullish Momentum (Baseline)

**Zweck**: Standard-Szenario zur Validierung der Basis-Funktionalität.

**Marktphase**:
- Beginn des Bull-Runs 2024 (Januar-März)
- BTC: $42k → $73k (+74%)
- ETH: $2.2k → $4k (+82%)

**Warum dieses Szenario?**
- Optimale Bedingungen für Momentum-Strategien
- Moderate Volatilität (keine extremen Moves)
- Hohe Liquidität (enge Spreads, niedriger Slippage)
- Dient als **Baseline** für Vergleiche

**Erwartete Risk-Engine-Events**:
- ✅ Keine Circuit-Breaker-Auslösungen
- ✅ Normale Position-Sizing
- ✅ Gelegentliche Exposure-Limits (bei >30%)
- ⚠️ Stop-Loss-Exits bei kleinen Pullbacks

**Target-Metriken**:
```yaml
Min PnL:         $5,000  (5% ROI)
Max Drawdown:    8%
Winrate:         >55%
Sharpe Ratio:    >1.5
Profit Factor:   >1.8
```

**Verwendung**:
```bash
python scripts/run_backtest.py --scenario bullish_momentum
```

---

### 🔴 2. High Volatility Stress (Crisis Test)

**Zweck**: Stress-Test der Risk-Engine unter extremen Bedingungen.

**Marktphase**:
- Mai 2021 Crash (Mai 10-25)
- BTC: $58k → $30k (-48% in 2 Wochen!)
- ETH: $4.1k → $1.9k (-54%)

**Warum dieses Szenario?**
- Testet **Circuit-Breaker** und **Daily-Drawdown-Limits**
- Simuliert Flash-Crashes und extreme Volatilität
- Validiert Emergency-Stop-Mechanismen
- Prüft Slippage-Handling bei niedriger Liquidität

**Erwartete Risk-Engine-Events**:
- 🔴 **Circuit-Breaker**: Mehrfach ausgelöst (Drawdown >7%)
- 🔴 **Daily Drawdown**: Limit erreicht an 3-5 Tagen
- ⚠️ **Exposure-Reduzierung**: Automatisch auf 20%
- ⚠️ **Slippage-Alerts**: Bei Crash-Candles >5%

**Target-Metriken**:
```yaml
Min PnL:         -$5,000  (Verluste OK - Survival zählt!)
Max Drawdown:    10% (CRITICAL: Circuit-Breaker muss greifen)
Winrate:         >40% (niedrig = OK)
Sharpe Ratio:    >0.5 (negativ erwartet)
```

**⚠️ WICHTIG**: In diesem Szenario ist **Kapitalerhalt** das Ziel, nicht Profit!

**Verwendung**:
```bash
python scripts/run_backtest.py --scenario high_volatility_stress --verbose
```

---

### 🟡 3. Sideways Chop (Whipsaw Test)

**Zweck**: Test von Over-Trading-Protection und Signal-Quality-Filtern.

**Marktphase**:
- Sommer 2024 Konsolidierung (Juli-August)
- BTC: $60k-$70k (Range-Bound, viele False-Breakouts)
- ETH: $3k-$3.5k (ähnlich)

**Warum dieses Szenario?**
- Momentum-Strategien leiden in Sideways-Märkten
- Viele **False-Breakouts** führen zu Verlusten
- Testet **Frequenzbegrenzung** (max 5 Trades/Tag)
- Validiert **Signal-Strength-Filter** (min 0.70)

**Erwartete Risk-Engine-Events**:
- ⚠️ **Trade-Rejection**: Viele Signale rejected (zu schwach)
- ⚠️ **Frequenz-Limit**: Max-Trades-per-Day erreicht
- ✅ **Position-Sizing**: Reduziert auf 6% (vorsichtig)

**Target-Metriken**:
```yaml
Min PnL:         -$2,000  (Break-Even = Erfolg)
Max Drawdown:    6%
Winrate:         >45% (schwierig in Chop)
Sharpe Ratio:    >0.3 (nahe 0)
```

**💡 Lernziel**: Verstehen, wann die Strategie **NICHT** traden sollte.

**Verwendung**:
```bash
python scripts/run_backtest.py --scenario sideways_chop
```

---

### 🚨 4. Flash Crash Emergency (Extreme Event)

**Zweck**: Test der Emergency-Stop-Logik bei Flash-Crashes.

**Marktphase**:
- 19. Mai 2021 (exakter Flash-Crash-Tag)
- BTC: $43k → $30k → $40k (in 4 Stunden!)
- Liquidationen: >$8 Milliarden

**Warum dieses Szenario?**
- **Worst-Case-Szenario** für alle Trading-Systeme
- Testet **Circuit-Breaker** bei >20% Move in <1h
- Validiert **Emergency-Close-All-Positions** Logik
- Prüft Slippage-Handling bei Order-Book-Kollaps

**Erwartete Risk-Engine-Events**:
- 🔴 **EMERGENCY STOP**: Alle Positionen sofort geschlossen
- 🔴 **Trading Halted**: System pausiert Trading komplett
- 🔴 **Slippage >10%**: Fills deutlich schlechter als erwartet

**Target-Metriken**:
```yaml
Min PnL:         -$2,000  (Minimale Verluste = ERFOLG!)
Max Drawdown:    5% (Circuit-Breaker bei 5%)
Winrate:         30% (egal - Survival zählt)
Max Trades:      10 (sehr wenige - sofortiger Stop)
```

**🎯 Erfolgs-Kriterium**: System überlebt ohne katastrophale Verluste.

**Verwendung**:
```bash
python scripts/run_backtest.py --scenario flash_crash_emergency --log-level DEBUG
```

---

### 🟢 5. Multi-Symbol Correlation (Portfolio Test)

**Zweck**: Portfolio-Risk-Management mit 5 korrelierten Assets.

**Marktphase**:
- Q1 2024 Altcoin-Rally (Februar-April)
- BTC, ETH, BNB, SOL, MATIC alle bullish
- Hohe Korrelation (>0.7 zwischen allen Pairs)

**Warum dieses Szenario?**
- Testet **Portfolio-Exposure-Limits** (max 40%)
- Validiert **Correlation-Checks** (max 3 korrelierte Positionen)
- Prüft **Position-Sizing** bei Multi-Symbol-Portfolios

**Erwartete Risk-Engine-Events**:
- ⚠️ **Exposure-Limit**: Erreicht bei 40% (5 Positionen gleichzeitig)
- ⚠️ **Correlation-Check**: Blockt 4. korreliertes Asset
- ✅ **Position-Sizing**: 8% pro Symbol (statt 10%)

**Target-Metriken**:
```yaml
Min PnL:         $8,000  (Diversifikation → höherer Gewinn)
Max Drawdown:    10%
Winrate:         >52%
Sharpe Ratio:    >1.3
Profit Factor:   >1.6
```

**💡 Lernziel**: Portfolio-Diversifikation vs. Over-Exposure-Risiko.

**Verwendung**:
```bash
python scripts/run_backtest.py --scenario multi_symbol_correlation
```

---

### 🟡 6. Low Liquidity Slippage (Execution Test)

**Zweck**: Test von Slippage-Toleranzen und Order-Rejection bei niedriger Liquidität.

**Marktphase**:
- Sommer 2024 (Juni)
- BTCUSDT: Hohe Liquidität (Referenz)
- MATICUSDT: Medium Liquidity
- RUNEUSDT: Low Liquidity (Small-Cap)

**Warum dieses Szenario?**
- Realistische Bedingungen für Small-Cap-Altcoins
- Testet **Slippage-Checks** (max 8% Slippage)
- Validiert **Spread-Checks** (max 5% Bid-Ask)
- Prüft **Volume-Checks** (min $100k Volume/Candle)

**Erwartete Risk-Engine-Events**:
- 🔴 **Order-Rejection**: Viele Orders rejected (zu hoher Spread)
- ⚠️ **Slippage-Alerts**: Fills 3-8% schlechter als erwartet
- ⚠️ **Volume-Check**: RUNEUSDT oft unter Threshold

**Target-Metriken**:
```yaml
Min PnL:         $1,000  (niedrigere Erwartung)
Max Drawdown:    8%
Winrate:         >48%
Sharpe Ratio:    >0.8
Max Trades:      80 (viele rejected)
```

**💡 Lernziel**: Wann sollte die Strategie auf Low-Liquidity-Assets verzichten?

**Verwendung**:
```bash
python scripts/run_backtest.py --scenario low_liquidity_slippage
```

---

### 🟢 7. Consistent Trend Optimal (Best Case)

**Zweck**: Maximale Performance unter idealen Bedingungen.

**Marktphase**:
- Q4 2023 Bull-Run (Oktober-Dezember)
- BTC: $27k → $44k (+63%)
- ETH: $1.6k → $2.4k (+50%)
- Starker, konsistenter Trend ohne große Pullbacks

**Warum dieses Szenario?**
- **Best-Case-Szenario** für Momentum-Strategien
- Validiert maximale Performance-Metriken
- Dient als **Referenz** für Parameter-Optimierung
- Testet **Trailing-Stops** und **Pyramiding**

**Erwartete Risk-Engine-Events**:
- ✅ Keine Circuit-Breaker
- ✅ Trailing-Stops aktiviert (Gewinne laufen lassen)
- ✅ Pyramiding: Nachlegen in bestehende Positionen (max 2x)

**Target-Metriken**:
```yaml
Min PnL:         $12,000  (12% ROI - HOCH!)
Max Drawdown:    8%
Winrate:         >60%
Sharpe Ratio:    >2.0 (exzellent)
Profit Factor:   >2.5
```

**🎯 Ziel**: Maximale Performance-Metriken als Benchmark.

**Verwendung**:
```bash
python scripts/run_backtest.py --scenario consistent_trend_optimal --enable-pyramiding
```

---

## Verwendung

### Einzelnes Szenario ausführen

```bash
# Standard-Ausführung
python scripts/run_backtest.py --scenario bullish_momentum

# Mit Verbose-Logging
python scripts/run_backtest.py --scenario high_volatility_stress --verbose

# Mit Custom Output-Path
python scripts/run_backtest.py --scenario sideways_chop --output results/chop_test_1.json
```

### Alle Szenarien nacheinander

```bash
# Sequenziell
python scripts/run_all_scenarios.py

# Parallel (4 Worker)
python scripts/run_all_scenarios.py --parallel --workers 4
```

### Benchmark-Vergleich

```bash
# Szenario vs. Buy-&-Hold
python scripts/compare_to_benchmark.py \
  --scenario bullish_momentum \
  --benchmark buy_and_hold_btc
```

### Parameter-Override

```bash
# Custom Risk-Parameter für Test
python scripts/run_backtest.py \
  --scenario bullish_momentum \
  --max-position-pct 0.15 \
  --max-exposure-pct 0.40
```

---

## Metriken & Interpretation

### Performance-Metriken

#### 1. **Total PnL** (Profit & Loss)
- **Definition**: Gesamtgewinn/-verlust in USD
- **Interpretation**:
  - Positiv: Strategie profitabel
  - Negativ: Strategie verliert Geld
  - Vergleich mit Buy-&-Hold wichtig!

#### 2. **ROI** (Return on Investment)
- **Formel**: `(Final Equity - Initial Equity) / Initial Equity`
- **Interpretation**:
  - >10% annualisiert: Sehr gut
  - 5-10%: Gut
  - <5%: Verbesserungsbedarf

#### 3. **Max Drawdown**
- **Definition**: Größter Rückgang vom Peak zur Talsohle
- **Interpretation**:
  - <5%: Exzellent
  - 5-10%: Gut (typisch)
  - >15%: Kritisch (Risk-Engine überprüfen!)

#### 4. **Sharpe Ratio**
- **Formel**: `(Mean Return - Risk-Free Rate) / Std Dev of Returns`
- **Interpretation**:
  - >2.0: Exzellent
  - 1.0-2.0: Sehr gut
  - 0.5-1.0: Akzeptabel
  - <0.5: Verbesserungsbedarf

#### 5. **Profit Factor**
- **Formel**: `Gross Profit / Gross Loss`
- **Interpretation**:
  - >2.0: Sehr gut
  - 1.5-2.0: Gut
  - 1.0-1.5: Akzeptabel
  - <1.0: Verluste!

#### 6. **Winrate**
- **Definition**: Anzahl profitable Trades / Total Trades
- **Interpretation**:
  - >60%: Exzellent
  - 50-60%: Sehr gut
  - 40-50%: Akzeptabel (wenn Profit Factor >1.5)
  - <40%: Kritisch

### Risk-Metriken

#### 1. **Circuit-Breaker-Events**
- **Anzahl**: Wie oft wurde Circuit-Breaker ausgelöst?
- **Interpretation**:
  - 0: Optimal (normale Bedingungen)
  - 1-2: OK (High-Volatility-Szenarien)
  - >3: Kritisch (Risk-Parameter anpassen?)

#### 2. **Daily-Drawdown-Violations**
- **Anzahl**: Wie oft wurde Daily-Drawdown-Limit erreicht?
- **Interpretation**: Sollte minimal sein (<3x in Backtests)

#### 3. **Exposure-Limit-Hits**
- **Anzahl**: Wie oft wurde Max-Exposure erreicht?
- **Interpretation**:
  - Häufig: Strategie zu aggressiv
  - Nie: Zu konservativ?

#### 4. **Slippage-Average**
- **Durchschnitt**: Durchschnittlicher Slippage pro Trade
- **Interpretation**:
  - <1%: Exzellent
  - 1-3%: Normal
  - >5%: Kritisch (Liquiditätsprobleme)

### Trade-Statistiken

```json
{
  "total_trades": 87,
  "winning_trades": 52,
  "losing_trades": 35,
  "winrate": 0.598,
  "avg_win": 450.32,
  "avg_loss": -230.18,
  "largest_win": 1823.50,
  "largest_loss": -892.30,
  "avg_trade_duration": "3h 42m"
}
```

---

## Best Practices

### 1. Szenario-Reihenfolge

**Empfohlene Ausführungsreihenfolge**:

1. **Bullish Momentum** → Baseline etablieren
2. **Consistent Trend Optimal** → Best-Case verstehen
3. **Sideways Chop** → Worst-Normal-Case verstehen
4. **High Volatility Stress** → Risk-Engine validieren
5. **Flash Crash Emergency** → Extreme-Event-Handling
6. **Multi-Symbol Correlation** → Portfolio-Management
7. **Low Liquidity Slippage** → Execution-Quality

### 2. Parameter-Tuning

**Iterativer Prozess**:

```
1. Baseline-Run mit Standard-Parametern
   ↓
2. Metriken analysieren (Drawdown, Sharpe, PnL)
   ↓
3. Parameter anpassen (z.B. max_position_pct)
   ↓
4. Erneut testen
   ↓
5. Vergleichen (Vorher/Nachher)
   ↓
6. Wenn besser → Übernehmen, sonst zurücksetzen
```

**Beispiel**:
```bash
# Baseline
python scripts/run_backtest.py --scenario bullish_momentum
# → Sharpe: 1.3, Drawdown: 12%

# Parameter-Tuning: Position-Size reduzieren
python scripts/run_backtest.py --scenario bullish_momentum --max-position-pct 0.08
# → Sharpe: 1.5, Drawdown: 8% (BESSER!)
```

### 3. Mehrfach-Runs

**Warum?**
- Randomness in Slippage-Simulation
- Order-Filling-Timing
- Edge-Cases erkennen

**Vorgehen**:
```bash
# 10 Runs mit verschiedenen Seeds
for i in {1..10}; do
  python scripts/run_backtest.py \
    --scenario bullish_momentum \
    --seed $i \
    --output results/run_$i.json
done

# Statistik über alle Runs
python scripts/analyze_multiple_runs.py results/*.json
```

### 4. Vergleich mit Benchmarks

**Immer vergleichen mit**:
- Buy-&-Hold BTC
- Buy-&-Hold ETH
- Equal-Weight-Portfolio (BTC/ETH/BNB)

**Beispiel**:
```bash
python scripts/compare_strategies.py \
  --scenario bullish_momentum \
  --benchmarks buy_and_hold_btc equal_weight_portfolio
```

**Interpretation**:
- **Strategie > Benchmark**: Erfolg! ✅
- **Strategie < Benchmark**: Verbesserungsbedarf ⚠️
- **Strategie ≈ Benchmark**: OK, aber Risiko-Adjustierung prüfen

---

## Troubleshooting

### Problem: "Insufficient data for timeframe"

**Ursache**: Marktdaten für gewählten Zeitraum nicht verfügbar.

**Lösung**:
```bash
# Daten-Download prüfen
python scripts/download_market_data.py \
  --symbol BTCUSDT \
  --start 2024-01-15 \
  --end 2024-03-15 \
  --interval 15m

# Verfügbare Daten prüfen
ls data/market_data/BTCUSDT_15m_*.parquet
```

### Problem: "All trades rejected by Risk Engine"

**Ursache**: Risk-Parameter zu streng oder Marktbedingungen außerhalb Toleranzen.

**Lösung**:
```bash
# Debug-Modus aktivieren
python scripts/run_backtest.py \
  --scenario sideways_chop \
  --log-level DEBUG \
  --save-risk-decisions

# Risk-Decisions analysieren
python scripts/analyze_risk_decisions.py results/risk_decisions.json
```

**Typische Gründe**:
- Slippage zu hoch → `max_slippage_pct` erhöhen
- Spread zu hoch → `max_spread_pct` erhöhen
- Volume zu niedrig → `min_volume_threshold` senken

### Problem: "Unrealistic performance (>100% ROI)"

**Ursache**: Bug in Simulation oder unrealistische Parameter.

**Checks**:
1. **Commission aktiviert?** → `commission_pct: 0.0006`
2. **Slippage aktiviert?** → `enable_slippage_simulation: true`
3. **Position-Sizing korrekt?** → Max 10% pro Trade
4. **Lookahead-Bias?** → Keine Future-Daten in Signal-Logic

### Problem: "High Drawdown (>20%)"

**Ursache**: Circuit-Breaker greift nicht oder Risk-Parameter zu aggressiv.

**Lösung**:
```bash
# Circuit-Breaker-Logs prüfen
grep "CIRCUIT_BREAKER" results/backtest.log

# Wenn keine Einträge → Bug im Risk-Manager!
python tests/test_risk_engine.py -v -k test_circuit_breaker
```

---

## Weiterführende Dokumentation

- **N1 Architektur**: `backoffice/docs/architecture/N1_ARCHITEKTUR.md`
- **Risk-Engine Logic**: `backoffice/docs/services/risk/RISK_LOGIC.md`
- **Strategy Documentation**: `backoffice/docs/strategy/MOMENTUM_STRATEGY.md`
- **Event Schemas**: `backoffice/docs/schema/EVENT_SCHEMA.json`
- **API Reference**: `backoffice/docs/api/BACKTEST_ENGINE_API.md`

---

## Changelog

| Version | Datum       | Änderungen                                    |
|---------|-------------|-----------------------------------------------|
| 1.0.0   | 2025-11-21  | Initial Release (7 Szenarien)                |

---

## Support & Kontakt

Bei Fragen oder Problemen:

1. **Issues**: GitHub Issues → `jannekbuengener/Claire_de_Binare_Cleanroom`
2. **Dokumentation**: `backoffice/docs/`
3. **Tests**: `pytest tests/test_backtest_scenarios.py -v`

---

**Viel Erfolg beim Backtesting!** 🚀📊
