# Event Validation Guide für Claire de Binare

**Version**: 1.0
**Status**: ✅ Production Ready
**Datum**: 2025-11-21

---

## 📋 Übersicht

Dieses Dokument beschreibt die Event-Validierungsstrategie für Claire de Binare. Alle Events, die durch das System fließen, werden gegen JSON-Schemas validiert, um Datenintegrität und Typ-Sicherheit zu gewährleisten.

## 🎯 Ziele

1. **Datenintegrität**: Sicherstellen, dass alle Events valide Daten enthalten
2. **Früherkennung**: Fehler an der Eingabe erkennen, nicht erst bei der Verarbeitung
3. **Dokumentation**: Schemas dienen als lebende Dokumentation
4. **Typ-Sicherheit**: Validierung von Datentypen, Formaten und Constraints

## 📊 Validierte Event-Types

| Event Type | Schema | Beschreibung |
|-----------|--------|--------------|
| `market_data` | [market_data.schema.json](../../schemas/market_data.schema.json) | Marktdaten von Screener |
| `signal` | [signal.schema.json](../../schemas/signal.schema.json) | Trading-Signale |
| `risk_decision` | [risk_decision.schema.json](../../schemas/risk_decision.schema.json) | Risk-Validierungsergebnisse |
| `order` | [order.schema.json](../../schemas/order.schema.json) | Genehmigte Orders |
| `order_result` | [order_result.schema.json](../../schemas/order_result.schema.json) | Ausführungsergebnisse |
| `alert` | [alert.schema.json](../../schemas/alert.schema.json) | System- und Risk-Alerts |

## 🚀 Usage

### Basic Validation

```python
from services.event_validation import validate_event, is_valid_event

# Event erstellen
event = {
    "type": "signal",
    "symbol": "BTC_USDT",
    "direction": "BUY",
    "strength": 0.82,
    "timestamp": 1730443260000
}

# Validierung mit Exception
try:
    validate_event(event)
    print("✅ Event ist valide")
except ValidationError as e:
    print(f"❌ Validierungsfehler: {e}")

# Validierung ohne Exception
if is_valid_event(event):
    publish_to_redis("signals", event)
else:
    logger.warning(f"Invalid event: {event}")
```

### Service Integration

#### Signal Engine (Producer)

```python
from services.event_validation import validate_event

def generate_signal(market_data):
    signal = {
        "type": "signal",
        "symbol": market_data["symbol"],
        "direction": calculate_direction(),
        "strength": calculate_strength(),
        "timestamp": int(time.time() * 1000),
        "strategy_id": "momentum_v1"
    }

    # Validiere vor dem Publish
    validate_event(signal, "signal")

    # Publish zu Redis
    redis_client.publish("signals", json.dumps(signal))
    logger.info(f"Published validated signal for {signal['symbol']}")
```

#### Risk Manager (Consumer & Producer)

```python
from services.event_validation import validate_event, is_valid_event

def consume_signal(signal):
    # Validiere eingehenden Event
    if not is_valid_event(signal, "signal"):
        logger.warning(f"Received invalid signal: {signal}")
        return

    # Verarbeite Signal
    decision = evaluate_risk(signal)

    # Validiere ausgehenden Event
    validate_event(decision, "risk_decision")

    # Publish Decision
    redis_client.publish("orders", json.dumps(decision))
```

#### Execution Service (Consumer & Producer)

```python
from services.event_validation import validate_event

def consume_order(order):
    # Validiere Order
    validate_event(order, "order")

    # Führe Order aus
    result = execute_order(order)

    # Erstelle und validiere Result
    order_result = {
        "type": "order_result",
        "order_id": order["order_id"],
        "status": "FILLED",
        "symbol": order["symbol"],
        "filled_quantity": order["quantity"],
        "price": result["fill_price"],
        "timestamp": int(time.time() * 1000)
    }

    validate_event(order_result, "order_result")
    redis_client.publish("order_results", json.dumps(order_result))
```

### Mixin Pattern für Services

```python
from services.event_validation import validate_event, is_valid_event

class ValidatedEventPublisher:
    """Mixin für Services, die Events publishen."""

    def publish_event(self, channel: str, event: Dict[str, Any]) -> None:
        """Publish event mit Validierung."""
        validate_event(event)
        self.redis_client.publish(channel, json.dumps(event))
        logger.info(f"Published {event['type']} to {channel}")


class ValidatedEventConsumer:
    """Mixin für Services, die Events konsumieren."""

    def consume_event(self, event: Dict[str, Any]) -> bool:
        """Consume und validiere event."""
        if not is_valid_event(event):
            logger.warning(f"Received invalid event: {event}")
            return False

        self.process_event(event)
        return True


class SignalEngine(ValidatedEventPublisher, ValidatedEventConsumer):
    """Signal Engine mit automatischer Validierung."""
    pass
```

