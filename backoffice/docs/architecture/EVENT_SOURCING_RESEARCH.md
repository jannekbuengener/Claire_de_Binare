# Event-Sourcing & Simulationsarchitektur für Trading-Systeme
## Research Deep-Dive für Claire de Binaire

**Erstellt**: 2025-11-19
**Status**: Research Report
**Scope**: Deterministisches Event-Sourcing, Replay-Architektur, Best Practices

---

## Executive Summary

Dieses Dokument fasst aktuelle Best Practices (2024/2025) für Event-Sourcing in Trading-Systemen zusammen und leitet konkrete Empfehlungen für die Weiterentwicklung von Claire de Binaire ab.

**Key Findings**:
1. **Event-Modellierung**: Klare Trennung von 5 Event-Typen (MarketData, Signal, Order, Fill, PortfolioState)
2. **Determinismus**: Seeded RNGs, Zeit als Input-Event, keine globalen Nebenwirkungen
3. **Snapshotting**: Erst ab 50-100 Events/Aggregate, nicht vorzeitig optimieren
4. **CQRS**: Klare Trennung Read/Write für Paper-Trading vs. Live-Systeme

---

## 1. Event-Modellierung für Trading

### 1.1 Core Event-Typen (Industry Standard)

Basierend auf **QuantStart Event-Driven Backtesting** und **LMAX Architecture**:

| Event-Type | Producer | Consumer | Payload | Retention |
|-----------|----------|----------|---------|-----------|
| **MarketData** | Screener/API | Signal Engine | price, volume, timestamp, symbol | 7 days |
| **Signal** | Signal Engine | Risk Manager | symbol, direction, confidence, reason | 90 days |
| **Order** | Risk Manager | Execution Service | symbol, quantity, price, order_type | 7 years |
| **Fill** | Execution Service | Portfolio Manager | executed_price, quantity, fees, slippage | 7 years |
| **PortfolioState** | Portfolio Manager | Analytics/DB | positions, cash, pnl, exposure | 7 years |

**Zusätzliche Event-Typen für Audit/Debug**:
- `RiskDecision` – Risk-Check Results (approved/rejected + reason)
- `Alert` – System-Alerts (errors, circuit breaker, etc.)
- `StrategyState` – Internal Strategy-State (für Replay)

### 1.2 Event-Schema Best Practices

**Pflichtfelder für ALLE Events**:
```python
{
    "event_id": "uuid",           # Unique ID
    "event_type": "market_data",  # Event-Type
    "timestamp": "ISO-8601",      # Wann erzeugt (UTC)
    "sequence_id": 12345,         # Monoton steigend (pro Service)
    "correlation_id": "uuid",     # Trace-ID (über Services hinweg)
    "causation_id": "uuid",       # Parent-Event-ID
    "version": "1.0",             # Schema-Version
    "source": "cdb_screener",     # Welcher Service
    "data": { ... }               # Event-Payload
}
```

**Kausalität modellieren**:
- **correlation_id**: Bleibt gleich über gesamten Flow (MarketData → Signal → Order → Fill)
- **causation_id**: ID des direkten Parent-Events (Fill.causation_id = Order.event_id)
- **sequence_id**: Lokale Sequenz-Nummer (pro Service), für Ordering innerhalb eines Streams

### 1.3 Claire de Binaire Status-Check

**✅ Bereits implementiert**:
- Event-Types: `market_data`, `signals`, `orders`, `order_results` ✅
- Redis Pub/Sub für Event-Bus ✅
- PostgreSQL für Persistence ✅

**🔄 Zu ergänzen**:
- [ ] **Event-ID/Sequence-ID**: Hinzufügen zu allen Events
- [ ] **correlation_id/causation_id**: Für End-to-End Tracing
- [ ] **Schema-Versioning**: Explizite Version in Events
- [ ] **RiskDecision-Events**: Separater Event-Type (nicht nur Logs)
- [ ] **PortfolioState-Events**: Snapshots nach jedem Fill

---

## 2. Determinismus & Reproducibility

### 2.1 Quellen von Non-Determinismus (und wie man sie eliminiert)

Basierend auf **Peter Lawrey's "Hyper-Deterministic HFT Systems"** (Dez 2024):

| Quelle | Problem | Lösung |
|--------|---------|--------|
| **System.currentTimeMillis()** | Jeder Replay gibt andere Zeit | Zeit als Event-Input (ClockEvent) |
| **Random()** | Unterschiedliche Zufallszahlen | Seeded RNG (fester Seed pro Run) |
| **UUID.randomUUID()** | Nicht reproduzierbar | Seeded UUID-Generator |
| **Netzwerk-Latenz** | Variable Timings | Latenz als Event-Attribut loggen |
| **Thread-Interleaving** | Race Conditions | Single-Threaded Event-Loop (LMAX-Style) |
| **Externe APIs** | Daten ändern sich | Record & Replay Pattern |

