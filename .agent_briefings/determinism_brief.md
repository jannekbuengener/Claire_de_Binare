# DETERMINISM INSPECTOR - BRIEFING

**Mission:** Stelle sicher, dass Pydantic-Models deterministisch sind

**Kontext:**
- CDB hat 95/100 Determinismus-Score (siehe determinism-inspection-report.md)
- Freqtrade nutzt Pydantic OHNE api_version (Schwäche)
- CDB MUSS besser sein: Pydantic MIT Versionierung + Determinismus

**DEINE AUFGABE:**

## 1. Pydantic Determinism Risks
**PRÜFE:**
- Werden Timestamps deterministisch generiert? (utcnow() vs time.time())
- Werden UUIDs deterministisch generiert? (uuid5 vs uuid4)
- Sind Pydantic Models immutable? (frozen=True?)
- Gibt es Random-Defaults? (z.B. `id: str = Field(default_factory=uuid4)`)

**ANTI-PATTERNS (VERBIETEN):**
```python
# ❌ NON-DETERMINISTIC
class BadModel(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)  # ← CHAOS
    id: str = Field(default_factory=lambda: str(uuid4()))      # ← CHAOS
```

**BEST-PRACTICES (ERZWINGEN):**
```python
# ✅ DETERMINISTIC
class GoodModel(BaseModel):
    api_version: Literal["v1.0"] = "v1.0"
    timestamp: datetime  # Required field (kein default)
    id: str              # Required field (kein default)

    class Config:
        frozen = True    # Immutable
```

## 2. Guardrail Tests
**NEUE TESTS:**
- Contract Tests prüfen Determinismus
- Round-Trip Tests (Serialize → Deserialize → Equal)
- Replay Tests (gleicher Input → gleicher Output)

**BEISPIEL:**
```python
# tests/contracts/test_determinism.py
@freeze_time("2025-01-01 12:00:00")
def test_market_data_deterministic():
    payload = {"symbol": "BTC", "price": 50000}
    msg1 = MarketDataV1.model_validate(payload)
    msg2 = MarketDataV1.model_validate(payload)
    assert msg1 == msg2  # ← Muss immer True sein
```

## 3. Integration mit bestehenden Utils
**CDB hat bereits:**
- `core/utils/clock.py` - utcnow(clock) injectable
- `core/utils/uuid_gen.py` - generate_uuid(seed) deterministisch
- `tests/unit/test_clock.py` - Guardrail-Test

**WIE kombinieren mit Pydantic?**
```python
from core.utils.clock import utcnow
from core.utils.uuid_gen import generate_uuid_hex

class MarketDataV1(BaseModel):
    timestamp: datetime
    event_id: str

    @classmethod
    def create(cls, symbol: str, price: float, seed: int):
        return cls(
            timestamp=utcnow(),  # ← Injectable clock
            event_id=generate_uuid_hex(f"{symbol}-{price}", seed),
            symbol=symbol,
            price=price,
        )
```

## 4. Deliverable
**FORMAT:**
```markdown
## PYDANTIC DETERMINISM RULES:
1. [Regel 1]
2. [Regel 2]
...

## ANTI-PATTERNS GEFUNDEN:
- [File:Line] - [Problem]

## GUARDRAIL TESTS:
- test_determinism_no_random_defaults.py
- test_determinism_round_trip.py
- test_determinism_replay.py

## INTEGRATION:
[Wie Pydantic + CDB Utils kombiniert werden]
```

**ZEIT:** 30 Minuten
**OUTPUT:** D:\Dev\Workspaces\Repos\Claire_de_Binare\.orchestrator_outputs\determinism_guarantees.md
