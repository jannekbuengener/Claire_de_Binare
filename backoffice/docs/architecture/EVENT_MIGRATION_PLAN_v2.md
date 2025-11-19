# Event Migration Plan v2 – Rückwärtskompatible BaseEvent-Migration

**Version**: 1.0
**Status**: 🟡 Design-Phase
**Erstellt**: 2025-11-19
**Branch**: `claude/event-sourcing-trading-research-01UD3wojoxzrnGE6aL8iZoCJ`
**Commits**: 6a7d337, e5774ed

---

## Executive Summary

Dieses Dokument beschreibt die schrittweise Migration bestehender Event-Typen (`MarketData`, `Signal`, `Order`, `OrderResult`, `Alert`) auf die neue **BaseEvent-Architektur** (Event Sourcing v2).

**Ziele**:
- ✅ **Rückwärtskompatibilität**: Keine Breaking Changes für bestehende Services
- ✅ **Schrittweise Migration**: Ein Event-Type nach dem anderen
- ✅ **Determinismus**: ClockEvent + correlation_id für Replay
- ✅ **Audit-Trail**: End-to-End Tracing über alle Services
- ✅ **Testing**: Golden Run Tests erkennen Regressionen

**Migrationsstrategie**: **Adapter-Pattern** (Alt → Adapter → BaseEvent → Services)

---

## 1. Bestandsaufnahme

### 1.1 Bestehende Event-Typen (v1 Schema)

| Event-Type | Definiert in | Producer | Consumer | Schema-Version | Tests |
|-----------|-------------|----------|----------|---------------|-------|
| **MarketData** | `backoffice/services/signal_engine/models.py` | Screener (cdb_ws) | Signal Engine | v1.0 | ❌ None |
| **Signal** | `backoffice/services/signal_engine/models.py` | Signal Engine | Risk Manager | v1.0 | ❌ None |
| **Signal** (Duplikat) | `backoffice/services/risk_manager/models.py` | - | Risk Manager | v1.0 | ❌ None |
| **Order** | `backoffice/services/risk_manager/models.py` | Risk Manager | Execution Service | v1.0 | ❌ None |
| **Order** (Duplikat) | `backoffice/services/execution_service/models.py` | - | Execution Service | v1.0 | ❌ None |
| **OrderResult** | `backoffice/services/risk_manager/models.py` | Execution Service | Portfolio Manager | v1.0 | ❌ None |
| **ExecutionResult** | `backoffice/services/execution_service/models.py` | Execution Service | Portfolio Manager | v1.0 | ❌ None |
| **Alert** | `backoffice/services/risk_manager/models.py` | Risk Manager | Notifications | v1.0 | ❌ None |

### 1.2 Neue Event-Typen (v2 Schema – bereits implementiert)

| Event-Type | Definiert in | Status | Tests |
|-----------|-------------|--------|-------|
| **BaseEvent** | `backoffice/services/common/events.py` | ✅ Fertig | ✅ 9/9 |
| **ClockEvent** | `backoffice/services/common/events.py` | ✅ Fertig | ✅ 9/9 |
| **RiskDecisionEvent** | `backoffice/services/common/events.py` | ✅ Fertig | ✅ 9/9 |

### 1.3 Schema-Unterschiede (v1 vs. v2)

**v1 Schema** (Beispiel: MarketData):
```python
@dataclass
class MarketData:
    symbol: str
    price: float
    volume: float
    pct_change: float
    timestamp: int
    interval: str = "15m"
    type: Literal["market_data"] = "market_data"
```

**v2 Schema** (Ziel: MarketData extends BaseEvent):
```python
@dataclass
class MarketData(BaseEvent):
    # BaseEvent-Felder (geerbt):
    # event_id: str = uuid()
    # event_type: str = "market_data"
    # timestamp: int = now_ms()
    # version: str = "2.0"
    # source: str = "cdb_screener"
    # sequence_id: Optional[int] = None
    # correlation_id: Optional[str] = None
    # causation_id: Optional[str] = None

    # MarketData-spezifische Felder:
    symbol: str
    price: float
    volume: float
    pct_change: float
    interval: str = "15m"
```

**Neue Felder** (v2):
- ✅ `event_id` – Unique ID (UUID)
- ✅ `sequence_id` – Monoton steigend (pro Service)
- ✅ `correlation_id` – End-to-End Flow-ID
- ✅ `causation_id` – Parent-Event-ID
- ✅ `version` – Schema-Version ("2.0")
- ✅ `source` – Produzierender Service

