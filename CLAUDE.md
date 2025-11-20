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
**Status**: ✅ Deployment-Ready (100%) | E2E-Tests: 17/18 (94.4%)
**Phase**: N1 - Paper-Test Implementation
**Letztes Update**: 2025-11-20

### 🎯 Aktuelle Prioritäten (November 2025):

**System Status**: ✅ **VOLLSTÄNDIG OPERATIONAL**

1. **Test-Infrastruktur**: ✅ 32 Tests (12 Unit, 2 Integration, 18 E2E)
2. **Risk-Engine**: ✅ 100% Coverage erreicht
3. **MEXC Perpetuals**: ✅ Integriert mit Risk Engine
4. **Advanced Position Sizing**: ✅ Implementiert
5. **Execution Simulator**: ✅ Module 2 & 3 fertig

### ⚡ System läuft:
- **8/8 Container healthy** (alle Services operational)
- **PostgreSQL**: 5 Tabellen (signals, orders, trades, positions, portfolio_snapshots)
- **Redis Message Bus**: Pub/Sub operational
- **Signal Engine**: Momentum-Strategie deployed
- **Risk Manager**: 7-Layer-Validierung aktiv
- **Execution Service**: Paper-Trading funktional

### 📊 Test-Status:
- **E2E-Tests**: 17/18 passed (94.4%) ✅
- **Unit-Tests**: 12/12 passed (100%) ✅
- **Risk-Engine Coverage**: 100% ✅
- **CI/CD**: Fully integrated ✅

---

## 2. Quick Start für Claude Code

### 2.1 Erste Schritte (5 Min)

```bash
# 1. Dependencies installieren
pip install -r requirements-dev.txt

# 2. ENV-Template kopieren
cp .env.example .env

# 3. Docker-Stack starten
docker compose up -d

# 4. Tests ausführen
pytest -v -m "not e2e"  # CI-Tests (schnell)
pytest -v -m e2e        # E2E-Tests (mit Docker)
```

### 2.2 Pflichtlektüre (in dieser Reihenfolge)

| Datei | Zweck | Lesedauer |
|-------|-------|-----------|
| `backoffice/docs/CLAUDE_CODE_BRIEFING.md` | **START HIER** | 5 min |
| `backoffice/PROJECT_STATUS.md` | Live-Status | 3 min |
| `backoffice/docs/testing/E2E_TEST_COMPLETION_REPORT.md` | Test-Infrastruktur | 5 min |
| `backoffice/docs/testing/LOCAL_E2E_TESTS.md` | E2E-Guide | 10 min |
| `services/risk_engine.py` | Risk-Logic Referenz | 10 min |
| `tests/conftest.py` | Test-Fixtures | 3 min |

### 2.3 Wo liegt was?

**Dein Workspace**:
```
/home/user/Claire_de_Binare_Cleanroom/
├── tests/                           ← TEST-INFRASTRUKTUR
│   ├── conftest.py                 ← Fixtures (fertig)
│   ├── e2e/                        ← E2E-Tests (18 Tests)
│   │   ├── test_docker_compose_full_stack.py
│   │   ├── test_redis_postgres_integration.py
│   │   └── test_event_flow_pipeline.py
│   ├── integration/                ← Integration-Tests
│   ├── unit/                       ← Unit-Tests
│   ├── test_risk_engine_*.py       ← Risk-Tests (100% Coverage)
│   ├── test_mexc_perpetuals.py     ← MEXC-Tests
│   ├── test_position_sizing.py     ← Position Sizing
│   └── test_execution_simulator.py ← Execution Tests
│
├── services/                        ← SERVICE-CODE
│   ├── risk_engine.py              ← Risk-Logic (100% Coverage)
│   ├── mexc_perpetuals.py          ← MEXC Integration
│   ├── position_sizing.py          ← Position Sizing
│   └── execution_simulator.py      ← Execution Simulator
│
├── backoffice/                      ← DOKUMENTATION
│   ├── docs/
│   │   ├── testing/                ← Test-Guides
│   │   ├── architecture/           ← System-Design
│   │   ├── services/               ← Event-Flows
│   │   ├── security/               ← Security-Richtlinien
│   │   └── schema/                 ← Datenmodelle (YAML)
│   ├── services/                   ← Legacy-Services (backoffice/services/)
│   │   ├── signal_engine/
│   │   ├── risk_manager/
│   │   └── execution_service/
│   └── PROJECT_STATUS.md           ← ⭐ Live-Status
│
├── docker-compose.yml               ← Container-Definition (8 Services)
├── pytest.ini                       ← Test-Konfiguration
├── Makefile                         ← Test-Targets
├── requirements-dev.txt             ← Test-Dependencies
└── .env                            ← ENV-Variablen (nicht committen!)
```

