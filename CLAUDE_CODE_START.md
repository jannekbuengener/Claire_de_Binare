# 🎯 Claude Code Briefing: Pytest-Implementierung

## 📋 Kontext

Du arbeitest an **Claire de Binaire**, einem autonomen Krypto-Trading-Bot.

**Aktueller Status:**
- ✅ System läuft (4 Container healthy)
- ✅ pytest installiert und konfiguriert
- ✅ Test-Struktur vorhanden (`tests/` Ordner)
- ✅ Fixtures definiert (`conftest.py`)
- 🔄 **4 Test-Templates warten auf Implementierung**

---

## 🎯 Deine Aufgabe

**Implementiere die 4 Risk-Engine Tests in `tests/test_risk_engine_core.py`**

Aktuell sind alle Tests mit `pytest.skip("Implementation pending")` markiert.
Du sollst die echte Test-Logik implementieren.

---

## 📂 Wichtige Dateien

### Deine Arbeitsdateien:
- `tests/test_risk_engine_core.py` ← **HIER arbeitest du**
- `tests/conftest.py` ← Fixtures (fertig, nutzbar)

### Referenz-Dateien:
- `backoffice/docs/CLAUDE_CODE_BRIEFING.md` ← Ausführliche Anleitung
- `CLAUDE.md` ← Projekt-Übersicht
- `services/cdb_risk/service.py` ← Risk-Manager Logic (Referenz)

---

## ✅ Die 4 Tests die du implementieren sollst:

### Test 1: `test_daily_drawdown_blocks_trading`
**Ziel:** Trading wird blockiert bei Tagesverlust > 5%

**Was testen:**
- Arrange: `daily_pnl = -6000` (= -6% bei 100k Kapital)
- Act: Signal validieren
- Assert: `approved = False`, Grund enthält "daily_drawdown"

### Test 2: `test_exposure_blocks_new_orders`
**Ziel:** Neue Orders blockiert bei Gesamt-Exposure > 30%

**Was testen:**
- Arrange: `total_exposure = 0.30` (am Limit)
- Act: Signal validieren
- Assert: `approved = False`, Grund enthält "exposure"

### Test 3: `test_circuit_breaker_stops_all_trading`
**Ziel:** Circuit Breaker stoppt ALLE Trades bei > 10% Verlust

**Was testen:**
- Arrange: `daily_pnl = -11000` (= -11% Verlust)
- Act: Signal validieren
- Assert: `approved = False`, Circuit Breaker aktiv

### Test 4: `test_position_size_calculation`
**Ziel:** Positionsgröße wird korrekt berechnet

**Was testen:**
- Arrange: Kapital 100k, MAX_POSITION_PCT = 10%, BTC @ 50k
- Act: Position-Size berechnen
- Assert: Max Size = 10k USD = 0.2 BTC

---

## 🔧 Verfügbare Fixtures (aus conftest.py)

```python
def test_example(risk_config, sample_risk_state, sample_signal_event):
    # risk_config: Dict mit MAX_POSITION_PCT, MAX_DAILY_DRAWDOWN_PCT, etc.
    # sample_risk_state: Dict mit total_exposure, daily_pnl, etc.
    # sample_signal_event: Dict mit type, symbol, price, etc.
```

**Alle Fixtures:**
- `risk_config` - Risk-Limits
- `sample_risk_state` - Risk-State
- `sample_signal_event` - Test-Signal
- `mock_redis` - Redis Mock (für Integration-Tests)
- `mock_postgres` - PostgreSQL Mock (für Integration-Tests)

---

## 💡 Implementierungs-Ansatz

**Du hast 2 Optionen:**