**Entfernte Felder** (in v2 umbenannt/verschoben):
- ❌ `type` (v1) → `event_type` (v2) [BaseEvent]

### 1.4 Verwendungsstellen

#### MarketData
**Producer**: `backoffice/services/signal_engine/service.py`
```python
def process_market_data(self, data: dict):
    market_data = MarketData.from_dict(data)  # v1 Schema
    # ... Verarbeitung
```

**Consumer**: `backoffice/services/signal_engine/service.py` (selbst)

#### Signal
**Producer**: `backoffice/services/signal_engine/service.py`
```python
signal = Signal(
    symbol=market_data.symbol,
    side=side,
    confidence=confidence,
    reason=reason,
    timestamp=market_data.timestamp,  # v1: timestamp ohne event_id
    price=market_data.price,
    pct_change=market_data.pct_change
)
self.redis_client.publish("signals", json.dumps(signal.to_dict()))
```

**Consumer**: `backoffice/services/risk_manager/service.py`
```python
signal_data = json.loads(message["data"])
signal = Signal.from_dict(signal_data)  # v1 Schema
```

#### Order
**Producer**: `backoffice/services/risk_manager/service.py`
```python
order = Order(
    symbol=signal.symbol,
    side=signal.side,
    quantity=quantity,
    stop_loss_pct=stop_loss_pct,
    signal_id=signal.timestamp,  # v1: keine event_id, nutzt timestamp!
    reason=signal.reason,
    timestamp=int(time.time())
)
self.redis_client.publish("orders", json.dumps(order.to_dict()))
```

**Consumer**: `backoffice/services/execution_service/service.py`
```python
order_data = json.loads(message["data"])
order = Order.from_event(order_data)  # v1 Schema
```

#### OrderResult / ExecutionResult
**Producer**: `backoffice/services/execution_service/mock_executor.py`
```python
result = ExecutionResult(
    order_id=str(uuid.uuid4()),
    symbol=order.symbol,
    side=order.side,
    quantity=order.quantity,
    filled_quantity=filled_qty,
    status="FILLED",
    price=fill_price,
    timestamp=datetime.utcnow().isoformat()  # v1: datetime.now() → NON-deterministisch!
)
```

**Consumer**: `backoffice/services/risk_manager/service.py` (OrderResult)

### 1.5 Probleme im aktuellen Schema (v1)

| Problem | Betroffene Events | Impact |
|---------|------------------|--------|
| **Keine event_id** | Alle | Kein eindeutiges Tracking, duplicate detection unmöglich |
| **Keine correlation_id** | Alle | End-to-End Tracing fehlt |
| **datetime.now()** | ExecutionResult | Non-deterministisch, Replay unmöglich |
| **Duplikate** | Signal, Order | 2 Definitionen, Inkonsistenzen |
| **signal_id=timestamp** | Order | Fragil, nicht eindeutig |
| **Kein Schema-Versioning** | Alle | Backward-Kompatibilität unklar |

---

## 2. Zielbild (v2 Schema)

### 2.1 MarketData (v2)

**Datei**: `backoffice/services/common/events.py` (neu erstellen)

```python
@dataclass
class MarketDataEvent(BaseEvent):
    """
    Market-Data Event vom Screener.

    v2 Schema: Extends BaseEvent
    """
    symbol: str
    price: float
    volume: float
    pct_change: float
    interval: str = "15m"

    event_type: Literal["market_data"] = "market_data"

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "pct_change": self.pct_change,
            "interval": self.interval,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "MarketDataEvent":
        base = super().from_dict(data)
        return cls(
            event_id=base.event_id,
            timestamp=base.timestamp,
            version=base.version,
            source=base.source,
            sequence_id=base.sequence_id,
            correlation_id=base.correlation_id,
            causation_id=base.causation_id,
            symbol=data["symbol"],
            price=float(data["price"]),
            volume=float(data["volume"]),
            pct_change=float(data["pct_change"]),
            interval=data.get("interval", "15m"),
        )
```

### 2.2 Signal (v2)

```python
@dataclass
class SignalEvent(BaseEvent):
    """
    Signal Event vom Signal Engine.

    v2 Schema: Extends BaseEvent
    """
    symbol: str
    side: Literal["BUY", "SELL"]
    confidence: float
    reason: str
    price: float
    pct_change: float

    event_type: Literal["signal"] = "signal"

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "symbol": self.symbol,
            "side": self.side,
            "confidence": self.confidence,
            "reason": self.reason,
            "price": self.price,
            "pct_change": self.pct_change,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "SignalEvent":
        base = super().from_dict(data)
        return cls(
            event_id=base.event_id,
            timestamp=base.timestamp,
            version=base.version,
            source=base.source,
            sequence_id=base.sequence_id,
            correlation_id=base.correlation_id,
            causation_id=base.causation_id,
            symbol=data["symbol"],
            side=data["side"],
            confidence=float(data["confidence"]),
            reason=data["reason"],
            price=float(data["price"]),
            pct_change=float(data["pct_change"]),
        )
```

