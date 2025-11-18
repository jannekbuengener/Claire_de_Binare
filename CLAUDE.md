# CLAUDE.md – KI-Agent-Protokoll für Claire de Binaire

> **Für Claude Code**: Start mit [Abschnitt 2: Quick Start](#2-quick-start-für-claude-code)

---

## 📋 Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Quick Start für Claude Code](#2-quick-start-für-claude-code)
3. [Projektkontext](#3-projektkontext)
4. [Repository-Struktur](#4-repository-struktur)
5. [Arbeitsweisen](#5-arbeitsweisen-nach-aufgabentyp)
6. [Event-Flow & Architektur](#6-event-flow--architektur)
7. [Code-Standards](#7-code-standards--best-practices)
8. [Testing](#8-testing-mit-pytest)
9. [Troubleshooting](#9-troubleshooting)
10. [Goldene Regeln](#10-goldene-regeln)

---

## 1. Executive Summary

**Projekt**: Claire de Binaire – Autonomer Krypto-Trading-Bot  
**Status**: ✅ Deployment-Ready (100%) | End-to-End Tests: 7/7  
**Phase**: N1 - Paper-Test Implementation  
**Deine Aufgabe**: Pytest-Struktur finalisieren, Tests implementieren

### 🎯 Aktuelle Prioritäten (November 2025):

1. **Pytest implementieren** (4 Risk-Engine Tests als Templates vorhanden)
2. **Test-Coverage erhöhen** (Ziel: >60%)
3. **Signal-Engine Tests** (neue Test-Datei erstellen)
4. **Integration-Tests** (Redis/PostgreSQL Mocks)

### ⚡ System läuft:
- 4/4 Container healthy
- PostgreSQL mit 10 Tabellen
- Redis Message Bus operational
- Signal Engine + Risk Manager deployed

---

## 2. Quick Start für Claude Code

### 2.1 Erste Schritte (5 Min)

```bash
# 1. Dependencies installieren
pip install -r requirements-dev.txt

# 2. Tests ausführen (sollten alle skippen)
pytest -v

# 3. Erste Test-Implementierung
# Öffne: tests/test_risk_engine_core.py
# Implementiere: test_daily_drawdown_blocks_trading
```

### 2.2 Pflichtlektüre (in dieser Reihenfolge)

| Datei | Zweck | Lesedauer |
|-------|-------|-----------|
| `backoffice/docs/CLAUDE_CODE_BRIEFING.md` | **START HIER** | 5 min |
| `backoffice/PROJECT_STATUS.md` | Live-Status | 3 min |
| `services/cdb_risk/service.py` | Risk-Logic Referenz | 10 min |
| `tests/conftest.py` | Test-Fixtures | 3 min |

### 2.3 Wo liegt was?

**Dein Workspace**:
```
C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Cleanroom\
├── tests/                    ← DU ARBEITEST HIER
│   ├── conftest.py          ← Fixtures (fertig)
│   ├── test_risk_engine_core.py  ← 4 TODO-Tests
│   └── test_*.py            ← Du erstellst neue
├── services/                ← Service-Code (Referenz)
│   ├── cdb_risk/service.py ← Risk-Logic
│   ├── cdb_core/service.py ← Signal-Logic
│   └── ...
├── pytest.ini               ← Config (fertig)
└── requirements-dev.txt     ← Dependencies (fertig)
```

### 2.4 Dein erster Test (Copy & Paste)

```python
# In tests/test_risk_engine_core.py
# Ersetze "pytest.skip(...)" durch:

@pytest.mark.unit
def test_daily_drawdown_blocks_trading(risk_config, sample_risk_state):
    """Test: Trading blockiert bei Daily Drawdown > 5%"""
    # Arrange
    from services.cdb_risk.service import RiskManager
    risk_mgr = RiskManager()
    
    state = sample_risk_state.copy()
    state["daily_pnl"] = -6000.0  # -6% bei 100k Kapital
    
    signal = {
        "type": "signal",
        "symbol": "BTCUSDT",
        "signal_type": "buy",
        "price": 50000.0
    }
    
    # Act
    result = risk_mgr.validate_signal(signal, state, risk_config)
    
    # Assert
    assert result["approved"] is False, "Signal sollte blockiert sein"
    assert "daily_drawdown" in result["reason"].lower()
```

---

## 3. Projektkontext

### 3.1 Naming (KRITISCH – nicht ändern!)

**Dokumentation/Kommunikation**:
- ✅ **Claire de Binaire** (offiziell)

**Code/Tech-IDs**:
- ✅ `claire_de_binaire` (DB-Name, Volumes)
- ✅ `cdb_*` (Service-Präfix: `cdb_core`, `cdb_risk`)

❌ **VERALTET**: „Claire de Binare" (alte Schreibweise – bei Fund melden)

### 3.2 System-Übersicht

**Container (4/4 healthy)**:
```
cdb_postgres  → Port 5432 (PostgreSQL)
cdb_redis     → Port 6379 (Message Bus)
cdb_signal    → Port 8001 (Signal Engine)
cdb_risk      → Port 8002 (Risk Manager)
```

**Services (Status)**:
- ✅ Signal Engine – Momentum-Strategie implementiert
- ✅ Risk Manager – 7-Layer-Validierung aktiv
- ⏳ Execution Service – In Vorbereitung

**Test-Status**:
- ✅ End-to-End: 7/7 manuell bestanden
- 🔄 Pytest: 4 Templates, 0 implementiert → **DEINE AUFGABE**

---

## 4. Repository-Struktur

### 4.1 Haupt-Verzeichnisse

```
Claire_de_Binare_Cleanroom/
├── services/              # 🐳 Microservices (Python)│   ├── cdb_ws/           # WebSocket-Screener (8000)
│   ├── cdb_core/         # Signal Engine (8001)
│   ├── cdb_risk/         # Risk Manager (8002)
│   └── cdb_execution/    # Execution Service (8003)
│
├── tests/                # 🧪 Pytest-Suite ← DU ARBEITEST HIER
│   ├── conftest.py      # Fixtures & Mocks
│   ├── test_risk_*.py   # Risk-Tests
│   └── test_signal_*.py # Signal-Tests
│
├── backoffice/          # 📚 Dokumentation
│   ├── docs/
│   │   ├── architecture/       # System-Design
│   │   ├── services/          # Event-Flows
│   │   ├── security/          # Security-Richtlinien
│   │   ├── schema/            # Datenmodelle (YAML)
│   │   └── CLAUDE_CODE_BRIEFING.md  # ← START HIER
│   └── PROJECT_STATUS.md       # ⭐ Live-Status
│
├── docker-compose.yml   # Container-Definition
├── pytest.ini          # Test-Config
├── requirements-dev.txt # Test-Dependencies
└── .env                # ENV-Variablen (nicht committen!)
```

### 4.2 Datei-Zuordnung (für neue Dateien)

| Was du erstellst | Wohin |
|-----------------|-------|
| Test-Code | `tests/test_*.py` |
| Service-Code | `services/cdb_*/` |
| Dokumentation | `backoffice/docs/` |
| Schemas | `backoffice/docs/schema/` |
| Runbooks | `backoffice/docs/runbooks/` |

---

## 5. Arbeitsweisen nach Aufgabentyp

### 5.1 Test-Engineering (Deine Hauptaufgabe)

**Workflow**:
1. Lese Template in `tests/test_risk_engine_core.py`
2. Analysiere Service-Logic in `services/cdb_risk/service.py`
3. Ersetze `pytest.skip(...)` durch echten Test
4. Führe aus: `pytest -v tests/test_risk_engine_core.py`
5. Coverage prüfen: `pytest --cov=services`

**Test-Struktur (Pflicht)**:
```python
@pytest.mark.unit  # Oder: integration, slow
def test_descriptive_name(fixture1, fixture2):
    """
    Gegeben: Ausgangssituation
    Wenn: Aktion X
    Dann: Erwartetes Ergebnis Y
    """
    # Arrange - Setup
    state = sample_risk_state.copy()
    state["daily_pnl"] = -6000.0
    
    # Act - Ausführung
    result = risk_engine.validate_signal(signal, state, config)
    
    # Assert - Prüfung
    assert result["approved"] is False
    assert "daily_drawdown" in result["reason"]
```

**Fixtures nutzen** (aus `conftest.py`):
- `mock_redis` – Redis ohne echten Server
- `mock_postgres` – PostgreSQL ohne DB
- `sample_signal_event` – Test-Signal
- `sample_risk_state` – Risk-State
- `risk_config` – Risk-Limits
- `signal_config` – Signal-Parameter

**Test-Ausführung**:
```bash
# Alle Tests
pytest -v

# Nur Unit-Tests (schnell, keine DB)
pytest -v -m unit

# Nur Risk-Tests
pytest -v tests/test_risk_engine_core.py

# Mit Coverage
pytest --cov=services --cov-report=html
# Öffne: htmlcov/index.html
```

### 5.2 Code-Entwicklung (Services)

**Tech-Stack**:
- Python 3.11+ mit Type Hints (Pflicht)
- Pydantic für Data Models
- Redis für Message Bus
- PostgreSQL für Persistence
- Flask für Health-Endpoints

**Code-Standards**:
```python
# ✅ GUT
from typing import Dict, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class SignalEvent(BaseModel):
    type: str
    symbol: str
    price: float
    confidence: float
    timestamp: str

def validate_signal(
    signal: SignalEvent,
    risk_state: Dict,
    config: Dict
) -> Dict[str, bool]:
    """
    Validiert Signal gegen Risk-Limits.
    
    Args:
        signal: Trading-Signal
        risk_state: Aktueller Risk-State
        config: Risk-Konfiguration
        
    Returns:
        {"approved": bool, "reason": str}
    """
    logger.info(f"Validiere Signal: {signal.symbol}")
    # ... Logic
    return {"approved": True, "reason": ""}

# ❌ SCHLECHT
def check(data):  # Keine Type Hints
    print(data)  # print() statt logging
    return True  # Keine Begründung
```

### 5.3 Dokumentations-Arbeit

**Scope**:
- ✅ `backoffice/docs/` – Darf geändert werden
- ✅ `backoffice/PROJECT_STATUS.md` – Aktualisieren
- ❌ `archive/` – Read-Only (nicht ändern!)

**Prüfpunkte bei Doku-Audit**:
1. Projektname: „Claire de Binaire" (nicht „Binare")
2. Tech-IDs: `claire_de_binaire`, `cdb_*`
3. Links funktionsfähig
4. Status aktuell
5. Code-Beispiele lauffähig

---

## 6. Event-Flow & Architektur

### 6.1 N1 Paper-Phase Pipeline

```
┌──────────────┐
│ MEXC API     │
└──────┬───────┘
       ↓ market_data
┌──────────────┐
│ Screener WS  │ (cdb_ws:8000)
└──────┬───────┘
       ↓ market_data (Redis)
┌──────────────┐
│ Signal Eng.  │ (cdb_core:8001)
└──────┬───────┘
       ↓ signals (Redis)
┌──────────────┐
│ Risk Manager │ (cdb_risk:8002)
└──────┬───────┘
       ↓ orders (Redis)
┌──────────────┐
│ Execution    │ (cdb_execution:8003)
└──────┬───────┘
       ↓ order_results (Redis)
┌──────────────┐
│ PostgreSQL   │ (cdb_postgres:5432)
└──────────────┘
```

### 6.2 Event-Types (FIXIERT – nicht umbenennen)

| Event-Type | Channel (Redis) | Producer | Consumer |
|-----------|----------------|----------|----------|
| `market_data` | `market_data` | Screener | Signal Engine |
| `signals` | `signals` | Signal Engine | Risk Manager |
| `orders` | `orders` | Risk Manager | Execution |
| `order_results` | `order_results` | Execution | DB-Writer |
| `alerts` | `alerts` | Risk/System | Notifications |

### 6.3 Risk-Engine: 7-Layer-Validierung

**Reihenfolge (wichtig für Tests)**:

1. **Data Quality** – Prüft: Stale/Invalid Data
2. **Position Limits** – Prüft: Max Position Size (10%)
3. **Daily Drawdown** – Prüft: Max Loss/Tag (5%)
4. **Total Exposure** – Prüft: Gesamt-Exposure (30%)
5. **Circuit Breaker** – Prüft: Emergency Stop (10% Loss)
6. **Spread Check** – Prüft: Bid-Ask-Spread
7. **Timeout Check** – Prüft: Data Freshness

**ENV-Variablen (in `.env`)**:
```bash
# Risk Limits (NICHT ÄNDERN ohne Rücksprache)
MAX_POSITION_PCT=0.10           # 10% pro Position
MAX_DAILY_DRAWDOWN_PCT=0.05     # 5% Max Tagesverlust
MAX_TOTAL_EXPOSURE_PCT=0.30     # 30% Gesamt-Exposure
CIRCUIT_BREAKER_THRESHOLD_PCT=0.10  # 10% Emergency Stop
MAX_SLIPPAGE_PCT=0.02           # 2% Max Slippage
DATA_STALE_TIMEOUT_SEC=60       # 60s Timeout
```

---

## 7. Code-Standards & Best Practices

### 7.1 Python-Style (Pflicht)

```python
# Type Hints IMMER
from typing import Dict, List, Optional

def process_signal(
    signal: Dict,
    state: Dict
) -> Dict[str, bool]:
    """Docstring im Google-Style"""
    pass

# Logging statt print()
import logging
logger = logging.getLogger(__name__)
logger.info("Signal empfangen")  # ✅
print("Signal empfangen")         # ❌

# ENV-Config, keine Hardcodes
import os
MAX_POSITION = float(os.getenv("MAX_POSITION_PCT", "0.10"))  # ✅
MAX_POSITION = 0.10  # ❌

# Error-Handling spezifisch
try:
    result = api_call()
except requests.HTTPError as e:  # ✅ Spezifisch
    logger.error(f"API Error: {e}")
except Exception:  # ❌ Zu breit
    pass
```

### 7.2 Service-Struktur (Template)

```python
# services/cdb_*/service.py
import os
import logging
from typing import Dict
from flask import Flask, jsonify

# Logging Setup
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

# Health-Endpoint (Pflicht)
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "service_name",
        "version": "0.1.0"
    })

# Main Logic
class ServiceCore:
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        return {
            "param": os.getenv("PARAM", "default")
        }
    
    def process(self, event: Dict) -> Dict:
        logger.info(f"Processing: {event}")
        # ... Logic
        return {"result": "success"}

if __name__ == "__main__":
    service = ServiceCore()
    app.run(host="0.0.0.0", port=8001)
```

### 7.3 Commit-Messages (Conventional Commits)

```bash
# Format: <type>: <description>

# Types:
feat:     # Neues Feature
fix:      # Bugfix
test:     # Tests hinzugefügt/geändert
docs:     # Dokumentation
refactor: # Code-Refactoring
chore:    # Build/Tooling

# Beispiele:
git commit -m "feat: add daily drawdown test"
git commit -m "fix: risk validation logic"
git commit -m "test: increase coverage to 65%"
git commit -m "docs: update claude.md for Claude Code"
```

---

## 8. Testing mit pytest

### 8.1 Test-Kategorien (Marker)

```python
@pytest.mark.unit          # Schnell, keine Ext. Dependencies
@pytest.mark.integration   # Mit Redis/PostgreSQL
@pytest.mark.slow         # >1s Runtime
@pytest.mark.risk         # Risk-Manager spezifisch
@pytest.mark.signal       # Signal-Engine spezifisch
```

**Ausführung nach Kategorie**:
```bash
pytest -v -m unit          # Nur Unit-Tests
pytest -v -m "not slow"    # Ohne langsame Tests
pytest -v -m risk          # Nur Risk-Tests
```

### 8.2 Fixtures (aus conftest.py)

**Mock-Fixtures**:
```python
def test_with_mock_redis(mock_redis):
    """Redis wird gemockt, kein echter Server nötig"""
    mock_redis.ping()  # Returns True
    mock_redis.publish("channel", "data")  # Returns 1
```

**Data-Fixtures**:
```python
def test_with_sample_data(sample_signal_event, risk_config):
    """Vordefinierte Test-Daten nutzen"""
    signal = sample_signal_event  # {"type": "signal", ...}
    config = risk_config  # {"MAX_POSITION_PCT": 0.10, ...}
```

### 8.3 Assertion-Patterns

```python
# Boolean-Checks
assert result["approved"] is False  # ✅ Explizit
assert not result["approved"]       # ❌ Implizit

# String-Checks
assert "daily_drawdown" in result["reason"].lower()  # ✅ Case-insensitive
assert result["reason"] == "Daily Drawdown"  # ❌ Fragil

# Numeric Checks
assert abs(result["value"] - 10000.0) < 0.01  # ✅ Float-Vergleich
assert result["value"] == 10000.0  # ❌ Float-Equality

# Error-Checks
with pytest.raises(ValueError, match="Invalid signal"):  # ✅
    process_invalid_signal()
```

### 8.4 Test-Daten erstellen

```python
# Basis-State kopieren und modifizieren
def test_custom_scenario(sample_risk_state):
    state = sample_risk_state.copy()
    state["daily_pnl"] = -6000.0  # Anpassen
    state["total_exposure"] = 0.25
    # Test mit modifiziertem State
```

---

## 9. Troubleshooting

### 9.1 Pytest findet Tests nicht

**Problem**: `pytest` meldet "no tests collected"

**Lösung**:
```bash
# 1. Prüfen: Sind Tests in tests/ Ordner?
ls tests/

# 2. Prüfen: Haben Dateien test_*.py Format?
ls tests/test_*.py

# 3. Prüfen: pytest.ini vorhanden?
cat pytest.ini

# 4. Expliziter Pfad
pytest -v tests/test_risk_engine_core.py
```

### 9.2 Import-Errors

**Problem**: `ModuleNotFoundError: No module named 'services'`

**Lösung**:
```bash
# Python-Path setzen (im Projekt-Root)
export PYTHONPATH=$PYTHONPATH:$(pwd)  # Linux/Mac
$env:PYTHONPATH += ";$(Get-Location)" # Windows PowerShell

# Oder: pytest mit -s Flag
pytest -v -s
```

### 9.3 Redis/PostgreSQL Connection-Errors

**Problem**: Tests schlagen fehl mit "Connection refused"

**Lösung**:
```python
# In Tests: IMMER Mocks nutzen für Unit-Tests
def test_with_mock(mock_redis, mock_postgres):
    # Keine echte Verbindung nötig
    pass

# Integration-Tests: Container prüfen
docker compose ps  # Sollte alle grün zeigen
```

### 9.4 Fixtures not found

**Problem**: `fixture 'sample_signal_event' not found`

**Lösung**:
```bash
# 1. Prüfen: conftest.py in tests/?
ls tests/conftest.py

# 2. Prüfen: Fixture definiert?
grep "def sample_signal_event" tests/conftest.py

# 3. pytest Cache löschen
pytest --cache-clear
rm -rf .pytest_cache
```

---

## 10. Goldene Regeln

### ❌ Absolut verboten:

1. **Archive ändern** – `archive/` ist Read-Only
2. **ENV hardcoden** – Immer `os.getenv()`
3. **Secrets committen** – `.env` in `.gitignore`
4. **`print()` nutzen** – Nur `logger.info()`
5. **Event-Types umbenennen** – `market_data`, `signals`, etc. sind fix
6. **Tech-IDs ändern** – `claire_de_binaire`, `cdb_*` sind fix
7. **Dateien löschen** – Ohne Rückfrage mit Jannek

### ✅ Immer tun:

1. **Type Hints** – Für alle Funktions-Parameter
2. **Structured Logging** – JSON-Format bevorzugt
3. **ENV-Config** – Keine Hardcodes
4. **Tests schreiben** – Für neue Features
5. **Doku aktualisieren** – Bei Änderungen
6. **PROJECT_STATUS.md updaten** – Bei Meilensteinen
7. **Arrange-Act-Assert** – In allen Tests

### 🤔 Bei Unsicherheit:

**NICHT raten** – Stattdessen:
1. Unsicherheit explizit benennen
2. Relevante Datei vorschlagen zum Prüfen
3. Auf Jannek's Antwort warten

**Beispiel**:
> „Ich bin unsicher, ob Layer 3 implementiert ist.  
> Soll ich `services/cdb_risk/service.py` analysieren?"

---

## 11. Hilfreiche Kommandos

### Docker:
```bash
# Status
docker compose ps

# Logs (letzte 100 Zeilen)
docker compose logs --tail=100 cdb_risk

# Health-Check
curl -fsS http://localhost:8002/health

# Restart
docker compose restart cdb_risk
```

### Pytest:
```bash
# Alle Tests
pytest -v

# Mit Coverage
pytest --cov=services --cov-report=html

# Nur fehlgeschlagene erneut
pytest --lf

# Verbose Output
pytest -vv -s

# Bestimmte Datei
pytest -v tests/test_risk_engine_core.py::test_daily_drawdown_blocks_trading
```

### Code-Suche:
```bash
# Falsche Projektbezeichnung finden
grep -r "Claire de Binare" backoffice/ --exclude-dir=archive

# ENV-Variablen finden
grep -r "os.getenv" services/

# TODO-Marker finden
grep -r "TODO" services/ tests/
```

---

## 12. Kommunikation mit Jannek

### Sprach-Konventionen:

**Deutsch**:
- Kommunikation mit Jannek
- Dokumentations-Texte
- Docstrings

**Englisch**:
- Code (Funktionen, Klassen, Variablen)
- ENV-Keys (`MAX_POSITION_PCT`)
- Event-Types (`market_data`)
- Git-Commits

### Standard-Workflow (5 Schritte):

1. **Klären** – Ziel wiederholen, Kontext erfragen
2. **Analysieren** – Code prüfen, Konflikte benennen
3. **Planen** – Schritt-Liste, Scope definieren
4. **Implementieren** – Vollständiger Code, Tests
5. **Next Steps** – Zusammenfassung, konkreter Vorschlag

---

## 13. Quick Reference

### Wichtige Dateien:

| Datei | Zweck |
|-------|-------|
| `backoffice/PROJECT_STATUS.md` | Live-Status des Projekts |
| `backoffice/docs/CLAUDE_CODE_BRIEFING.md` | Dein Briefing |
| `services/cdb_risk/service.py` | Risk-Logic (Referenz) |
| `services/cdb_core/service.py` | Signal-Logic (Referenz) |
| `tests/conftest.py` | Test-Fixtures |
| `pytest.ini` | Test-Konfiguration |
| `.env` | ENV-Variablen (nicht committen!) |

### Service-Ports:

| Service | Port | Endpoint |
|---------|------|----------|
| WebSocket/REST | 8000 | `/health` |
| Signal Engine | 8001 | `/health`, `/status` |
| Risk Manager | 8002 | `/health`, `/status` |
| Execution | 8003 | `/health`, `/status` |
| PostgreSQL | 5432 | - |
| Redis | 6379 | - |

### Risk-Limits (ENV):

```bash
MAX_POSITION_PCT=0.10              # 10%
MAX_DAILY_DRAWDOWN_PCT=0.05        # 5%
MAX_TOTAL_EXPOSURE_PCT=0.30        # 30%
CIRCUIT_BREAKER_THRESHOLD_PCT=0.10 # 10%
```

---

## 14. Definition of Done (N1 MVP)

### Infrastruktur:
- ✅ 4 Container healthy
- ✅ Health-Endpoints aktiv
- ✅ Structured Logging

### Services:
- ✅ Signal Engine deployed
- ✅ Risk Manager deployed
- ⏳ Execution Service (Mock)

### Testing:
- ✅ End-to-End: 7/7 manual
- 🔄 **Pytest: 4 Tests implementiert** ← DEINE AUFGABE
- ⏳ Coverage >60%

### Daten:
- ✅ PostgreSQL (10 Tabellen)
- ✅ Redis Message Bus
- ⏳ Trade-Historie persistent

### Success-Kriterien:
1. `docker compose up -d` → alle healthy
2. Market Data → Signal → Risk → Execution (end-to-end)
3. Risk-Limits greifen
4. **pytest -v → alle Tests grün** ← DEIN ZIEL
5. Coverage-Report >60%

---

**Version**: 3.0 (Optimiert für Claude Code)  
**Letzte Aktualisierung**: 2025-11-18  
**Maintainer**: Claire de Binaire Team  
**Dein Ansprechpartner**: Jannek (via Claude Chat)

---

## 🎯 Dein nächster Schritt:

```bash
# 1. Dependencies installieren
pip install -r requirements-dev.txt

# 2. Tests prüfen (sollten skippen)
pytest -v

# 3. Ersten Test implementieren
# Öffne: tests/test_risk_engine_core.py
# Funktion: test_daily_drawdown_blocks_trading

# 4. Test ausführen
pytest -v tests/test_risk_engine_core.py

# 5. Bei Erfolg: Nächsten Test
```

**Viel Erfolg! 🚀**