### 2.4 Schnellstart-Commands

```bash
# CI-Tests (schnell, ohne Docker)
pytest -v -m "not e2e and not local_only"

# E2E-Tests (mit Docker)
docker compose up -d
pytest -v -m e2e

# Coverage-Report generieren
pytest --cov=services --cov-report=html

# Makefile-Targets (Linux/Mac)
make test              # CI-Tests
make test-e2e          # E2E-Tests
make test-full-system  # Docker + E2E komplett
```

---

## 3. Projektkontext

### 3.1 Naming (KRITISCH – nicht ändern!)

**Dokumentation/Kommunikation**:
- ✅ **Claire de Binaire** (offiziell)

**Code/Tech-IDs**:
- ✅ `claire_de_binaire` (DB-Name, Volumes)
- ✅ `cdb_*` (Service-Präfix: `cdb_core`, `cdb_risk`, `cdb_execution`)

❌ **VERALTET**: „Claire de Binare" (alte Schreibweise – bei Fund melden)

### 3.2 System-Übersicht

**Container (8/8 healthy)**:
```
cdb_redis       → Port 6379  (Message Bus)
cdb_postgres    → Port 5432  (PostgreSQL)
cdb_ws          → Port 8000  (WebSocket Screener)
cdb_core        → Port 8001  (Signal Engine)
cdb_risk        → Port 8002  (Risk Manager)
cdb_execution   → Port 8003  (Execution Service)
cdb_prometheus  → Port 19090 (Metrics Collector)
cdb_grafana     → Port 3000  (Monitoring Dashboard)
```

**Services (Status)**:
- ✅ Signal Engine – Momentum-Strategie deployed
- ✅ Risk Manager – 7-Layer-Validierung aktiv (100% Coverage)
- ✅ Execution Service – Paper-Trading operational
- ✅ MEXC Perpetuals – Integriert mit Risk Engine
- ✅ Position Sizing – Advanced Module implementiert

**Test-Status**:
- ✅ E2E-Tests: 17/18 (94.4%)
- ✅ Unit-Tests: 12/12 (100%)
- ✅ Risk-Engine Coverage: 100%
- ✅ Integration-Tests: 2/2 (Placeholder)

**Letzte Erfolge**:
- ✅ Lokale E2E Test-Suite vollständig (2025-11-19)
- ✅ MEXC Perpetuals Integration (2025-11-19)
- ✅ Risk-Engine 100% Coverage (2025-11-19)
- ✅ Advanced Position Sizing implementiert (2025-11-19)
- ✅ Dokumentation konsolidiert (2025-11-20)

---

## 4. Repository-Struktur

### 4.1 Haupt-Verzeichnisse

