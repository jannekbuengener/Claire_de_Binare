# Database Enhancement Roadmap - Claire de Binaire
**Datum**: 2025-11-20 18:15 UTC
**Strategie**: 3-Phasen Progressive Enhancement
**Ziel**: Von 7/10 → 10/10 Tracking-Coverage

---

## 🎯 3-PHASEN-PLAN

### ✅ **PHASE 1: VALIDATION** (Jetzt - Tag 0)
**Dauer**: 1-2 Stunden  
**Ziel**: Bestehende 5 Tabellen validieren, Paper-Trading starten

**Tasks**:
- [x] Schema-Analyse abgeschlossen ✅
- [ ] Container starten (PostgreSQL + Redis)
- [ ] Schema-Erstellung validieren (6 Tabellen vorhanden?)
- [ ] Initial Portfolio prüfen (100k USDT vorhanden?)
- [ ] JSONB-Metadata-Strategy definieren (Best Practices)
- [ ] Erste Paper-Trading-Session (1-2 Stunden)
- [ ] Daten-Sammlung analysieren (was wurde geschrieben?)

**Deliverables**:
- ✅ Funktionierende Basis-Infrastruktur
- ✅ Erste Trading-Daten in DB
- ✅ Gap-Identifikation aus realen Daten

**Success Criteria**:
```
✅ Alle 5 Tabellen beschreibbar
✅ Mind. 10 Signals in DB
✅ Mind. 5 Orders in DB
✅ Mind. 2 Trades in DB
✅ Portfolio-Snapshots werden geschrieben (1/min)
```

---

### 🔴 **PHASE 2: CRITICAL ENHANCEMENTS** (Tag 1-2)
**Dauer**: 4-6 Stunden  
**Ziel**: risk_events + execution_analysis hinzufügen

**Tasks**:
- [ ] DATABASE_SCHEMA_v2.sql erstellen
  - [ ] risk_events Tabelle definieren
  - [ ] execution_analysis Tabelle definieren
  - [ ] Migration-Script schreiben (v1.0.0 → v2.0.0)
- [ ] Service-Updates:
  - [ ] Risk-Manager: risk_events logging implementieren
  - [ ] Execution-Service: execution_analysis logging implementieren
- [ ] Testing:
  - [ ] Unit-Tests für neue Tabellen
  - [ ] Integration-Tests für Logging-Flow
- [ ] Migration ausführen
- [ ] Paper-Trading-Session mit neuen Tabellen (4-8 Stunden)

**Deliverables**:
- ✅ risk_events Tabelle aktiv
- ✅ execution_analysis Tabelle aktiv
- ✅ Services loggen in neue Tabellen
- ✅ Erste Analyse-Queries funktionieren

**New SQL Schema**:
```sql
-- risk_events
CREATE TABLE risk_events (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    order_id INTEGER REFERENCES orders(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    check_type VARCHAR(50),
    check_result VARCHAR(20),
    check_value DECIMAL(18, 8),
    check_limit DECIMAL(18, 8),
    portfolio_state JSONB,
    risk_config JSONB,
    reason TEXT
);

CREATE INDEX idx_risk_events_check_type ON risk_events(check_type);
CREATE INDEX idx_risk_events_result ON risk_events(check_result);
CREATE INDEX idx_risk_events_timestamp ON risk_events(timestamp DESC);

-- execution_analysis
CREATE TABLE execution_analysis (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER REFERENCES trades(id),
    signal_timestamp TIMESTAMP WITH TIME ZONE,
    order_timestamp TIMESTAMP WITH TIME ZONE,
    execution_timestamp TIMESTAMP WITH TIME ZONE,
    signal_to_order_ms INTEGER,
    order_to_execution_ms INTEGER,
    total_latency_ms INTEGER,
    expected_price DECIMAL(18, 8),
    execution_price DECIMAL(18, 8),
    slippage_bps DECIMAL(10, 2),
    slippage_reason VARCHAR(100),
    price_before DECIMAL(18, 8),
    price_after DECIMAL(18, 8),
    market_impact_bps DECIMAL(10, 2),
    execution_quality_score DECIMAL(5, 4),
    metadata JSONB
);

CREATE INDEX idx_execution_analysis_trade_id ON execution_analysis(trade_id);
CREATE INDEX idx_execution_analysis_quality ON execution_analysis(execution_quality_score DESC);
```