### 2.3 Order (v2)

```python
@dataclass
class OrderEvent(BaseEvent):
    """
    Order Event vom Risk Manager.

    v2 Schema: Extends BaseEvent
    """
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    stop_loss_pct: float
    signal_id: str  # v2: UUID statt timestamp!
    reason: str
    client_id: Optional[str] = None

    event_type: Literal["order"] = "order"

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "stop_loss_pct": self.stop_loss_pct,
            "signal_id": self.signal_id,
            "reason": self.reason,
        })
        if self.client_id is not None:
            result["client_id"] = self.client_id
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "OrderEvent":
        base = super().from_dict(data)
        return cls(
            event_id=base.event_id,
            timestamp=base.timestamp,
            version=base.version,
            source=base.source,
            sequence_id=base.sequence_id,
            correlation_id=base.correlation_id,
            causation_id=base.causation_id,
            symbol=data["symbol"],
            side=data["side"],
            quantity=float(data["quantity"]),
            stop_loss_pct=float(data["stop_loss_pct"]),
            signal_id=data["signal_id"],
            reason=data["reason"],
            client_id=data.get("client_id"),
        )
```

### 2.4 OrderResult (v2)

```python
@dataclass
class OrderResultEvent(BaseEvent):
    """
    Order-Result Event vom Execution Service.

    v2 Schema: Extends BaseEvent
    """
    order_id: str
    status: Literal["FILLED", "REJECTED", "ERROR"]
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    filled_quantity: float
    price: Optional[float] = None
    client_id: Optional[str] = None
    error_message: Optional[str] = None

    event_type: Literal["order_result"] = "order_result"

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "order_id": self.order_id,
            "status": self.status,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
        })
        if self.price is not None:
            result["price"] = self.price
        if self.client_id is not None:
            result["client_id"] = self.client_id
        if self.error_message is not None:
            result["error_message"] = self.error_message
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "OrderResultEvent":
        base = super().from_dict(data)
        return cls(
            event_id=base.event_id,
            timestamp=base.timestamp,
            version=base.version,
            source=base.source,
            sequence_id=base.sequence_id,
            correlation_id=base.correlation_id,
            causation_id=base.causation_id,
            order_id=data["order_id"],
            status=data["status"],
            symbol=data["symbol"],
            side=data["side"],
            quantity=float(data["quantity"]),
            filled_quantity=float(data["filled_quantity"]),
            price=(float(data["price"]) if data.get("price") is not None else None),
            client_id=data.get("client_id"),
            error_message=data.get("error_message"),
        )
```

### 2.5 Alert (v2)

```python
@dataclass
class AlertEvent(BaseEvent):
    """
    Alert Event vom Risk Manager.

    v2 Schema: Extends BaseEvent
    """
    level: Literal["INFO", "WARNING", "CRITICAL"]
    code: str
    message: str
    context: Dict[str, Any]

    event_type: Literal["alert"] = "alert"

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "context": self.context,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "AlertEvent":
        base = super().from_dict(data)
        return cls(
            event_id=base.event_id,
            timestamp=base.timestamp,
            version=base.version,
            source=base.source,
            sequence_id=base.sequence_id,
            correlation_id=base.correlation_id,
            causation_id=base.causation_id,
            level=data["level"],
            code=data["code"],
            message=data["message"],
            context=data["context"],
        )
```

---

## 3. Migrationsstrategie: Adapter-Pattern

### 3.1 Warum Adapter-Pattern?

**Problem**: Services erwarten v1 Schema, wir wollen v2 Schema einführen.

**Lösung**: Adapter zwischen Alt (v1) und Neu (v2):

```
┌─────────────┐
│ Producer    │
│ (v1 Code)   │
└──────┬──────┘
       ↓ v1 Event (kein event_id)
┌──────────────┐
│ Adapter      │ ← Konvertiert v1 → v2
│ (Migration)  │    Fügt event_id, correlation_id hinzu
└──────┬───────┘
       ↓ v2 Event (mit BaseEvent-Feldern)
┌──────────────┐
│ Consumer     │
│ (v2 Code)    │
└──────────────┘
```