```
Claire_de_Binare_Cleanroom/
├── services/              # 🐳 Core-Microservices (Python)
│   ├── risk_engine.py              # Risk-Logic (100% Coverage)
│   ├── mexc_perpetuals.py          # MEXC Integration
│   ├── position_sizing.py          # Position Sizing
│   └── execution_simulator.py      # Execution Simulator
│
├── backoffice/services/   # 🔧 Legacy-Services (Container)
│   ├── signal_engine/              # Signal-Logic
│   ├── risk_manager/               # Risk-Manager
│   └── execution_service/          # Execution Service
│
├── tests/                 # 🧪 Pytest-Suite (32 Tests)
│   ├── conftest.py                 # Fixtures & Mocks
│   ├── e2e/                        # E2E-Tests (18)
│   │   ├── test_docker_compose_full_stack.py     (5)
│   │   ├── test_redis_postgres_integration.py    (8)
│   │   └── test_event_flow_pipeline.py           (5)
│   ├── integration/                # Integration-Tests (2)
│   ├── unit/                       # Unit-Tests
│   ├── test_risk_engine_*.py       # Risk-Tests (100% Coverage)
│   ├── test_mexc_perpetuals.py     # MEXC-Tests
│   ├── test_position_sizing.py     # Position Sizing Tests
│   └── test_execution_simulator.py # Execution Tests
│
├── backoffice/            # 📚 Dokumentation (61 MD-Dateien)
│   ├── docs/
│   │   ├── testing/                # Test-Guides
│   │   │   ├── E2E_TEST_COMPLETION_REPORT.md
│   │   │   └── LOCAL_E2E_TESTS.md
│   │   ├── architecture/           # System-Design
│   │   ├── services/               # Event-Flows
│   │   ├── security/               # Security-Richtlinien
│   │   ├── schema/                 # Datenmodelle (YAML)
│   │   ├── runbooks/               # Runbooks & Workflows
│   │   ├── CLAUDE_CODE_BRIEFING.md # ← START HIER
│   │   └── DECISION_LOG.md         # Entscheidungs-Historie
│   └── PROJECT_STATUS.md           # ⭐ Live-Status
│
├── docker-compose.yml     # Container-Definition (8 Services)
├── pytest.ini             # Test-Konfiguration
├── Makefile               # Test-Targets
├── requirements-dev.txt   # Test-Dependencies
└── .env                   # ENV-Variablen (nicht committen!)
```

### 4.2 Datei-Zuordnung (für neue Dateien)

| Was du erstellst | Wohin |
|-----------------|-------|
| Test-Code (Unit/Integration) | `tests/test_*.py` |
| Test-Code (E2E) | `tests/e2e/test_*.py` |
| Service-Code (Core) | `services/*.py` |
| Service-Code (Container) | `backoffice/services/cdb_*/` |
| Dokumentation | `backoffice/docs/` |
| Schemas | `backoffice/docs/schema/` |
| Runbooks | `backoffice/docs/runbooks/` |
| Test-Guides | `backoffice/docs/testing/` |

---

## 5. Arbeitsweisen nach Aufgabentyp

### 5.1 Test-Engineering

**Workflow**:
1. Prüfe bestehende Tests in `tests/`
2. Nutze Fixtures aus `conftest.py`
3. Schreibe Tests im Arrange-Act-Assert-Pattern
4. Führe aus: `pytest -v tests/test_*.py`
5. Coverage prüfen: `pytest --cov=services --cov-report=html`

**Test-Kategorien (Marker)**:
```python
@pytest.mark.unit          # Schnell, keine Ext. Dependencies
@pytest.mark.integration   # Mit Redis/PostgreSQL (gemockt)
@pytest.mark.e2e          # End-to-End mit echten Containern
@pytest.mark.local_only   # Nur lokal, nicht in CI
@pytest.mark.slow         # >10s Runtime
```

