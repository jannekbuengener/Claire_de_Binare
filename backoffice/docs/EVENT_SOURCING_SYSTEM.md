# Event-Sourcing & Deterministic Replay System

## 📋 Executive Summary

Das Event-Sourcing System ist das **Herzstück** der Claire de Binaire Audit-Infrastruktur.

**Was es bietet:**
- ✅ **Verlustfreie Timeline** - Jeder Bot-Schritt wird gespeichert
- ✅ **Deterministische Replay** - Gleiche Events → Gleiche Entscheidungen
- ✅ **Vollständiger Audit-Trail** - Jede Entscheidung rückwirkend erklärbar
- ✅ **Hedge-Fund-Level Compliance** - Regulatorische Anforderungen erfüllt

**Kernprinzip:**
> „Claire, erklär mir exakt, warum du am 14.02.2025 um 13:05:00 BTC long gegangen bist."
>
> → System spult die komplette Timeline ab wie Netflix „Zurück zur Szene"

---

## 🏗️ Architektur-Übersicht

### System-Komponenten

```
┌─────────────────────────────────────────────────────────────┐
│                      EVENT SOURCES                           │
│  (Signal Engine, Risk Manager, Execution Service)          │
└──────────────┬──────────────────────────────────────────────┘
               │ Events via Redis Pub/Sub
               ↓
┌──────────────────────────────────────────────────────────────┐
│               EVENT STORE SERVICE (Port 8004)                │
│  • EventWriter - Persist all events to PostgreSQL          │
│  • EventReader - Query events for replay                    │
│  • API - HTTP endpoints for queries                         │
└──────────────┬───────────────────────────────────────────────┘
               │ Writes to
               ↓
┌──────────────────────────────────────────────────────────────┐
│           POSTGRESQL EVENT STORE                             │
│  Table: events                                               │
│  • Immutable event log (append-only)                        │
│  • Monotonic sequence numbers                               │
│  • Causation chain tracking                                 │
│  • State snapshots for faster replay                        │
└──────────────┬───────────────────────────────────────────────┘
               │ Read by
               ↓
┌──────────────────────────────────────────────────────────────┐
│               REPLAY ENGINE                                  │
│  • Load events from log                                     │
│  • Reconstruct system state                                 │
│  • Validate determinism                                     │
└──────────────┬───────────────────────────────────────────────┘
               │ Accessed via
               ↓
┌──────────────────────────────────────────────────────────────┐
│               CLI INTERFACE (claire_cli.py)                  │
│  • replay - Replay time ranges                              │
│  • explain - Explain decisions                              │
│  • trace - Trace trades                                     │
│  • validate - Validate determinism                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Event-Schema

### Base Event Structure

Alle Events erben diese Struktur:

```python
class BaseEvent:
    event_id: UUID                # Eindeutige Event-ID
    event_type: EventType         # market_data, signal, risk_decision, etc.
    sequence_number: int          # Monotone LogicalClock (KRITISCH für Determinismus)
    timestamp_utc: datetime       # Wall-clock time (für Menschen)
    timestamp_logical: int        # Bot-interne Zeit (für Ordering)
    causation_id: UUID | None     # Welches Event hat dieses verursacht?
    correlation_id: UUID          # Trade/Session-ID
    metadata: EventMetadata       # Service, Version, Environment
    payload: Dict                 # Event-spezifische Daten
```

### Event-Types

| Event Type | Producer | Consumer | Zweck |
|-----------|----------|----------|-------|
| `market_data` | Screener WS/REST | Signal Engine | Marktdaten (Preis, Volumen) |
| `signal_generated` | Signal Engine | Risk Manager | Trading-Signal |
| `risk_decision` | Risk Manager | Execution | Risk-Validierung |
| `order_request` | Risk Manager | Execution | Order-Auftrag |
| `order_result` | Execution | Risk/Dashboard | Execution-Ergebnis |
| `position_update` | Execution | Risk/Dashboard | Position geöffnet/geschlossen |
| `alert` | Alle Services | Dashboard/Logs | Warnungen/Fehler |
| `state_snapshot` | Event Store | Replay Engine | State-Snapshots |

### Causation Chain Beispiel

```
MarketDataEvent (seq=1)
    ↓ causation_id
