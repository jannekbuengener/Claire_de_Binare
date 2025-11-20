# Database Tracking Gap-Analyse - Claire de Binaire
**Datum**: 2025-11-20 18:10 UTC
**Status**: Analyse was getrackt wird vs. was fehlt

---

## 📊 AKTUELLES TRACKING (Was wird gespeichert)

### 1️⃣ **signals** Tabelle ✅
**Was wird getrackt:**
- ✅ Symbol (z.B. BTCUSDT)
- ✅ Signal-Typ (buy/sell)
- ✅ Preis
- ✅ Konfidenz (0.0-1.0)
- ✅ Timestamp
- ✅ Source (momentum_strategy)
- ✅ Metadata (JSONB - flexibel)

**Was FEHLT:**
- ❌ **Indikator-Werte** (RSI, MACD, Bollinger, etc.)
- ❌ **Signal-Strength** (wie stark war das Signal?)
- ❌ **Market-Context** (Trend, Volatilität zum Signal-Zeitpunkt)
- ❌ **Signal-Version** (welche Strategy-Version hat es generiert?)

---

### 2️⃣ **orders** Tabelle ✅
**Was wird getrackt:**
- ✅ Signal-ID (Foreign Key)
- ✅ Symbol, Side, Order-Type
- ✅ Preis, Größe
- ✅ Approval-Status (approved/rejected)
- ✅ Rejection-Reason
- ✅ Status (pending/filled/cancelled)
- ✅ Filled-Size, Avg-Fill-Price
- ✅ Timestamps (created/submitted/filled)
- ✅ Metadata (JSONB)

**Was FEHLT:**
- ❌ **Risk-Check Details** (welche Risk-Layer wurden geprüft?)
- ❌ **Position-Size Calculation** (warum genau diese Größe?)
- ❌ **Expected vs. Actual** (erwarteter vs. tatsächlicher Fill)
- ❌ **Order-Latency** (Zeit von Signal → Order → Fill)
- ❌ **Partial-Fill-History** (wenn Order schrittweise gefüllt wurde)

---

### 3️⃣ **trades** Tabelle ✅
**Was wird getrackt:**
- ✅ Order-ID (Foreign Key)
- ✅ Symbol, Side, Preis, Größe
- ✅ Execution-Preis
- ✅ Slippage (in Basis Points)
- ✅ Fees
- ✅ Timestamp
- ✅ Exchange (MEXC)
- ✅ Exchange-Trade-ID
- ✅ Metadata (JSONB)

**Was FEHLT:**
- ❌ **Slippage-Breakdown** (was verursachte das Slippage?)
- ❌ **Liquidity-Context** (Order-Book-Depth zum Trade-Zeitpunkt)
- ❌ **Market-Impact** (wie hat unsere Order den Markt beeinflusst?)
- ❌ **Trade-Venue** (welcher spezifische Pool/Venue bei DEX?)

---

### 4️⃣ **positions** Tabelle ✅
**Was wird getrackt:**
- ✅ Symbol (UNIQUE)
- ✅ Side (long/short/none)
- ✅ Größe, Entry-Preis, Current-Preis
- ✅ Unrealized PnL, Realized PnL
- ✅ Stop-Loss, Take-Profit, Liquidation-Preis
- ✅ Timestamps (opened/updated/closed)
- ✅ Metadata (JSONB)

**Was FEHLT:**
- ❌ **Position-History** (wie hat sich die Position über Zeit entwickelt?)
- ❌ **Max-Drawdown der Position** (schlechtester Punkt)
- ❌ **Max-Profit der Position** (bester Punkt)
- ❌ **Holding-Duration** (wie lange wurde gehalten?)
- ❌ **Exit-Reason** (warum wurde geschlossen? Stop-Loss/Take-Profit/Manual?)
- ❌ **Win/Loss-Classification** (für Statistics)

---

### 5️⃣ **portfolio_snapshots** Tabelle ✅
**Was wird getrackt:**
- ✅ Timestamp
- ✅ Total-Equity, Available-Balance, Margin-Used
- ✅ Daily-PnL, Unrealized-PnL, Realized-PnL
- ✅ Total-Exposure-Pct, Max-Drawdown-Pct
- ✅ Open-Positions (Anzahl)
- ✅ Metadata (JSONB)

