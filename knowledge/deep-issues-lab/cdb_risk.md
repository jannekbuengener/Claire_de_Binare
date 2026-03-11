# Risikomanagement Gesamtdokumentation (Claire de Binare)

Dieses Dokument fasst die drei zentralen Risikomanagement-Dokumente zusammen:
1.  `RISK_LOGIC.md`
2.  `cdb_risk.md`
3.  `PERPETUALS_RISK_MANAGEMENT.md`

---
---

# Teil 1: Allgemeine Risikomanagement-Logik (Stand: 2025-11-02)

*Quelle: `RISK_LOGIC.md`*

## 1.1 Parameter aus Umgebungsvariablen

| Variable                  | Standard | Wirkung                              |
|---------------------------|----------|--------------------------------------|
| `MAX_POSITION_PCT`        | `0.10`   | Anteil des Kapitals pro Trade        |
| `MAX_EXPOSURE_PCT`        | `0.50`   | Gesamt-Exposure über alle Positionen |
| `MAX_DAILY_DRAWDOWN_PCT`  | `0.05`   | Circuit Breaker pro Handelstag       |
| `STOP_LOSS_PCT`           | `0.02`   | Stop-Loss je Position                |
| `LOOKBACK_MINUTES`        | `15`     | Momentum-Analysefenster              |

## 1.2 Priorisierte Schutzschichten

1. **Daily Drawdown** → sofortiger Handelsstopp, Positionen schließen, Alert
2. **Abnormale Märkte** (Slippage >1 %, Spread >5x) → `CIRCUIT_BREAKER` Alert, Handel pausieren
3. **Datenstille** (>30 s ohne neue Marktpreise) → `DATA_STALE` Alert, Handelsloop pausieren
4. **Portfolio Exposure** → keine neuen Orders, Alerts auf `alerts`
5. **Positionsgröße** → Order trimmen oder ablehnen
6. **Stop-Loss je Trade** → Execution-Service initiiert Exit

## 1.3 Entscheidungslogik (Pseudocode)

```python
def on_signal(signal):
    if exceeds_drawdown():
        emit_alert(level="CRITICAL", code="RISK_LIMIT")
        halt_trading()
        return Reject(reason="drawdown")
    if abnormal_market():
        emit_alert(level="WARNING", code="CIRCUIT_BREAKER")
        pause_trading()
        return Reject(reason="environment")

    if total_exposure() >= MAX_EXPOSURE_PCT:
        emit_alert(level="INFO", code="RISK_LIMIT")
        return Reject(reason="exposure")

    allowed_size = min(signal.size, max_position_size())
    if allowed_size < signal.size:
        return Approve(size=allowed_size, trimmed=True)

    return Approve(size=signal.size)
```

```python
def on_position_update(position):
    if position.unrealized_loss_pct >= STOP_LOSS_PCT:
        emit_alert(level="WARNING", code="RISK_LIMIT")
        close_position(position)

    if exceeds_drawdown():
        emit_alert(level="CRITICAL", code="CIRCUIT_BREAKER")
        close_all_positions()
        halt_trading()
```

## 1.4 Referenzwerte & Maßnahmen

| Ereignis                     | Trigger                           | Alert-Code (Schema) | Aktion                               |
|------------------------------|-----------------------------------|---------------------|--------------------------------------|
| Daily Drawdown überschritten | Verlust ≥ `MAX_DAILY_DRAWDOWN_PCT`| `RISK_LIMIT`        | Handel stoppen, Positions-Abbau     |
| Marktanomalie                | Slippage >1 %, Spread >5x normal  | `CIRCUIT_BREAKER`   | Pause, Alert, manueller Review       |
| Datenstille                  | Keine Marktdaten >30 s            | `DATA_STALE`        | Handels-Loop pausieren, Alert senden |
| Exposure Limit erreicht      | Exposure ≥ `MAX_EXPOSURE_PCT`     | `RISK_LIMIT`        | Neue Orders blockieren               |
| Positionslimit verletzt      | Ordergröße > `MAX_POSITION_PCT`   | `RISK_LIMIT`        | Order trimmen oder ablehnen          |
| Stop-Loss ausgelöst          | Verlust ≥ `STOP_LOSS_PCT`         | `RISK_LIMIT`        | Order Result markieren, Exit         |