### 2.2 Deterministic Design Principles

**Regel 1: Zeit ist Input, nicht Output**
```python
# ❌ SCHLECHT (non-deterministic)
def generate_signal():
    now = datetime.now()  # System-Zeit
    if market_open(now):
        return create_signal()

# ✅ GUT (deterministic)
def generate_signal(clock_event: ClockEvent):
    now = clock_event.timestamp  # Event-Zeit
    if market_open(now):
        return create_signal()
```

**Regel 2: Seeded Randomness**
```python
# ❌ SCHLECHT
import random
random_value = random.random()  # Nicht reproduzierbar

# ✅ GUT
import random
random.seed(42)  # Fester Seed für Replay
random_value = random.random()  # Reproduzierbar

# ✅ BESSER (Seed aus Event)
def process_event(event, rng_state):
    rng = random.Random(rng_state["seed"])
    value = rng.random()
    rng_state["seed"] = rng.getstate()  # State für nächstes Event
    return value, rng_state
```

**Regel 3: Externe Dependencies als Events**
```python
# ❌ SCHLECHT
price = api.get_price("BTCUSDT")  # Externe API

# ✅ GUT
# 1. Live: API-Call → Event schreiben
api_event = {"type": "market_data", "price": api.get_price("BTCUSDT")}
event_store.append(api_event)

# 2. Replay: Event lesen
api_event = event_store.read_next()
price = api_event["price"]
```

### 2.3 Replay-Validation Patterns

**Golden Run Pattern** (aus Research zu "golden testing"):

1. **Initial Run**: Produktion läuft, Events werden geloggt
2. **Golden Run**: Replay in Test-Umgebung, Snapshots erstellen
3. **Regression Test**: Jeder Code-Change wird gegen Golden Run validiert

```python
# Golden Run Creation
golden_run = {
    "run_id": "2025-01-15_production",
    "events": [...],  # Alle Events
    "snapshots": {
        "after_event_100": hash_state(state_100),
        "after_event_500": hash_state(state_500),
        "final_state": hash_state(final_state)
    }
}

# Regression Test
def test_replay_matches_golden():
    replay_state = replay_events(golden_run["events"])
    assert hash_state(replay_state) == golden_run["snapshots"]["final_state"]
```

**State-Hashing** (für Vergleiche):
```python
import hashlib
import json

def hash_state(state: dict) -> str:
    """Deterministisch: sortierte Keys, JSON, SHA256"""
    normalized = json.dumps(state, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()
```

### 2.4 Claire de Binaire Status-Check

**✅ Bereits implementiert**:
- Event-Store für Replay ✅
- Deterministischer Kernel (laut CLAUDE.md) ✅
- Audit-Trail ✅

**🔄 Zu ergänzen**:
- [ ] **ClockEvent**: Zeit als explizites Event (nicht `datetime.now()`)
- [ ] **Seeded RNG**: Falls Randomness genutzt wird (z.B. bei Monte-Carlo-Sims)
- [ ] **Golden Run Tests**: Regression-Tests mit State-Hashing
- [ ] **Event-Store Isolation**: Separate Stores für Paper vs. Live

---

## 3. Snapshotting & Performance

### 3.1 Wann Snapshots erstellen?

**Industry Consensus** (aus CQRS/Event-Sourcing Research):

| Trigger | Schwellwert | Use-Case |
|---------|-------------|----------|
| **Event-Count** | 50-100 Events | Default für Aggregates |
| **Time-Based** | Täglich/Wöchentlich | Portfolio-Snapshots |
| **Behavioral** | Session-Ende | User-Actions (Netflix-Ansatz) |
| **Performance** | Replay >100ms | Wenn Rebuild zu langsam |

**Wichtigste Regel**: "Don't snapshot unless you actually need it" (aus Research)

### 3.2 Snapshot-Strategien

**Strategie 1: Event-Count-Based**
```python
class Portfolio:
    SNAPSHOT_INTERVAL = 50  # Alle 50 Events

    def apply_event(self, event):
        self.events.append(event)
        self._rebuild_state(event)

        if len(self.events) % self.SNAPSHOT_INTERVAL == 0:
            self.create_snapshot()

    def create_snapshot(self):
        snapshot = {
            "timestamp": self.events[-1]["timestamp"],
            "event_sequence": len(self.events),
            "state": self.current_state.copy()
        }
        snapshot_store.save(snapshot)
```

