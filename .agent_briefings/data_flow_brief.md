# DATA FLOW OBSERVER - BRIEFING

**Mission:** Analysiere Integration von Pydantic Contracts in Redis/Service Flow

**Kontext:**
- CDB Pipeline: MEXC WS → cdb_ws → Redis → cdb_signal → cdb_risk → cdb_execution
- Aktuell: Duck-Typing + Dataclasses (siehe Issue #345 KeyError)
- Ziel: Pydantic Contracts mit api_version

**DEINE AUFGABE:**

## 1. Current Flow Mapping
**Redis Pub/Sub Messages:**
- `market_data` - cdb_ws → cdb_signal
- `signals` - cdb_signal → cdb_risk
- `orders` - cdb_risk → cdb_execution
- `order_results` - cdb_execution → (consumers)

**Für jede Message:**
- Aktuelles Format (Dataclass/Dict?)
- Serialization (JSON/Pickle/Protobuf?)
- Validation (Wo? Wie?)

## 2. Pydantic Integration Points
**WO müssen Contracts hin?**
- Publisher Side (Services produzieren Messages)
- Subscriber Side (Services konsumieren Messages)
- Redis Layer (Serialization/Deserialization)

**WIE sieht der neue Flow aus?**
```python
# Publisher
msg = MarketDataV1(symbol="BTC", price=50000)
redis.publish("market_data", msg.model_dump_json())

# Subscriber
raw = redis.subscribe("market_data")
msg = MarketDataV1.model_validate_json(raw)
```

## 3. Backward Compatibility
**FRAGEN:**
- Können alte Messages (ohne Pydantic) noch gelesen werden?
- Brauchen wir Migrations-Layer?
- Wie lange Co-Existenz (Dataclass + Pydantic)?

## 4. Deliverable
**FORMAT:**
```markdown
## CURRENT FLOW:
[Diagramm: Service → Redis → Service]

## PYDANTIC INTEGRATION:
[Diagramm: Service → Pydantic → Redis → Pydantic → Service]

## CHANGES REQUIRED:
- cdb_ws: [Änderungen]
- cdb_signal: [Änderungen]
- cdb_risk: [Änderungen]
- cdb_execution: [Änderungen]
- Redis Layer: [Änderungen]

## BACKWARD COMPATIBILITY:
[Strategie für Migration ohne Downtime]
```

**ZEIT:** 30 Minuten
**OUTPUT:** D:\Dev\Workspaces\Repos\Claire_de_Binare\.orchestrator_outputs\data_flow_integration.md