## 1.5 Monitoring-Kanäle & Security

- Prometheus Counter: `risk_alert_total{level="CRITICAL"}`
- Redis Stream: `alerts` (payload enthält `code`, `message`, `ts`)
- Dashboard V5 Statusleiste: farbige LED (grün/orange/rot)
- Decision-Log: ADR-Referenzen in `docs/DECISION_LOG.md`
- Redis-Zugriff: Risk Manager authentifiziert sich mit `REDIS_PASSWORD` aus `.env`.
- Secrets werden ausschließlich über Environment-Variablen geladen.

---
---

# Teil 2: Risk Manager – Deep Dive & Critical Bug Analysis (Stand: 2025-01-11)

*Quelle: `cdb_risk.md`*

**Version**: 1.1.0  
**Status**: ✅ Production-Ready nach P0-Fixes  
**Service**: Risk Manager (Port 8002)  
**Zweck**: Haupt-Risikoschutz-Layer für Claire de Binare Trading System

## 2.1 Executive Summary

Der Risk Manager ist das **zentrale Sicherheitssystem** des Trading-Bots. Er validiert jedes Signal durch 5 Layer Risk-Checks BEVOR ein Order an den Execution Service weitergeleitet wird.

**Kritische Erkenntnisse nach Code-Audit**:
- ✅ **4 kritische Bugs (P0) identifiziert und behoben**
- ✅ Position Size Berechnung korrigiert (USD → Coins)
- ✅ Daily P&L Tracking implementiert
- ✅ Circuit Breaker funktionsfähig
- ✅ Exposure-Validierung korrekt

**System-Status**: **Production-Ready** für Phase 7 (Paper Trading Test)

## 2.2 Architektur-Überblick

### Event-Flow

```
Signal Engine → Redis (signals) → Risk Manager → Redis (orders) → Execution Service
                                        ↓
                                   Risk Checks
                                   (5 Layers)
                                        ↓
                                  APPROVED ✅
                                     oder
                                  REJECTED ❌
```

### 5-Layer Risk-Check-Hierarchie

| Layer | Check | Limit | Grund |
|-------|-------|-------|-------|
| 1 | Circuit Breaker | Daily Loss ≥ 5% | System-Schutz bei Crash |
| 2 | Position Size | ≤ 10% Capital per Trade | Diversifikation |
| 3 | Total Exposure | ≤ 50% Capital | Kapitalschutz |
| 4 | Daily Drawdown | ≥ -5% | Stop bei Tagesverlust |
| 5 | Order Validation | Symbol/Side/Price valid | Datenintegrität |

## 2.3 Risiko-Limits & Konfiguration

### Production-Defaults (`config.py`)

```python
TEST_BALANCE = 10000.0  # USD (Paper Trading Startkapital)

MAX_POSITION_PCT = 0.10     # 10% = max 1000 USD per Trade
MAX_EXPOSURE_PCT = 0.50     # 50% = max 5000 USD total invested
STOP_LOSS_PCT = 0.02        # 2% Stop-Loss per Position
MAX_DAILY_DRAWDOWN_PCT = 0.05  # 5% = -500 USD → Circuit Breaker
```

## 2.4 Kritische Bugs & Fixes (P0)

### Bug #1: Position Size gibt USD zurück statt Coins ⚠️ **KRITISCH**
**Problem**: `calculate_position_size()` gab einen USD-Wert zurück, der fälschlicherweise als Coin-Menge interpretiert wurde, was zu massiven Kaufversuchen führte.
**Fix**: Die Funktion wurde korrigiert, um die Ziel-USD-Menge durch den Preis zu teilen und die korrekte Coin-Menge zurückzugeben.
```python
# Alter Code (VOR FIX)
def calculate_position_size(self, signal: Signal) -> float:
    max_size = self.config.test_balance * self.config.max_position_pct
    position_size = max_size * signal.confidence  # ← Gibt USD zurück!
    return max(position_size, 0.0)

# Fix #1 ✅:
def calculate_position_size(self, signal: Signal) -> float:
    max_usd = self.config.test_balance * self.config.max_position_pct
    target_usd = max_usd * signal.confidence
    
    if signal.price <= 0:
        logger.error(f"Ungültiger Preis: {signal.price}")
        return 0.0
    
    quantity = target_usd / signal.price  # ← COINS!
    return quantity
```