**Strategie 2: Time-Based** (für Claire de Binaire Portfolio)
```python
# Täglich um 00:00 UTC (nach Tagesabschluss)
def daily_portfolio_snapshot(portfolio_state):
    snapshot = {
        "type": "portfolio_snapshot",
        "timestamp": "2025-01-15T00:00:00Z",
        "positions": portfolio_state["positions"],
        "cash": portfolio_state["cash"],
        "daily_pnl": portfolio_state["daily_pnl"],
        "total_pnl": portfolio_state["total_pnl"]
    }
    db.save("portfolio_snapshots", snapshot)
```

**Strategie 3: Snapshot as Cache**
- Snapshot-Store kann jederzeit gelöscht werden
- Event-Store ist Source of Truth
- Snapshots nur für Performance-Optimierung

### 3.3 Snapshot-Rebuild Performance

**Trade-offs**:
- **Ohne Snapshot**: 1000 Events × 0.5ms = 500ms Rebuild-Zeit
- **Mit Snapshot (alle 50 Events)**: Snapshot laden (5ms) + 50 Events (25ms) = 30ms

**Wann lohnt sich Snapshotting?**
- ✅ Bei >100 Events pro Aggregate
- ✅ Bei Aggregates, die oft gelesen werden
- ❌ Bei Aggregates mit <50 Events
- ❌ Bei schreiblastigen Systemen (Snapshot-Overhead)

### 3.4 Event-Stream Partitioning & Archivierung

**Kafka Best Practices** (aus "Event stream partitioning" Research):

**Partitionierungs-Strategien**:
1. **Topic-per-Entity-Type**: `market_data`, `signals`, `orders` (← Claire de Binaire nutzt das)
2. **Topic-per-Entity**: `BTCUSDT_events`, `ETHUSDT_events` (für sehr hohe Volumen)
3. **Single-Topic**: Alle Events in einem Topic (nur für kleine Systeme)

**Archivierungs-Strategie**:
```yaml
# Retention-Policy für Claire de Binaire
topics:
  market_data:
    retention: 7 days      # Kurze Retention (hohe Frequenz)
    partition_key: symbol  # Nach Symbol partitionieren

  signals:
    retention: 90 days     # Mittel (für Backtests)
    partition_key: date    # Nach Tag partitionieren

  orders:
    retention: 7 years     # Lang (Regulatorik)
    partition_key: symbol
    archive_to: S3/PostgreSQL  # Nach 90 Tagen archivieren
```

**Wann Events archivieren?**
- MarketData: Nach 7 Tagen → Cold Storage (S3)
- Signals: Nach 90 Tagen → Cold Storage
- Orders/Fills: Nach 1 Jahr → Cold Storage (aber 7 Jahre aufbewahren)

### 3.5 Claire de Binaire Status-Check

**✅ Bereits implementiert**:
- PostgreSQL für Portfolio-Snapshots (Tabelle `portfolio_snapshots`) ✅
- Redis Message Bus (Topics: market_data, signals, orders) ✅

**🔄 Zu ergänzen**:
- [ ] **Snapshot-Policy definieren**: Wann Snapshots für Portfolio?
- [ ] **Retention-Policy**: Wie lange Events in Redis behalten?
- [ ] **Archivierungs-Strategie**: MarketData nach 7 Tagen archivieren?
- [ ] **Event-Store Größen-Monitoring**: Wann partitionieren/archivieren?

---

## 4. Architekturpatterns: CQRS & Paper/Live Separation

### 4.1 CQRS (Command Query Responsibility Segregation)

**Prinzip**: Writes und Reads trennen

```
┌─────────────┐
│ WRITE SIDE  │ (Commands → Events)
├─────────────┤
│ Event Store │ ← Append-Only
└──────┬──────┘
       │ Event Stream
       ↓
┌─────────────┐
│ READ SIDE   │ (Queries → Projections)
├─────────────┤
│ PostgreSQL  │ ← Optimized für Reads
└─────────────┘
```

**Vorteile für Trading-Systeme**:
- ✅ Write-Side: Optimiert für schnelle Order-Execution (In-Memory)
- ✅ Read-Side: Optimiert für Analytics/Reporting (Denormalized DB)
- ✅ Unabhängiges Scaling (mehr Read-Replicas bei Bedarf)
- ✅ Klare Trennung: Commands können nicht "versehentlich" lesen