**Vorteile**:
- ✅ **Rückwärtskompatibilität**: Alte Producer laufen weiter
- ✅ **Schrittweise Migration**: Ein Service nach dem anderen
- ✅ **Testbar**: Adapter ist isoliert testbar

### 3.2 Adapter-Implementierung (Beispiel: MarketData)

**Datei**: `backoffice/services/common/adapters.py` (neu)

```python
"""
Event Adapters - v1 → v2 Migration
"""
import uuid
from typing import Dict, Any, Optional
from .events import BaseEvent, MarketDataEvent, SignalEvent, OrderEvent


class EventAdapter:
    """
    Adapter für v1 → v2 Event-Migration.

    Konvertiert alte Events (ohne event_id) zu neuen Events (mit BaseEvent-Feldern).
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._sequence_counter = 0

    def _next_sequence_id(self) -> int:
        """Generiert nächste Sequence-ID"""
        self._sequence_counter += 1
        return self._sequence_counter

    def adapt_market_data(
        self,
        v1_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
    ) -> MarketDataEvent:
        """
        Konvertiert v1 MarketData → v2 MarketDataEvent.

        Args:
            v1_data: v1 Schema (from Redis/Dict)
            correlation_id: Optional correlation ID (neu in v2)
            causation_id: Optional causation ID (neu in v2)

        Returns:
            MarketDataEvent (v2 Schema)
        """
        # v2 Event erstellen mit neuen Feldern
        return MarketDataEvent(
            # BaseEvent-Felder (NEU in v2):
            event_id=str(uuid.uuid4()),
            timestamp=int(v1_data["timestamp"]),
            version="2.0",
            source=self.service_name,
            sequence_id=self._next_sequence_id(),
            correlation_id=correlation_id or str(uuid.uuid4()),  # Neue Flow-ID
            causation_id=causation_id,

            # MarketData-Felder (aus v1):
            symbol=v1_data["symbol"],
            price=float(v1_data["price"]),
            volume=float(v1_data["volume"]),
            pct_change=float(v1_data["pct_change"]),
            interval=v1_data.get("interval", "15m"),
        )

    def adapt_signal(
        self,
        v1_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
    ) -> SignalEvent:
        """Konvertiert v1 Signal → v2 SignalEvent"""
        return SignalEvent(
            event_id=str(uuid.uuid4()),
            timestamp=int(v1_data["timestamp"]),
            version="2.0",
            source=self.service_name,
            sequence_id=self._next_sequence_id(),
            correlation_id=correlation_id or str(uuid.uuid4()),
            causation_id=causation_id,

            symbol=v1_data["symbol"],
            side=v1_data["side"],
            confidence=float(v1_data["confidence"]),
            reason=v1_data["reason"],
            price=float(v1_data["price"]),
            pct_change=float(v1_data["pct_change"]),
        )

    def adapt_order(
        self,
        v1_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
    ) -> OrderEvent:
        """Konvertiert v1 Order → v2 OrderEvent"""
        return OrderEvent(
            event_id=str(uuid.uuid4()),
            timestamp=int(v1_data["timestamp"]),
            version="2.0",
            source=self.service_name,
            sequence_id=self._next_sequence_id(),
            correlation_id=correlation_id or str(uuid.uuid4()),
            causation_id=causation_id,

            symbol=v1_data["symbol"],
            side=v1_data["side"],
            quantity=float(v1_data["quantity"]),
            stop_loss_pct=float(v1_data["stop_loss_pct"]),
            signal_id=str(v1_data.get("signal_id", "")),  # v1: int → v2: str (UUID)
            reason=v1_data["reason"],
            client_id=v1_data.get("client_id"),
        )
```

### 3.3 Adapter-Usage (Signal Engine Beispiel)

**Datei**: `backoffice/services/signal_engine/service.py` (Migration)

