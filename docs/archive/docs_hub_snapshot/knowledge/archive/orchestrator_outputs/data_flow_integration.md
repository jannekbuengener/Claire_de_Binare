# DATA FLOW OBSERVER REPORT

**Agent:** Data Flow Observer
**Mission:** Pydantic Integration in Redis/Service Flow
**Date:** 2025-12-29
**Analysis Duration:** 30 minutes

---

## EXECUTIVE SUMMARY

**CURRENT FLOW:** Duck-Typing + Manual JSON Serialization
**TARGET FLOW:** Pydantic Auto-Validation + Type-Safe Serialization
**INTEGRATION POINTS:** 4 Critical Points (Publish, Subscribe, Validation, Error Handling)
**BACKWARD COMPATIBILITY:** ACHIEVABLE (mit api_version Default)

**KEY FINDING:** Redis Layer ist bereits JSON-basiert → Pydantic Integration **NON-BREAKING** wenn richtig implementiert

---

## 1. CURRENT FLOW MAPPING

### 1.1 End-to-End Pipeline

```
MEXC WebSocket → cdb_ws → Redis (market_data) → cdb_signal → Redis (signals) → cdb_risk → Redis (orders) → cdb_execution → Redis (order_results)
```

**4 Redis Pub/Sub Topics:**
1. `market_data` - cdb_ws → cdb_signal
2. `signals` - cdb_signal → cdb_risk
3. `orders` - cdb_risk → cdb_execution
4. `order_results` - cdb_execution → (consumers)

---

### 1.2 Topic: market_data (cdb_ws → cdb_signal)

**Publisher:** `services/ws/mexc_v3_client.py`

**Current Code:**
```python
# AKTUELL (Manual JSON Serialization)
payload = {
    "symbol": f"{base_currency}/{quote_currency}",
    "price": deal.price,
    "volume": deal.volume,
    "timestamp": msg.timestamp,
    "ts_ms": msg.timestamp,
    "side": "BUY" if deal.isBuyer else "SELL",
    "venue": "mexc",
}
redis.publish("market_data", json.dumps(payload))  # ← Manual JSON
```

**Target Code (Pydantic):**
```python
# ZIEL (Pydantic Auto-Serialization)
from core.domain.contracts import MarketDataV1

market_data = MarketDataV1(
    symbol=f"{base_currency}/{quote_currency}",
    price=deal.price,
    volume=deal.volume,
    timestamp=msg.timestamp,
    side="BUY" if deal.isBuyer else "SELL",
    venue="mexc",
)
redis.publish("market_data", market_data.model_dump_json())  # ← Pydantic JSON
```

**Subscriber:** `services/signal/service.py`

**Current Code:**
```python
# AKTUELL (Manual Parsing + Duck-Typing)
message = pubsub.get_message()
data = json.loads(message["data"])
market_data = MarketData.from_dict(data)  # ← Can fail with KeyError
```

**Target Code (Pydantic):**
```python
# ZIEL (Pydantic Auto-Validation)
from core.domain.contracts import MarketDataV1
from pydantic import ValidationError

message = pubsub.get_message()
try:
    market_data = MarketDataV1.model_validate_json(message["data"])  # ← Auto-Validation
except ValidationError as e:
    logger.error(f"Invalid market_data schema: {e}")
    # → Schema-Verstoß wird sofort erkannt
```

**Changes Required:**
- ✅ cdb_ws: Replace `json.dumps(payload)` → `MarketDataV1(...).model_dump_json()`
- ✅ cdb_signal: Replace `MarketData.from_dict()` → `MarketDataV1.model_validate_json()`
- ✅ Add `ValidationError` Exception Handling

---

### 1.3 Topic: signals (cdb_signal → cdb_risk)

**Publisher:** `services/signal/service.py`

**Current Code:**
```python
# AKTUELL
signal = Signal(symbol="BTC", side="BUY", ...)
redis.publish("signals", json.dumps(signal.to_dict()))
```

**Target Code (Pydantic):**
```python
# ZIEL
signal = SignalV1(symbol="BTC", side="BUY", timestamp=utcnow().timestamp(), ...)
redis.publish("signals", signal.model_dump_json())
```

**Subscriber:** `services/risk/service.py`

**Current Code:**
```python
# AKTUELL
data = json.loads(message["data"])
signal = Signal.from_dict(data)  # ← Duck-Typing
```