## 🔍 Schema-Features

### Validierungsregeln

Alle Schemas validieren:

1. **Required Fields**: Pflichtfelder müssen vorhanden sein
2. **Type Constraints**: Datentypen (string, number, integer, boolean)
3. **Value Constraints**: Wertebereiche (minimum, maximum, exclusiveMinimum)
4. **Enums**: Vordefinierte Wertelisten
5. **Patterns**: Regex-Validierung (z.B. Symbol-Format)
6. **Timestamps**: Unix-Zeit in Millisekunden (>= 1000000000000)

### Beispiel: market_data Schema

```json
{
  "type": "object",
  "required": ["type", "symbol", "timestamp", "close", "volume", "interval"],
  "properties": {
    "type": {"const": "market_data"},
    "symbol": {
      "type": "string",
      "pattern": "^[A-Z0-9]+_[A-Z]+$"
    },
    "timestamp": {
      "type": "integer",
      "minimum": 1000000000000
    },
    "close": {
      "type": "number",
      "exclusiveMinimum": 0
    },
    "interval": {
      "type": "string",
      "enum": ["1m", "5m", "15m", "1h", "4h", "1d"]
    }
  }
}
```

## 🧪 Testing

### Unit Tests

```bash
# Alle Validierungs-Tests
pytest tests/test_event_validation.py -v

# Spezifischer Test
pytest tests/test_event_validation.py::TestSignalValidation::test_valid_signal_event -v
```

### Integration Tests

```bash
# Event-Flow Integration Tests
pytest tests/test_integration_event_validation.py -v

# Test der kompletten Pipeline
pytest tests/test_integration_event_validation.py::TestEventFlowValidation::test_full_pipeline_success_flow -v
```

### Pre-Commit Validation

Event-Schemas werden automatisch bei jedem Commit validiert:

```bash
# Manual pre-commit run
pre-commit run validate-json-schemas --all-files

# Test der gesamten Pre-Commit Suite
pre-commit run --all-files
```

## 📈 Test-Coverage

**Test-Statistik** (Stand: 2025-11-21):
- **Unit Tests**: 22/22 passed (100%)
- **Integration Tests**: 10/10 passed (100%)
- **Total**: 32 Tests, 100% Pass Rate

**Test-Kategorien**:
- ✅ Valid Event Tests (positive cases)
- ✅ Invalid Event Tests (negative cases)
- ✅ Field Requirement Tests
- ✅ Type Constraint Tests
- ✅ Value Range Tests
- ✅ Enum Validation Tests
- ✅ Pattern Validation Tests
- ✅ Cross-Event Validation Tests
- ✅ Event Flow Pipeline Tests

## ⚠️ Best Practices

### DO ✅

1. **Validiere vor dem Publish**: Immer Events validieren, bevor sie in Redis publiziert werden
2. **Validiere nach dem Consume**: Immer Events validieren, nachdem sie von Redis gelesen wurden
3. **Log Validation Errors**: Fehler detailliert loggen für Debugging
4. **Use Type Hints**: Python Type Hints für Event-Dictionaries verwenden
5. **Test Edge Cases**: Grenzfälle und ungültige Daten testen

```python
# ✅ GOOD
from services.event_validation import validate_event

try:
    validate_event(event, "signal")
    redis_client.publish("signals", json.dumps(event))
except ValidationError as e:
    logger.error(f"Signal validation failed: {e}")
    metrics.increment("validation_errors", tags=["event_type:signal"])
```

### DON'T ❌

1. **Skip Validation**: Nie Validierung überspringen "weil es eh passt"
2. **Silent Failures**: Validierungsfehler nicht ignorieren
3. **Modify Schemas Without Tests**: Schemas nur mit entsprechenden Tests ändern
4. **Hardcode Values**: Keine festen Werte in Events hardcoden

```python
# ❌ BAD - No validation
redis_client.publish("signals", json.dumps(event))

# ❌ BAD - Silent failure
if not is_valid_event(event):
    pass  # Einfach ignorieren

# ❌ BAD - Hardcoded values
event = {"symbol": "BTC_USDT", "price": 50000}  # Fehlende Felder
```