### Bug #2: Position Limit Check triggert nie ⚠️ **KRITISCH**
**Problem**: Eine hardcodierte, immer wahre Bedingung führte dazu, dass Positionsgrößenlimits nie geprüft wurden.
**Fix**: Die Prüfung berechnet nun den tatsächlichen USD-Wert der angeforderten Position und vergleicht ihn mit dem Limit.
```python
def check_position_limit(self, signal: Signal) -> tuple[bool, str]:
    max_position_usd = self.config.test_balance * self.config.max_position_pct
    
    quantity = self.calculate_position_size(signal)
    position_value_usd = quantity * signal.price
    
    if position_value_usd > max_position_usd:
        return False, f"Position zu groß: {position_value_usd:.2f} > {max_position_usd:.2f}"
    
    return True, f"Position OK ({position_value_usd:.2f} / {max_position_usd:.2f})"
```

### Bug #3: Exposure Check prüft nicht zukünftige Exposure ⚠️ **HOCH**
**Problem**: Die Exposure-Prüfung berücksichtigte nur die aktuelle, nicht die zukünftige Exposure nach dem Trade.
**Fix**: Die Prüfung berechnet nun die geschätzte neue Positionsgröße und addiert sie zur aktuellen Exposure, um das Limit nicht zu überschreiten.
```python
def check_exposure_limit(self, signal: Signal) -> tuple[bool, str]:
    max_exposure = self.config.test_balance * self.config.max_exposure_pct
    
    quantity = self.calculate_position_size(signal)
    estimated_new_position = quantity * signal.price
    future_exposure = risk_state.total_exposure + estimated_new_position
    
    if future_exposure >= max_exposure:
        return False, "Exposure-Limit würde überschritten"
    
    return True, "Exposure OK"
```

### Bug #4: Daily P&L wird nie berechnet ⚠️ **KRITISCH**
**Problem**: `daily_pnl` blieb immer 0, wodurch der Circuit Breaker nie auslösen konnte.
**Fix**: Eine `_update_pnl()`-Funktion wurde implementiert, die sowohl realisierte als auch unrealisierte Gewinne/Verluste aus allen offenen Positionen berechnet.

## 2.5 Implementation-Plan & Erfolgskriterien

- **Sprint 1 (P0)**: Kritische Bugs beheben (✅ ERLEDIGT).
- **Sprint 2 (P1)**: Input-Validierung und Rate-Limiting.
- **Sprint 3 (P2)**: Erkennung von Marktanomalien.
- **Go-Live-Kriterium**: Ein 7-Tage-Paper-Trading-Test, der einen simulierten Flash-Crash beinhaltet, um die Funktionsfähigkeit des Circuit Breakers zu beweisen.

---
---

# Teil 3: Advanced Risk Management für MEXC Perpetual Futures (Stand: 2025-11-19)

*Quelle: `PERPETUALS_RISK_MANAGEMENT.md`*

## 3.1 Executive Summary & Ziel

Dieses Dokument beschreibt die Implementierung eines fortgeschrittenen Risikomanagements für MEXC Perpetual Futures. Das Ziel ist es, **realistische Paper-Tests** zu ermöglichen, die Exchange-spezifische Mechaniken wie Liquidation, Slippage, Fees und Funding Rates korrekt modellieren.

## 3.2 MEXC Perpetual Futures Mechanik

