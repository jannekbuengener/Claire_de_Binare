# Local E2E Tests - Claire de Binaire

> **Dokumentation für lokale End-to-End Tests**
> Erstellt: 2025-11-19
> Status: ✅ Implementiert & Validiert

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Test-Kategorien](#test-kategorien)
3. [Voraussetzungen](#voraussetzungen)
4. [Schnellstart](#schnellstart)
5. [Test-Ausführung](#test-ausführung)
6. [Test-Beschreibungen](#test-beschreibungen)
7. [Troubleshooting](#troubleshooting)
8. [Integration mit CI/CD](#integration-mit-cicd)

---

## Übersicht

Das Claire-Projekt unterscheidet zwischen **CI-Tests** (schnell, mit Mocks) und **lokalen E2E-Tests** (mit echten Containern).

### Warum lokale-only Tests?

E2E-Tests sind:
- **Zu langsam** für CI (>10s Laufzeit)
- **Ressourcen-intensiv** (benötigen Docker-Container)
- **Nur lokal sinnvoll** für manuelle System-Validierung

### Test-Architektur

```
tests/
├── unit/                     # Unit-Tests (CI + lokal)
│   ├── test_risk_engine_core.py
│   └── test_risk_engine_edge_cases.py
├── integration/              # Integration mit Mocks (CI + lokal)
│   └── test_event_pipeline.py
└── e2e/                      # E2E mit echten Containern (NUR lokal)
    ├── test_docker_compose_full_stack.py
    ├── test_redis_postgres_integration.py
    └── test_event_flow_pipeline.py
```

---

## Test-Kategorien

### Pytest-Marker

| Marker | Beschreibung | CI | Lokal |
|--------|--------------|:--:|:-----:|
| `@pytest.mark.unit` | Schnelle Unit-Tests | ✅ | ✅ |
| `@pytest.mark.integration` | Integration mit Mocks | ✅ | ✅ |
| `@pytest.mark.e2e` | End-to-End mit Containern | ❌ | ✅ |
| `@pytest.mark.local_only` | Explizit nur lokal | ❌ | ✅ |
| `@pytest.mark.slow` | Tests mit >10s Laufzeit | ❌ | ✅ |

### Test-Scopes

**CI-Tests** (GitHub Actions):
```bash
pytest -m "not e2e and not local_only"
```
- ✅ Unit-Tests
- ✅ Integration-Tests (mit Mocks)
- ❌ E2E-Tests
- ⚡ Laufzeit: <5s

**Lokale E2E-Tests**:
```bash
pytest -m e2e
```
- ✅ Docker Compose Stack-Validierung
- ✅ Redis & PostgreSQL Integration
- ✅ Event-Flow Pipeline
- 🐢 Laufzeit: 30-60s

---

## Voraussetzungen

### 1. Dependencies installieren

```bash
pip install -r requirements-dev.txt
```

### 2. .env-Datei konfigurieren

Erstelle `.env` im Projekt-Root:

```bash
# Redis
REDIS_PASSWORD=claire_redis_secret_2024

# PostgreSQL
POSTGRES_USER=claire_user
POSTGRES_PASSWORD=claire_db_secret_2024
POSTGRES_DB=claire_de_binare

# Grafana (für Monitoring)
GRAFANA_PASSWORD=admin
```

### 3. Docker Compose starten

```bash
docker compose up -d
```

Warte 10-15 Sekunden, bis alle Container healthy sind:

```bash
docker compose ps
```

Erwartete Ausgabe:
```
NAME            STATUS
cdb_redis       Up (healthy)
cdb_postgres    Up (healthy)
cdb_ws          Up (healthy)
cdb_core        Up (healthy)
cdb_risk        Up (healthy)
cdb_execution   Up (healthy)
cdb_prometheus  Up (healthy)
cdb_grafana     Up (healthy)
```

---

## Schnellstart

### Variante 1: Mit Makefile (Linux/Mac)

```bash
# Alle CI-Tests (Unit + Integration, ohne E2E)
make test

# Nur Unit-Tests
make test-unit

# Nur E2E-Tests (benötigt Docker)
make test-e2e

# Vollständig: Docker starten + E2E-Tests
make test-full-system
```

### Variante 2: Direkt mit pytest (Windows/Linux/Mac)

```bash
# CI-Tests (schnell, ohne E2E)
pytest -v -m "not e2e and not local_only"

# Nur E2E-Tests
pytest -v -m e2e

# Nur lokale-only Tests
pytest -v -m local_only

# Bestimmte Test-Datei
pytest -v tests/e2e/test_docker_compose_full_stack.py
```

---

## Test-Ausführung

### 1. CI-Tests (schnell, automatisch in GitHub Actions)

```bash
pytest -v -m "not e2e and not local_only"
```

**Ergebnis**:
```
======================== 12 passed, 2 skipped, 18 deselected =========================
Laufzeit: ~0.5s
```

- ✅ 12 Unit-Tests bestanden
- ⏭️ 2 Integration-Tests geskippt (Placeholders)
- 🚫 18 E2E-Tests deselektiert (nicht in CI)

### 2. E2E-Tests (lokal, mit Docker)

**Voraussetzung**: Docker Compose läuft (`docker compose up -d`)

```bash
pytest -v -m e2e
```

**Erwartetes Ergebnis**:
```
tests/e2e/test_docker_compose_full_stack.py::test_docker_compose_stack_is_running PASSED
tests/e2e/test_docker_compose_full_stack.py::test_docker_compose_containers_are_healthy PASSED
tests/e2e/test_docker_compose_full_stack.py::test_http_health_endpoints_respond PASSED
tests/e2e/test_docker_compose_full_stack.py::test_services_respond_with_valid_health_json PASSED
tests/e2e/test_docker_compose_full_stack.py::test_docker_compose_config_is_valid PASSED

tests/e2e/test_redis_postgres_integration.py::test_redis_connection PASSED
tests/e2e/test_redis_postgres_integration.py::test_redis_pub_sub_basic PASSED
tests/e2e/test_redis_postgres_integration.py::test_redis_set_get PASSED
tests/e2e/test_redis_postgres_integration.py::test_redis_event_bus_simulation PASSED
tests/e2e/test_redis_postgres_integration.py::test_postgres_connection PASSED
tests/e2e/test_redis_postgres_integration.py::test_postgres_tables_exist PASSED
tests/e2e/test_redis_postgres_integration.py::test_postgres_insert_select_signal PASSED
tests/e2e/test_redis_postgres_integration.py::test_redis_to_postgres_flow PASSED

tests/e2e/test_event_flow_pipeline.py::test_market_data_event_published PASSED
tests/e2e/test_event_flow_pipeline.py::test_signal_engine_responds_to_market_data PASSED
tests/e2e/test_event_flow_pipeline.py::test_risk_manager_validates_signal PASSED
tests/e2e/test_event_flow_pipeline.py::test_full_event_pipeline_simulation PASSED
tests/e2e/test_event_flow_pipeline.py::test_all_services_are_healthy_for_event_flow PASSED

======================== 18 passed in 35s =========================
```

### 3. Coverage-Report (ohne E2E)

```bash
pytest --cov=services --cov=backoffice/services --cov-report=html -m "not e2e and not local_only"
```

Öffne: `htmlcov/index.html`

---

## Test-Beschreibungen

### tests/e2e/test_docker_compose_full_stack.py

**Zweck**: Validiert Docker Compose Stack

| Test | Beschreibung |
|------|-------------|
| `test_docker_compose_stack_is_running` | Alle Container laufen |
| `test_docker_compose_containers_are_healthy` | Alle Health-Checks bestehen |
| `test_http_health_endpoints_respond` | HTTP /health Endpoints antworten |
| `test_services_respond_with_valid_health_json` | Health-JSON ist valide |
| `test_docker_compose_config_is_valid` | docker-compose.yml Syntax OK |

### tests/e2e/test_redis_postgres_integration.py

**Zweck**: Testet echte Redis & PostgreSQL Integration

| Test | Beschreibung |
|------|-------------|
| `test_redis_connection` | Redis-Verbindung funktioniert |
| `test_redis_pub_sub_basic` | Pub/Sub Pattern funktioniert |
| `test_redis_set_get` | SET/GET Operations |
| `test_redis_event_bus_simulation` | Event-Bus Pattern (market_data → signals) |
| `test_postgres_connection` | PostgreSQL-Verbindung funktioniert |
| `test_postgres_tables_exist` | Erwartete Tabellen existieren |
| `test_postgres_insert_select_signal` | INSERT/SELECT in signals-Tabelle |
| `test_redis_to_postgres_flow` | Cross-Service: Redis → PostgreSQL |

### tests/e2e/test_event_flow_pipeline.py

**Zweck**: Testet vollständigen Event-Flow

| Test | Beschreibung |
|------|-------------|
| `test_market_data_event_published` | Market-Data Events werden gepublished |
| `test_signal_engine_responds_to_market_data` | Signal-Engine reagiert auf Market-Data |
| `test_risk_manager_validates_signal` | Risk-Manager validiert Signale |
| `test_full_event_pipeline_simulation` | End-to-End: Market-Data → DB |
| `test_all_services_are_healthy_for_event_flow` | Alle Services sind healthy |

---

## Troubleshooting

### Problem: "Docker Compose Stack nicht gestartet"

**Symptom**:
```
pytest.skip: Docker Compose Stack nicht gestartet.
```

**Lösung**:
```bash
# .env-Datei prüfen (siehe oben)
docker compose up -d

# Warte 10s
sleep 10

# Status prüfen
docker compose ps
```

### Problem: "Redis nicht erreichbar"

**Symptom**:
```
redis.ConnectionError: Connection refused
```

**Lösung**:
```bash
# Redis-Container prüfen
docker compose logs cdb_redis

# Passwort in .env korrekt?
cat .env | grep REDIS_PASSWORD

# Container neu starten
docker compose restart cdb_redis
```

### Problem: "PostgreSQL nicht erreichbar"

**Symptom**:
```
psycopg2.OperationalError: Connection refused
```

**Lösung**:
```bash
# PostgreSQL-Container prüfen
docker compose logs cdb_postgres

# .env-Variablen korrekt?
cat .env | grep POSTGRES

# Container neu starten
docker compose restart cdb_postgres
```

### Problem: "Health-Check schlägt fehl"

**Symptom**:
```
assert is_healthy, "Container 'cdb_core' ist nicht healthy"
```

**Lösung**:
```bash
# Container-Logs prüfen
docker compose logs cdb_core

# Health-Status prüfen
docker inspect cdb_core | grep -i health

# Container neu bauen
docker compose up -d --build cdb_core
```

### Problem: Tests sind zu langsam

**Symptom**:
E2E-Tests dauern >60s

**Erklärung**:
Das ist normal! E2E-Tests mit echten Containern sind langsam.

**Optimierung**:
- Führe nur geänderte Test-Dateien aus:
  ```bash
  pytest -v tests/e2e/test_docker_compose_full_stack.py
  ```
- Nutze `pytest-xdist` für parallele Ausführung:
  ```bash
  pip install pytest-xdist
  pytest -v -m e2e -n auto
  ```

---

## Integration mit CI/CD

### GitHub Actions (.github/workflows/ci.yaml)

E2E-Tests sind **explizit deaktiviert** in CI:

```yaml
- run: pytest -q -m "not e2e and not local_only"
```

**Warum?**
- ❌ Zu langsam (>30s)
- ❌ Benötigt Docker-in-Docker
- ❌ Ressourcen-intensiv
- ✅ Lokal ausreichend validiert

### Pre-Commit Hooks (.pre-commit-config.yaml)

E2E-Tests sind **explizit deaktiviert** in Pre-Commit:

```yaml
args: ["-q", "-m", "not e2e and not local_only"]
```

**Warum?**
- ⚡ Commits sollen schnell sein (<5s)
- 🚫 Keine Container-Starts bei jedem Commit
- ✅ Unit + Integration-Tests reichen

---

## Workflow-Empfehlung

### Tägliche Entwicklung

```bash
# 1. Feature entwickeln
# 2. Unit-Tests schreiben & ausführen
pytest -v tests/test_risk_engine_core.py

# 3. Pre-Commit Hook (automatisch bei Commit)
git add .
git commit -m "feat: add daily drawdown test"
# → Führt automatisch Unit + Integration-Tests aus

# 4. Push → CI läuft automatisch
git push
```

### Vor großen Releases

```bash
# 1. Docker Stack starten
docker compose up -d

# 2. Alle E2E-Tests ausführen
pytest -v -m e2e

# 3. Coverage prüfen
pytest --cov=services --cov-report=html

# 4. Manuell validieren
# - Öffne http://localhost:3000 (Grafana)
# - Öffne http://localhost:8000/health (Screener)
# - Prüfe Logs: docker compose logs
```

---

## Nächste Schritte

### Geplante Erweiterungen

- [ ] **CLI-Tests**: `claire run-paper`, `claire run-scenarios`
- [ ] **Performance-Tests**: Load-Testing mit `locust`
- [ ] **Replay-Tests**: Event-Sourcing Replay-Validierung
- [ ] **Chaos-Tests**: Container-Ausfälle simulieren
- [ ] **Security-Tests**: Penetration Testing

### Bekannte Einschränkungen

- ⚠️ E2E-Tests setzen `.env`-Datei voraus (nicht in Git)
- ⚠️ Grafana/Prometheus-Tests fehlen noch
- ⚠️ Multi-Container Orchestration ohne Kubernetes

---

## Zusammenfassung

### Was wurde implementiert?

✅ **Test-Struktur**:
- 3 E2E-Test-Dateien mit 18 Tests
- Saubere Trennung: CI vs. lokale Tests
- Pytest-Marker: `e2e`, `local_only`, `slow`

✅ **Infrastruktur**:
- Makefile mit sinnvollen Targets
- pytest.ini mit erweiterten Markern
- Pre-Commit Hooks (ohne E2E)
- CI/CD Integration (ohne E2E)

✅ **Dokumentation**:
- Dieser Guide
- Inline-Kommentare in Test-Dateien
- Troubleshooting-Sektion

### Wie startet man lokale E2E-Tests?

```bash
# 1. Dependencies
pip install -r requirements-dev.txt

# 2. .env konfigurieren
cp .env.example .env  # Falls vorhanden
# Oder manuell erstellen (siehe oben)

# 3. Docker starten
docker compose up -d

# 4. E2E-Tests ausführen
pytest -v -m e2e
```

### Wie stellt man sicher, dass CI nicht blockiert wird?

✅ CI führt **nur** aus:
```bash
pytest -m "not e2e and not local_only"
```

✅ Pre-Commit Hooks führen **nur** aus:
```bash
pytest -m "not e2e and not local_only"
```

✅ E2E-Tests werden **nur manuell** gestartet:
```bash
pytest -m e2e  # Explizit
```

---

**Version**: 1.0
**Autor**: Claire Local Test Orchestrator
**Letzte Aktualisierung**: 2025-11-19
**Maintainer**: Claire de Binaire Team
