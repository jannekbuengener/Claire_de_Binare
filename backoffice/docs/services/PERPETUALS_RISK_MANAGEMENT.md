# MEXC Perpetual Futures Risk Management – Deep Dive

**Projekt:** Claire de Binare
**Erstellt:** 2025-11-19
**Autor:** Claude (IT-Chef)
**Status:** Implementation Guide

---

## 📋 Executive Summary

Dieses Dokument beschreibt die vollständige Implementierung von **MEXC Perpetual Futures Risk Management** für Claire de Binare. Es basiert auf offizieller MEXC-API-Dokumentation (2024) und erweitert die bestehende Risk-Engine um:

1. **Exchange-spezifische Mechaniken** (Margin, Leverage, Liquidation)
2. **Advanced Position Sizing** (Vol-Targeting, Kelly, Fixed-Fractional)
3. **Realistic Execution Simulation** (Slippage, Fees, Partial Fills)
4. **Risk Analytics** (MaxDD, Tail-Risk, Performance-Metriken)

---

## 🎯 Ziel

**Realistische Paper-Tests** für Momentum-Strategien auf MEXC Perpetual Futures, die:
- ✅ Liquidation-Risiko korrekt modellieren
- ✅ Slippage & Fees realistisch simulieren
- ✅ Funding Rates berücksichtigen (8h-Intervalle)
- ✅ Backtest-Bias minimieren
- ✅ Performance-Metriken berechnen (Sharpe, MaxDD, etc.)

---

## 1️⃣ MEXC Perpetual Futures Mechanik

### 1.1 Position Margin & Leverage

**Position Margin Formula:**
```
Position Margin = (Entry Price × Position Size × Contract Multiplier) / Leverage
```

**Beispiel (BTC/USDT):**
- Entry Price: 50,000 USDT
- Position Size: 10,000 Contracts
- Contract Multiplier: 0.0001 BTC
- Leverage: 25x

```python
position_margin = (50000 × 10000 × 0.0001) / 25
position_margin = 5000 / 25 = 200 USDT
```

**MEXC Leverage Limits:**
- Standard: **1x - 125x**
- Select Contracts: bis zu 200x-500x
- Claire: **Max 10x** (Sicherheitslimit)

---

### 1.2 Liquidation Price Calculation

**MEXC verwendet Fair Price (nicht Market Price) für Liquidation.**

**Long Position Liquidation Price:**
```
LP_long = (Maintenance Margin - Position Margin + Entry Price × Size) / Size
```

**Short Position Liquidation Price:**
```
LP_short = (Entry Price × Size - Maintenance Margin + Position Margin) / Size
```

**Maintenance Margin Rate (MMR):**
```
MMR = Maintenance Margin / Position Value
```

**Liquidation tritt ein wenn:** `MMR >= 100%`

---

**Beispiel: Long Position**

Annahmen:
- Entry Price: 50,000 USDT
- Position Size: 0.1 BTC (10,000 Contracts × 0.0001)
- Leverage: 10x
- Maintenance Margin Rate: 0.5% (MEXC Standard für niedrige Leverage)

```python
# Position Value
position_value = 50000 × 0.1 = 5000 USDT

# Position Margin
position_margin = position_value / 10 = 500 USDT

# Maintenance Margin
maintenance_margin = position_value × 0.005 = 25 USDT

# Liquidation Price (Long)
liq_price_long = (25 - 500 + 50000 × 0.1) / 0.1
liq_price_long = (25 - 500 + 5000) / 0.1
liq_price_long = 4525 / 0.1 = 45,250 USDT
```

**Liquidation Distance:** (50,000 - 45,250) / 50,000 = **9.5%**

---

**Beispiel: Short Position**

```python
# Liquidation Price (Short)
liq_price_short = (50000 × 0.1 - 25 + 500) / 0.1
liq_price_short = (5000 - 25 + 500) / 0.1
liq_price_short = 5475 / 0.1 = 54,750 USDT
```

**Liquidation Distance:** (54,750 - 50,000) / 50,000 = **9.5%**

---

### 1.3 Cross Margin vs. Isolated Margin

| Feature | Cross Margin | Isolated Margin |
|---------|--------------|-----------------|
| **Margin Source** | Gesamtes Account-Balance | Nur zugewiesene Margin |
| **Risk** | Gesamtes Konto bei Liquidation | Nur Position-Margin verloren |
| **Leverage Adjustment** | Eingeschränkt | Frei anpassbar |
| **Use Case** | Diversifizierte Portfolios | Single-Position Risk-Control |
| **Claire Default** | ❌ Nicht verwendet | ✅ **Isolated (safer)** |

