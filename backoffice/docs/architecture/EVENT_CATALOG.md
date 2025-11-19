# Event-Catalog – Claire de Binaire

**Version**: 2.0
**Status**: ✅ Implementiert
**Erstellt**: 2025-11-19
**Basiert auf**: EVENT_SOURCING_RESEARCH.md

---

## Übersicht

Dieser Catalog dokumentiert alle Event-Types im Claire de Binaire System. Jedes Event folgt dem **Event Sourcing v2 Schema** mit Pflichtfeldern für Tracing und Determinismus.

---

## Event-Schema v2 (Base)

### BaseEvent (alle Events erben davon)

**Pflichtfelder**:
```python
{
    "event_id": "uuid",           # Unique ID (UUID v4)
    "event_type": "string",       # Type des Events
    "timestamp": 1700000000000,   # Unix-Timestamp in ms
    "version": "2.0",             # Schema-Version
    "source": "cdb_service",      # Welcher Service (z.B. "cdb_risk")
}
```

**Optionale Felder (für Tracing)**:
```python
{
    "sequence_id": 12345,         # Monoton steigend (pro Service)
    "correlation_id": "uuid",     # End-to-End Flow-ID
    "causation_id": "uuid",       # Parent-Event-ID
}
```

**Zweck**:
- **event_id**: Eindeutige Identifikation jedes Events
- **sequence_id**: Ordering innerhalb eines Service-Streams
- **correlation_id**: Tracking über Services hinweg (MarketData → Signal → Order → Fill)
- **causation_id**: Direkter Parent (Fill.causation_id = Order.event_id)

---

## Event-Types

### 1. ClockEvent

**Type**: `clock`
**Producer**: System Clock / Backtest Simulator
**Consumer**: Alle Services (für deterministische Zeit)
**Retention**: 1 Tag

**Schema**:
```python
{
    "event_id": "uuid",
    "event_type": "clock",
    "timestamp": 1700000000000,
    "version": "2.0",
    "source": "system_clock",  # oder "backtest"

    # ClockEvent-spezifisch:
    "current_time": 1700000000000  # Aktuelle System-Zeit in ms
}
```

**Zweck**:
- Deterministische Zeit für Replays
- Statt `datetime.now()` lesen Services die Zeit aus ClockEvents
- Ermöglicht Backtests mit simulierter Zeit

**Usage**:
```python
# Produktion: Echte Zeit
clock = ClockEvent(current_time=ClockEvent.now(), source="system_clock")

# Backtest: Simulierte Zeit
clock = ClockEvent(current_time=backtest_ts, source="backtest")
```

---

### 2. MarketData

**Type**: `market_data`
**Producer**: Screener (WebSocket/REST)
**Consumer**: Signal Engine
**Channel**: Redis `market_data`
**Retention**: 7 Tage

**Schema**:
```python
{
    "event_id": "uuid",
    "event_type": "market_data",
    "timestamp": 1700000000000,
    "version": "2.0",
    "source": "cdb_screener",
    "sequence_id": 12345,
    "correlation_id": "uuid",  # Neue Flow-ID

    # MarketData-spezifisch:
    "symbol": "BTCUSDT",
    "price": 50000.0,
    "volume": 123.45,
    "pct_change": 2.5,  # Prozentuale Änderung
    "interval": "15m"   # Zeitintervall
}
```

**Zweck**:
- Marktdaten-Updates vom Screener
- Trigger für Signal-Generierung

---

### 3. Signal

**Type**: `signal`
**Producer**: Signal Engine
**Consumer**: Risk Manager
**Channel**: Redis `signals`
**Retention**: 90 Tage

**Schema**:
```python
{
    "event_id": "uuid",
    "event_type": "signal",
    "timestamp": 1700000000000,
    "version": "2.0",
    "source": "cdb_signal",
    "sequence_id": 12346,
    "correlation_id": "uuid",  # Gleiche ID wie MarketData
    "causation_id": "market_data_event_id",

    # Signal-spezifisch:
    "symbol": "BTCUSDT",
    "side": "BUY",  # oder "SELL"
    "confidence": 0.85,  # 0.0 - 1.0
    "reason": "Momentum: +2.5% (Schwelle: 2.0%)",
    "price": 50000.0,
    "pct_change": 2.5
}
```

**Zweck**:
- Trading-Signale vom Signal-Engine
- Enthält Kauf-/Verkaufsempfehlung

---

### 4. RiskDecision

**Type**: `risk_decision`
**Producer**: Risk Manager
**Consumer**: Execution Service / Analytics
**Channel**: Redis `risk_decisions` (neu)
**Retention**: 7 Jahre (Audit)