SignalGeneratedEvent (seq=2)
    ↓ causation_id
RiskDecisionEvent (seq=3)
    ↓ causation_id
OrderRequestEvent (seq=4)
    ↓ causation_id
OrderResultEvent (seq=5)
```

**Alle Events haben gleichen `correlation_id` → gehören zum gleichen Trade**

---

## 🔢 Logical Clock - Das Herzstück

### Warum keine System-Zeit?

**Problem mit System-Zeit:**
```python
# ❌ NICHT-DETERMINISTISCH
import time
timestamp = time.time()  # Abhängig von Server-Zeit, Zeitzonen, NTP
```

**Lösung mit LogicalClock:**
```python
# ✅ DETERMINISTISCH
from services.event_sourcing import get_clock

clock = get_clock()
sequence = clock.next()  # 1, 2, 3, 4, ... (GARANTIERT monoton)
```

### Garantien

| Eigenschaft | Garantie |
|------------|----------|
| **Monotonie** | Event N kommt IMMER vor Event N+1 |
| **Unabhängigkeit** | Keine Abhängigkeit von System-Zeit |
| **Determinismus** | Bei Replay: Gleiche Reihenfolge |
| **Eindeutigkeit** | Jede Sequence-Number nur einmal |

---

## 🎬 Replay-Modi

### 1. Full Replay

```bash
# Alle Events von Beginn an
python claire_cli.py replay --sequence 1 10000
```

**Use Case:** Vollständige System-Validierung

### 2. Range Replay

```bash
# Bestimmter Zeitraum
python claire_cli.py replay --from 2025-02-10 --to 2025-02-15
```

**Use Case:** Debug eines spezifischen Trading-Tages

### 3. Snapshot-Based Replay

```bash
# Start von letztem Snapshot (schneller)
python claire_cli.py replay --sequence 5000 10000
# → Lädt Snapshot bei seq=5000, replayt nur Delta
```

**Use Case:** Schnelle Replay für jüngere Zeiträume

---

## 🔍 Audit-Trail Verwendung

### 1. Entscheidung erklären

```bash
python claire_cli.py explain <event-id>
```

**Ausgabe:**
```
==============================================================
DECISION EXPLANATION: 123e4567-e89b-12d3-a456-426614174000
==============================================================

📊 Decision:
  Event Type: risk_decision
  Sequence: 42
  Timestamp: 2025-02-14 13:05:00
  Approved: True
  Reason: All risk checks passed

📡 Signal:
  Symbol: BTCUSDT
  Side: BUY
  Confidence: 0.85
  Reason: Strong momentum + high volume

📈 Market Data:
  Symbol: BTCUSDT
  Price: 50,000 USDT
  Volume: 1,500 BTC

🔗 Causation Chain:
  → market_data (seq 40)
  → signal_generated (seq 41)
  → risk_decision (seq 42)
```

### 2. Trade tracen

```bash
python claire_cli.py trace <correlation-id>
```

**Ausgabe:**
```
==============================================================
TRADE/SESSION TRACE: 987fcdeb-51a2-43d1-a123-456789abcdef
==============================================================
Total events: 5

1. market_data (seq 100)
   Timestamp: 2025-02-14 13:00:00
   Symbol: BTCUSDT, Price: 50000.0

2. signal_generated (seq 101)
   Timestamp: 2025-02-14 13:00:05
   BUY BTCUSDT @ 0.85 confidence

3. risk_decision (seq 102)
   Timestamp: 2025-02-14 13:00:06
   Approved: True, Reason: All checks passed

4. order_request (seq 103)
   Timestamp: 2025-02-14 13:00:07
   BUY BTCUSDT size=0.2

