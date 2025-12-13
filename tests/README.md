# Claire de Binare - Test Suite

> **Schnellstart-Guide für Tests**

---

## 🚀 Schnellstart

```bash
# 1. Dependencies installieren
pip install -r requirements-dev.txt

# 2. Alle CI-Tests ausführen (schnell, ohne E2E)
pytest -v -m "not e2e and not local_only"

# 3. E2E-Tests ausführen (benötigt Docker)
docker compose up -d
pytest -v -m e2e
```

---

## 📁 Test-Struktur

```
tests/
├── unit/                     # Unit-Tests (CI + lokal)
│   ├── test_risk_engine_core.py
│   └── test_risk_engine_edge_cases.py
│
├── integration/              # Integration mit Mocks (CI + lokal)
│   └── test_event_pipeline.py
│
├── e2e/                      # E2E mit echten Containern (NUR lokal)
│   ├── test_docker_compose_full_stack.py
│   ├── test_redis_postgres_integration.py
│   └── test_event_flow_pipeline.py
│
└── conftest.py              # Shared Fixtures
```

---

## 🏷️ Test-Kategorien

| Marker | CI | Lokal | Laufzeit | Docker benötigt |
|--------|:--:|:-----:|:--------:|:---------------:|
| `unit` | ✅ | ✅ | <1s | ❌ |
| `integration` | ✅ | ✅ | <5s | ❌ (Mocks) |
| `e2e` | ❌ | ✅ | 30-60s | ✅ |
| `local_only` | ❌ | ✅ | variabel | ✅ |
| `slow` | ❌ | ✅ | >10s | ✅ |

---

## 🧪 Test-Commands

### CI-Tests (schnell, automatisch)

```bash
# Alle CI-Tests
pytest -v -m "not e2e and not local_only"

# Nur Unit-Tests
pytest -v -m unit

# Mit Coverage
pytest --cov=services --cov-report=html
```

### E2E-Tests (lokal, manuell)

```bash
# Voraussetzung: Docker starten
docker compose up -d

# Alle E2E-Tests
pytest -v -m e2e

# Bestimmte Test-Datei
pytest -v tests/e2e/test_docker_compose_full_stack.py
```

### Mit Makefile (Linux/Mac)

```bash
make test              # CI-Tests
make test-unit         # Nur Unit-Tests
make test-e2e          # E2E-Tests
make test-full-system  # Docker + E2E
```

---

## 📊 Erwartete Ergebnisse

### CI-Tests (ohne E2E)

```
================ 102 passed, 2 skipped, 18 deselected in 0.59s =================
```

- ✅ 102 Tests bestanden (90 Unit + 12 Integration)
- ⏭️ 2 Integration-Tests geskippt (Placeholders)
- 🚫 18 E2E-Tests deselektiert

### E2E-Tests (mit Docker)

```
======================== 18 passed in 35s =========================
```

- ✅ 5 Docker Compose Stack-Tests
- ✅ 8 Redis/PostgreSQL Integration-Tests
- ✅ 5 Event-Flow Pipeline-Tests

---

## 🔧 Fixtures

Verfügbare Fixtures in `conftest.py`:

### Unit-Test Fixtures (mit Mocks)
- `mock_redis` - Gemockter Redis-Client
- `mock_postgres` - Gemockter PostgreSQL-Pool
- `risk_config` - Risk-Konfiguration
- `sample_risk_state` - Portfolio-Snapshot
- `sample_signal_event` - Test-Signal

### E2E-Test Fixtures (echte Verbindungen)
- `redis_connection` - Echte Redis-Verbindung
- `postgres_connection` - Echte PostgreSQL-Verbindung
- `docker_compose_running` - Prüft ob Docker läuft
- `clean_test_data` - Cleanup nach Test

---

## ⚠️ Troubleshooting

### Tests schlagen fehl: "Docker nicht gestartet"

```bash
# .env-Datei erstellen (siehe .env.example)
# Dann:
docker compose up -d
sleep 10  # Warte bis Container healthy sind
pytest -v -m e2e
```

### Tests schlagen fehl: "Module not found"

```bash
pip install -r requirements-dev.txt
```

### E2E-Tests sind zu langsam

Das ist normal! E2E-Tests mit echten Containern dauern 30-60s.

Optimierung:
```bash
# Nur geänderte Test-Datei ausführen
pytest -v tests/e2e/test_docker_compose_full_stack.py

# Parallele Ausführung
pip install pytest-xdist
pytest -v -m e2e -n auto
```

---

## 📚 Weitere Dokumentation

- **Vollständige E2E-Dokumentation**: `backoffice/docs/testing/LOCAL_E2E_TESTS.md`
- **Projekt-Anleitung**: `CLAUDE.md`
- **CI/CD-Konfiguration**: `.github/workflows/ci.yaml`
- **Pre-Commit Hooks**: `.pre-commit-config.yaml`

---

## ✅ Pre-Commit Hooks (optional)

```bash
# Installation
pip install pre-commit
pre-commit install

# Manuell ausführen
pre-commit run --all-files
```

**Hinweis**: Pre-Commit Hooks führen **nur CI-Tests** aus (keine E2E).

---

**Version**: 1.0
**Letzte Aktualisierung**: 2025-11-19