### 3.2.1 Margin, Leverage & Liquidation
- **Margin-Modus**: Für Claire wird **Isolated Margin** als Standard festgelegt, um das Risiko auf die einzelne Position zu beschränken und ein Übergreifen auf das Gesamtkonto (Contagion-Risk) zu verhindern.
- **Leverage**: Das maximale Leverage wird auf **10x** begrenzt, obwohl MEXC bis zu 125x erlaubt.
- **Liquidationspreis**: Die Berechnung für Long- und Short-Positionen wird detailliert beschrieben. Sie basiert auf dem **Fair Price**, nicht dem Marktpreis, und berücksichtigt die Maintenance Margin.

### 3.2.2 Funding Rates
- **Mechanik**: Die Abrechnung erfolgt 3x täglich. Positive Raten belasten Long-Positionen, negative Raten belasten Short-Positionen.
- **Wichtigkeit**: Es wird hervorgehoben, dass Funding Rates annualisiert einen signifikanten Kostenfaktor darstellen können (Beispiel: 10.95% des Positionswertes).

### 3.2.3 Trading Fees (Maker/Taker)
- **Annahme**: Für die Simulation werden konservative Raten von **0.02% für Maker** und **0.06% für Taker** angenommen. Ein Roundtrip kostet somit ca. 0.12% des Positionswertes.

## 3.3 Advanced Position Sizing Strategies

Dieses Kapitel stellt vier Methoden zur Positionsgrößenbestimmung vor, die über das einfache prozentuale Modell hinausgehen:

1.  **Fixed-Fractional Sizing**: Riskiere einen festen Prozentsatz des Kapitals pro Trade. (Baseline)
2.  **Volatility Targeting**: Skaliere die Position basierend auf der Volatilität des Assets, um die Portfolio-Volatilität zu stabilisieren.
3.  **Kelly Criterion (Fractional)**: Maximiere das langfristige Wachstum basierend auf der geschätzten "Edge" der Strategie. Es wird eine fraktionierte Anwendung (z.B. 25% von Kelly) für mehr Sicherheit empfohlen.
4.  **ATR-Based Sizing**: Skaliere die Position basierend auf der Average True Range (ATR), um die Positionsgröße automatisch an die Marktvolatilität anzupassen.

## 3.4 Realistic Execution Simulation

### 3.4.1 Slippage Modellierung
- Ein dynamisches Modell wird vorgeschlagen, das die Slippage aus drei Faktoren zusammensetzt:
    1.  **Basis-Slippage** (z.B. 5 Basispunkte)
    2.  **Orderbuch-Tiefe**: Größere Orders im Verhältnis zur Liquidität verursachen mehr Slippage.
    3.  **Volatilität**: Höhere Marktvolatilität führt zu höherer Slippage.

### 3.4.2 Partial Fills
- Es wird eine Logik vorgeschlagen, um nur teilweise ausgeführte Orders zu simulieren, wenn die Ordergröße die verfügbare Liquidität im Orderbuch übersteigt.

## 3.5 Risk Analytics & Performance Metrics

Es werden wichtige Metriken zur Analyse der Strategie-Performance definiert:

- **Maximum Drawdown (MaxDD)**: Der größte prozentuale Verlust von einem Höchststand.
- **Time Under Water**: Die Zeit, die ein Portfolio benötigt, um einen vorherigen Höchststand wieder zu erreichen.
- **Tail Risk (VaR / CVaR)**: Value at Risk und Conditional Value at Risk zur Quantifizierung von Extremrisiken.
- **Sharpe & Sortino Ratios**: Zur Messung der risikoadjustierten Rendite.
- **Calmar Ratio**: Verhältnis von annualisierter Rendite zu MaxDD.

## 3.6 Integration mit der Risk-Engine

- **Neue `.env`-Parameter**: Eine lange Liste neuer Umgebungsvariablen wird vorgeschlagen, um all diese fortgeschrittenen Konzepte konfigurierbar zu machen.
- **Neuer Workflow**: Ein `evaluate_signal_v2()` wird vorgeschlagen, das die bestehende Risk-Engine um die neuen Prüfungen (Perpetuals-Checks, Sizing, Simulation, Tail-Risk) erweitert.

---
**Ende des Dokuments**