**Warum Isolated für Claire?**
- ✅ Begrenzt Verlust pro Trade
- ✅ Kein Contagion-Risk zwischen Positionen
- ✅ Besseres Risk-Management für Momentum-Strategien

---

### 1.4 Funding Rates

**MEXC Funding Rate Mechanik:**
- **Settlement:** 3× täglich (00:00, 08:00, 16:00 UTC)
- **Calculation:** `Funding Fee = Position Value × Funding Rate`

**Direction:**
- **Positive Rate** → Long Positions **zahlen** Shorts
- **Negative Rate** → Short Positions **zahlen** Longs

**Wichtig für Paper-Trading:**
- Nur charged wenn Position **zum Settlement-Zeitpunkt offen** ist
- Orders innerhalb ±15s des Timestamps: möglicherweise nicht settled

**Typische Funding Rates (BTC/USDT):**
- Normal: -0.01% bis +0.01% (pro 8h)
- Extremfall (Bull-Market): +0.05% bis +0.10%
- Annualisiert: ~1% - 3% (normale Märkte)

**Beispiel:**
```python
position_value = 50000 USDT
funding_rate = 0.0001  # 0.01% pro 8h
funding_fee = 50000 × 0.0001 = 5 USDT (pro 8h)

# Annualisiert (365 Tage × 3 Settlements/Tag)
annual_funding = 5 × 3 × 365 = 5475 USDT (10.95% des Position Value!)
```

---

### 1.5 Trading Fees (Maker/Taker)

**MEXC Perpetual Futures Fees (2024):**

| Fee Type | Rate | Claire Assumption |
|----------|------|-------------------|
| **Maker** | 0.00% - 0.02% | **0.02%** (konservativ) |
| **Taker** | 0.02% - 0.06% | **0.06%** (konservativ) |

**Fee Calculation:**
```
Fee = Position Value × Fee Rate
```

**Beispiel (Market Order = Taker):**
```python
position_value = 50000 USDT
taker_fee = 50000 × 0.0006 = 30 USDT
```

**Roundtrip Cost (Entry + Exit):**
```
Roundtrip Cost = (Entry Fee + Exit Fee)
              = (50000 × 0.0006) + (50000 × 0.0006)
              = 60 USDT (0.12% des Position Value)
```

---

## 2️⃣ Advanced Position Sizing Strategies

### 2.1 Fixed-Fractional Sizing (Baseline)

**Konzept:** Riskiere festen % des Equity pro Trade.

**Formula:**
```
Position Size = (Equity × Risk Fraction) / (Entry Price × Stop Loss Distance)
```

**Beispiel:**
- Equity: 100,000 USDT
- Risk per Trade: 2% = 2,000 USDT
- Entry Price: 50,000 USDT
- Stop Loss: 2% (= 1,000 USDT Distance)

```python
position_size_usd = 2000 / (0.02 × 50000)
position_size_usd = 2000 / 1000 = 2.0
# → Position = 2× Stop-Distance = 100,000 USDT
```

**Vorteil:** Einfach, intuitiv, gut für diskretionäre Trader.
**Nachteil:** Ignoriert Volatilität.

---

### 2.2 Volatility Targeting

**Konzept:** Skaliere Position basiert auf aktueller Asset-Volatilität.

**Formula:**
```
Position Size = (Equity × Target Vol) / (Asset Vol × Current Price)
```

**Beispiel:**
- Equity: 100,000 USDT
- Target Portfolio Vol: 20% (annualized)
- BTC Vol: 60% (annualized)
- BTC Price: 50,000 USDT

```python
notional = (100000 × 0.20) / 0.60
notional = 33,333 USDT

position_size_btc = 33333 / 50000 = 0.6667 BTC
```

**Vorteil:** Stabilisiert Portfolio-Volatilität über verschiedene Regime.
**Nachteil:** Braucht gute Vol-Schätzung (z.B. Parkinson, GARCH).

---

### 2.3 Kelly Criterion (mit Fractional Limiter)

**Konzept:** Maximiere langfristiges Wachstum basiert auf Edge.

**Full Kelly Formula:**
```
Kelly % = (Win Rate × Avg Win - Loss Rate × Avg Loss) / Avg Win
```

**Sicherer: Fractional Kelly (25% - 50%)**
```
Position Size = Equity × (Kelly % × Fraction)
```

