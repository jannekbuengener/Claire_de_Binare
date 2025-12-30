# Canonical Message Contracts

**Issue:** #356
**Status:** ✅ Active (v1.0)
**Owner:** Team B (Engineering)

## Übersicht

Dieses Verzeichnis definiert die **kanonischen Message Contracts** für alle Redis Pub/Sub und Stream Messages in Claire de Binare. Contracts garantieren:

- **Typ-Sicherheit**: Klare Feldtypen und Constraints
- **Versionierung**: Schema Evolution via `schema_version` Field
- **Validierung**: Automatische CI-Tests gegen JSON Schemas
- **Migration**: Klare Upgrade-Pfade für Breaking Changes

---

## Contracts (v1.0)

### 1. market_data (Pub/Sub Topic)

**Schema:** [`market_data.schema.json`](./market_data.schema.json)
**Topic:** `market_data` (Redis Pub/Sub)
**Publisher:** `cdb_ws` (WebSocket Service)
**Consumers:** `cdb_signal` (Signal Engine), `cdb_paper` (Paper Trading)

**Required Fields:**
- `schema_version`: `"v1.0"`
- `source`: `"mexc"` | `"binance"` | `"bybit"` | `"stub"`
- `symbol`: Trading pair (z.B. `"BTCUSDT"`)
- `ts_ms`: Timestamp (milliseconds, integer)
- `price`: Trade price (string für Precision)
- `trade_qty`: Trade quantity (string für Precision) ⚠️ **NEU in v1.0** (war `qty`)
- `side`: `"buy"` | `"sell"` | `"unknown"` (lowercase)

**Beispiel:**
```json
{
  "schema_version": "v1.0",
  "source": "mexc",
  "symbol": "BTCUSDT",
  "ts_ms": 1735574400000,
  "price": "50000.50",
  "trade_qty": "1.5",
  "side": "buy"
}
```

**Migration Notes:**
- `qty` → `trade_qty` (Breaking Change in v1.0)
- `volume` field wurde entfernt (Aggregation downstream)

---

### 2. signal (Redis Stream)

**Schema:** [`signal.schema.json`](./signal.schema.json)
**Stream:** `trading_signals` (Redis Stream via XADD)
**Publisher:** `cdb_signal` (Signal Engine)
**Consumers:** `cdb_risk` (Risk Manager), `cdb_paper` (Paper Trading)

**Required Fields:**
- `schema_version`: `"v1.0"`
- `signal_id`: Unique identifier (UUID/Hash)
- `strategy_id`: Strategy identifier
- `symbol`: Trading pair
- `side`: `"BUY"` | `"SELL"` (uppercase)
- `timestamp`: Signal generation time (seconds, integer)

**Optional Fields:**
- `bot_id`: Bot instance identifier
- `strength`: Signal strength (0.0-1.0)
- `confidence`: Confidence level (0.0-1.0)
- `price`: Price at signal time
- `reason`: Human-readable justification
- `pct_change`: Percentage change
- `type`: Event type discriminator (`"signal"`)

**Beispiel:**
```json
{
  "schema_version": "v1.0",
  "signal_id": "sig-20251230-btcusdt-001",
  "strategy_id": "momentum-v2",
  "bot_id": "bot-alpha-1",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "timestamp": 1735574400,
  "strength": 0.85,
  "confidence": 0.92,
  "price": 50100.50,
  "reason": "Strong uptrend momentum detected",
  "type": "signal"
}
```