### Option A: Mock-basiert (empfohlen für Start)
```python
@pytest.mark.unit
def test_daily_drawdown_blocks_trading(risk_config, sample_risk_state):
    # Arrange
    state = sample_risk_state.copy()
    state["daily_pnl"] = -6000.0  # -6% Verlust
    
    # Act
    # Hier musst du die Risk-Logic nachbilden oder mocken
    # Z.B. eine validate_signal() Funktion schreiben
    
    # Assert
    assert result["approved"] is False
    assert "daily_drawdown" in result["reason"].lower()
```

### Option B: Service-Import (wenn du die echte Logic nutzen willst)
```python
from services.cdb_risk.service import RiskManager

@pytest.mark.unit
def test_daily_drawdown_blocks_trading(risk_config, sample_risk_state):
    # Arrange
    risk_mgr = RiskManager()
    state = sample_risk_state.copy()
    state["daily_pnl"] = -6000.0
    
    signal = {
        "type": "signal",
        "symbol": "BTCUSDT",
        "signal_type": "buy",
        "price": 50000.0
    }
    
    # Act
    result = risk_mgr.validate_signal(signal, state, risk_config)
    
    # Assert
    assert result["approved"] is False
```

**⚠️ Wichtig:** 
- Falls `services/cdb_risk/service.py` noch keine `validate_signal()` Methode hat, musst du sie entweder:
  1. Mock-basiert testen (Option A)
  2. Oder die Methode zuerst in `service.py` hinzufügen

Schau dir `services/cdb_risk/service.py` an und entscheide, welche Option besser passt.

---

## 🚀 Start-Workflow

### Schritt 1: Datei öffnen
```bash
code tests/test_risk_engine_core.py
```

### Schritt 2: Ersten Test implementieren
Ersetze in `test_daily_drawdown_blocks_trading`:
```python
pytest.skip("Implementation pending")
```

durch echte Test-Logic.

### Schritt 3: Test ausführen
```bash
pytest -v tests/test_risk_engine_core.py::test_daily_drawdown_blocks_trading
```

### Schritt 4: Weiter zum nächsten Test
Wenn Test 1 grün ist, mache Test 2, dann 3, dann 4.

---

## ✅ Erfolgs-Kriterien

**Minimum (Phase 1):**
- ✅ 4 Tests implementiert (kein `pytest.skip()` mehr)
- ✅ Alle Tests laufen durch (`pytest -v`)
- ✅ Mindestens 2 Tests bestehen (grün)

**Optimal (Phase 2):**
- ✅ Alle 4 Tests grün
- ✅ Tests nutzen echte Service-Logic (wenn möglich)
- ✅ Coverage-Report zeigt >50%

---

## 🆘 Troubleshooting

### Problem: Import-Error `ModuleNotFoundError: services`
**Lösung:**
```python
# Am Anfang der Test-Datei:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Problem: Fixtures nicht gefunden
**Lösung:** Prüfe ob `tests/conftest.py` existiert und Fixtures definiert sind.

### Problem: Service hat keine validate_signal() Methode
**Lösung:** Nutze Mock-basierten Ansatz (Option A) statt Service-Import.

---

## 📚 Zusätzliche Ressourcen

**Falls du mehr Kontext brauchst:**
1. `backoffice/docs/CLAUDE_CODE_BRIEFING.md` - Ausführliche Anleitung
2. `CLAUDE.md` - Projekt-Übersicht mit allen Standards
3. `services/cdb_risk/service.py` - Risk-Manager Implementierung
4. `pytest.ini` - Test-Konfiguration

**Pytest Commands:**
```bash
pytest -v                        # Alle Tests
pytest -v -m unit               # Nur Unit-Tests
pytest --cov=services           # Mit Coverage
pytest -k "drawdown"            # Nur Tests mit "drawdown" im Namen
```

---

## 🎯 Los geht's!

**Dein erster Command:**
```bash
# Test-Datei öffnen
code tests/test_risk_engine_core.py

# Oder direkt starten:
pytest -v tests/test_risk_engine_core.py
```

**Fang mit Test 1 an:** `test_daily_drawdown_blocks_trading`

Viel Erfolg! 🚀