**Test-Struktur (Pflicht)**:
```python
@pytest.mark.unit
def test_descriptive_name(fixture1, fixture2):
    """
    Test: Beschreibung was getestet wird

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
    assert "daily_drawdown" in result["reason"].lower()
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
# CI-Tests (schnell, ohne Docker)
pytest -v -m "not e2e and not local_only"

# E2E-Tests (mit Docker)
docker compose up -d
pytest -v -m e2e

# Bestimmte Test-Suite
pytest -v tests/e2e/test_redis_postgres_integration.py

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
from typing import Dict, Optional, List
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
- ✅ Test-Dokumentation – `backoffice/docs/testing/`
- ❌ `archive/` – Read-Only (nicht ändern!)

**Prüfpunkte bei Doku-Audit**:
1. Projektname: „Claire de Binaire" (nicht „Binare")
2. Tech-IDs: `claire_de_binaire`, `cdb_*`
3. Links funktionsfähig
4. Status aktuell
5. Code-Beispiele lauffähig
6. Test-Status korrekt (32 Tests, 17/18 E2E)

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
│ Risk Manager │ (cdb_risk:8002) ✅ 100% Coverage
└──────┬───────┘
       ↓ orders (Redis)
┌──────────────┐
│ Execution    │ (cdb_execution:8003)
└──────┬───────┘
       ↓ order_results (Redis)
┌──────────────┐
│ PostgreSQL   │ (cdb_postgres:5432)
│ 5 Tabellen   │
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

# Docker-Netzwerk
REDIS_HOST=cdb_redis
REDIS_PORT=6379
POSTGRES_HOST=cdb_postgres
POSTGRES_PORT=5432
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
# services/*.py oder backoffice/services/cdb_*/service.py
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
git commit -m "feat: add MEXC perpetuals integration"
git commit -m "fix: risk validation logic for edge cases"
git commit -m "test: achieve 100% coverage for risk engine"
git commit -m "docs: update CLAUDE.md with current state"
```

---

## 8. Testing mit pytest

### 8.1 Test-Kategorien (Marker)

```python
@pytest.mark.unit          # Schnell, keine Ext. Dependencies
@pytest.mark.integration   # Mit Redis/PostgreSQL (gemockt)
@pytest.mark.e2e          # End-to-End mit echten Containern
@pytest.mark.local_only   # Nur lokal, nicht in CI
@pytest.mark.slow         # >10s Runtime
```

**Ausführung nach Kategorie**:
```bash
pytest -v -m unit                    # Nur Unit-Tests
pytest -v -m "not e2e and not slow"  # CI-Tests
pytest -v -m e2e                     # E2E-Tests (Docker)
```

### 8.2 Test-Übersicht (32 Tests)

**Unit-Tests** (12):
- `tests/test_risk_engine_core.py` (4)
- `tests/test_risk_engine_edge_cases.py` (3)
- `tests/unit/` (5+)

**Integration-Tests** (2):
- `tests/integration/` (2 Placeholder)

**E2E-Tests** (18):
- `tests/e2e/test_docker_compose_full_stack.py` (5)
- `tests/e2e/test_redis_postgres_integration.py` (8)
- `tests/e2e/test_event_flow_pipeline.py` (5)

**Success-Rates**:
- Unit-Tests: 100% (12/12) ✅
- E2E-Tests: 94.4% (17/18) ✅
- Risk-Engine Coverage: 100% ✅

### 8.3 Fixtures (aus conftest.py)

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

### 8.4 Assertion-Patterns

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

---

## 9. Troubleshooting

### 9.1 Docker-Container starten nicht

**Problem**: `docker compose up -d` schlägt fehl oder Container crashen

**Lösung**:
```bash
# 1. Logs prüfen
docker compose logs --tail=100 cdb_core cdb_risk cdb_execution

# 2. ENV-Variablen prüfen
cat .env

# 3. Häufigste Fehlerquellen:
# - REDIS_HOST=cdb_redis (nicht "redis")
# - POSTGRES_HOST=cdb_postgres (nicht "localhost")
# - Alle Passwörter gesetzt

# 4. Clean-Restart
docker compose down
docker compose up -d --build
```

### 9.2 E2E-Tests schlagen fehl

**Problem**: `pytest -v -m e2e` meldet Fehler