**Migration Notes:**
- `direction` → `side` (Breaking Change in v1.0)
- `timestamp`: Changed from float to integer (seconds)
- **None-Werte MÜSSEN vor Redis XADD gefiltert werden** (siehe Issue #349)

---

## Verwendung

### 1. Validierung (Python)

```python
import json
from pathlib import Path
from jsonschema import validate, ValidationError

# Schema laden
schema_path = Path("docs/contracts/market_data.schema.json")
with open(schema_path) as f:
    schema = json.load(f)

# Message validieren
message = {
    "schema_version": "v1.0",
    "source": "mexc",
    "symbol": "BTCUSDT",
    "ts_ms": 1735574400000,
    "price": "50000.50",
    "trade_qty": "1.5",
    "side": "buy"
}

try:
    validate(instance=message, schema=schema)
    print("✅ Message is valid")
except ValidationError as e:
    print(f"❌ Validation failed: {e.message}")
```

### 2. Tests ausführen

```bash
# Alle Contract-Tests
pytest tests/unit/contracts/test_contracts.py -v

# Nur market_data Tests
pytest tests/unit/contracts/test_contracts.py::TestMarketDataContract -v

# Nur signal Tests
pytest tests/unit/contracts/test_contracts.py::TestSignalContract -v
```

### 3. CI/CD Integration

Contracts werden automatisch validiert via `.github/workflows/contracts.yml`:
- Bei Push auf `main` (Änderungen in `docs/contracts/**`)
- Bei Pull Requests
- **Required Check:** `validate-contracts` muss grün sein vor Merge

---

## Schema Evolution

### Versionierung

Alle Schemas nutzen **Semantic Versioning** im `schema_version` Field:
- `v1.0`: Initiale Version (Breaking Changes: `qty→trade_qty`, `direction→side`)
- `v1.1`: Minor Changes (neue optionale Fields)
- `v2.0`: Major Changes (Breaking Changes)

### Breaking Changes

**Wenn ein Breaking Change notwendig ist:**
1. Neue Schema-Version erstellen (z.B. `v2.0`)
2. Migration Guide schreiben (siehe [`MIGRATION.md`](./MIGRATION.md))
3. **Dual Publishing** für 2 Wochen (Publisher senden beide Versionen)
4. Consumers updaten auf neue Version
5. Alte Version deprecaten + entfernen

**Beispiel Dual Publishing (market_data v1.0 → v2.0):**
```python
# Publisher sendet BEIDE Versionen für 2 Wochen
redis.publish("market_data", json.dumps({
    "schema_version": "v1.0",
    "qty": "1.5",           # OLD field
    "trade_qty": "1.5",     # NEW field
    ...
}))
```

---

## Migration Guides

- [v1.0 Migration Guide](./MIGRATION.md) - `qty→trade_qty`, `direction→side`

---

## Beispiele

- **Valid Examples:** [`examples/market_data_valid.json`](./examples/market_data_valid.json), [`examples/signal_valid.json`](./examples/signal_valid.json)
- **Invalid Examples:** [`examples/market_data_invalid.json`](./examples/market_data_invalid.json), [`examples/signal_invalid.json`](./examples/signal_invalid.json)

Alle Beispiele werden automatisch gegen Schemas validiert in `tests/unit/contracts/test_contracts.py`.

---

## Troubleshooting

### ❌ "additionalProperties not allowed"

**Problem:** Message enthält Field, das nicht im Schema definiert ist.

**Lösung:**
- Prüfen ob Field in Schema existiert
- Legacy Fields entfernen (`qty`, `direction`, `volume`)
- Bei Bedarf Schema erweitern (Minor Version Bump)

### ❌ "trade_qty is required"

**Problem:** Publisher verwendet noch altes `qty` Field.

**Lösung:**
- Code updaten: `qty` → `trade_qty`
- Migration Guide beachten: [`MIGRATION.md`](./MIGRATION.md)

### ❌ "side must be lowercase"

**Problem:** market_data erwartet `"buy"/"sell"`, nicht `"BUY"/"SELL"`.

**Lösung:**
- `side.lower()` vor Publish (market_data)
- Signals behalten `"BUY"/"SELL"` (uppercase)

---

## Ownership & Governance

- **Schema Changes:** Require PR Review + CI green
- **Breaking Changes:** Require Migration Guide + 2-week Dual Publishing
- **Version Bumps:** Update `schema_version` const in `.schema.json` files

**Contact:** Team B (Engineering)
**Issue Tracker:** [#356](https://github.com/jannekbuengener/Claire_de_Binare/issues/356)