**Schema**:
```python
{
    "event_id": "uuid",
    "event_type": "risk_decision",
    "timestamp": 1700000000000,
    "version": "2.0",
    "source": "cdb_risk",
    "sequence_id": 12347,
    "correlation_id": "uuid",  # Gleiche ID wie Signal
    "causation_id": "signal_event_id",

    # RiskDecision-spezifisch:
    "signal_id": "signal_event_id",
    "approved": true,  # oder false
    "reason": null,  # Bei approved=false: "max_daily_drawdown_exceeded"
    "position_size": 0.5,  # Genehmigte Position-Größe
    "stop_price": 48000.0  # Berechneter Stop-Loss (optional)
}
```

**Zweck**:
- Audit-Trail für Risk-Entscheidungen
- Ermöglicht Replay und Analyse von Risk-Blockierungen

**Rejection-Reasons**:
- `max_daily_drawdown_exceeded` – Tagesverlust > 5%
- `max_exposure_reached` – Gesamt-Exposure > 30%
- `max_position_exceeded` – Position > 10% Kapital
- `circuit_breaker_active` – Emergency Stop aktiv
- `data_stale` – Daten zu alt (>60s)

---

### 5. Order

**Type**: `order`
**Producer**: Risk Manager
**Consumer**: Execution Service
**Channel**: Redis `orders`
**Retention**: 7 Jahre (Regulatorik)

**Schema**:
```python
{
    "event_id": "uuid",
    "event_type": "order",
    "timestamp": 1700000000000,
    "version": "2.0",
    "source": "cdb_risk",
    "sequence_id": 12348,
    "correlation_id": "uuid",  # Gleiche ID wie Signal
    "causation_id": "risk_decision_event_id",

    # Order-spezifisch:
    "symbol": "BTCUSDT",
    "side": "BUY",  # oder "SELL"
    "quantity": 0.5,  # Genehmigte Menge
    "stop_loss_pct": 0.04,  # 4% Stop-Loss
    "signal_id": "signal_event_id",
    "reason": "Momentum: +2.5%",
    "client_id": "optional_client_id"  # Optional
}
```

**Zweck**:
- Order-Instruktionen für Execution Service
- Enthält genehmigte Position-Größe und Stop-Loss

---

### 6. OrderResult (Fill)

**Type**: `order_result`
**Producer**: Execution Service
**Consumer**: Portfolio Manager / Database Writer
**Channel**: Redis `order_results`
**Retention**: 7 Jahre (Regulatorik)

**Schema**:
```python
{
    "event_id": "uuid",
    "event_type": "order_result",
    "timestamp": 1700000000000,
    "version": "2.0",
    "source": "cdb_execution",
    "sequence_id": 12349,
    "correlation_id": "uuid",  # Gleiche ID wie Order
    "causation_id": "order_event_id",

    # OrderResult-spezifisch:
    "order_id": "order_event_id",
    "status": "FILLED",  # oder "REJECTED", "ERROR"
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": 0.5,
    "filled_quantity": 0.5,  # Tatsächlich ausgeführt
    "price": 50100.0,  # Ausführungs-Preis
    "client_id": "optional_client_id",
    "error_message": null  # Bei status=ERROR
}
```

**Zweck**:
- Bestätigung der Order-Ausführung
- Enthält tatsächlichen Fill-Preis und Menge

**Status-Werte**:
- `FILLED` – Vollständig ausgeführt
- `REJECTED` – Broker hat abgelehnt
- `ERROR` – Technischer Fehler

---

### 7. Alert

**Type**: `alert`
**Producer**: Risk Manager / System
**Consumer**: Notifications / Monitoring
**Channel**: Redis `alerts`
**Retention**: 30 Tage

**Schema**:
```python
{
    "event_id": "uuid",
    "event_type": "alert",
    "timestamp": 1700000000000,
    "version": "2.0",
    "source": "cdb_risk",
    "sequence_id": 12350,

    # Alert-spezifisch:
    "level": "CRITICAL",  # INFO, WARNING, CRITICAL
    "code": "CIRCUIT_BREAKER_TRIGGERED",
    "message": "Circuit Breaker aktiviert: Tagesverlust -10%",
    "context": {
        "daily_pnl": -10000.0,
        "threshold": -10000.0
    }
}
```

**Zweck**:
- System-Alerts bei Limit-Verletzungen
- Monitoring und Notifications

**Alert-Codes**:
- `CIRCUIT_BREAKER_TRIGGERED` – Emergency Stop
- `MAX_DAILY_DRAWDOWN` – Tagesverlust-Limit
- `MAX_EXPOSURE` – Exposure-Limit
- `DATA_STALE` – Daten-Timeout
- `SERVICE_ERROR` – Service-Fehler