## 🔧 Troubleshooting

### Validation Error: Missing Required Field

```python
ValidationError: Event validation failed for signal: root: 'timestamp' is a required property
```

**Lösung**: Pflichtfeld hinzufügen:

```python
signal = {
    "type": "signal",
    "symbol": "BTC_USDT",
    "direction": "BUY",
    "timestamp": int(time.time() * 1000)  # ← Hinzufügen
}
```

### Validation Error: Pattern Mismatch

```python
ValidationError: Event validation failed for market_data: symbol: 'btc_usdt' does not match '^[A-Z0-9]+_[A-Z]+$'
```

**Lösung**: Korrektes Format verwenden:

```python
# ❌ Falsch
symbol = "btc_usdt"  # Lowercase

# ✅ Richtig
symbol = "BTC_USDT"  # Uppercase
```

### Validation Error: Value Out of Range

```python
ValidationError: Event validation failed for signal: strength: 1.5 is greater than the maximum of 1
```

**Lösung**: Wert in erlaubten Bereich bringen:

```python
# ❌ Falsch
strength = 1.5  # > 1.0

# ✅ Richtig
strength = min(calculated_strength, 1.0)  # Cap at 1.0
```

### Schema Not Found

```python
WARNING: No schema found for event type: custom_event
```

**Lösung**: Entweder:

1. **Neues Schema erstellen**: `schemas/custom_event.schema.json`
2. **Strict Mode deaktivieren**: Für experimentelle Events

```python
# Strict mode deaktiviert (nur für Development)
validator = EventValidator(strict_mode=False)
```

## 📚 Weiterführende Dokumentation

- **JSON Schemas**: [schemas/README.md](../../schemas/README.md)
- **N1 Architektur**: [N1_ARCHITEKTUR.md](architecture/N1_ARCHITEKTUR.md)
- **Service Data Flows**: [SERVICE_DATA_FLOWS.md](services/SERVICE_DATA_FLOWS.md)
- **Event-Sourcing**: [EVENT_SOURCING_SYSTEM.md](EVENT_SOURCING_SYSTEM.md)
- **KODEX**: [KODEX – Claire de Binare.md](KODEX%20–%20Claire%20de%20Binare.md)

## 🔄 Schema-Evolution

### Breaking Changes

Wenn ein Schema Breaking Changes benötigt:

1. **ADR erstellen**: Dokumentiere Änderung in `DECISION_LOG.md`
2. **Version erhöhen**: Update `$id` im Schema
3. **Migration Guide**: Dokumentiere Migrationspfad
4. **Backward Compatibility**: Wenn möglich, beide Versionen parallel unterstützen

### Non-Breaking Changes

Erlaubte Änderungen ohne Breaking Changes:

- ✅ Neue optionale Felder hinzufügen
- ✅ Beschreibungen aktualisieren
- ✅ Beispiele hinzufügen
- ✅ Constraints lockern (z.B. max erhöhen)

Nicht erlaubt:

- ❌ Required Felder hinzufügen
- ❌ Felder entfernen
- ❌ Typen ändern
- ❌ Enums reduzieren
- ❌ Constraints verschärfen

## 🎯 Performance

**Validation Overhead**: ~0.1ms pro Event (gemessen mit 10k Events)

```python
# Benchmark (durchschnittlich)
- market_data: 0.08ms
- signal: 0.09ms
- risk_decision: 0.12ms
- order: 0.10ms
- order_result: 0.13ms
- alert: 0.09ms
```

**Optimierungen**:
- Schemas werden beim Start geladen (nicht bei jeder Validierung)
- Validators werden cached
- Validierung läuft synchron (kein I/O)

## 🚨 Monitoring

### Metriken

Empfohlene Prometheus-Metriken:

```python
from prometheus_client import Counter, Histogram

validation_errors = Counter(
    'validation_errors_total',
    'Total validation errors by event type',
    ['event_type']
)

validation_duration = Histogram(
    'validation_duration_seconds',
    'Time spent validating events',
    ['event_type']
)
```

### Alerts

Empfohlene Alerting-Rules:

```yaml
- alert: HighValidationErrorRate
  expr: rate(validation_errors_total[5m]) > 10
  annotations:
    summary: High rate of validation errors

- alert: ValidationErrorSpike
  expr: increase(validation_errors_total[1m]) > 50
  annotations:
    summary: Spike in validation errors
```

---

**Maintainer**: Claire de Binare Architecture Team
**Last Updated**: 2025-11-21
**Status**: ✅ Production Ready
