# Audit Trail - Claire de Binare (Issue #249)

Dokumentation der Auditierbarkeit für Real-Money-Trading.

## Status: ✅ Grundgerüst vorhanden

### Vorhandene Strukturen

| Tabelle | Audit-Felder | Vollständigkeit |
|---------|--------------|-----------------|
| signals | timestamp, source, metadata | ✅ Vollständig |
| orders | created_at, submitted_at, filled_at, rejection_reason, metadata | ✅ Vollständig |
| trades | timestamp, exchange_trade_id, slippage_bps, metadata | ✅ Vollständig |
| positions | opened_at, updated_at, closed_at, metadata | ✅ Vollständig |
| portfolio_snapshots | timestamp, metadata | ✅ Vollständig |

### Trade-Kette

```
Signal → Order → Trade → Position → Snapshot
   ↓        ↓       ↓        ↓          ↓
  id     signal_id order_id symbol   timestamp
```

Jeder Trade ist über diese Kette vollständig nachvollziehbar.

## Logging-Konventionen

### Strukturiertes Logging

```python
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def log_trade_event(event_type: str, data: dict):
    """Strukturiertes Trade-Logging für Audit-Trail."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "data": data
    }
    logger.info(json.dumps(log_entry))
```

### Event-Types

| Event-Type | Beschreibung | Pflichtfelder |
|------------|--------------|---------------|
| SIGNAL_GENERATED | Neues Signal | symbol, signal_type, price, confidence |
| ORDER_CREATED | Order erstellt | order_id, symbol, side, size |
| ORDER_APPROVED | Risk-Check bestanden | order_id, risk_score |
| ORDER_REJECTED | Risk-Check fehlgeschlagen | order_id, rejection_reason |
| TRADE_EXECUTED | Trade ausgeführt | trade_id, order_id, execution_price |
| POSITION_OPENED | Position eröffnet | symbol, entry_price, size |
| POSITION_CLOSED | Position geschlossen | symbol, exit_price, pnl |
| CIRCUIT_BREAKER | Breaker ausgelöst | breaker_type, metrics |

## Retention Policy

| Datentyp | Retention | Begründung |
|----------|-----------|------------|
| Trades | ∞ (unbegrenzt) | Regulatorische Anforderung |
| Orders | ∞ (unbegrenzt) | Audit-Trail |
| Signals | 90 Tage | Analyse |
| Snapshots | 365 Tage | Performance-Tracking |
| Logs | 30 Tage | Debugging |

## Compliance-Checkliste

### MiFID II / Regulatorische Anforderungen

- [x] Eindeutige Trade-ID (exchange_trade_id)
- [x] Zeitstempel mit Timezone (TIMESTAMP WITH TIME ZONE)
- [x] Preis und Menge gespeichert
- [x] Slippage dokumentiert (slippage_bps)
- [x] Gebühren erfasst (fees)
- [x] Signal-zu-Trade-Kette nachvollziehbar

### Technische Anforderungen

- [x] Immutable Append-Only (kein UPDATE auf trades)
- [x] Metadata-Feld für erweiterbare Informationen
- [x] Index auf Timestamp für schnelle Abfragen
- [x] Schema-Versionierung (schema_version Tabelle)

## Zukünftige Erweiterungen (Optional)

### Explizite Audit-Log Tabelle

```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50), -- 'signal', 'order', 'trade', etc.
    entity_id INTEGER,
    actor VARCHAR(50), -- 'system', 'user', 'agent:claude'
    action VARCHAR(50), -- 'create', 'update', 'delete'
    old_value JSONB,
    new_value JSONB,
    metadata JSONB
);
```

### PostgreSQL Trigger für automatisches Logging

```sql
CREATE OR REPLACE FUNCTION log_trade_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (event_type, entity_type, entity_id, action, new_value)
    VALUES ('TRADE_EXECUTED', 'trade', NEW.id, 'create', to_jsonb(NEW));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## Verifizierung

```sql
-- Trade-Audit-Kette prüfen
SELECT
    t.id as trade_id,
    t.timestamp as trade_time,
    t.symbol,
    t.side,
    t.execution_price,
    o.id as order_id,
    o.created_at as order_time,
    s.id as signal_id,
    s.timestamp as signal_time,
    s.confidence
FROM trades t
LEFT JOIN orders o ON t.order_id = o.id
LEFT JOIN signals s ON o.signal_id = s.id
ORDER BY t.timestamp DESC
LIMIT 10;
```