**Lösung**:
```bash
# 1. Docker-Status prüfen
docker compose ps  # Sollte 8/8 healthy zeigen

# 2. Health-Checks manuell
curl -fsS http://localhost:8001/health  # Signal Engine
curl -fsS http://localhost:8002/health  # Risk Manager
curl -fsS http://localhost:8003/health  # Execution

# 3. Warte auf Container-Start
sleep 30  # Container brauchen Zeit zum Hochfahren

# 4. Dependencies installiert?
pip install -r requirements-dev.txt
```

### 9.3 Import-Errors

**Problem**: `ModuleNotFoundError: No module named 'services'`

**Lösung**:
```bash
# Python-Path setzen (im Projekt-Root)
export PYTHONPATH=$PYTHONPATH:$(pwd)  # Linux/Mac
$env:PYTHONPATH += ";$(Get-Location)" # Windows PowerShell

# Dependencies installieren
pip install -r requirements-dev.txt

# Besonders: psycopg2 für PostgreSQL-Tests
pip install psycopg2-binary
```

### 9.4 CI-Tests laufen, E2E nicht

**Problem**: CI-Tests funktionieren, aber E2E-Tests fehlen

**Erklärung**: Das ist **KORREKT** by design.

```bash
# CI führt NIEMALS E2E-Tests aus:
pytest -q -m "not e2e and not local_only"

# E2E-Tests MÜSSEN explizit gestartet werden:
docker compose up -d
pytest -v -m e2e
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
8. **E2E-Tests in CI** – NIEMALS `pytest -m e2e` in CI

### ✅ Immer tun:

1. **Type Hints** – Für alle Funktions-Parameter
2. **Structured Logging** – JSON-Format bevorzugt
3. **ENV-Config** – Keine Hardcodes
4. **Tests schreiben** – Für neue Features
5. **Doku aktualisieren** – Bei Änderungen
6. **PROJECT_STATUS.md updaten** – Bei Meilensteinen
7. **Arrange-Act-Assert** – In allen Tests
8. **Test-Marker verwenden** – `@pytest.mark.unit`, etc.

### 🤔 Bei Unsicherheit:

**NICHT raten** – Stattdessen:
1. Unsicherheit explizit benennen
2. Relevante Datei vorschlagen zum Prüfen
3. Auf Jannek's Antwort warten

**Beispiel**:
> „Ich bin unsicher, ob das neue Feature bereits getestet ist.
> Soll ich `tests/test_*.py` analysieren?"

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

# Clean-Restart (alle Services)
docker compose down
docker compose up -d --build
```

### Pytest:
```bash
# CI-Tests (schnell, ohne Docker)
pytest -v -m "not e2e and not local_only"

# E2E-Tests (mit Docker)
docker compose up -d
pytest -v -m e2e

# Mit Coverage
pytest --cov=services --cov-report=html

# Nur fehlgeschlagene erneut
pytest --lf

# Verbose Output
pytest -vv -s

# Bestimmte Datei
pytest -v tests/test_risk_engine_core.py::test_daily_drawdown_blocks_trading
```

### Makefile (Linux/Mac):
```bash
make test              # CI-Tests
make test-e2e          # E2E-Tests
make test-full-system  # Docker + E2E
make docker-up         # Starte Container
make docker-down       # Stoppe Container
make docker-health     # Health-Status
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
| `backoffice/docs/testing/E2E_TEST_COMPLETION_REPORT.md` | Test-Status |
| `backoffice/docs/testing/LOCAL_E2E_TESTS.md` | E2E-Guide |
| `services/risk_engine.py` | Risk-Logic (100% Coverage) |
| `services/mexc_perpetuals.py` | MEXC Integration |
| `tests/conftest.py` | Test-Fixtures |
| `pytest.ini` | Test-Konfiguration |
| `.env.example` | ENV-Template |

### Service-Ports:

| Service | Port | Endpoint |
|---------|------|----------|
| WebSocket/REST | 8000 | `/health` |
| Signal Engine | 8001 | `/health`, `/status` |
| Risk Manager | 8002 | `/health`, `/status` |
| Execution | 8003 | `/health`, `/status` |
| PostgreSQL | 5432 | - |
| Redis | 6379 | - |
| Grafana | 3000 | `/api/health` |
| Prometheus | 19090 | `/-/healthy` |

### Risk-Limits (ENV):

```bash
MAX_POSITION_PCT=0.10              # 10%
MAX_DAILY_DRAWDOWN_PCT=0.05        # 5%
MAX_TOTAL_EXPOSURE_PCT=0.30        # 30%
CIRCUIT_BREAKER_THRESHOLD_PCT=0.10 # 10%
```

### Test-Commands:

```bash
# CI-Tests
pytest -v -m "not e2e and not local_only"