---

## Event-Flow Pipeline

```
┌──────────────┐
│ MEXC API     │
└──────┬───────┘
       ↓ 1. MarketData
┌──────────────┐
│ Screener     │ (cdb_screener)
└──────┬───────┘
       ↓ 2. Signal
┌──────────────┐
│ Signal Eng.  │ (cdb_signal)
└──────┬───────┘
       ↓ 3. RiskDecision
┌──────────────┐
│ Risk Manager │ (cdb_risk)
└──────┬───────┘
       ↓ 4. Order
┌──────────────┐
│ Execution    │ (cdb_execution)
└──────┬───────┘
       ↓ 5. OrderResult
┌──────────────┐
│ PostgreSQL   │
└──────────────┘
```

**correlation_id Flow**:
```
MarketData (corr_id: A)
  → Signal (corr_id: A, causation_id: MarketData.event_id)
    → RiskDecision (corr_id: A, causation_id: Signal.event_id)
      → Order (corr_id: A, causation_id: RiskDecision.event_id)
        → OrderResult (corr_id: A, causation_id: Order.event_id)
```

---

## Kausalität & Tracing

### correlation_id
- **Zweck**: End-to-End Tracing
- **Verhalten**: Bleibt gleich über gesamten Flow
- **Beispiel**: MarketData, Signal, RiskDecision, Order, OrderResult haben alle gleiche correlation_id

### causation_id
- **Zweck**: Direkter Parent
- **Verhalten**: Zeigt auf event_id des auslösenden Events
- **Beispiel**: Signal.causation_id = MarketData.event_id

### sequence_id
- **Zweck**: Ordering innerhalb eines Service
- **Verhalten**: Monoton steigend (pro Service)
- **Beispiel**: cdb_signal: 1, 2, 3, ...

---

## Retention-Policy

| Event-Type | Retention | Grund |
|-----------|-----------|-------|
| `clock` | 1 Tag | Nur für Debugging |
| `market_data` | 7 Tage | Hohe Frequenz, wenig Speicher |
| `signal` | 90 Tage | Backtests, Analyse |
| `risk_decision` | 7 Jahre | Audit, Regulatorik |
| `order` | 7 Jahre | Regulatorik (MiFID II) |
| `order_result` | 7 Jahre | Regulatorik (MiFID II) |
| `alert` | 30 Tage | Monitoring, Debugging |

**Archivierung**:
- **Nach 7 Tagen**: MarketData → Cold Storage (S3)
- **Nach 90 Tagen**: Signals → Cold Storage
- **Nach 1 Jahr**: Orders/OrderResults → Cold Storage (aber 7 Jahre aufbewahren)

---

## Versionierung

**Aktuell**: Schema v2.0

**Migration von v1.0 → v2.0**:
- ✅ Hinzugefügt: `event_id`, `sequence_id`, `correlation_id`, `causation_id`, `version`, `source`
- ✅ Neuer Event-Type: `risk_decision`
- ✅ Neuer Event-Type: `clock`

**Backward-Kompatibilität**:
- v1.0 Events ohne neue Felder werden beim Lesen mit Defaults gefüllt
- v2.0 Events sind forward-kompatibel (alte Services ignorieren neue Felder)

---

## Testing

**Golden Run Tests**:
- ✅ 9/9 Tests bestanden (tests/test_golden_run.py)
- State-Hashing für Replay-Validierung
- Determinismus-Tests für ClockEvent
- End-to-End Tracing-Tests

**Unit Tests**:
- Event Serialization (to_dict / from_dict)
- correlation_id Tracking
- causation_id Chaining

---

## Implementierungs-Status

| Event-Type | Schema v2 | Tests | Docs | Status |
|-----------|-----------|-------|------|--------|
| BaseEvent | ✅ | ✅ | ✅ | Done |
| ClockEvent | ✅ | ✅ | ✅ | Done |
| RiskDecisionEvent | ✅ | ✅ | ✅ | Done |
| MarketData | 🔄 | ⏳ | ✅ | Migration pending |
| Signal | 🔄 | ⏳ | ✅ | Migration pending |
| Order | 🔄 | ⏳ | ✅ | Migration pending |
| OrderResult | 🔄 | ⏳ | ✅ | Migration pending |
| Alert | 🔄 | ⏳ | ✅ | Migration pending |

**Nächste Schritte**:
1. MarketData auf BaseEvent migrieren
2. Signal auf BaseEvent migrieren
3. Order auf BaseEvent migrieren
4. OrderResult auf BaseEvent migrieren
5. Alert auf BaseEvent migrieren

---

**Version**: 2.0
**Autor**: Claire de Binaire Team
**Review**: TBD
**Approval**: TBD