**Beispiel:**
- Win Rate: 55%
- Avg Win: 3%
- Avg Loss: 1.5%
- Equity: 100,000 USDT

```python
kelly_pct = (0.55 × 0.03 - 0.45 × 0.015) / 0.03
kelly_pct = (0.0165 - 0.00675) / 0.03 = 0.325 (32.5%)

# Fractional Kelly (25%)
position_size = 100000 × 0.325 × 0.25 = 8,125 USDT
```

**Vorteil:** Optimal für bekannte Edge.
**Nachteil:** Braucht gute Win-Rate / Payoff-Schätzung.

---

### 2.4 ATR-Based Sizing

**Konzept:** Skaliere Position basiert auf Average True Range.

**Formula:**
```
Stop Distance = ATR × Multiplier
Position Size = (Equity × Risk %) / Stop Distance
```

**Beispiel:**
- Equity: 100,000 USDT
- Risk: 2% = 2,000 USDT
- ATR (14-day): 2,500 USDT
- Multiplier: 2.0

```python
stop_distance = 2500 × 2.0 = 5,000 USDT

position_size_usd = 2000 / 5000 = 0.4
# → 40% of Equity = 40,000 USDT
```

**Vorteil:** Passt sich automatisch an Volatilität an.
**Nachteil:** Lagging Indicator (ATR reagiert verzögert).

---

## 3️⃣ Realistic Execution Simulation

### 3.1 Slippage Modellierung

**Base Slippage Model:**
```python
slippage_bps = base_slippage + (order_size / order_book_depth) × depth_impact_factor
               + volatility_multiplier × current_volatility
```

**Claire Defaults:**
- Base Slippage: **5 bps** (0.05%)
- Depth Impact Factor: **0.10** (10% Impact bei Order = 100% Depth)
- Volatility Multiplier: **2.0** (Slippage verdoppelt bei 2× Vol)

**Beispiel (Normal Market):**
```python
order_size = 50,000 USDT
order_book_depth = 1,000,000 USDT  # Top 10 Levels
volatility = 0.02  # 2% hourly vol

slippage_bps = 5 + (50000 / 1000000) × 0.10 × 10000
             + 2.0 × 0.02 × 10000
slippage_bps = 5 + 5 + 40 = 50 bps (0.50%)
```

**Beispiel (Stressed Market):**
```python
order_book_depth = 200,000 USDT  # Thin liquidity
volatility = 0.08  # 8% hourly vol

slippage_bps = 5 + (50000 / 200000) × 0.10 × 10000
             + 2.0 × 0.08 × 10000
slippage_bps = 5 + 25 + 160 = 190 bps (1.90%)
```

---

### 3.2 Partial Fills

**Partial Fill Logic:**
```python
if order_size > order_book_depth × fill_threshold:
    filled_size = order_book_depth × fill_threshold
    filled_ratio = filled_size / order_size
else:
    filled_size = order_size
    filled_ratio = 1.0
```

**Claire Default:** `fill_threshold = 0.80` (nur 80% der Depth nutzbar)

**Beispiel:**
```python
order_size = 100,000 USDT
order_book_depth = 80,000 USDT

# Partial Fill
filled_size = 80000 × 0.80 = 64,000 USDT
filled_ratio = 64000 / 100000 = 0.64 (64%)
```

---

### 3.3 Order Queue Delays

**Limit Order Fill Probability:**
```python
# Simplified: Distance from Mid-Price
fill_probability = 1 - (distance_bps / max_distance_bps)

# Time-weighted:
fill_probability × (1 - exp(-time_in_queue / avg_fill_time))
```

**Claire verwendet:** Vereinfachtes Modell (nur für Advanced Features).

---

## 4️⃣ Risk Analytics & Performance Metrics

### 4.1 Maximum Drawdown (MaxDD)

**Definition:** Größter Peak-to-Trough Verlust.

**Calculation:**
```python
running_max = max(equity[:i])
drawdown[i] = (equity[i] - running_max) / running_max
max_drawdown = min(drawdown)
```

**Beispiel:**
```
Equity Curve: [100k, 105k, 110k, 95k, 100k]
Peaks:        [100k, 105k, 110k, 110k, 110k]
Drawdowns:    [0%, 0%, 0%, -13.6%, -9.1%]
MaxDD = -13.6%
```

**Recovery Time:** Anzahl Perioden von Trough bis neuer Peak.

---

### 4.2 Time Under Water

**Definition:** % der Zeit unter vorherigem Peak.

**Calculation:**
```python
underwater_periods = count(equity[i] < running_max[i])
time_under_water = underwater_periods / total_periods
```

