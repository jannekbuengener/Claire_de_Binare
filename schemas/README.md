# Event Schemas für Claire de Binare

Dieses Verzeichnis enthält JSON-Schema-Definitionen für alle Event-Topics im Claire de Binare Trading-System.

## 📋 Übersicht

| Schema | Beschreibung | Producer | Consumer |
|--------|--------------|----------|----------|
| `market_data.schema.json` | Marktdaten-Events (Candles) | WS/REST Screener | Signal Engine |
| `signal.schema.json` | Trading-Signale | Signal Engine | Risk Manager |
| `risk_decision.schema.json` | Risk-Validierungsergebnisse | Risk Manager | (Intern) |
| `order.schema.json` | Genehmigte Orders | Risk Manager | Execution Service |
| `order_result.schema.json` | Order-Ausführungsergebnisse | Execution Service | Risk Manager, Dashboard, DB |
| `alert.schema.json` | System- und Risk-Alerts | Risk/Execution | Dashboard, Notifications |

## 🎯 Verwendung

### Validierung in Python

```python
import json
import jsonschema

# Schema laden
with open('schemas/market_data.schema.json') as f:
    schema = json.load(f)

# Event validieren
event = {
    "type": "market_data",
    "symbol": "BTC_USDT",
    "timestamp": 1730443200000,
    "close": 35250.5,
    "volume": 184.12,
    "interval": "1m"
}

try:
    jsonschema.validate(instance=event, schema=schema)
    print("✅ Event ist valide")
except jsonschema.ValidationError as e:
    print(f"❌ Validierungsfehler: {e.message}")
```

### Validierung in TypeScript

```typescript
import Ajv from 'ajv';
import marketDataSchema from './schemas/market_data.schema.json';

const ajv = new Ajv();
const validate = ajv.compile(marketDataSchema);

const event = {
  type: "market_data",
  symbol: "BTC_USDT",
  timestamp: 1730443200000,
  close: 35250.5,
  volume: 184.12,
  interval: "1m"
};

if (validate(event)) {
  console.log("✅ Event ist valide");
} else {
  console.log("❌ Validierungsfehler:", validate.errors);
}
```

## 📊 Event-Beispiele

### market_data

```json
{
  "type": "market_data",
  "symbol": "BTC_USDT",
  "timestamp": 1730443200000,
  "open": 35210.0,
  "high": 35280.5,
  "low": 35190.0,
  "close": 35250.5,
  "volume": 184.12,
  "interval": "1m"
}
```

### signal

```json
{
  "type": "signal",
  "symbol": "BTC_USDT",
  "direction": "BUY",
  "strength": 0.82,
  "reason": "MOMENTUM_BREAKOUT",
  "timestamp": 1730443260000,
  "strategy_id": "momentum_v1"
}
```

### risk_decision

```json
{
  "type": "risk_decision",
  "symbol": "BTC_USDT",
  "requested_direction": "BUY",
  "approved": true,
  "approved_size": 0.05,
  "reason_code": "OK",
  "timestamp": 1730443270000
}
```

### order

```json
{
  "type": "order",
  "order_id": "ORD_1730443270_BTC_USDT",
  "symbol": "BTC_USDT",
  "side": "BUY",
  "quantity": 0.05,
  "order_type": "MARKET",
  "timestamp": 1730443270000,
  "paper_trading": true
}
```

### order_result

```json
{
  "type": "order_result",
  "order_id": "ORD_1730443270_BTC_USDT",
  "status": "FILLED",
  "symbol": "BTC_USDT",
  "filled_quantity": 0.05,
  "price": 35260.1,
  "timestamp": 1730443280000,
  "paper_trading": true
}
```

### alert

```json
{
  "type": "alert",
  "level": "CRITICAL",
  "code": "DRAWDOWN_LIMIT_HIT",
  "message": "Maximaler Drawdown erreicht. Trading gestoppt.",
  "timestamp": 1730443300000,
  "service": "risk_manager",
  "action_required": true
}
```

## 🔍 Schema-Features

### Validierungsregeln

- **Required Fields**: Pflichtfelder, die immer vorhanden sein müssen
- **Type Constraints**: Datentypen (string, number, integer, boolean)
- **Value Constraints**: Wertebereiche (minimum, maximum, exclusiveMinimum)
- **Enums**: Vordefinierte Wertelisten (z.B. BUY/SELL, CRITICAL/WARNING/INFO)
- **Patterns**: Regex-Validierung (z.B. Symbol-Format: `^[A-Z0-9]+_[A-Z]+$`)
- **Conditional Validation**: Abhängige Felder (z.B. price required wenn order_type="LIMIT")

### Timestamp-Format

Alle Timestamps verwenden **Unix-Zeit in Millisekunden**:
- Format: Integer
- Minimum: 1000000000000 (≈ 2001-09-09)
- Beispiel: `1730443200000` = 2024-11-01 10:00:00 UTC

### Symbol-Format

Trading-Pairs folgen dem Pattern: `BASE_QUOTE`
- ✅ Valide: `BTC_USDT`, `ETH_USDT`, `SOL_USDT`
- ❌ Invalide: `btc_usdt`, `BTC-USDT`, `BTCUSDT`

## 🛠 Development

### Schema-Änderungen

Bei Änderungen an Schemas:

1. Schema-Datei anpassen
2. Version im `$id` Field aktualisieren
3. Tests aktualisieren
4. Dokumentation aktualisieren
5. Migration Guide erstellen (bei Breaking Changes)

### Testing

```bash
# Python: JSON Schema Validation
pip install jsonschema
python -c "
import json
import jsonschema
schema = json.load(open('schemas/market_data.schema.json'))
event = {...}
jsonschema.validate(event, schema)
"

# CLI: JSON Schema Validation (mit ajv-cli)
npm install -g ajv-cli
ajv validate -s schemas/market_data.schema.json -d test_event.json
```

## 📚 Referenzen

- **JSON Schema Draft-07**: https://json-schema.org/draft-07/schema
- **N1 Architektur**: `backoffice/docs/architecture/N1_ARCHITEKTUR.md`
- **Service Data Flows**: `backoffice/docs/services/SERVICE_DATA_FLOWS.md`
- **KODEX**: `backoffice/docs/KODEX – Claire de Binare.md`

## 📝 Changelog

| Version | Datum | Änderungen |
|---------|-------|------------|
| 1.0.0 | 2025-11-21 | Initial schema creation für alle 6 Event-Topics |

---

**Maintainer**: Claire de Binare Architecture Team
**Status**: ✅ Production Ready