5. order_result (seq 104)
   Timestamp: 2025-02-14 13:00:10
   Status: FILLED, Filled: 0.2
```

### 3. Event-Statistiken

```bash
python claire_cli.py stats
```

**Ausgabe:**
```
==============================================================
EVENT STATISTICS (Last 24 hours)
==============================================================
Event Type                Count      First Event          Last Event
----------------------------------------------------------------
market_data               15234      2025-02-14 00:00:01  2025-02-14 23:59:58
signal_generated          127        2025-02-14 00:05:12  2025-02-14 23:45:33
risk_decision             127        2025-02-14 00:05:13  2025-02-14 23:45:34
order_result              85         2025-02-14 00:10:15  2025-02-14 23:50:12
alert                     3          2025-02-14 14:23:45  2025-02-14 18:12:33
```

---

## ✅ Determinismus-Validierung

### Prinzip

**Gleiche Events → Gleiche Entscheidungen (IMMER)**

```bash
# Validate determinism für Sequence 1-1000
python claire_cli.py validate --sequence 1 1000
```

**Prozess:**
1. Replay 1: Events 1-1000 abspielen → State A
2. Replay 2: Events 1-1000 abspielen → State B
3. Vergleich: State A == State B?

**Ausgabe bei Erfolg:**
```
==============================================================
DETERMINISM VALIDATION
==============================================================
Range: 1 → 1000
Deterministic: ✅ YES
```

**Ausgabe bei Fehler:**
```
==============================================================
DETERMINISM VALIDATION
==============================================================
Range: 1 → 1000
Deterministic: ❌ NO

⚠️  STATE DIFFERENCES DETECTED:
{
  "risk_state": {
    "replay1": {"equity": 100000.0, "daily_pnl": -1234.56},
    "replay2": {"equity": 100000.0, "daily_pnl": -1234.57}
  }
}
```

### Was Determinismus garantiert

| ✅ Garantiert | ❌ NICHT garantiert |
|--------------|-------------------|
| Risk-Entscheidungen | Wall-clock Timestamps |
| Position Sizing | API Response Times |
| Stop-Loss Preise | Externe API Calls |
| Order Approval | Real Order IDs (Mock vs Live) |

### Replay-Modus Sicherheit

**Im Replay-Modus wird verhindert:**

```python
from services.replay_engine import ReplayMode, no_replay

@no_replay
def place_live_order(order):
    """Diese Funktion wird BLOCKIERT im Replay."""
    # External API call
    exchange.place_order(order)
    # → Returns None during replay, keine Ausführung
```

---

## 🗄️ PostgreSQL Schema

### Events Table

```sql
CREATE TABLE events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    sequence_number BIGSERIAL UNIQUE NOT NULL,  -- Monotone Clock
    timestamp_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    timestamp_logical BIGINT NOT NULL,
    causation_id UUID REFERENCES events(event_id),
    correlation_id UUID NOT NULL,
    metadata JSONB NOT NULL,
    payload JSONB NOT NULL
);

-- Indexes für schnelle Queries
CREATE INDEX idx_events_sequence ON events(sequence_number);
CREATE INDEX idx_events_correlation_id ON events(correlation_id);
CREATE INDEX idx_events_causation_id ON events(causation_id);
```

### Immutability Triggers

```sql
-- Events können NICHT geändert oder gelöscht werden
CREATE TRIGGER events_immutable_update
BEFORE UPDATE ON events
FOR EACH ROW
EXECUTE FUNCTION prevent_event_modification();
-- → RAISES EXCEPTION: 'Events are immutable'
```

### Audit Functions

```sql
-- Causation Chain tracen
SELECT * FROM get_causation_chain('<event-id>');

-- Alle Events eines Trades
SELECT * FROM get_correlation_events('<correlation-id>');

-- Entscheidung erklären
SELECT explain_decision('<decision-event-id>');