**Claire de Binaire Mapping**:
| CQRS Layer | Claire Component | Storage |
|-----------|------------------|---------|
| **Write: Command** | Risk Manager (validate signal) | Redis Events |
| **Write: Event Store** | Event Store | PostgreSQL (events table) |
| **Read: Projection** | Trading Statistics | PostgreSQL (portfolio_snapshots, trades) |

### 4.2 Event Sourcing vs. CQRS

**Wichtig**: Event Sourcing ≠ CQRS (aber sie passen gut zusammen)

| Pattern | Zweck | Claire de Binaire |
|---------|-------|------------------|
| **Event Sourcing** | State aus Events rebuilden | ✅ Ja (Event Store, Replay) |
| **CQRS** | Writes und Reads trennen | 🔄 Teilweise (Redis vs. PostgreSQL) |

**Kombination ES + CQRS**:
```python
# Write Side (Event Sourcing)
def execute_order(order_command):
    events = []
    events.append({"type": "order_submitted", "data": order_command})
    # ... Business Logic
    events.append({"type": "order_filled", "data": fill_result})

    event_store.append_all(events)  # Append-Only
    return events

# Read Side (CQRS Projection)
def on_order_filled(event):
    """Event Handler: Update Read-DB"""
    db.execute("""
        INSERT INTO trades (symbol, price, quantity, timestamp)
        VALUES (:symbol, :price, :quantity, :timestamp)
    """, event["data"])
```

### 4.3 N1 (Paper) vs. N2+ (Live) Separation

**Architektur-Pattern**: Shared Event-Layer, Separate Execution

```
┌──────────────────────────────────────┐
│         SHARED EVENT LAYER           │
├──────────────────────────────────────┤
│ Signal Engine                        │
│ Risk Manager                         │
│ Event Store (Replay, Audit)          │
└──────────┬───────────────────────────┘
           │
     ┌─────┴─────┐
     ↓           ↓
┌─────────┐ ┌─────────┐
│ N1      │ │ N2+     │
│ PAPER   │ │ LIVE    │
├─────────┤ ├─────────┤
│ Mock    │ │ Real    │
│ Exec    │ │ Broker  │
│ Sim DB  │ │ Prod DB │
└─────────┘ └─────────┘
```

**Implementierungs-Strategie**:

1. **Shared Components** (identischer Code):
   - Signal Engine
   - Risk Manager
   - Event Store
   - Event Schema

2. **Environment-Specific** (via ENV-Variablen):
   - Execution Service (`EXECUTION_MODE=paper|live`)
   - Database (`POSTGRES_DB=claire_paper|claire_live`)
   - Broker API (`BROKER_API_URL=mock|real`)

```python
# Execution Service mit Mode-Switch
class ExecutionService:
    def __init__(self):
        self.mode = os.getenv("EXECUTION_MODE", "paper")

        if self.mode == "paper":
            self.executor = MockExecutor()  # Simuliert Fills
        elif self.mode == "live":
            self.executor = BrokerExecutor()  # Echte API
        else:
            raise ValueError(f"Invalid mode: {self.mode}")

    def execute_order(self, order):
        return self.executor.execute(order)  # Polymorphismus
```

**Vorteile**:
- ✅ **Code Reuse**: Signal/Risk-Logic identisch in Paper & Live
- ✅ **Safe Testing**: Paper-Modus kann nicht versehentlich echte Orders senden
- ✅ **Live-Nähe**: Paper-Modus nutzt echte MarketData & Risk-Checks
- ✅ **Gradual Rollout**: Paper → Live Transition durch ENV-Variable

**Testing-Strategie**:
| Phase | Environment | Purpose |
|-------|------------|---------|
| **N1-A** | `EXECUTION_MODE=paper` + Mock Data | Unit/Integration Tests |
| **N1-B** | `EXECUTION_MODE=paper` + Live Data | Paper-Trading (Live-Nähe) |
| **N2-A** | `EXECUTION_MODE=live` + Tiny Positions | Live-Pilot (min. Risk) |
| **N2-B** | `EXECUTION_MODE=live` + Full Positions | Production |

### 4.4 Claire de Binaire Status-Check

**✅ Bereits implementiert**:
- Paper-Trading Runner ✅
- Scenario Orchestrator ✅
- Event Store ✅
- ENV-basierte Config ✅

**🔄 Zu ergänzen**:
- [ ] **EXECUTION_MODE ENV**: Paper vs. Live explizit konfigurieren
- [ ] **Separate Databases**: `claire_paper` vs. `claire_live`
- [ ] **CQRS Read-Projections**: Optimierte Views für Analytics
- [ ] **Shared Event Schema**: Versioning für Schema-Kompatibilität

---

