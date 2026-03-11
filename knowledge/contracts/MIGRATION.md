# Contract Migration Guide - v1.0

**Issue:** #356
**Effective Date:** 2025-12-30
**Migration Deadline:** 2026-01-13 (2 Wochen)

---

## Overview

Contract v1.0 führt **Breaking Changes** ein zur Standardisierung der Message Contracts. Alle Publisher und Consumer MÜSSEN bis zum Deadline migriert werden.

**Breaking Changes:**
1. market_data: `qty` → `trade_qty`
2. market_data: `volume` field entfernt
3. signal: `direction` → `side`
4. signal: `timestamp` Type Change (float → integer)

---

## 1. market_data Contract Migration

### Breaking Change: `qty` → `trade_qty`

**Rationale:** Klarere Semantik (Trade Quantity vs. aggregierte Volume).

**Old Format (deprecated):**
```json
{
  "source": "mexc",
  "symbol": "BTCUSDT",
  "ts_ms": 1735574400000,
  "price": "50000.50",
  "qty": "1.5",        // ❌ DEPRECATED
  "side": "buy"
}
```

**New Format (v1.0):**
```json
{
  "schema_version": "v1.0",   // ✅ NEU: Schema version
  "source": "mexc",
  "symbol": "BTCUSDT",
  "ts_ms": 1735574400000,
  "price": "50000.50",
  "trade_qty": "1.5",          // ✅ NEU: Renamed field
  "side": "buy"
}
```

### Code Migration (Publisher)

**Datei:** `services/ws/mexc_v3_client.py:normalize_deal()`

**Before:**
```python
def normalize_deal(self, deal):
    """Normalize MEXC protobuf deal to market_data format"""
    return {
        "source": "mexc",
        "symbol": deal.s.decode('utf-8'),
        "ts_ms": deal.t,
        "price": deal.p.decode('utf-8'),
        "qty": deal.v.decode('utf-8'),    # ❌ OLD field
        "side": side_map.get(deal.S, "unknown")
    }
```

**After:**
```python
def normalize_deal(self, deal):
    """Normalize MEXC protobuf deal to market_data format"""
    return {
        "schema_version": "v1.0",         # ✅ ADD schema_version
        "source": "mexc",
        "symbol": deal.s.decode('utf-8'),
        "ts_ms": deal.t,
        "price": deal.p.decode('utf-8'),
        "trade_qty": deal.v.decode('utf-8'),  # ✅ RENAME qty → trade_qty
        "side": side_map.get(deal.S, "unknown")
    }
```

### Code Migration (Consumer)

**Datei:** `services/signal/models.py:MarketData.from_dict()`

**Before:**
```python
@classmethod
def from_dict(cls, data: dict):
    return cls(
        symbol=data["symbol"],
        price=float(data["price"]),
        timestamp=int(data.get("timestamp", 0) or data.get("ts_ms", 0)),
        volume=float(data.get("volume", 0.0)),  # ❌ REMOVED field
        ...
    )
```

**After:**
```python
@classmethod
def from_dict(cls, data: dict):
    return cls(
        symbol=data["symbol"],
        price=float(data["price"]),
        timestamp=int(data.get("timestamp", 0) or data.get("ts_ms", 0)),
        # volume field removed (calculate downstream if needed)
        ...
    )
```

---

## 2. signal Contract Migration

### Breaking Change: `direction` → `side`

**Rationale:** Alignment mit market_data Terminologie (`side`).

**Old Format (deprecated):**
```python
@dataclass
class Signal:
    signal_id: str | None = None
    strategy_id: str | None = None
    symbol: str = ""
    direction: str = ""        # ❌ DEPRECATED
    timestamp: float = 0.0     # ❌ DEPRECATED (float)
    ...
```

**New Format (v1.0):**
```python
@dataclass
class Signal:
    signal_id: str | None = None
    strategy_id: str | None = None
    symbol: str = ""
    side: Literal["BUY", "SELL"] | None = None  # ✅ NEU
    timestamp: int = 0         # ✅ Type Change (integer)
    ...
```

### Code Migration (Publisher)

**Datei:** `services/signal/models.py:Signal.__post_init__()`

**Before:**
```python
def __post_init__(self):
    # Backfill legacy fields
    if self.side is None and self.direction:
        self.side = self.direction  # ❌ Temporary backfill
```

**After:**
```python
def __post_init__(self):
    # No backfill needed - side is now primary field
    pass
```

**Datei:** `services/signal/models.py:Signal.to_dict()`

**Before:**
```python
def to_dict(self) -> dict:
    return {
        "signal_id": self.signal_id,
        "strategy_id": self.strategy_id,
        "symbol": self.symbol,
        "direction": self.direction,   # ❌ OLD field
        "timestamp": self.timestamp,   # ❌ float
        ...
    }
```

**After:**
```python
def to_dict(self) -> dict:
    return {
        "schema_version": "v1.0",     # ✅ ADD schema_version
        "signal_id": self.signal_id,
        "strategy_id": self.strategy_id,
        "symbol": self.symbol,
        "side": self.side,            # ✅ NEW field
        "timestamp": int(self.timestamp),  # ✅ Ensure integer
        ...
    }
```