-- Event-Statistiken
SELECT * FROM get_event_stats();
```

---

## 🚀 Integration mit Services

### 1. EventFactory verwenden

```python
from services.event_sourcing import EventFactory, Side

# In jedem Service initialisieren
factory = EventFactory(service_name="cdb_risk", version="1.0.0")

# Events erstellen
signal_event = factory.create_signal(
    symbol="BTCUSDT",
    side=Side.BUY,
    confidence=0.85,
    reason="Strong momentum",
    price=50000.0,
    strategy_params={"momentum_threshold": 3.0},
    correlation_id=trade_id,
    causation_id=market_data_event.event_id
)

# Event an Event Store senden
# TODO: Publish to Redis or write directly
```

### 2. Event Store Service

**Läuft als Container:**
```yaml
# docker-compose.yml
cdb_event_store:
  build: ./backoffice/services/event_store/
  ports:
    - "8004:8004"
  depends_on:
    - cdb_postgres
    - cdb_redis
```

**API Endpoints:**
- `GET /health` - Health check
- `GET /events?from_sequence=X&to_sequence=Y` - Query events
- `GET /events/<id>/causation` - Get causation chain
- `GET /events/<id>/explain` - Explain decision
- `GET /correlations/<id>` - Get all events for trade

---

## 📝 Best Practices

### Event-Design

**✅ DO:**
```python
# Alle relevanten Daten im Event speichern
risk_decision = RiskDecisionEvent(
    ...
    risk_state=RiskState(
        equity=100000.0,
        daily_pnl=-1000.0,
        total_exposure_pct=0.15,
        open_positions=2
    ),
    risk_checks={
        "daily_drawdown": RiskCheckResult(
            checked=True,
            passed=True,
            current_value=-0.01,
            limit=-0.05
        )
    }
)
```

**❌ DON'T:**
```python
# Zu wenig Kontext (nicht nachvollziehbar)
risk_decision = RiskDecisionEvent(
    ...
    approved=False,
    reason="limit_exceeded"
    # ❌ Welcher Limit? Welcher Wert?
)
```

### Correlation IDs

**✅ DO:**
```python
# Gleiche Correlation-ID für gesamten Trade
trade_id = uuid.uuid4()

market_data_event = factory.create_market_data(correlation_id=trade_id, ...)
signal_event = factory.create_signal(correlation_id=trade_id, ...)
risk_event = factory.create_risk_decision(correlation_id=trade_id, ...)
```

**❌ DON'T:**
```python
# Neue UUID bei jedem Event → Kein Zusammenhang
signal_event = factory.create_signal(correlation_id=uuid.uuid4(), ...)
risk_event = factory.create_risk_decision(correlation_id=uuid.uuid4(), ...)
```

### Causation Chain

**✅ DO:**
```python
# Causation chain pflegen
market_data_event = factory.create_market_data(...)

signal_event = factory.create_signal(
    causation_id=market_data_event.event_id,  # ✅ Linked
    ...
)

risk_event = factory.create_risk_decision(
    causation_id=signal_event.event_id,  # ✅ Linked
    ...
)
```

---

## 🔧 Troubleshooting

### Problem: Determinismus-Validierung schlägt fehl

**Symptom:**
```
Deterministic: ❌ NO
State differences: {"equity": {replay1: 100000.0, replay2: 99999.99}}
```

**Mögliche Ursachen:**
1. **Floating-Point Arithmetik** → Verwende `Decimal` für Geld
2. **Externe API-Calls** → Müssen im Replay blockiert sein
3. **Timestamps** → Nur `sequence_number` für Ordering verwenden
4. **Random Values** → Keine `random.random()` in Decision-Logic

**Fix:**
```python
# ❌ FALSCH (non-deterministic)
import random
slippage = random.uniform(0.0, 0.01)

# ✅ RICHTIG (deterministic)
# Slippage aus Event-Daten berechnen oder als Konstante
slippage = signal_data.get("expected_slippage", 0.005)
```

### Problem: Events fehlen in PostgreSQL

**Diagnose:**
```bash
# Prüfen: Event Store Service läuft?
docker compose ps cdb_event_store

