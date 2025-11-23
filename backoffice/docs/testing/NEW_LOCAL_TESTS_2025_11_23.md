# Neue Lokale Tests (2025-11-23) - Schnellstart

> **Ergänzung zu LOCAL_E2E_TESTS.md**
> **Neu hinzugefügt**: 19 Tests in 3 Kategorien

---

## 🆕 Neu hinzugefügte lokale-only Tests

### 1. CLI-Tools Tests (`test_cli_tools.py`)

**8 Tests** für Command-Line Scripts (query_analytics.py):

```bash
# Ausführung
make test-local-cli
# oder
pytest -v -m local_only tests/local/test_cli_tools.py
```

**Was wird getestet:**
- ✅ Script existiert & ist Python-valid
- ✅ --help funktioniert
- ✅ --last-signals N zeigt Signals
- ✅ --last-trades N zeigt Trades
- ✅ --portfolio-summary zeigt Portfolio
- ✅ --trade-statistics zeigt Stats
- ✅ Error-Handling (ungültige Args)
- ✅ DB-Connection-Failure graceful

**Benötigt:**
- PostgreSQL mit Daten
- ENV: `POSTGRES_HOST=localhost`, `POSTGRES_PASSWORD=...`

---

### 2. Chaos/Resilience Tests (`test_chaos_resilience.py`)

**5 Tests** für Container-Ausfälle & Recovery:

```bash
# ⚠️  DESTRUKTIV - nur wenn System stabil!
make test-local-chaos
# oder
pytest -v -m "local_only and chaos" tests/local/test_chaos_resilience.py
```

**Was wird getestet:**
- ✅ Redis crasht & recovered automatisch
- ✅ PostgreSQL crasht & recovered
- ✅ cdb_core crasht, andere Services laufen weiter (Partial Failure)
- ✅ Concurrent Redis + PostgreSQL Crash (Worst-Case)
- ✅ Services reconnecten nach Recovery

**Benötigt:**
- Docker Compose CLI
- Alle 9 Container running
- `pip install redis psycopg2-binary`

**⚠️  ACHTUNG:**
- Diese Tests sind **SEHR DESTRUKTIV** - Container werden ge-killed!
- Nur ausführen wenn System stabil ist
- Nicht in Production!

---

### 3. Backup & Recovery Tests (`test_backup_recovery.py`)

**6 Tests** für Database Backup/Restore:

```bash
# Ausführung
make test-local-backup
# oder
pytest -v -m local_only tests/local/test_backup_recovery.py
```

**Was wird getestet:**
- ✅ pg_dump erstellt .sql Dump-File
- ✅ pg_restore funktioniert (Drop & Recreate DB)
- ✅ Alle 5 Tabellen im Dump enthalten
- ✅ Backup-Performance <60s
- ✅ Data Integrity nach Restore
- ✅ Automated Backup-Script Konzept

**Benötigt:**
- PostgreSQL mit Daten
- Docker Compose CLI (für pg_dump inside container)
- `pip install psycopg2-binary`

---

## 📊 Neue Test-Statistik

| Kategorie | Vorher | Neu | Gesamt |
|-----------|--------|-----|--------|
| **Total Tests** | 104 | +19 | **123** |
| **CI-Tests** | 86 | - | 86 |
| **E2E-Tests** | 18 | - | 18 |
| **Local-Only** | - | +19 | **19** |

**Breakdown Local-Only:**
- CLI-Tools: 8 Tests
- Chaos/Resilience: 5 Tests
- Backup & Recovery: 6 Tests

---

## 🔧 Neue Makefile-Targets

```bash
# Hilfe anzeigen
make help

# Neue Targets:
make test-local-cli        # CLI-Tools Tests (safe)
make test-local-backup     # Backup & Recovery Tests (safe)
make test-local-chaos      # Chaos/Resilience Tests (DESTRUKTIV!)
```

---

## 🎯 Quick-Start (Benutzer-Perspektive)

### Schritt 1: Dependencies installieren

```bash
pip install redis psycopg2-binary
```

### Schritt 2: Docker Compose starten

```bash
docker compose up -d
docker compose ps  # Sollte 9/9 healthy zeigen
```

### Schritt 3: Tests ausführen (empfohlene Reihenfolge)

```bash
# 1. CLI-Tools Tests (safe)
make test-local-cli
# Erwartung: 8 passed in ~10s

# 2. Backup & Recovery Tests (safe)
make test-local-backup
# Erwartung: 6 passed in ~30s

# 3. Chaos/Resilience Tests (DESTRUKTIV - als letztes!)
make test-local-chaos
# Erwartung: 5 passed in ~120s
```

---

## ⚠️  Troubleshooting

### Problem: Import-Errors (redis, psycopg2)

```bash
# Error:
ModuleNotFoundError: No module named 'redis'

# Lösung:
pip install redis psycopg2-binary
```

### Problem: Docker Command Not Found

```bash
# Error:
/bin/bash: docker: command not found

# Lösung:
# Docker Desktop installieren und starten
# Dann: docker compose up -d
```

### Problem: PostgreSQL Connection Refused

```bash
# Error:
psycopg2.OperationalError: could not connect to server

# Lösung:
docker compose ps  # Prüfe ob cdb_postgres healthy ist
docker compose logs cdb_postgres --tail=50  # Check Logs
```

### Problem: Tests skippen (DB leer)

```bash
# Output:
SKIPPED [1] tests/local/test_cli_tools.py: DB has no signals yet

# Lösung:
# Das ist OK - Test skippt gracefully wenn DB leer ist
# Um Test wirklich zu testen: Daten generieren
pytest -v -m e2e  # E2E-Tests generieren Daten
```

---

## 📚 Weiterführende Dokumentation

- **Gap Analysis**: `backoffice/docs/testing/LOCAL_TEST_GAP_ANALYSIS.md`
- **Implementation Report**: `backoffice/docs/testing/LOCAL_TEST_IMPLEMENTATION_REPORT.md`
- **Basis-Doku**: `backoffice/docs/testing/LOCAL_E2E_TESTS.md`

---

**Status**: ✅ Implementiert (2025-11-23)
**Nächster Schritt**: User führt Tests lokal aus und validiert Ergebnisse.