```python
# VORHER (v1):
from .models import MarketData, Signal

def process_market_data(self, data: dict):
    market_data = MarketData.from_dict(data)  # v1 Schema
    # ... Business Logic

    signal = Signal(
        symbol=market_data.symbol,
        side="BUY",
        confidence=0.8,
        reason="Momentum",
        timestamp=market_data.timestamp,
        price=market_data.price,
        pct_change=market_data.pct_change
    )
    self.redis_client.publish("signals", json.dumps(signal.to_dict()))


# NACHHER (v2 mit Adapter):
from backoffice.services.common.events import MarketDataEvent, SignalEvent
from backoffice.services.common.adapters import EventAdapter

def __init__(self):
    self.adapter = EventAdapter("cdb_signal")
    self.sequence_counter = SequenceCounter("cdb_signal")

def process_market_data(self, data: dict):
    # v1 → v2 Migration via Adapter
    market_data = self.adapter.adapt_market_data(
        v1_data=data,
        correlation_id=None  # Neue Flow-ID generieren
    )

    # ... Business Logic (nutzt jetzt v2 Event)

    # v2 Signal erstellen (mit correlation_id vom MarketData)
    signal = SignalEvent(
        # BaseEvent-Felder:
        event_id=str(uuid.uuid4()),
        timestamp=int(time.time() * 1000),
        version="2.0",
        source="cdb_signal",
        sequence_id=self.sequence_counter.next(),
        correlation_id=market_data.correlation_id,  # ← Gleiche Flow-ID!
        causation_id=market_data.event_id,  # ← Parent-Event

        # Signal-Felder:
        symbol=market_data.symbol,
        side="BUY",
        confidence=0.8,
        reason="Momentum",
        price=market_data.price,
        pct_change=market_data.pct_change
    )

    self.redis_client.publish("signals", json.dumps(signal.to_dict()))
```

### 3.4 Rückwärtskompatibilität sicherstellen

**Problem**: Alte Consumer erwarten v1 Schema.

**Lösung**: Adapter kann auch v2 → v1 konvertieren:

```python
class EventAdapter:
    def to_v1_dict(self, v2_event: BaseEvent) -> Dict[str, Any]:
        """
        Konvertiert v2 Event → v1 Dict (für alte Consumer).

        Entfernt: event_id, sequence_id, correlation_id, causation_id, version, source
        """
        v2_dict = v2_event.to_dict()

        # v1-kompatibles Dict (nur Event-spezifische Felder)
        v1_dict = {
            "type": v2_dict["event_type"],
            "timestamp": v2_dict["timestamp"],
        }

        # Event-spezifische Felder (ohne BaseEvent-Felder)
        for key, value in v2_dict.items():
            if key not in {"event_id", "event_type", "version", "source",
                          "sequence_id", "correlation_id", "causation_id"}:
                v1_dict[key] = value

        return v1_dict
```

---

## 4. Risikoanalyse

### 4.1 Betroffene Services

| Service | Impact | Risk | Mitigation |
|---------|--------|------|------------|
| **Signal Engine** | Producer (MarketData, Signal) | 🟡 Medium | Adapter-Pattern, Tests |
| **Risk Manager** | Consumer (Signal), Producer (Order, RiskDecision) | 🟡 Medium | Adapter-Pattern, Tests |
| **Execution Service** | Consumer (Order), Producer (OrderResult) | 🟡 Medium | Adapter-Pattern, Tests |
| **Portfolio Manager** | Consumer (OrderResult) | 🟢 Low | Nur Consumer, kein Breaking Change |

### 4.2 Breaking-Change-Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| **Producer sendet v2, Consumer erwartet v1** | 🟡 Medium | 🔴 High | Adapter bietet to_v1_dict() |
| **event_id fehlt in alten Events** | 🟢 Low | 🟡 Medium | Adapter generiert event_id |
| **signal_id ist UUID statt int** | 🟡 Medium | 🟡 Medium | Adapter konvertiert int → str |
| **Tests brechen** | 🟢 Low | 🟢 Low | Keine Tests vorhanden (!) |
| **datetime.now() vs. ClockEvent** | 🟡 Medium | 🟡 Medium | Schrittweise Migration |

### 4.3 Test-Strategie

**Golden Run Tests**:
- ✅ **Bereits vorhanden**: `tests/test_golden_run.py` (9/9 bestanden)
- 🔄 **Erweitern**: Adapter-Tests hinzufügen

**Adapter-Tests** (neu):
```python
# tests/test_event_adapters.py

def test_adapt_market_data_v1_to_v2():
    """Test: v1 MarketData → v2 MarketDataEvent"""
    adapter = EventAdapter("cdb_signal")

    v1_data = {
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "volume": 123.45,
        "pct_change": 2.5,
        "timestamp": 1700000000000,
        "interval": "15m",
        "type": "market_data"
    }

    v2_event = adapter.adapt_market_data(v1_data)

    # Assert: BaseEvent-Felder generiert
    assert v2_event.event_id is not None
    assert v2_event.version == "2.0"
    assert v2_event.source == "cdb_signal"
    assert v2_event.sequence_id == 1
    assert v2_event.correlation_id is not None

    # Assert: MarketData-Felder übernommen
    assert v2_event.symbol == "BTCUSDT"
    assert v2_event.price == 50000.0
```