**Was FEHLT:**
- ❌ **Sharpe-Ratio** (Risk-Adjusted Return)
- ❌ **Win-Rate** (% gewonnene Trades)
- ❌ **Profit-Factor** (Gewinn/Verlust-Ratio)
- ❌ **Average-Win vs. Average-Loss**
- ❌ **Max-Consecutive-Wins/Losses**
- ❌ **Exposure-per-Asset** (nicht nur Gesamt-Exposure)
- ❌ **Correlation-Metrics** (zwischen Positionen)

---

## ❌ WAS FEHLT KOMPLETT (Neue Tabellen)

### 🔴 KRITISCH Fehlend:

#### 1. **risk_events** Tabelle
**Zweck**: Risk-Check-Details aufzeichnen

**Sollte tracken:**
```sql
CREATE TABLE risk_events (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    order_id INTEGER REFERENCES orders(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Risk-Check-Details
    check_type VARCHAR(50), -- 'daily_drawdown', 'position_limit', 'exposure', etc.
    check_result VARCHAR(20), -- 'pass', 'fail', 'warning'
    check_value DECIMAL(18, 8),
    check_limit DECIMAL(18, 8),
    
    -- Context
    portfolio_state JSONB,
    risk_config JSONB,
    
    -- Reason
    reason TEXT
);
```

**Warum wichtig?**
- ✅ Verstehen, WARUM Orders abgelehnt wurden
- ✅ Risk-Engine-Performance analysieren
- ✅ False-Positives erkennen
- ✅ Risk-Limits optimieren

---

#### 2. **performance_metrics** Tabelle
**Zweck**: Aggregierte Metriken über Zeiträume

**Sollte tracken:**
```sql
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    period_type VARCHAR(20), -- 'hourly', 'daily', 'weekly', 'monthly'
    
    -- Returns
    total_return_pct DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    
    -- Win/Loss
    win_rate DECIMAL(5, 4),
    profit_factor DECIMAL(10, 4),
    avg_win DECIMAL(18, 8),
    avg_loss DECIMAL(18, 8),
    
    -- Drawdown
    max_drawdown_pct DECIMAL(5, 4),
    max_drawdown_duration_hours INTEGER,
    
    -- Volume
    total_trades INTEGER,
    total_volume DECIMAL(18, 8),
    total_fees DECIMAL(18, 8),
    
    -- Risk
    avg_exposure_pct DECIMAL(5, 4),
    max_exposure_pct DECIMAL(5, 4),
    
    metadata JSONB
);
```

**Warum wichtig?**
- ✅ Performance-Trends erkennen
- ✅ Strategie-Vergleiche
- ✅ Reporting vereinfachen
- ✅ Backtesting-Validierung

---

#### 3. **market_conditions** Tabelle
**Zweck**: Market-Context zum Signal-/Trade-Zeitpunkt

**Sollte tracken:**
```sql
CREATE TABLE market_conditions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Price-Action
    price DECIMAL(18, 8),
    volume_24h DECIMAL(18, 8),
    volatility_1h DECIMAL(10, 4),
    
    -- Trend
    trend_direction VARCHAR(10), -- 'bullish', 'bearish', 'sideways'
    trend_strength DECIMAL(5, 4), -- 0.0-1.0
    
    -- Liquidity
    bid_ask_spread_bps DECIMAL(10, 2),
    order_book_depth DECIMAL(18, 8),
    
    -- Indicators (optional)
    rsi_14 DECIMAL(5, 2),
    macd_signal DECIMAL(10, 4),
    bb_position DECIMAL(5, 4), -- Position in Bollinger Bands
    
    metadata JSONB
);
```

**Warum wichtig?**
- ✅ Verstehen, in welchem Market-Context Trades erfolgreich waren
- ✅ Strategy-Parameter optimieren
- ✅ Market-Regime-Detection
- ✅ Signal-Quality-Analyse

---

#### 4. **execution_analysis** Tabelle
**Zweck**: Detaillierte Execution-Analyse

**Sollte tracken:**
```sql
CREATE TABLE execution_analysis (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER REFERENCES trades(id),
    
    -- Timing
    signal_timestamp TIMESTAMP WITH TIME ZONE,
    order_timestamp TIMESTAMP WITH TIME ZONE,
    execution_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- Latency
    signal_to_order_ms INTEGER,
    order_to_execution_ms INTEGER,
    total_latency_ms INTEGER,
    
    -- Slippage-Breakdown
    expected_price DECIMAL(18, 8),
    execution_price DECIMAL(18, 8),
    slippage_bps DECIMAL(10, 2),
    slippage_reason VARCHAR(100), -- 'market_movement', 'liquidity', 'latency'
    
    -- Market-Impact
    price_before DECIMAL(18, 8),
    price_after DECIMAL(18, 8),
    market_impact_bps DECIMAL(10, 2),
    
    -- Quality-Score
    execution_quality_score DECIMAL(5, 4), -- 0.0-1.0
    
    metadata JSONB
);
```