**Success Criteria**:
```
✅ Migration läuft ohne Fehler
✅ Mind. 20 risk_events Einträge
✅ Mind. 10 execution_analysis Einträge
✅ Latency-Analyse funktioniert
✅ Rejection-Reason-Analyse funktioniert
```

---

### 🟡 **PHASE 3: COMPLETE ENHANCEMENT** (Tag 3-7)
**Dauer**: 8-12 Stunden  
**Ziel**: performance_metrics + market_conditions + alerts hinzufügen

**Tasks**:
- [ ] DATABASE_SCHEMA_v3.sql erstellen
  - [ ] performance_metrics Tabelle
  - [ ] market_conditions Tabelle
  - [ ] alerts Tabelle (optional)
  - [ ] strategy_versions Tabelle (optional)
- [ ] Service-Updates:
  - [ ] Analytics-Service erstellen (aggregiert Metriken)
  - [ ] Market-Data-Service: market_conditions logging
  - [ ] Alert-Service: alerts logging
- [ ] Dashboard-Queries:
  - [ ] Performance-Dashboard SQL-Queries
  - [ ] Risk-Dashboard SQL-Queries
  - [ ] Market-Context SQL-Queries
- [ ] Testing:
  - [ ] Unit-Tests für alle neuen Tabellen
  - [ ] Integration-Tests
  - [ ] E2E-Tests mit vollem Stack
- [ ] Migration ausführen
- [ ] Paper-Trading-Session (1 Woche)

**Deliverables**:
- ✅ Alle 9 Tabellen aktiv (5 + 4 neue)
- ✅ Automatische Metrik-Aggregation
- ✅ Market-Context bei jedem Signal
- ✅ Alert-History persistent
- ✅ Performance-Dashboards funktionieren

**New SQL Schema**:
```sql
-- performance_metrics
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    period_type VARCHAR(20),
    total_return_pct DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    win_rate DECIMAL(5, 4),
    profit_factor DECIMAL(10, 4),
    avg_win DECIMAL(18, 8),
    avg_loss DECIMAL(18, 8),
    max_drawdown_pct DECIMAL(5, 4),
    max_drawdown_duration_hours INTEGER,
    total_trades INTEGER,
    total_volume DECIMAL(18, 8),
    total_fees DECIMAL(18, 8),
    avg_exposure_pct DECIMAL(5, 4),
    max_exposure_pct DECIMAL(5, 4),
    metadata JSONB
);

-- market_conditions
CREATE TABLE market_conditions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    price DECIMAL(18, 8),
    volume_24h DECIMAL(18, 8),
    volatility_1h DECIMAL(10, 4),
    trend_direction VARCHAR(10),
    trend_strength DECIMAL(5, 4),
    bid_ask_spread_bps DECIMAL(10, 2),
    order_book_depth DECIMAL(18, 8),
    rsi_14 DECIMAL(5, 2),
    macd_signal DECIMAL(10, 4),
    bb_position DECIMAL(5, 4),
    metadata JSONB
);

-- alerts
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20),
    category VARCHAR(50),
    code VARCHAR(50),
    message TEXT,
    related_signal_id INTEGER,
    related_order_id INTEGER,
    related_trade_id INTEGER,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB
);
```

**Success Criteria**:
```
✅ Migration läuft ohne Fehler
✅ Tägliche Performance-Metriken werden berechnet
✅ Market-Conditions bei jedem Signal
✅ Mind. 100 market_conditions Einträge
✅ Alerts werden persistent gespeichert
✅ Dashboard-Queries < 100ms
```

---

## 📊 TRACKING-COVERAGE PROGRESSION

```
PHASE 1 (Baseline):
████████████████████░░░░░░░░░░░  70% - Basis-Tracking

PHASE 2 (+ risk_events + execution_analysis):
██████████████████████████░░░░░  90% - Kritisches Tracking

PHASE 3 (+ performance_metrics + market_conditions):
████████████████████████████████ 100% - Komplettes Tracking ✅
```

---

## 🛠️ MIGRATION-STRATEGIE

### Sicherer Migrations-Ansatz:

**Phase 1 → Phase 2**:
```sql
-- Backup vor Migration
pg_dump -U claire_user -d claire_de_binare > backup_phase1.sql

-- Migration ausführen
psql -U claire_user -d claire_de_binare < DATABASE_SCHEMA_v2.sql

-- Validieren
SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1;
-- Erwartung: '2.0.0'
```