**Target Code (Pydantic):**
```python
# ZIEL
signal = SignalV1.model_validate_json(message["data"])  # ← Type-Safe
```

**Changes Required:**
- ✅ cdb_signal: Replace `.to_dict()` → `.model_dump_json()`
- ✅ cdb_risk: Replace `.from_dict()` → `.model_validate_json()`

---

### 1.4 Topic: orders (cdb_risk → cdb_execution)

**Publisher:** `services/risk/service.py`

**Current Code:**
```python
# AKTUELL
order = Order(order_id="...", symbol="BTC", side="BUY", ...)
redis.publish("orders", json.dumps(order.to_dict()))
redis.xadd("orders_stream", order.to_dict())  # ← Redis Stream (dict)
```

**Target Code (Pydantic):**
```python
# ZIEL
order = OrderV1(order_id="...", symbol="BTC", side="BUY", timestamp=utcnow().timestamp(), ...)
redis.publish("orders", order.model_dump_json())  # Pub/Sub
redis.xadd("orders_stream", order.model_dump())  # Stream (dict, nicht JSON)
```

**⚠️ WICHTIG:** Redis Streams brauchen `model_dump()` (dict), NICHT `model_dump_json()` (str)!

**Subscriber:** `services/execution/service.py`

**Current Code:**
```python
# AKTUELL
data = json.loads(message["data"])
order = Order.from_dict(data)
```

**Target Code (Pydantic):**
```python
# ZIEL
order = OrderV1.model_validate_json(message["data"])
```

**Changes Required:**
- ✅ cdb_risk: Replace `.to_dict()` → `.model_dump()` / `.model_dump_json()`
- ✅ cdb_execution: Replace `.from_dict()` → `.model_validate_json()`
- ⚠️ **KRITISCH:** Redis Stream vs Pub/Sub (dict vs JSON)

---

### 1.5 Topic: order_results (cdb_execution → consumers)

**Publisher:** `services/execution/service.py`

**Current Code:**
```python
# AKTUELL (3 Outputs!)
order_result = OrderResult(order_id="...", status="FILLED", ...)

# 1. Redis Pub/Sub
redis.publish("order_results", json.dumps(asdict(order_result)))

# 2. Redis Stream
redis.xadd("order_results_stream", asdict(order_result))

# 3. PostgreSQL
db.insert_order_result(order_result)
```

**Target Code (Pydantic):**
```python
# ZIEL
order_result = OrderResultV1(order_id="...", status="FILLED", timestamp=utcnow().timestamp(), ...)

# 1. Redis Pub/Sub
redis.publish("order_results", order_result.model_dump_json())

# 2. Redis Stream
redis.xadd("order_results_stream", order_result.model_dump())

# 3. PostgreSQL (bleibt identisch, dict())
db.insert_order_result(order_result.model_dump())
```

**Changes Required:**
- ✅ cdb_execution: Replace `asdict()` → `.model_dump()` / `.model_dump_json()`
- ✅ Consumers: Replace `from_dict()` → `.model_validate_json()`

---

## 2. PYDANTIC INTEGRATION POINTS

### 2.1 Integration Point 1: Publisher Side

**WHERE:** Services produzieren Messages

**PATTERN:**
```python
# OLD (Dataclass)
message = Signal(symbol="BTC", side="BUY", ...)
redis.publish("signals", json.dumps(message.to_dict()))

# NEW (Pydantic)
message = SignalV1(symbol="BTC", side="BUY", timestamp=utcnow().timestamp(), ...)
redis.publish("signals", message.model_dump_json())
```

**CHANGES:**
- ✅ Replace `json.dumps(message.to_dict())` → `message.model_dump_json()`
- ✅ Add required fields (timestamp, api_version)
- ✅ Use Injectable Clock (`utcnow()`) für Determinismus

**FILES:** 7 Files (1 pro Service)

---

### 2.2 Integration Point 2: Subscriber Side

**WHERE:** Services konsumieren Messages

**PATTERN:**
```python
# OLD (Dataclass + Duck-Typing)
data = json.loads(message["data"])
signal = Signal.from_dict(data)  # ← KeyError möglich

# NEW (Pydantic + Auto-Validation)
from pydantic import ValidationError

try:
    signal = SignalV1.model_validate_json(message["data"])
except ValidationError as e:
    logger.error(f"Invalid signal schema: {e}")
    metrics.increment("validation_errors_total")
    continue  # Skip invalid message
```