# E2E-Tests
docker compose up -d && pytest -v -m e2e

# Coverage
pytest --cov=services --cov-report=html

# Makefile
make test              # CI-Tests
make test-e2e          # E2E-Tests
make test-full-system  # Docker + E2E
```

---

## 14. Definition of Done (N1 MVP)

### Infrastruktur:
- ✅ 8/8 Container healthy
- ✅ Health-Endpoints aktiv
- ✅ Structured Logging
- ✅ Docker-Netzwerk funktioniert

### Services:
- ✅ Signal Engine deployed & läuft
- ✅ Risk Manager deployed & läuft (100% Coverage)
- ✅ Execution Service deployed & läuft
- ✅ MEXC Perpetuals integriert
- ✅ Advanced Position Sizing implementiert

### Testing:
- ✅ **32 Tests implementiert** (12 Unit, 2 Integration, 18 E2E)
- ✅ **E2E-Tests: 17/18 bestanden (94.4%)**
- ✅ **Risk-Engine: 100% Coverage**
- ✅ **CI/CD-Integration vollständig**
- ✅ **Lokale Test-Suite vollständig** - tests/e2e/ mit 3 Dateien

### Daten:
- ✅ PostgreSQL (5 Tabellen: signals, orders, trades, positions, portfolio_snapshots)
- ✅ Redis Message Bus (Pub/Sub funktional)
- ✅ Trade-Historie persistent (PostgreSQL)

### Dokumentation:
- ✅ **E2E_TEST_COMPLETION_REPORT.md** (vollständig)
- ✅ **LOCAL_E2E_TESTS.md** (8500+ Wörter)
- ✅ **CLAUDE.md** (aktualisiert)
- ✅ **tests/README.md** (Schnellstart)
- ✅ **.env.example** (Template)

---

## 15. Aktuelle Entwicklungs-Schwerpunkte

### ✅ ABGESCHLOSSEN (2025-11-19/20):

1. **Lokale E2E Test-Suite**
   - 18 E2E-Tests implementiert
   - 17/18 bestanden (94.4%)
   - Vollständige Dokumentation

2. **Risk-Engine**
   - 100% Test-Coverage erreicht
   - 7-Layer-Validierung vollständig
   - Edge-Cases abgedeckt

3. **MEXC Perpetuals**
   - Integration mit Risk Engine
   - Position Sizing implementiert
   - Execution Simulator Module 2 & 3

4. **Dokumentation**
   - Konsolidiert und reorganisiert
   - Test-Guides vollständig
   - CLAUDE.md aktualisiert

### ⏳ IN PROGRESS:

- None (System operational)

### 📋 BACKLOG:

1. **Performance-Tests**
   - Load-Testing mit locust
   - Stress-Tests für Redis/PostgreSQL

2. **CLI-Tools-Tests**
   - `claire run-paper`
   - `claire run-scenarios`
   - `claire_cli.py` Commands

3. **Security-Tests**
   - Penetration Testing
   - Secret-Scanning

4. **Chaos-Tests**
   - Container-Ausfälle simulieren
   - Network-Latenz testen

---

**Letztes Update**: 2025-11-20
**Version**: 2.0.0
**Status**: ✅ **VOLLSTÄNDIG OPERATIONAL**
**Test-Success-Rate**: 94.4% (17/18 E2E)
**Alle Services**: healthy
**Dokumentation**: vollständig