**Phase 2 → Phase 3**:
```sql
-- Backup
pg_dump -U claire_user -d claire_de_binare > backup_phase2.sql

-- Migration
psql -U claire_user -d claire_de_binare < DATABASE_SCHEMA_v3.sql

-- Validieren
SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1;
-- Erwartung: '3.0.0'
```

---

## 📈 ERWARTETE DATEN-VOLUMEN

### Phase 1 (Baseline):
- **800 KB/Tag** (~3,400 Events)

### Phase 2 (+ risk_events + execution_analysis):
- **1.2 MB/Tag** (~5,000 Events)
  - +200 KB risk_events
  - +200 KB execution_analysis

### Phase 3 (Komplett):
- **2.0 MB/Tag** (~8,000 Events)
  - +500 KB market_conditions (1/min)
  - +100 KB performance_metrics
  - +200 KB alerts

**6 Monate**: ~360 MB (sehr effizient!)

---

## 🎯 DECISION POINTS

### Nach Phase 1 (Entscheidung):
- ✅ **Weiter zu Phase 2?** Wenn Basis funktioniert
- ❌ **Stop?** Wenn Basis-Probleme auftreten

### Nach Phase 2 (Entscheidung):
- ✅ **Weiter zu Phase 3?** Wenn risk_events + execution_analysis wertvoll sind
- ⏸️ **Pause?** Wenn Phase 2 genug ist (90% Coverage)

### Nach Phase 3:
- ✅ **Production-Ready!** Komplettes Tracking-System

---

## 💡 JSONB-QUICK-WINS (Sofort nutzbar)

**Während Phase 1** - Nutze Metadata-Spalten besser:

### signals.metadata:
```json
{
  "indicators": {
    "rsi_14": 67.5,
    "macd": "bullish_cross",
    "bb_upper": 51200.0,
    "bb_lower": 48500.0
  },
  "signal_strength": 0.92,
  "market_regime": "trending_up",
  "volatility_1h": 0.025,
  "strategy_version": "v1.2.3",
  "confidence_factors": {
    "momentum": 0.85,
    "volume": 0.78,
    "trend": 0.95
  }
}
```

### trades.metadata:
```json
{
  "execution_venue": "MEXC_SPOT",
  "latency_ms": {
    "signal_to_order": 45,
    "order_to_fill": 120,
    "total": 165
  },
  "order_book_snapshot": {
    "bid_depth_usdt": 10000.0,
    "ask_depth_usdt": 8500.0,
    "spread_bps": 5
  },
  "market_conditions": {
    "price_before": 50000.0,
    "price_after": 50015.0,
    "volatility": 0.02
  }
}
```

### positions.metadata:
```json
{
  "max_unrealized_pnl": 850.50,
  "min_unrealized_pnl": -320.00,
  "max_unrealized_pnl_pct": 0.085,
  "min_unrealized_pnl_pct": -0.032,
  "holding_duration_hours": 4.5,
  "exit_reason": "take_profit",
  "exit_trigger": "manual",
  "risk_reward_ratio": 2.65,
  "trades_count": 3
}
```

---

## 🚀 TIMELINE

```
DAY 0:     Phase 1 START → Validate Baseline (1-2h)
DAY 0-1:   Phase 1 Paper-Trading Session (collect data)
DAY 1:     Phase 1 → Phase 2 Decision
DAY 1-2:   Phase 2 Implementation (4-6h)
DAY 2-3:   Phase 2 Paper-Trading Session
DAY 3:     Phase 2 → Phase 3 Decision
DAY 3-7:   Phase 3 Implementation (8-12h)
DAY 7-14:  Phase 3 Paper-Trading (1 week)
DAY 14:    Production-Ready Assessment ✅
```

---

## 🎯 SUCCESS METRICS

### Phase 1 Success:
- ✅ All 5 tables writable
- ✅ Data persistence confirmed
- ✅ Performance acceptable (<1ms INSERT)

### Phase 2 Success:
- ✅ Risk rejection reasons analyzable
- ✅ Execution latency measurable
- ✅ Slippage causes identifiable

### Phase 3 Success:
- ✅ Automated performance reporting
- ✅ Market-context correlation analysis
- ✅ Alert history tracking
- ✅ Dashboard queries <100ms

---

**Status**: 📋 Roadmap definiert - Ready für Phase 1 Start! 🚀