---

### 4.3 Tail Risk Metrics (VaR / CVaR)

**Value at Risk (VaR 95%):**
```
VaR_95 = 5th Percentile of Returns Distribution
```

**Conditional VaR (CVaR / Expected Shortfall):**
```
CVaR_95 = Mean of all returns worse than VaR_95
```

**Beispiel:**
```python
returns = [-0.05, -0.03, -0.02, 0.01, 0.02, 0.03]
sorted_returns = [-0.05, -0.03, -0.02, 0.01, 0.02, 0.03]

# VaR 95% (5th percentile bei 6 samples)
VaR_95 = sorted_returns[0] = -5%

# CVaR (mean of returns <= VaR)
CVaR_95 = mean([-0.05]) = -5%
```

---

### 4.4 Sharpe & Sortino Ratios

**Sharpe Ratio:**
```
Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
```

**Sortino Ratio:**
```
Sortino = (Mean Return - Risk Free Rate) / Downside Deviation
```

**Downside Deviation:** Nur negative Returns betrachten.

**Beispiel:**
```python
returns = [0.02, 0.01, -0.01, 0.03, -0.02]
mean_return = 0.006 (0.6%)
std_dev = 0.0187 (1.87%)
risk_free = 0.0 (für Krypto)

sharpe = 0.006 / 0.0187 = 0.32

# Sortino (nur negative returns)
negative_returns = [-0.01, -0.02]
downside_dev = std([-0.01, -0.02]) = 0.007
sortino = 0.006 / 0.007 = 0.86
```

---

### 4.5 Calmar Ratio

**Calmar Ratio:**
```
Calmar = Annualized Return / Maximum Drawdown
```

**Beispiel:**
```python
annual_return = 0.25 (25%)
max_drawdown = 0.10 (10%)

calmar = 0.25 / 0.10 = 2.5
```

**Interpretation:**
- Calmar > 3.0: Excellent
- Calmar 1.0 - 3.0: Good
- Calmar < 1.0: Poor

---

## 5️⃣ Integration mit Risk-Engine

### 5.1 ENV-Parameter (Neue Additions)

**In `.env` hinzufügen:**

```bash
# ===== PERPETUAL FUTURES CONFIG =====
# Margin & Leverage
MARGIN_MODE=isolated              # isolated | cross
MAX_LEVERAGE=10                   # 1-125 (Claire: max 10x)
MIN_LIQUIDATION_DISTANCE=0.15     # 15% min distance

# Position Sizing
SIZING_METHOD=fixed_fractional    # fixed_fractional | vol_targeting | kelly | atr
TARGET_VOL=0.20                   # 20% annual target vol (für vol_targeting)
RISK_PER_TRADE=0.02              # 2% max risk per trade
KELLY_FRACTION=0.25              # 25% of full Kelly (safety)
ATR_MULTIPLIER=2.0               # Stop = ATR × 2

# Execution Simulation
MAKER_FEE=0.0002                 # 0.02%
TAKER_FEE=0.0006                 # 0.06%
BASE_SLIPPAGE_BPS=5              # 5 basis points base slippage
DEPTH_IMPACT_FACTOR=0.10         # 10% impact at 100% depth utilization
VOL_SLIPPAGE_MULTIPLIER=2.0      # Slippage doubles at 2× volatility
FILL_THRESHOLD=0.80              # Max 80% of order book depth usable

# Funding Rates
FUNDING_RATE=0.0001              # 0.01% per 8h (default)
FUNDING_SETTLEMENT_HOURS=8       # MEXC: 3× täglich

# Risk Analytics
ENABLE_TAIL_RISK_CHECKS=true     # VaR/CVaR validation
VAR_CONFIDENCE=0.95              # 95% VaR
MAX_ACCEPTABLE_VAR=0.05          # 5% max daily VaR
```

---

### 5.2 Workflow Integration

**Bestehende Risk-Engine (`services/risk_engine.py`):**
```
evaluate_signal() → Basic Checks (Drawdown, Exposure, Position Size)
```

**Neue Enhanced Version (`evaluate_signal_v2()`):**
```
1. Basic Checks (wie bisher)
2. Advanced Position Sizing (Vol-Targeting / Kelly / etc.)
3. Perpetuals-Checks (Liquidation Distance, Margin Requirements)
4. Execution Simulation (Slippage, Fees)
5. Tail-Risk Validation (VaR Check)
→ RiskDecision mit erweiterten Metadaten
```

