# Testing Guide – Claire de Binaire

Umfassende Anleitung für das Testing-Framework von Claire de Binaire.

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Quick Start](#quick-start)
3. [Test-Typen](#test-typen)
4. [Test-Ausführung](#test-ausführung)
5. [Coverage](#coverage)
6. [Pre-Commit Hooks](#pre-commit-hooks)
7. [CI/CD Integration](#cicd-integration)
8. [Best Practices](#best-practices)

---

## Übersicht

### Test-Statistiken

```
Total Tests:     73 passed, 1 skipped
Coverage:        100% (53/53 statements)
Test Files:      6 aktive Dateien
Test Types:      Unit (65), Integration (5), Property-Based (8)
Runtime:         ~2.5 seconds (all tests)
```

### Test-Framework

- **pytest** – Test Runner & Framework
- **pytest-cov** – Coverage Reporting
- **pytest-mock** – Mocking für Integration Tests
- **hypothesis** – Property-Based Testing
- **pyyaml** – Docker Compose Validation

---

## Quick Start

### 1. Installation

```bash
# Dependencies installieren
pip install -r requirements-dev.txt

# Optional: Pre-Commit Hooks aktivieren
./scripts/setup-dev.sh
```

### 2. Tests ausführen

```bash
# Alle Tests
pytest -v

# Mit Coverage
pytest --cov=services --cov-report=html

# Nur schnelle Unit-Tests
pytest -v -m unit
```

### 3. Coverage Report anschauen

```bash
# HTML Report generieren
pytest --cov=services --cov-report=html

# Browser öffnen
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## Test-Typen

### 1. Unit Tests (65 Tests)

**Zweck**: Isolierte Tests einzelner Funktionen ohne externe Dependencies.

**Marker**: `@pytest.mark.unit`

**Beispiele**:
- `test_risk_engine_core.py` – Basis-Funktionalität
- `test_risk_engine_edge_cases.py` – Edge-Cases & Grenzwerte
- `test_docker_compose_validation.py` – Config-Validierung

**Ausführung**:
```bash
pytest -v -m unit
```

**Eigenschaften**:
- ✅ Schnell (<0.1s pro Test)
- ✅ Keine externen Services (Redis/PostgreSQL)
- ✅ Deterministisch
- ✅ Für CI/CD geeignet

---

### 2. Parametrized Tests (39 Test-Szenarien)

**Zweck**: Mehrere Szenarien mit einem Test abdecken.

**Datei**: `test_risk_engine_parametrized.py`

**Beispiel**:
```python
@pytest.mark.unit
@pytest.mark.parametrize(
    "daily_pnl,expected_approved",
    [
        (-6000.0, False),  # Über Limit
        (-5000.0, False),  # Am Limit
        (-4999.9, True),   # Unter Limit
    ],
)
def test_daily_drawdown_scenarios(daily_pnl, expected_approved):
    # Test mit verschiedenen PnL-Werten
    ...
```

**Kategorien**:
- Daily Drawdown (7 Szenarien)
- Exposure Limits (7 Szenarien)
- Position Sizing (10 Szenarien)
- Stop-Loss (10 Szenarien)
- Boundary Values (5 Szenarien)

---

### 3. Property-Based Tests (8 Tests)

**Zweck**: Automatisches Finden von Edge-Cases durch randomisierte Inputs.

**Framework**: Hypothesis

**Datei**: `test_risk_engine_hypothesis.py`

**Beispiel**:
```python
from hypothesis import given, strategies as st

@pytest.mark.unit
@given(
    equity=st.floats(min_value=1000.0, max_value=10_000_000.0),
    price=st.floats(min_value=0.01, max_value=1_000_000.0),
)
def test_position_size_never_exceeds_max_pct(equity, price):
    # Hypothesis generiert automatisch 100+ Test-Fälle
    ...
```

**Getestete Invarianten**:
- Position-Size überschreitet nie MAX_POSITION_PCT
- Stop-Loss immer korrekt platziert (Long/Short)
- Drawdown-Decisions konsistent
- Exposure-Limits respektiert

**Ausführung**:
```bash
# Mit Statistics
pytest tests/test_risk_engine_hypothesis.py --hypothesis-show-statistics

# Mehr Test-Fälle generieren
pytest tests/test_risk_engine_hypothesis.py --hypothesis-max-examples=1000
```

---

### 4. Integration Tests (5 Tests)

**Zweck**: Testen der Interaktion zwischen Services (mit Mocks).

**Marker**: `@pytest.mark.integration`

**Datei**: `test_event_pipeline.py`

**Beispiel**:
```python
@pytest.mark.integration
def test_end_to_end_signal_to_order_flow(mock_redis, ...):
    # Simuliert: Signal → Risk → Order Pipeline
    ...
```

**Test-Szenarien**:
- Redis Pub/Sub Event-Flow
- PostgreSQL Persistence
- End-to-End Signal→Order Pipeline
- Rejected Signal Handling
- Batch Signal Processing

**Ausführung**:
```bash
pytest -v -m integration
```

---

### 5. Docker Compose Validation (9 Tests)

**Zweck**: Validierung der docker-compose.yml ohne Docker.

**Datei**: `test_docker_compose_validation.py`

**Getestet**:
- ✅ YAML-Syntax gültig
- ✅ Required Services vorhanden
- ✅ Health-Checks konfiguriert
- ✅ Ports korrekt gemappt
- ✅ Volumes konfiguriert
- ✅ Networks korrekt
- ✅ Restart-Policies gesetzt

---

## Test-Ausführung

### Basis-Kommandos

```bash
# Alle Tests
pytest -v

# Nur Unit-Tests (schnell)
pytest -v -m unit

# Nur Integration-Tests
pytest -v -m integration

# Spezifische Datei
pytest -v tests/test_risk_engine_core.py

# Spezifischer Test
pytest -v tests/test_risk_engine_core.py::test_daily_drawdown_blocks_orders
```

### Mit Coverage

```bash
# Terminal-Report
pytest --cov=services --cov-report=term-missing

# HTML-Report
pytest --cov=services --cov-report=html
open htmlcov/index.html

# JSON-Report (für CI/CD)
pytest --cov=services --cov-report=json

# Coverage-Threshold erzwingen
pytest --cov=services --cov-fail-under=95
```

### Fortgeschritten

```bash
# Parallele Ausführung (mit pytest-xdist)
pytest -n auto

# Nur fehlgeschlagene Tests erneut
pytest --lf

# Stop bei erstem Fehler
pytest -x

# Verbose Output mit Tracebacks
pytest -vv -s

# Mit pdb bei Fehler
pytest --pdb

# Hypothese mit mehr Beispielen
pytest tests/test_risk_engine_hypothesis.py --hypothesis-max-examples=500
```

---

## Coverage

### Coverage-Report verstehen

```
Name                      Stmts   Miss  Cover   Missing
-------------------------------------------------------
services/__init__.py          0      0   100%
services/risk_engine.py      53      0   100%
-------------------------------------------------------
TOTAL                        53      0   100%
```

**Spalten**:
- **Stmts**: Anzahl ausführbarer Statements
- **Miss**: Nicht abgedeckte Statements
- **Cover**: Coverage-Prozentsatz
- **Missing**: Zeilen ohne Coverage

### Coverage-Ziele

```
✅ Minimum: 95% (CI/CD Threshold)
✅ Target:  100%
✅ Aktuell: 100% ✨
```

### HTML-Report

Der HTML-Report zeigt:
- ✅ Line-by-Line Coverage
- ⚠️ Ungetestete Branches
- 📊 Function-Level Coverage
- 🔍 Fehlende Lines highlighted

```bash
pytest --cov=services --cov-report=html
open htmlcov/index.html
```

---

## Pre-Commit Hooks

### Aktivierung

```bash
# Automatisch via Script
./scripts/setup-dev.sh

# Manuell
cp scripts/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Was wird geprüft?

Vor jedem Commit:

1. ✅ **Unit Tests** laufen durch
2. ✅ **Coverage** ≥ 95%
3. ✅ **Keine Debug-Statements** (`pdb`, `breakpoint()`, `print()`)
4. ⚠️ **TODO/FIXME** werden gewarnt (kein Fail)

### Hook deaktivieren (temporär)

```bash
# Für einen Commit überspringen
git commit --no-verify -m "message"
```

---

## CI/CD Integration

### GitHub Actions

**Workflow**: `.github/workflows/pytest.yml`

**Trigger**:
- Push zu `main`, `develop`, `claude/**`
- Pull Requests zu `main`, `develop`

**Matrix**:
- Python 3.11
- Python 3.12

**Steps**:
1. Checkout Code
2. Setup Python + Cache
3. Install Dependencies
4. Run pytest + Coverage
5. Upload Coverage zu Codecov
6. Enforce 95% Threshold

### Docker Health Check

**Workflow**: `.github/workflows/docker-health.yml`

**Prüft**:
- ✅ docker-compose.yml Syntax
- ✅ PostgreSQL Health
- ✅ Redis Health
- ✅ Container Startup

---

## Best Practices

### 1. Test-Struktur (Arrange-Act-Assert)

```python
@pytest.mark.unit
def test_position_size_respects_max_pct():
    # Arrange - Setup
    signal = {"price": 50_000.0, "size": 1.0}
    config = {"MAX_POSITION_PCT": 0.10, "ACCOUNT_EQUITY": 100_000.0}

    # Act - Ausführung
    size = risk_engine.limit_position_size(signal, config)

    # Assert - Prüfung
    assert size == pytest.approx(0.2)
```

### 2. Fixtures nutzen

```python
# Aus conftest.py wiederverwendbar
def test_with_fixtures(risk_config, sample_signal_event):
    # Fixtures automatisch injiziert
    decision = risk_engine.evaluate_signal(sample_signal_event, ...)
    ...
```

### 3. Sprechende Test-Namen

```python
# ✅ GUT
def test_daily_drawdown_blocks_orders_when_limit_exceeded():
    ...

# ❌ SCHLECHT
def test_dd():
    ...
```

### 4. Docstrings mit Kontext

```python
def test_exposure_limit_exceeded():
    """Signal wird blockiert wenn total_exposure_pct > MAX_EXPOSURE_PCT.

    Gegeben: Portfolio mit 28% Exposure
    Wenn: Signal würde 10% hinzufügen (→ 38% > 30% limit)
    Dann: Signal wird mit Grund 'max_exposure_reached' abgelehnt
    """
    ...
```

### 5. Parametrize für ähnliche Tests

```python
# Statt 5 separate Tests
@pytest.mark.parametrize("pnl,expected", [
    (-6000, False),
    (-5000, False),
    (0, True),
])
def test_drawdown_scenarios(pnl, expected):
    ...
```

### 6. Hypothesis für komplexe Invarianten

```python
# Automatisch 100+ randomisierte Test-Fälle
@given(equity=st.floats(min_value=1000.0, max_value=1_000_000.0))
def test_position_size_invariant(equity):
    ...
```

---

## Troubleshooting

### Tests finden nicht

```bash
# Cache löschen
pytest --cache-clear
rm -rf .pytest_cache

# Expliziter Pfad
pytest -v tests/
```

### Import-Errors

```bash
# PYTHONPATH setzen
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Oder pytest mit -s
pytest -v -s
```

### Hypothesis Fehler

```bash
# Seed für Reproduzierbarkeit
pytest tests/test_risk_engine_hypothesis.py --hypothesis-seed=12345

# Database löschen
rm -rf .hypothesis/
```

### Coverage zu niedrig

```bash
# Fehlende Lines anzeigen
pytest --cov=services --cov-report=term-missing

# HTML für Details
pytest --cov=services --cov-report=html
```

---

## Weitere Ressourcen

- [pytest Dokumentation](https://docs.pytest.org/)
- [pytest-cov Guide](https://pytest-cov.readthedocs.io/)
- [Hypothesis Dokumentation](https://hypothesis.readthedocs.io/)
- [conftest.py](../../tests/conftest.py) – Projekt-spezifische Fixtures

---

**Version**: 1.0
**Letzte Aktualisierung**: 2025-11-19
**Maintainer**: Claire de Binaire Team