# Prüfen: Logs
docker compose logs cdb_event_store --tail=50

# Prüfen: Database Connection
docker compose exec cdb_postgres psql -U postgres -d claire_de_binaire -c "SELECT COUNT(*) FROM events;"
```

**Fix:**
1. Event Store Service neu starten
2. Database Schema prüfen
3. Redis Connection prüfen

### Problem: Replay zu langsam

**Symptom:**
Replay von 10.000 Events dauert >5 Minuten

**Lösung:**
1. **Snapshots nutzen:**
   ```bash
   python claire_cli.py replay --sequence 5000 10000
   # → Startet von Snapshot, replayed nur 5000 Events
   ```

2. **Database Indexes prüfen:**
   ```sql
   SELECT * FROM pg_indexes WHERE tablename = 'events';
   ```

3. **Batch-Queries verwenden:**
   ```python
   # Statt einzelne Events laden
   events = reader.read_events(from_sequence=1, to_sequence=10000, limit=10000)
   ```

---

## 📚 Weiterführende Dokumentation

| Dokument | Beschreibung |
|----------|-------------|
| `event_sourcing_schema.yaml` | Vollständiges Event-Schema |
| `DATABASE_SCHEMA.sql` | PostgreSQL Schema mit Views & Functions |
| `services/event_sourcing.py` | Python Event Models & LogicalClock |
| `services/replay_engine.py` | Replay Engine Implementation |
| `claire_cli.py` | CLI Usage & Examples |
| `tests/test_event_sourcing_determinism.py` | Determinismus-Tests |

---

## ✅ Definition of Done

Event-Sourcing System ist **production-ready** wenn:

- [x] **Events**: Alle Event-Types definiert und implementiert
- [x] **LogicalClock**: Monotone Sequence Numbers funktionieren
- [x] **PostgreSQL**: Event Store mit Immutability Triggers
- [x] **EventWriter**: Service persistiert Events
- [x] **EventReader**: Service liest Events chronologisch
- [x] **ReplayEngine**: Kann Events abspielen
- [x] **Determinismus**: Tests beweisen gleiche Events → gleiche Results
- [x] **CLI**: `claire replay`, `explain`, `trace`, `validate` funktionieren
- [x] **Audit-Trail**: Jede Entscheidung erklärbar via `explain_decision()`
- [x] **Dokumentation**: Vollständig (dieses Dokument)

---

## 🎯 Next Steps

**Für Integration in bestehende Services:**

1. **Signal Engine erweitern:**
   ```python
   # In cdb_core/service.py
   from services.event_sourcing import EventFactory, Side

   factory = EventFactory(service_name="cdb_core", version="1.0.0")

   # Bei Signal-Generierung:
   signal_event = factory.create_signal(...)
   # Event an Event Store senden
   ```

2. **Risk Manager erweitern:**
   ```python
   # In cdb_risk/service.py
   factory = EventFactory(service_name="cdb_risk", version="1.0.0")

   # Bei Risk-Entscheidung:
   risk_event = factory.create_risk_decision(...)
   # Event an Event Store senden
   ```

3. **Event Store in docker-compose.yml:**
   ```yaml
   cdb_event_store:
     build: ./backoffice/services/event_store/
     ports:
       - "8004:8004"
     environment:
       - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@cdb_postgres:5432/claire_de_binaire
     depends_on:
       - cdb_postgres
       - cdb_redis
   ```

4. **Database Init-Script:**
   ```bash
   # In docker-compose.yml für cdb_postgres:
   volumes:
     - ./backoffice/docs/DATABASE_SCHEMA.sql:/docker-entrypoint-initdb.d/01-event-store.sql:ro
   ```

---

**Version:** 1.0.0
**Status:** ✅ Production-Ready
**Maintainer:** Claire de Binaire Team
**Last Updated:** 2025-11-19