**Event-Flow:**
```
market_data → Signal Engine → Risk Manager (evaluate_signal_v2) → Execution Simulator → PostgreSQL
```

---

## 6️⃣ Testing Strategy

### 6.1 Unit Tests

**Modul 1: `tests/test_mexc_perpetuals.py`**
- Liquidation Price (Long/Short)
- Margin Calculation
- Funding Fees
- Cross vs. Isolated Logic

**Modul 2: `tests/test_position_sizing.py`**
- Fixed-Fractional
- Vol-Targeting
- Kelly Criterion
- ATR-Based

**Modul 3: `tests/test_execution_simulator.py`**
- Slippage Calculation
- Partial Fills
- Fee Calculation

**Modul 4: `tests/test_risk_analytics.py`**
- MaxDD
- VaR/CVaR
- Sharpe/Sortino
- Regime Detection

---

### 6.2 Integration Tests

**`tests/integration/test_perpetuals_full_flow.py`**

**Szenario 1: Normal Market**
```python
def test_full_flow_normal_market():
    # Setup
    equity = 100000
    signal = create_signal("BTCUSDT", "buy", 50000, confidence=0.75)
    market_conditions = {
        "volatility": 0.02,
        "order_book_depth": 1000000,
        "funding_rate": 0.0001
    }

    # Execute
    decision = evaluate_signal_v2(signal, risk_state, config, market_conditions)

    # Assert
    assert decision.approved is True
    assert decision.position_size > 0
    assert decision.metadata["liquidation_distance"] > 0.15
    assert decision.metadata["expected_slippage_bps"] < 20
```

**Szenario 2: Stressed Market**
```python
def test_full_flow_stressed_market():
    market_conditions = {
        "volatility": 0.08,  # 8% hourly vol
        "order_book_depth": 200000,  # Thin liquidity
        "funding_rate": 0.0005  # 0.05% per 8h
    }

    decision = evaluate_signal_v2(signal, risk_state, config, market_conditions)

    # Should reduce size or reject
    assert decision.position_size < normal_market_size or not decision.approved
```

---

### 6.3 Backtest Validation

**Ziel:** Validiere Realism vs. Historical Data

**Metriken:**
- MaxDD sollte < 20% sein (bei 10x Leverage)
- Sharpe > 1.0 für profitable Strategie
- Calmar > 2.0 (Ziel)
- VaR 95% < 5% (Daily)

**Backtest-Zeitraum:** Mindestens 6 Monate + Bull + Bear Phase.

---

## 7️⃣ Literatur & Referenzen

**MEXC Official Docs:**
- Margin & PnL: https://www.mexc.com/learn/article/17827791513099
- Liquidation FAQ: https://www.mexc.com/learn/article/faq-on-liquidation-for-futures-trading/1
- Fees: https://www.mexc.com/learn/article/17827791510370
- Funding Rates: https://www.mexc.com/learn/article/17827791509933

**Academic:**
- Kelly Criterion: Kelly (1956) "A New Interpretation of Information Rate"
- Vol-Targeting: Moreira & Muir (2017) "Volatility-Managed Portfolios"
- Slippage Modeling: Almgren & Chriss (2000) "Optimal Execution of Portfolio Transactions"

**Claire de Binare:**
- `KODEX.md` - Architektur-Prinzipien
- `canonical_schema.yaml` - System-Schema
- `EVENT_SCHEMA.json` - Event-Definitionen

---

## 📊 Appendix A: Quick Reference

**Liquidation Formulas:**
```python
# Long
liq_price_long = (MM - PM + entry_price * size) / size

# Short
liq_price_short = (entry_price * size - MM + PM) / size
```

**Fees & Funding:**
```python
maker_fee = position_value × 0.0002
taker_fee = position_value × 0.0006
funding_fee = position_value × funding_rate  # per 8h
```

**Position Sizing:**
```python
# Fixed-Fractional
size = (equity × risk_pct) / stop_distance

# Vol-Targeting
size = (equity × target_vol) / asset_vol

# Kelly
size = equity × kelly_fraction × (win_rate × avg_win - loss_rate × avg_loss) / avg_win
```

**Risk Metrics:**
```python
max_dd = min(equity - running_max) / running_max
sharpe = mean(returns) / std(returns)
calmar = annual_return / max_drawdown
```

---

**Ende der Dokumentation**

**Nächste Schritte:**
1. Implementation: `services/mexc_perpetuals.py`
2. Tests: `tests/test_mexc_perpetuals.py`
3. Integration: `services/risk_engine.py` erweitern