**Regression-Tests** (Golden Run):
```python
def test_migration_golden_run():
    """
    Test: Golden Run mit v1 → v2 Migration.

    Workflow:
    1. v1 Events einlesen (aus Production-Log)
    2. Adapter: v1 → v2
    3. Replay mit v2 Events
    4. Hash vergleichen mit Golden Run
    """
    # 1. v1 Events (simuliert)
    v1_events = [
        {"type": "market_data", "symbol": "BTCUSDT", ...},
        {"type": "signal", "symbol": "BTCUSDT", ...},
    ]

    # 2. Adapter: v1 → v2
    adapter = EventAdapter("cdb_signal")
    v2_events = [
        adapter.adapt_market_data(v1_events[0]),
        adapter.adapt_signal(v1_events[1],
                            correlation_id=v2_events[0].correlation_id)
    ]

    # 3. Replay
    state = replay_events(v2_events)

    # 4. Hash vergleichen
    assert hash_state(state) == golden_hash
```

### 4.4 Rollback-Plan

**Falls Migration fehlschlägt**:

1. **Git Revert**: `git revert <commit-hash>`
2. **Services neu deployen**: `docker compose up -d --build`
3. **Post-Mortem**: Logs analysieren, Golden Run Tests prüfen

**Canary-Deployment**:
- Migration zunächst nur für **Signal Engine** (1 Service)
- Live-Traffic beobachten (Grafana Dashboards)
- Bei Fehlern: Rollback innerhalb 5 Minuten

---

## 5. Implementierungsplan – Sprint 3

### 5.1 Scope-Definition

**Sprint 3, Schritt 1**: **Nur MarketData auf BaseEvent migrieren**

**Warum MarketData zuerst?**:
- ✅ Einfachster Event-Type (nur Daten, keine Business-Logic)
- ✅ Nur 1 Producer (Signal Engine)
- ✅ Nur 1 Consumer (Signal Engine selbst)
- ✅ Keine abhängigen Services (isoliert testbar)

**Out of Scope** (für Sprint 3):
- ❌ Signal, Order, OrderResult (später)
- ❌ ClockEvent-Integration (später)
- ❌ CQRS Read-Projections (später)

### 5.2 Subtasks

#### Task 1: Event-Klassen erstellen (2h)
**Datei**: `backoffice/services/common/events.py`

- [ ] `MarketDataEvent(BaseEvent)` implementieren
- [ ] `to_dict()` implementieren
- [ ] `from_dict()` implementieren
- [ ] Type Hints vollständig

**DoD**:
- ✅ Code folgt BaseEvent-Pattern
- ✅ Docstrings vollständig
- ✅ Type-Hints korrekt

#### Task 2: Adapter implementieren (3h)
**Datei**: `backoffice/services/common/adapters.py` (neu)

- [ ] `EventAdapter`-Klasse erstellen
- [ ] `adapt_market_data()` implementieren
- [ ] `to_v1_dict()` implementieren (Rückwärtskompatibilität)
- [ ] Sequence-Counter integrieren

**DoD**:
- ✅ v1 → v2 Konvertierung funktioniert
- ✅ v2 → v1 Konvertierung funktioniert
- ✅ event_id wird generiert
- ✅ correlation_id wird generiert

#### Task 3: Adapter-Tests schreiben (2h)
**Datei**: `tests/test_event_adapters.py` (neu)

- [ ] `test_adapt_market_data_v1_to_v2()`
- [ ] `test_adapt_market_data_generates_event_id()`
- [ ] `test_adapt_market_data_generates_correlation_id()`
- [ ] `test_to_v1_dict_removes_base_fields()`
- [ ] `test_sequence_id_increments()`

**DoD**:
- ✅ 5/5 Tests bestehen
- ✅ Code Coverage >90%

#### Task 4: Signal Engine migrieren (4h)
**Datei**: `backoffice/services/signal_engine/service.py`

- [ ] Import `MarketDataEvent` statt `MarketData`
- [ ] Import `EventAdapter`
- [ ] `process_market_data()` umschreiben (Adapter nutzen)
- [ ] Alte `MarketData`-Klasse deprecaten (nicht löschen!)

**DoD**:
- ✅ Service nutzt MarketDataEvent (v2)
- ✅ Alte Klasse bleibt (deprecated)
- ✅ Service startet ohne Fehler

#### Task 5: Integration-Tests (3h)
**Datei**: `tests/integration/test_signal_engine_migration.py` (neu)