**Warum wichtig?**
- ✅ Execution-Quality messen
- ✅ Slippage-Ursachen verstehen
- ✅ Latency-Probleme erkennen
- ✅ Venue-Selection optimieren

---

### 🟡 NICE-TO-HAVE:

#### 5. **strategy_versions** Tabelle
**Zweck**: Strategy-Version-Tracking

```sql
CREATE TABLE strategy_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE,
    deployed_at TIMESTAMP WITH TIME ZONE,
    
    -- Config
    strategy_name VARCHAR(50),
    parameters JSONB,
    
    -- Performance
    total_signals INTEGER,
    total_trades INTEGER,
    win_rate DECIMAL(5, 4),
    sharpe_ratio DECIMAL(10, 4),
    
    -- Status
    status VARCHAR(20), -- 'active', 'deprecated', 'testing'
    notes TEXT
);
```

**Warum nützlich?**
- ✅ A/B-Testing von Strategien
- ✅ Version-Performance vergleichen
- ✅ Rollback bei schlechter Performance

---

#### 6. **alerts** Tabelle
**Zweck**: System-Alerts persistent speichern

```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    level VARCHAR(20), -- 'info', 'warning', 'critical'
    category VARCHAR(50), -- 'risk', 'execution', 'system', 'market'
    code VARCHAR(50),
    message TEXT,
    
    -- Context
    related_signal_id INTEGER,
    related_order_id INTEGER,
    related_trade_id INTEGER,
    
    -- Status
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    
    metadata JSONB
);
```

**Warum nützlich?**
- ✅ Alert-History analysieren
- ✅ Alert-Häufigkeit tracken
- ✅ False-Positives erkennen

---

## 📊 EMPFOHLENE PRIORITÄTEN

### 🔴 PHASE 1 (Sofort für Paper-Trading):
1. ✅ **risk_events** - KRITISCH für Risk-Engine-Analyse
2. ✅ **execution_analysis** - WICHTIG für Execution-Quality

### 🟡 PHASE 2 (Nach 1 Woche Paper-Trading):
3. ✅ **performance_metrics** - Für Reporting
4. ✅ **market_conditions** - Für Strategy-Optimierung

### 🟢 PHASE 3 (Optional, später):
5. ⏳ **strategy_versions** - Bei A/B-Testing
6. ⏳ **alerts** - Bei Production-Deployment

---

## 💡 ZUSÄTZLICHE TRACKING-IDEEN

### In **signals.metadata** (JSONB):
```json
{
  "indicators": {
    "rsi_14": 67.5,
    "macd_signal": "bullish_cross",
    "bb_position": 0.85
  },
  "signal_strength": 0.92,
  "market_regime": "trending",
  "strategy_version": "v1.2.3"
}
```

### In **trades.metadata** (JSONB):
```json
{
  "execution_venue": "MEXC_SPOT",
  "order_book_snapshot": {
    "bid_depth": 10000.0,
    "ask_depth": 8500.0,
    "spread_bps": 5
  },
  "latency_ms": {
    "signal_to_order": 45,
    "order_to_fill": 120
  }
}
```

### In **positions.metadata** (JSONB):
```json
{
  "max_unrealized_pnl": 850.50,
  "min_unrealized_pnl": -320.00,
  "avg_holding_duration_hours": 4.5,
  "exit_reason": "take_profit",
  "risk_reward_ratio": 2.65
}
```

---

## 🎯 NÄCHSTE SCHRITTE

### Sofort:
1. **Entscheidung**: Welche neuen Tabellen jetzt anlegen?
2. **Migration**: `DATABASE_SCHEMA_v2.sql` erstellen
3. **Service-Updates**: Risk/Execution-Services anpassen für neues Tracking

### Empfehlung:
**START MIT**: `risk_events` + `execution_analysis`

Diese beiden Tabellen bringen den größten Mehrwert für Paper-Trading-Analyse!

---

**Fazit**: Aktuelles Tracking ist **solide Basis (7/10)**, aber **2-3 zusätzliche Tabellen** würden die Analyse-Möglichkeiten **massiv verbessern** (10/10)! 🎯
