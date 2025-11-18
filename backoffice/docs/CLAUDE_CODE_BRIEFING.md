# Claude Code Briefing: Pytest-Struktur finalisieren

## 🎯 Ziel

Pytest-Testing-Infrastruktur für **Claire de Binaire** vollständig implementieren.

---

## 📂 Ausgangslage

**System-Status:**
- ✅ 4 Container laufen (postgres, redis, signal_engine, risk_manager)
- ✅ End-to-End Tests manuell erfolgreich (7/7)
- ✅ Deployment-Readiness: 100%

**Was fehlt:**
- ❌ `tests/` Ordner-Struktur
- ❌ Pytest installiert
- ❌ Test-Code implementiert

---

## 📋 Aufgaben für Claude Code

### 1. Ordner-Struktur erstellen

Erstelle folgende Struktur im Projekt-Root:

```
tests/
├── conftest.py              (✅ Vorlage vorhanden)
├── test_risk_engine_core.py (✅ Template vorhanden)
├── test_risk_engine_limits.py
├── test_signal_engine_core.py
└── test_config_env.py
```

**Dateien kopieren:**
- `conftest.py` aus `/mnt/user-data/outputs/conftest.py`
- `test_risk_engine_core.py` aus `/mnt/user-data/outputs/test_risk_engine_core.py`

---

### 2. Dependencies installieren

**Im Projekt-Root:**

```bash
# Test-Dependencies hinzufügen
cp /mnt/user-data/outputs/requirements-dev.txt ./requirements-dev.txt

# Installieren (venv oder direkt)
pip install -r requirements-dev.txt
```

**Oder über Docker:**
```bash
# requirements-dev.txt zu services/risk_manager/requirements.txt hinzufügen
# Container neu bauen
```

---

### 3. Pytest-Konfiguration

Kopiere `pytest.ini`:

```bash
cp /mnt/user-data/outputs/pytest.ini ./pytest.ini
```

---

### 4. Tests implementieren

**Priorität 1: Risk-Engine Tests (test_risk_engine_core.py)**

Implementiere die 4 markierten Tests:
1. `test_daily_drawdown_blocks_trading` ✅ Template vorhanden
2. `test_exposure_blocks_new_orders` ✅ Template vorhanden
3. `test_circuit_breaker_stops_all_trading` ✅ Template vorhanden
4. `test_position_size_calculation` ✅ Template vorhanden

**Logik-Referenz:**
- Risk-Manager Code: `services/risk_manager/service.py`
- Risk-State: Siehe `conftest.py` Fixture `sample_risk_state`
- Limits: Siehe `conftest.py` Fixture `risk_config`

**Priorität 2: Risk-Engine Limits (test_risk_engine_limits.py)**

Neue Datei erstellen mit Tests für:
- Max Position Size Enforcement
- Total Exposure Tracking
- Concurrent Position Limits

**Priorität 3: Signal-Engine (test_signal_engine_core.py)**

Tests für:
- Signal-Generation Logic
- Confidence-Berechnung
- Momentum-Indikatoren

**Priorität 4: Config/ENV (test_config_env.py)**

Tests für:
- ENV-Variablen Validierung
- Config-Parsing
- Missing ENV Detection

---

### 5. Tests ausführen

**Lokal:**
```bash
pytest -v
pytest -v -m unit  # Nur Unit-Tests
pytest -v tests/test_risk_engine_core.py  # Einzelne Datei
```

**Coverage:**
```bash
pytest --cov=services --cov-report=html
```

---

## 🎯 Erfolgs-Kriterien

**Minimum (Phase 1):**
- ✅ `tests/` Ordner existiert
- ✅ `conftest.py` mit Fixtures
- ✅ 4 Risk-Engine Tests implementiert & grün
- ✅ `pytest -v` läuft ohne Fehler

**Wunsch (Phase 2):**
- ✅ 8+ Tests total (Risk + Signal)
- ✅ Coverage > 60%
- ✅ Integration-Tests mit Redis/PostgreSQL

---

## 📚 Referenz-Dokumente

**Im Projekt:**
- `PYTEST_LAYOUT.md` – Struktur-Übersicht
- `TEST_GUIDE.md` – Manual Testing Anleitung
- `SERVICE_TEMPLATE.md` – Service-Architektur
- `EVENT_SCHEMA.json` – Event-Datenstruktur

**Vorlagen (in /mnt/user-data/outputs/):**
- `conftest.py` – Basis-Fixtures ✅
- `test_risk_engine_core.py` – Test-Template ✅
- `requirements-dev.txt` – Dependencies ✅
- `pytest.ini` – Konfiguration ✅

---

## 🚨 Wichtige Hinweise

**Nicht mocken:**
- Service-Logik selbst (testen, nicht mocken)
- Business-Rules (Risk-Limits, Signal-Confidence)

**Mocken:**
- Redis-Verbindungen (außer bei Integration-Tests)
- PostgreSQL-Verbindungen (außer bei Integration-Tests)
- External APIs (MEXC, falls später relevant)

**Test-Stil:**
- Arrange-Act-Assert Pattern
- Sprechende Test-Namen (`test_daily_drawdown_blocks_trading`)
- Docstrings mit Given-When-Then

---

## 💬 Fragen an Claude Code

Falls unklar:
1. **Service-Logik:** Siehe `services/risk_manager/service.py`
2. **Event-Format:** Siehe `EVENT_SCHEMA.json`
3. **Architektur:** Siehe `ARCHITEKTUR.md`

Bei Problemen:
- Jannek fragen (IT-Chef Claude berichten)
- Logs prüfen (`docker compose logs cdb_risk`)

---

**Start:** Beginne mit `tests/` Ordner + `conftest.py` + Template kopieren.  
**Ziel:** 4 grüne Risk-Engine Tests in Phase 1.

Viel Erfolg! 🚀