- [ ] `test_signal_engine_receives_v1_market_data()`
- [ ] `test_signal_engine_produces_v2_events()`
- [ ] `test_correlation_id_is_preserved()`
- [ ] `test_golden_run_with_migration()`

**DoD**:
- ✅ 4/4 Tests bestehen
- ✅ Golden Run Hash stimmt überein

#### Task 6: Dokumentation aktualisieren (1h)
**Dateien**:
- `backoffice/docs/architecture/EVENT_CATALOG.md`
- `backoffice/docs/architecture/EVENT_MIGRATION_PLAN_v2.md`

- [ ] MarketData-Status auf "✅ Migriert" setzen
- [ ] Migration-Schritte dokumentieren
- [ ] Lessons Learned festhalten

**DoD**:
- ✅ Docs aktualisiert
- ✅ Migration-Status korrekt

### 5.3 Definition of Done (Sprint 3)

**Technisch**:
- ✅ MarketDataEvent (v2) implementiert
- ✅ EventAdapter implementiert und getestet
- ✅ Signal Engine nutzt MarketDataEvent
- ✅ 9/9 Golden Run Tests bestehen
- ✅ 4/4 Integration-Tests bestehen
- ✅ 5/5 Adapter-Tests bestehen
- ✅ Code Coverage >80% (neue Module)

**Funktional**:
- ✅ Signal Engine empfängt v1 MarketData (Rückwärtskompatibilität)
- ✅ Signal Engine produziert v2 Events (mit event_id, correlation_id)
- ✅ Keine Breaking Changes für andere Services
- ✅ Determinismus: Golden Run reproduzierbar

**Dokumentation**:
- ✅ EVENT_CATALOG.md aktualisiert
- ✅ EVENT_MIGRATION_PLAN_v2.md aktualisiert
- ✅ Lessons Learned dokumentiert

**Deployment**:
- ✅ Docker Build erfolgreich
- ✅ Health-Checks grün
- ✅ Services starten ohne Fehler

---

## 6. Zeitplan & Meilensteine

### Sprint 3 (Woche 1-2)
**Ziel**: MarketData auf v2 migrieren

| Woche | Meilenstein | Deliverable |
|-------|------------|-------------|
| Woche 1 | Event-Klassen & Adapter | MarketDataEvent + EventAdapter fertig |
| Woche 1 | Tests | 5/5 Adapter-Tests bestehen |
| Woche 2 | Signal Engine Migration | Service nutzt v2 Events |
| Woche 2 | Integration-Tests | 4/4 Tests bestehen, Golden Run grün |

### Sprint 4 (Woche 3-4)
**Ziel**: Signal auf v2 migrieren

| Woche | Meilenstein | Deliverable |
|-------|------------|-------------|
| Woche 3 | SignalEvent implementieren | SignalEvent (v2) fertig |
| Woche 3 | Adapter erweitern | `adapt_signal()` implementiert |
| Woche 4 | Risk Manager Migration | Consumer nutzt v2 Signal |
| Woche 4 | Tests & Doku | Tests grün, Doku aktualisiert |

### Sprint 5 (Woche 5-6)
**Ziel**: Order + OrderResult auf v2 migrieren

| Woche | Meilenstein | Deliverable |
|-------|------------|-------------|
| Woche 5 | OrderEvent + OrderResultEvent | Beide Events (v2) fertig |
| Woche 5 | Adapter erweitern | `adapt_order()`, `adapt_order_result()` |
| Woche 6 | Execution Service Migration | Service nutzt v2 Events |
| Woche 6 | End-to-End Tests | Kompletter Flow: MarketData → Order → OrderResult |

### Sprint 6+ (Woche 7+)
**Ziel**: ClockEvent Integration + CQRS

| Woche | Meilenstein | Deliverable |
|-------|------------|-------------|
| Woche 7 | ClockEvent Integration | Services nutzen ClockEvent statt datetime.now() |
| Woche 8 | CQRS Read-Projections | Analytics-DB mit Denormalized Views |
| Woche 9+ | Archivierung | Retention-Policy implementiert |

---

## 7. Lessons Learned & Best Practices

### 7.1 Aus der Research

**Was wir gelernt haben**:
- ✅ **Zeit als Input**: ClockEvent macht Replays deterministisch
- ✅ **Golden Run Tests**: State-Hashing erkennt Code-Änderungen
- ✅ **correlation_id**: End-to-End Tracing über Services
- ✅ **Adapter-Pattern**: Rückwärtskompatible Migration

### 7.2 Best Practices für Migration