---

## 3. Dual Publishing Strategy (2 Wochen)

**Phase 1 (Woche 1): Dual Publishing aktivieren**

Publisher senden **beide** Versionen für Backward Compatibility:

```python
# services/ws/mexc_v3_client.py
def normalize_deal(self, deal):
    """Dual publishing: OLD + NEW format"""
    return {
        "schema_version": "v1.0",
        "source": "mexc",
        "symbol": deal.s.decode('utf-8'),
        "ts_ms": deal.t,
        "price": deal.p.decode('utf-8'),

        # DUAL FIELDS (deprecated + canonical)
        "qty": deal.v.decode('utf-8'),        # ❌ DEPRECATED (for old consumers)
        "trade_qty": deal.v.decode('utf-8'),  # ✅ CANONICAL (for new consumers)

        "side": side_map.get(deal.S, "unknown")
    }
```

**Phase 2 (Woche 2): Consumer Migration**

Alle Consumer updaten ihre `from_dict()` Methoden:
- market_data: `data.get("trade_qty") or data.get("qty")` (fallback)
- signal: `data.get("side") or data.get("direction")` (fallback)

**Phase 3 (Nach 2 Wochen): Cleanup**

Publisher entfernen deprecated Fields:
```python
return {
    "schema_version": "v1.0",
    "source": "mexc",
    "symbol": deal.s.decode('utf-8'),
    "ts_ms": deal.t,
    "price": deal.p.decode('utf-8'),
    "trade_qty": deal.v.decode('utf-8'),  # ✅ Only canonical field
    "side": side_map.get(deal.S, "unknown")
}
```

---

## 4. Validation Checklist

### Publisher (services/ws/)

- [ ] `normalize_deal()`: `qty` → `trade_qty`
- [ ] Add `schema_version: "v1.0"` field
- [ ] Remove `volume` field
- [ ] Tests aktualisiert (`tests/unit/ws/`)

### Consumer (services/signal/)

- [ ] `MarketData.from_dict()`: Fallback `trade_qty or qty`
- [ ] Remove `volume` field usage
- [ ] Tests aktualisiert (`tests/unit/signal/`)

### Signal Publisher (services/signal/)

- [ ] `Signal.to_dict()`: `direction` → `side`
- [ ] `timestamp` → `int(timestamp)`
- [ ] Add `schema_version: "v1.0"` field
- [ ] Tests aktualisiert (`tests/unit/signal/`)

### Consumer (services/risk/, services/paper/)

- [ ] `Signal` parsing: Fallback `side or direction`
- [ ] `timestamp` handling (integer vs. float)
- [ ] Tests aktualisiert

---

## 5. Rollback Plan

**Falls Migration fehlschlägt:**

1. **Publisher:** Revert Commit + Deploy old version
2. **Consumer:** Fallback-Logik bleibt aktiv (kein Breaking Change)
3. **Schema:** Revert zu pre-v1.0 (kein Schema enforcement)

**No Data Loss:** Dual Publishing garantiert, dass alte Consumer weiterhin funktionieren.

---

## 6. Timeline

| Datum | Milestone |
|-------|-----------|
| 2025-12-30 | ✅ Contract v1.0 definiert (Issue #356) |
| 2026-01-02 | Dual Publishing aktiviert (Publisher) |
| 2026-01-06 | Consumer Migration abgeschlossen |
| 2026-01-13 | Cleanup (deprecated fields entfernt) |

---

## 7. Testing

**Local Tests (vor Merge):**
```bash
# Contract Validation Tests
pytest tests/unit/contracts/test_contracts.py -v

# Service Unit Tests (nach Migration)
pytest tests/unit/ws/ -v
pytest tests/unit/signal/ -v
pytest tests/unit/risk/ -v

# E2E Tests (mit neuen Contracts)
pytest tests/e2e/test_paper_trading_p0.py -v
```

**Evidence Requirements:**
- [ ] CI: `contracts` workflow grün
- [ ] CI: `unit` workflow grün
- [ ] E2E: Mindestens 1 erfolgreicher Lauf mit neuen Contracts

---

## 8. FAQ

**Q: Kann ich `qty` und `trade_qty` parallel verwenden?**
A: Ja, für 2 Wochen (Dual Publishing). Danach nur noch `trade_qty`.

**Q: Was passiert wenn Consumer alte Messages erhalten?**
A: Consumer sollten Fallback-Logik haben: `data.get("trade_qty") or data.get("qty")`.

**Q: Müssen Tests aktualisiert werden?**
A: Ja! Alle Unit + E2E Tests müssen neue Contracts verwenden.

**Q: Was wenn CI fehlschlägt?**
A: PR blockiert automatisch (Required Check: `validate-contracts`). Fix vor Merge!

---

## Contact

**Questions:** Issue #356
**Migration Support:** Team B (Engineering)
**Deadline:** 2026-01-13