**CHANGES:**
- ✅ Replace `json.loads() + from_dict()` → `model_validate_json()`
- ✅ Add `ValidationError` Exception Handling
- ✅ Add Metrics für Validation Errors

**FILES:** 7 Files (1 pro Service)

---

### 2.3 Integration Point 3: Redis Layer (Pub/Sub vs Stream)

**CRITICAL DIFFERENCE:**

**Pub/Sub:** Erwartet STRING (JSON)
```python
redis.publish("topic", message.model_dump_json())  # ← STRING
```

**Stream:** Erwartet DICT (Key-Value Pairs)
```python
redis.xadd("topic_stream", message.model_dump())  # ← DICT
```

**WHY?**
```python
# Redis Stream Syntax:
XADD stream_name * field1 value1 field2 value2 ...
# → Braucht DICT, nicht JSON String
```

**SOLUTION:**
```python
# Shared Helper Function
def publish_message(redis, topic, message):
    """Publish Pydantic Message zu Redis Pub/Sub + Stream"""
    # Pub/Sub (JSON String)
    redis.publish(topic, message.model_dump_json())

    # Stream (Dict)
    redis.xadd(f"{topic}_stream", message.model_dump())
```

**FILES:** 1 File (`core/redis/publisher.py` - NEU erstellen)

---

### 2.4 Integration Point 4: Error Handling

**OLD (Dataclass):**
```python
# KeyError wenn Field fehlt
data = json.loads(message)
symbol = data["symbol"]  # ← KeyError wenn "symbol" fehlt
```

**NEW (Pydantic):**
```python
# ValidationError wenn Schema nicht passt
try:
    signal = SignalV1.model_validate_json(message)
except ValidationError as e:
    # → Detaillierte Error-Infos (welches Field, warum)
    logger.error(f"Validation failed: {e.errors()}")
    # [{"loc": ["symbol"], "msg": "field required", "type": "missing"}]
```

**VORTEIL:** Pydantic gibt EXAKT an, was fehlt/falsch ist.

**CHANGES:**
- ✅ Replace `KeyError` Handling → `ValidationError` Handling
- ✅ Add Metrics für Validation Errors
- ✅ Add Structured Logging (error.errors())

**FILES:** 7 Files (1 pro Service)

---

## 3. PYDANTIC INTEGRATION FLOW (DIAGRAMM)

### 3.1 CURRENT FLOW (Dataclass)

```
[cdb_ws]
   ↓ Manual JSON Serialization
   payload = {"symbol": "BTC", "price": 50000}
   redis.publish("market_data", json.dumps(payload))
   ↓
[Redis Pub/Sub]
   ↓ message["data"] = '{"symbol": "BTC", "price": 50000}'
[cdb_signal]
   ↓ Manual Parsing
   data = json.loads(message["data"])
   market_data = MarketData.from_dict(data)  # ← KeyError Risk
   ↓
   process_market_data(market_data)
```

**PROBLEMS:**
- ❌ Keine Validation (KeyError möglich)
- ❌ Duck-Typing (Typo = Runtime Error)
- ❌ Keine Versionierung (Breaking Changes unsichtbar)

---

### 3.2 TARGET FLOW (Pydantic)

```
[cdb_ws]
   ↓ Pydantic Model Creation
   market_data = MarketDataV1(symbol="BTC", price=50000, timestamp=...)
   ↓ Auto-Validation (price > 0, symbol required)
   redis.publish("market_data", market_data.model_dump_json())
   ↓
[Redis Pub/Sub]
   ↓ message["data"] = '{"api_version": "v1.0", "symbol": "BTC", "price": 50000, ...}'
[cdb_signal]
   ↓ Pydantic Auto-Validation
   try:
       market_data = MarketDataV1.model_validate_json(message["data"])
   except ValidationError:
       logger.error("Schema violation")  # ← SOFORT ERKANNT
   ↓
   process_market_data(market_data)
```

**ADVANTAGES:**
- ✅ Auto-Validation (Schema-Verstöße sofort erkannt)
- ✅ Type-Safe (IDE Autocomplete, MyPy Check)
- ✅ Versionierung (api_version = "v1.0")
- ✅ Immutability (frozen=True → keine Mutation)