## 5. Konkrete Handlungsempfehlungen für Claire de Binaire

### 5.1 Kurzfristig (Sprint 1-2)

**Prio 1: Event-Schema erweitern**
```yaml
Tasks:
  - [ ] event_id (UUID) zu allen Events hinzufügen
  - [ ] sequence_id (monoton steigend) pro Service
  - [ ] correlation_id für End-to-End Tracing
  - [ ] causation_id für Parent-Event
  - [ ] Schema-Version ("1.0") explizit
  - [ ] RiskDecision als separaten Event-Type
```

**Prio 2: Determinismus härten**
```yaml
Tasks:
  - [ ] ClockEvent statt datetime.now()
  - [ ] Seeded RNG (falls genutzt)
  - [ ] Event-Store Isolation (Paper vs. Live)
  - [ ] Golden Run Test erstellen
```

**Prio 3: Dokumentation**
```yaml
Tasks:
  - [ ] Event-Catalog erstellen (alle Event-Types + Schema)
  - [ ] Retention-Policy dokumentieren
  - [ ] Replay-Runbook schreiben
```

### 5.2 Mittelfristig (Sprint 3-6)

**Prio 1: CQRS Read-Projections**
```yaml
Tasks:
  - [ ] Separate Read-DB für Analytics
  - [ ] Denormalisierte Views (trading_statistics, daily_pnl)
  - [ ] Event-Handler für Auto-Update
```

**Prio 2: Snapshotting**
```yaml
Tasks:
  - [ ] Portfolio-Snapshots (täglich)
  - [ ] Snapshot-Rebuild-Tests
  - [ ] Monitoring: Event-Count pro Aggregate
```

**Prio 3: Archivierung**
```yaml
Tasks:
  - [ ] MarketData nach 7 Tagen archivieren
  - [ ] Signals nach 90 Tagen archivieren
  - [ ] Cold-Storage (S3 oder PostgreSQL Archive)
```

### 5.3 Langfristig (Sprint 7+)

**Prio 1: Multi-Environment**
```yaml
Tasks:
  - [ ] Separate DBs: claire_paper, claire_live
  - [ ] EXECUTION_MODE ENV (paper|live)
  - [ ] Live-Pilot mit Mikro-Positionen
```

**Prio 2: Advanced Replay**
```yaml
Tasks:
  - [ ] Time-Travel Debugging UI
  - [ ] What-If Simulation (Event-Fork)
  - [ ] Chaos Engineering (Event-Injection)
```

---

## 6. Quellen & Weiterführende Literatur

### 6.1 Hochwertige Ressourcen (geprüft in Research)

**Event-Driven Backtesting**:
- QuantStart: "Event-Driven Backtesting with Python"
- Medium: "Building a Robust Backtesting Framework — Event-Driven Architecture"
- GitHub: barter-rs (Rust Event-Driven Framework)

**Determinismus**:
- Peter Lawrey: "Designing Hyper-Deterministic HFT Systems" (Dez 2024)
- Antithesis: "Deterministic Simulation Testing (DST)"
- FoundationDB: Deterministic Testing Whitepaper

**CQRS & Event Sourcing**:
- Martin Fowler: "LMAX Architecture"
- Greg Young: "CQRS & Event Sourcing Basics"
- Confluent: "Event Sourcing Using Apache Kafka"

**Snapshotting**:
- StackOverflow: "Snapshot taking and restore strategies"
- Reveno Framework: "High Load Trading with CQRS"
- ACM: "Using Event Sourcing and CQRS to Build High Performance Point Trading System"

**Causality & Ordering**:
- Leslie Lamport: "Time, Clocks, and the Ordering of Events in a Distributed System"
- Vector Clocks (Wikipedia + Kevin Sookocheff Blog)

### 6.2 Tools & Frameworks

**Event Stores**:
- EventStoreDB (spezialisiert für Event Sourcing)
- Apache Kafka (hoher Durchsatz, Partitioning)
- PostgreSQL (mit Event-Sourcing Schema)

**Testing**:
- pytest (Python)
- Golden Testing (Snapshot-basiert)
- Hypothesis (Property-Based Testing)

---

## 7. Nächste Schritte

1. **Review**: Dieses Dokument mit Jannek besprechen
2. **Priorisierung**: Sprint-Backlog für Prio 1 Tasks erstellen
3. **Prototyping**: Event-Schema v2 in einer Test-Branch implementieren
4. **Validation**: Golden Run Test schreiben (Proof-of-Concept)

---

**Version**: 1.0
**Autor**: Claude Code (Research)
**Review**: TBD
**Approval**: TBD
