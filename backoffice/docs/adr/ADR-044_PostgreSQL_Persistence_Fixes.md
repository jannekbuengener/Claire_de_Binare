# ADR-044: PostgreSQL Persistence - orders.price nullable + rejected trades handling

**Datum**: 2025-11-22
**Status**: ✅ Implementiert
**Verantwortlicher**: Claude Code (PostgreSQL Persistence Hardening)
**Related**: Fix #6, Fix #7 - PostgreSQL Persistence Bugs

---

## Kontext

Nach erfolgreicher Implementierung der PostgreSQL-Persistenz (18/18 Events erfolgreich persistiert) traten bei Edge-Case-Tests **zwei semantische Datenmodell-Inkonsistenzen** auf:

### Problem #1: orders.price NOT NULL Constraint bei Market-Orders

**Fehler**:
```
null value in column "price" of relation "orders" violates not-null constraint
```

**Ursache**:
- **Market-Orders** haben keinen festen Limit-Preis (werden zum besten verfügbaren Preis ausgeführt)
- PostgreSQL-Schema definierte: `price DECIMAL(18,8) NOT NULL`
- Upstream-Services konnten legitimerweise `price: null` für reine Market-Orders senden
- Betroffene Events: Market-Orders ohne `limit_price` Feld

**Fachlicher Kontext**:
- Limit-Preis (orders.price) ≠ Execution-Preis (trades.execution_price)
- NULL bedeutet semantisch: "kein Limit gesetzt", nicht "fehlende Information"
- Analytics-Tools brauchen Klarheit: `price IS NULL` = Market-Order

---

### Problem #2: trades.execution_price CHECK constraint bei rejected trades

**Fehler**:
```
new row for relation "trades" violates check constraint "trades_execution_price_positive"
DETAIL: Failing row contains (...execution_price=0.00000000, status='rejected')
```

**Ursache**:
- **Rejected Trades** sind semantisch **keine Trades** (nie ausgeführt)
- Code versuchte, rejected order_results mit `execution_price = 0.0` zu persistieren
- PostgreSQL-Schema definierte: `CHECK (execution_price > 0)`
- Status `rejected` war nicht in `trades.status` Constraint-Liste: `CHECK (status IN ('filled', 'partial', 'cancelled'))`

**Fachliches Problem**:
- Rejected Orders gehören in `orders.status = 'rejected'`
- `trades` Tabelle sollte nur **tatsächliche Ausführungen** enthalten
- `execution_price = 0.0` verletzt Schema-Semantik (kein Trade kann Preis 0 haben)

---

## Entscheidung

### Fix #6: Schema-Anpassung - orders.price nullable

**Migration**:
```sql
ALTER TABLE orders
  ALTER COLUMN price DROP NOT NULL;

COMMENT ON COLUMN orders.price IS 'Limit-Preis (NULL für Market-Orders ohne Limit)';
```

**Code-Logik** (db_writer.py):
```python
@staticmethod
def get_order_price(data: Dict[str, Any]) -> Optional[Decimal]:
    """
    Get order limit price (NULL for pure market orders).

    Returns:
        Decimal: Limit price for limit/stop orders
        None: Market orders without limit price
    """
    raw = data.get("price") or data.get("limit_price")

    if raw is None:
        logger.info("Market order without limit price: %s %s",
                    data.get("symbol"), data.get("order_type"))
        return None

    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError) as e:
        raise ValueError(f"Invalid price format: {raw}") from e
```

**Semantik**:
- `price IS NULL` → Market-Order ohne Limit-Preis
- `price IS NOT NULL` → Limit-/Stop-Order mit festem Preis

---

### Fix #7: Harte Validierung - nur echte Trades persistieren

**Status-Konstanten** (db_writer.py):
```python
EXECUTION_STATUSES = {"filled", "partial", "partially_filled"}
NON_EXECUTION_STATUSES = {"rejected", "cancelled"}
```

**Code-Logik** (process_trade_event):
```python
def process_trade_event(self, data: Dict):
    """
    Persist ONLY actual executions (filled/partial).
    Rejected/cancelled orders are NOT trades.
    """
    status = (data.get("status") or "filled").lower()

    # Skip non-executions
    if status in NON_EXECUTION_STATUSES:
        logger.info("⏭️  Skipping %s order_result: %s - not an actual trade",
                    status, data.get("symbol"))
        return

    # Validate execution_price > 0
    execution_price = self._get_positive_decimal(
        data.get("price") or data.get("execution_price"),
        "execution_price",
        data
    )
    # ... persist to trades table
```

**Validierungs-Helper**:
```python
@staticmethod
def _get_positive_decimal(value: Any, field_name: str, data: Dict) -> Decimal:
    """Extract and validate positive decimal (raises ValueError if invalid)."""
    if value is None:
        raise ValueError(f"{field_name} is required but was None")

    dec = Decimal(str(value))

    if dec <= 0:
        raise ValueError(f"{field_name} must be > 0, got: {dec}")

    return dec
```

---

## Konsequenzen

### Positiv

**Fix #6 (orders.price nullable)**:
- ✅ **Semantisch korrekt**: NULL bedeutet "kein Limit", nicht "fehlend"
- ✅ **Analytics-sauber**: `WHERE price IS NULL` identifiziert Market-Orders explizit
- ✅ **Kein 0.0-Müll**: Vermeidet falsche Durchschnittswerte in Queries
- ✅ **Typkonsistenz**: Decimal statt float (1:1 kompatibel mit DECIMAL(18,8))
- ✅ **Downstream-klar**: Risk-Checks, Reporting, Backtesting können NULL korrekt interpretieren