---

## 4. BACKWARD COMPATIBILITY STRATEGY

### 4.1 Problem: Old Messages vs New Schema

**Scenario:** cdb_ws (OLD Dataclass) sendet Message ohne `api_version`, cdb_signal (NEW Pydantic) empfängt.

**Old Message:**
```json
{"symbol": "BTC", "price": 50000}
```

**New Schema:**
```python
class MarketDataV1(BaseModel):
    api_version: Literal["v1.0"] = "v1.0"  # ← Required?
    symbol: str
    price: float
    timestamp: int  # ← Required!
```

**Problem:** Old Message hat KEIN `timestamp` → ValidationError!

---

### 4.2 Solution: Optional Fields + Defaults

**Strategy:** Neue Required Fields MÜSSEN Defaults haben (temporär, nur für Migration).

```python
# MIGRATION-PHASE (Woche 1-3)
class MarketDataV1(BaseModel):
    api_version: Literal["v1.0"] = Field(default="v1.0")  # ← DEFAULT
    symbol: str
    price: float
    timestamp: int = Field(default_factory=lambda: int(time.time()))  # ← DEFAULT

# POST-MIGRATION (Woche 4+)
class MarketDataV1(BaseModel):
    api_version: Literal["v1.0"] = "v1.0"  # ← REQUIRED
    symbol: str
    price: float
    timestamp: int  # ← REQUIRED (kein Default mehr)
```

**Reasoning:**
- Woche 1-3: Old Messages (ohne timestamp) können gelesen werden (Default greift)
- Woche 4+: Alle Services senden NEW Messages (mit timestamp) → Default entfernen

---

### 4.3 Migration ohne Downtime

**Phase 1: Deploy Pydantic Models (Feature Flag OFF)**
```python
USE_PYDANTIC = os.getenv("USE_PYDANTIC_CONTRACTS", "false")

if USE_PYDANTIC == "true":
    market_data = MarketDataV1.model_validate_json(message)
else:
    market_data = MarketData.from_dict(json.loads(message))  # OLD
```

**Phase 2: Enable Feature Flag (Service für Service)**
```bash
# Woche 1: cdb_signal
docker-compose exec cdb_signal bash -c 'export USE_PYDANTIC_CONTRACTS=true'

# Woche 2: cdb_risk + cdb_execution
docker-compose exec cdb_risk bash -c 'export USE_PYDANTIC_CONTRACTS=true'
docker-compose exec cdb_execution bash -c 'export USE_PYDANTIC_CONTRACTS=true'

# Woche 3: cdb_ws (letzter Service)
docker-compose exec cdb_ws bash -c 'export USE_PYDANTIC_CONTRACTS=true'
```

**Phase 3: Remove Feature Flag (Woche 4)**
```python
# Alle Services nutzen Pydantic → Feature Flag entfernen
market_data = MarketDataV1.model_validate_json(message)  # Direkt
```

**Downtime:** **ZERO** (Feature Flag ermöglicht schrittweise Migration)

---

## 5. CHANGES REQUIRED (SERVICE-BY-SERVICE)

### 5.1 cdb_ws (WebSocket Service)

**Files:** `services/ws/mexc_v3_client.py`

**Changes:**
```python
# OLD
payload = {"symbol": "BTC", "price": 50000, "timestamp": 1234567890}
redis.publish("market_data", json.dumps(payload))

# NEW
from core.domain.contracts import MarketDataV1
from core.utils.clock import utcnow

market_data = MarketDataV1(
    symbol="BTC",
    price=50000,
    timestamp=int(utcnow().timestamp()),
    volume=1.5,
)
redis.publish("market_data", market_data.model_dump_json())
```

**Effort:** 2 Stunden

---

### 5.2 cdb_signal (Signal Engine)

**Files:** `services/signal/service.py`, `services/signal/models.py`

**Changes:**
```python
# OLD
data = json.loads(message["data"])
market_data = MarketData.from_dict(data)

# NEW
from pydantic import ValidationError

try:
    market_data = MarketDataV1.model_validate_json(message["data"])
except ValidationError as e:
    logger.error(f"Invalid market_data: {e}")
    continue
```

**Effort:** 3 Stunden (inkl. Signal Publishing)

---

### 5.3 cdb_risk (Risk Manager)

