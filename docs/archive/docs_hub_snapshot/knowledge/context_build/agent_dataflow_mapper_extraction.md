# Agent: dataflow_mapper
# Scan Date: 2025-12-28
# Scope: Events/DB/Integration

---

## Facts (verifiziert)

### Event-Driven Pipeline (Redis Pub/Sub)

```
market_data (WS)
     |
     v
  [cdb_ws] --publish--> "market_data" channel
     |
     v
[cdb_signal] <--subscribe-- "market_data"
     |
     +--publish--> "signals" channel
     |
     v
 [cdb_risk] <--subscribe-- "signals"
     |                     <--subscribe-- "order_results"
     +--publish--> "orders" channel
     +--publish--> "alerts" channel
     |
     v
[cdb_execution] <--subscribe-- "orders"
     |
     +--publish--> "order_results" channel
     |
     v
[cdb_db_writer] <--subscribe-- "signals", "orders", "order_results", "portfolio_snapshots"
     |
     v
  [PostgreSQL]
```

### Redis Channels (identifiziert)
| Channel | Publisher | Subscriber(s) |
|---------|-----------|---------------|
| market_data | cdb_ws | cdb_signal |
| signals | cdb_signal | cdb_risk, cdb_db_writer |
| orders | cdb_risk | cdb_execution, cdb_db_writer |
| order_results | cdb_execution | cdb_risk, cdb_db_writer |
| alerts | cdb_risk | (monitoring) |
| portfolio_snapshots | cdb_paper_runner | cdb_db_writer |

### Event Types (core/domain/event.py)
| EventType | Beschreibung |
|-----------|--------------|
| SIGNAL_GENERATED | Signal Engine hat Handelssignal erzeugt |
| ORDER_PLACED | Order wurde an Exchange gesendet |
| POSITION_OPENED | Position wurde eroeffnet |

### Event Schema (Event Dataclass)
```python
@dataclass
class Event:
    event_id: str           # UUID (deterministisch)
    event_type: EventType   # Enum
    timestamp: datetime     # ISO 8601
    payload: Dict[str, Any] # Flexibles Payload
    stream_id: str          # Aggregat-ID
    sequence_number: int    # Ordnung
    schema_version: str     # Default "1.0"
    metadata: Dict          # Optional
```

### PostgreSQL Tables (db_writer channels)
- signals -> signals table
- orders -> orders table
- order_results -> order_results table
- portfolio_snapshots -> portfolio_snapshots table

### Config Topics (aus Service Configs)
| Service | Input Topic | Output Topic |
|---------|-------------|--------------|
| signal | market_data (config.input_topic) | signals (config.output_topic) |
| risk | signals (config.input_topic) | orders (config.output_topic_orders) |
| risk | order_results (config.input_topic_order_results) | alerts (config.output_topic_alerts) |
| execution | orders (config.TOPIC_ORDERS) | order_results |

---

## Assumptions (zu validieren)

1. **Bidirektionale Kommunikation Risk<->Execution**: Risk subscribed zu order_results fuer Circuit Breaker Updates

2. **Paper Runner**: Vermutlich publiziert portfolio_snapshots, aber nicht explizit in service.py sichtbar

3. **Schema Versioning**: Event.schema_version existiert, aber Migration-Strategy unklar

---

## Gaps (identifiziert)

1. **Kein explizites Event Schema Registry**: Events sind in event.py definiert, aber kein zentrales Schema-Management

2. **Alert Channel Subscriber**: alerts Channel wird published, aber kein dedizierter Consumer sichtbar
   - Vermutlich Prometheus/Grafana Alert Integration

3. **Portfolio Snapshots Publisher**: Code fuer Publishing nicht verifiziert in paper_trading/service.py

---

## Source Pointers

- `D:\Dev\Workspaces\Repos\Claire_de_Binare\core\domain\event.py`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\services\db_writer\db_writer.py` (Zeile 57: channels)
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\services\signal\service.py` (Zeile 89: subscribe, 142: publish)
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\services\risk\service.py` (Zeile 117-121: subscribe, 429-451: publish)
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\services\execution\service.py` (Zeile 145: subscribe, 183-190: publish)