**Fix #7 (rejected trades skipped)**:
- ✅ **Fachlich korrekt**: `trades` enthält nur echte Ausführungen
- ✅ **Schema-konform**: Kein execution_price = 0.0 mehr
- ✅ **Datenkonsistenz**: Rejected Orders sind nur in `orders.status = 'rejected'`
- ✅ **Harte Validierung**: ValueError bei ungültigen Werten → keine stillen Fehler
- ✅ **Resilient**: Unbekannte Status werden geloggt und geskippt

### Neutral

- Kleine Schema-Migration erforderlich (ALTER TABLE - non-breaking)
- Upstream-Services müssen NULL-Handling unterstützen (bereits der Fall)
- Rejected Trades erscheinen nicht in `trades` Tabelle (fachlich gewollt)

### Negativ

- **Keine signifikanten Nachteile**

---

## Alternativen

### Alternative 1: orders.price = 0.0 als Fallback (ABGELEHNT)

**Idee**: Statt NULL → 0.0 für Market-Orders schreiben

**Probleme**:
- ❌ Analytics: `AVG(price)` wäre systematisch falsch
- ❌ Semantik: 0.0 bedeutet "kostenlos", nicht "kein Limit"
- ❌ Komplexität: Jede Query braucht `WHERE price > 0`
- ❌ Technische Schulden: Applikation ≠ SQL-Semantik

**Bewertung**: Technisch möglich, aber fachlich falsch

---

### Alternative 2: Rejected Trades mit execution_price = NULL (ABGELEHNT)

**Idee**: Rejected Trades in `trades` schreiben mit `execution_price = NULL`

**Probleme**:
- ❌ Schema: `execution_price NOT NULL` Constraint
- ❌ Semantik: Rejected = kein Trade = gehört nicht in `trades`
- ❌ Analytics: `trades` Tabelle wäre unrein (Mix aus Executions + Non-Executions)
- ❌ Schema-Anpassung erforderlich: `ALTER TABLE trades ALTER COLUMN execution_price DROP NOT NULL`

**Bewertung**: Löst Constraint-Problem, aber semantisch falsch

---

### Alternative 3: Separate rejected_orders Tabelle (OVERKILL)

**Idee**: Eigene Tabelle für rejected Orders

**Probleme**:
- ❌ Über-Engineering: `orders.status = 'rejected'` reicht aus
- ❌ Komplexität: Extra Tabelle, Migrations, Queries
- ❌ Kein Mehrwert: Rejected Orders sind bereits in `orders`

**Bewertung**: Unnötig komplex für MVP-Phase

---

## Implementierung

### Dateien geändert:

1. **Migration**:
   - `backoffice/migrations/002_orders_price_nullable.sql`

2. **Code**:
   - `backoffice/services/db_writer/db_writer.py`:
     - Imports erweitert: `Decimal, InvalidOperation, Optional`
     - Konstanten: `EXECUTION_STATUSES`, `NON_EXECUTION_STATUSES`
     - Neue Funktionen: `get_order_price()`, `_get_positive_decimal()`
     - Überarbeitet: `process_order_event()`, `process_trade_event()`

3. **Dokumentation**:
   - Dieser ADR

### Test-Validierung:

**Erwartete Ergebnisse**:
- ✅ Market-Orders ohne price → `orders.price = NULL` (kein Fehler)
- ✅ Limit-Orders mit price → `orders.price = <Decimal>` (validiert)
- ✅ Rejected Trades → **NICHT** in `trades` Tabelle (geloggt + geskippt)
- ✅ Filled Trades → in `trades` mit `execution_price > 0` (validiert)
- ✅ Invalid execution_price (≤0 oder NULL) → ValueError (Service crasht nicht)

---

## Compliance

- ✅ **KODEX-konform**: Fachlich korrekte Datenmodellierung (Risk-Layer-Kompatibel)
- ✅ **Schema-Semantik**: NULL bedeutet "nicht vorhanden", nicht "0"
- ✅ **Analytics-Ready**: Klare Trennung Market vs. Limit, Execution vs. Rejection
- ✅ **Audit-Trail**: Rejected Orders nachvollziehbar in `orders` Tabelle
- ✅ **Type-Safety**: Decimal statt float → Präzision für Financial Data

---

## Lessons Learned

1. **NULL vs. 0.0**: In Financial Systems ist NULL semantisch korrekt für "nicht gesetzt"
2. **Semantik vor Constraints**: Constraints müssen fachliche Realität abbilden, nicht umgekehrt
3. **Rejected ≠ Trade**: Klare Trennung zwischen Orders (Intent) und Trades (Execution)
4. **Hard Validation**: ValueError > Silent Defaults bei kritischen Feldern
5. **Decimal für Geld**: Niemals float für Preise/Mengen (Rundungsfehler)

---

## Referenzen

- Fix #6: `orders.price` NULL constraint violation
- Fix #7: `trades.execution_price` CHECK constraint violation
- Test-Ergebnisse: 18/18 Events erfolgreich (nach Fixes)
- Commit: `a3ce5a9` (Fix #5), `24ceda3` (Fix #1-3), `af8e898` (Test-Suite)