**Files:** `services/risk/service.py`

**Changes:**
```python
# OLD (Consume Signals)
signal = Signal.from_dict(json.loads(message))

# NEW
signal = SignalV1.model_validate_json(message["data"])

# OLD (Publish Orders)
redis.publish("orders", json.dumps(order.to_dict()))

# NEW
redis.publish("orders", order.model_dump_json())
```

**Effort:** 3 Stunden

---

### 5.4 cdb_execution (Execution Service)

**Files:** `services/execution/service.py`

**Changes:**
```python
# OLD (Consume Orders)
order = Order.from_dict(json.loads(message))

# NEW
order = OrderV1.model_validate_json(message["data"])

# OLD (Publish OrderResults)
redis.publish("order_results", json.dumps(asdict(order_result)))
redis.xadd("order_results_stream", asdict(order_result))

# NEW
redis.publish("order_results", order_result.model_dump_json())
redis.xadd("order_results_stream", order_result.model_dump())  # ← DICT!
```

**Effort:** 4 Stunden (3 Outputs: Pub/Sub, Stream, DB)

---

### 5.5 Redis Layer (Shared Helper)

**Files:** `core/redis/publisher.py` (NEU erstellen)

**Code:**
```python
# core/redis/publisher.py
from pydantic import BaseModel
import redis

def publish_message(redis_client: redis.Redis, topic: str, message: BaseModel):
    """Publish Pydantic Message zu Redis Pub/Sub + Stream"""
    # Pub/Sub (JSON String)
    redis_client.publish(topic, message.model_dump_json())

    # Stream (Dict)
    redis_client.xadd(f"{topic}_stream", message.model_dump())
```

**Usage:**
```python
# services/signal/service.py
from core.redis.publisher import publish_message

signal = SignalV1(...)
publish_message(redis_client, "signals", signal)
# → Automatisch Pub/Sub + Stream
```

**Effort:** 2 Stunden

---

## 6. DELIVERABLE SUMMARY

### 6.1 CURRENT FLOW
```
Service → Manual JSON → Redis → Manual Parse → Service
          (Duck-Typing, KeyError Risk)
```

### 6.2 PYDANTIC INTEGRATION
```
Service → Pydantic Model → Auto-Validation → Redis → Pydantic Parse → Service
          (Type-Safe, Schema Enforcement)
```

### 6.3 CHANGES REQUIRED

**cdb_ws:**
- Replace `json.dumps(payload)` → `MarketDataV1(...).model_dump_json()`
- Add `utcnow()` für Timestamps
- **Effort:** 2h

**cdb_signal:**
- Replace `MarketData.from_dict()` → `MarketDataV1.model_validate_json()`
- Replace `json.dumps(signal.to_dict())` → `signal.model_dump_json()`
- Add `ValidationError` Handling
- **Effort:** 3h

**cdb_risk:**
- Replace `Signal.from_dict()` → `SignalV1.model_validate_json()`
- Replace `json.dumps(order.to_dict())` → `order.model_dump_json()`
- **Effort:** 3h

**cdb_execution:**
- Replace `Order.from_dict()` → `OrderV1.model_validate_json()`
- Replace `asdict(order_result)` → `order_result.model_dump()` / `.model_dump_json()`
- **KRITISCH:** Redis Stream vs Pub/Sub (dict vs JSON)
- **Effort:** 4h

**Redis Layer:**
- Create `core/redis/publisher.py` (Shared Helper)
- **Effort:** 2h

**TOTAL EFFORT:** 14 Stunden (Service Layer)

---

### 6.4 BACKWARD COMPATIBILITY

**Strategy:** Optional Fields + Defaults während Migration

```python
# MIGRATION (Woche 1-3)
class MarketDataV1(BaseModel):
    api_version: Literal["v1.0"] = "v1.0"  # DEFAULT
    timestamp: int = Field(default_factory=lambda: int(time.time()))  # DEFAULT

# POST-MIGRATION (Woche 4+)
class MarketDataV1(BaseModel):
    api_version: Literal["v1.0"] = "v1.0"  # REQUIRED
    timestamp: int  # REQUIRED (kein Default)
```

**Downtime:** ZERO (Feature Flag Migration)

---

**Agent:** Data Flow Observer
**Report Status:** COMPLETE ✅
**Next:** Determinism Inspector Analysis