**DO**:
- ✅ Schrittweise Migration (1 Event-Type nach dem anderen)
- ✅ Adapter-Pattern für Rückwärtskompatibilität
- ✅ Golden Run Tests vor jeder Migration
- ✅ Alte Klassen deprecaten (nicht löschen)
- ✅ Dokumentation parallel aktualisieren

**DON'T**:
- ❌ Breaking Changes ohne Adapter
- ❌ Alle Events gleichzeitig migrieren
- ❌ Alte Klassen löschen (erst nach 6 Monaten)
- ❌ Tests überspringen
- ❌ Migration ohne Rollback-Plan

---

## 8. Offene Fragen

1. **Deployment-Strategie**: Canary vs. Blue-Green?
2. **Sequence-Counter Persistence**: In-Memory vs. Redis vs. PostgreSQL?
3. **correlation_id Generierung**: UUID vs. Ulid vs. Snowflake ID?
4. **Event-Store**: PostgreSQL vs. EventStoreDB vs. Kafka?
5. **Retention-Policy**: Wann alte Events (v1) löschen?

---

## 9. Nächste Schritte (Konkret für lokalen Sprint)

### Schritt 1: Vorbereitung (lokal)
```bash
# 1. Branch checken
git checkout claude/event-sourcing-trading-research-01UD3wojoxzrnGE6aL8iZoCJ
git pull

# 2. Dependencies installieren
pip install -r requirements-dev.txt

# 3. Tests ausführen (Baseline)
pytest tests/test_golden_run.py -v
# Erwartung: 9/9 bestanden
```

### Schritt 2: Implementierung (lokal)

**Task-Reihenfolge** (exakt so abarbeiten):

1. **MarketDataEvent implementieren** (backoffice/services/common/events.py)
   - Klasse nach Zielbild-Schema erstellen
   - to_dict() + from_dict() implementieren

2. **EventAdapter implementieren** (backoffice/services/common/adapters.py)
   - EventAdapter-Klasse erstellen
   - adapt_market_data() implementieren
   - to_v1_dict() implementieren

3. **Adapter-Tests schreiben** (tests/test_event_adapters.py)
   - 5 Tests nach DoD-Kriterien
   - Ausführen: `pytest tests/test_event_adapters.py -v`

4. **Signal Engine migrieren** (backoffice/services/signal_engine/service.py)
   - Import ändern (MarketDataEvent statt MarketData)
   - process_market_data() umschreiben
   - Adapter nutzen

5. **Integration-Tests** (tests/integration/test_signal_engine_migration.py)
   - 4 Tests schreiben
   - Golden Run erweitern

6. **Dokumentation aktualisieren**
   - EVENT_CATALOG.md: MarketData-Status auf "✅ Migriert"
   - EVENT_MIGRATION_PLAN_v2.md: Lessons Learned

### Schritt 3: Validierung (lokal)
```bash
# 1. Alle Tests ausführen
pytest -v

# 2. Coverage prüfen
pytest --cov=backoffice.services.common --cov-report=html

# 3. Docker Build testen
docker compose build cdb_signal

# 4. Service starten
docker compose up -d cdb_signal

# 5. Health-Check
curl -s http://localhost:8001/health
```

### Schritt 4: Commit & Push
```bash
git add backoffice/services/common/events.py
git add backoffice/services/common/adapters.py
git add tests/test_event_adapters.py
git add tests/integration/test_signal_engine_migration.py
git add backoffice/services/signal_engine/service.py
git add backoffice/docs/architecture/EVENT_CATALOG.md
git add backoffice/docs/architecture/EVENT_MIGRATION_PLAN_v2.md

git commit -m "feat: migrate MarketData to BaseEvent (v2 schema)

Implements Sprint 3, Schritt 1:
- MarketDataEvent extends BaseEvent
- EventAdapter for v1 → v2 migration
- Signal Engine uses MarketDataEvent
- 9/9 tests passing (5 adapter + 4 integration)
- Backward compatibility via to_v1_dict()

DoD:
✅ MarketDataEvent implemented
✅ EventAdapter with v1 → v2 conversion
✅ 5/5 Adapter-Tests passing
✅ 4/4 Integration-Tests passing
✅ 9/9 Golden Run Tests passing
✅ Code Coverage >80%
✅ Documentation updated
✅ No breaking changes
"

git push -u origin claude/event-sourcing-trading-research-01UD3wojoxzrnGE6aL8iZoCJ
```

---

**Version**: 1.0
**Status**: 🟡 Design-Phase (ready for implementation)
**Autor**: Claude Code (Browser)
**Review**: TBD
**Approval**: TBD
