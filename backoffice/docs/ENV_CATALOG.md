# ENV-Katalog – Claire de Binaire

**Projekt:** Claire de Binaire
**Erstellt:** 2025-11-21
**Version:** 1.0
**Status:** ✅ Kanonische Referenz

---

## 📋 Übersicht

Dieser Katalog enthält **alle Environment-Variablen** des Claire-de-Binaire-Systems, kategorisiert nach Funktion und Service-Zugehörigkeit.

**Quellen:**
- `.env.example` (primäre Referenz)
- `backoffice/docs/knowledge/output.md` (Risk-Architektur)
- `backoffice/docs/architecture/N1_ARCHITEKTUR.md` (System-Architektur)
- `backoffice/docs/infra/env_index.md` (Infra-Inventur)

**Anzahl Variablen:** 46 (26 aktiv, 20 deprecated/optional)

---

## 🔑 Kategorien

| Kategorie | Anzahl | Beschreibung |
|-----------|--------|--------------|
| **Risk** | 9 | Risk-Engine-Parameter und Limits |
| **DB** | 6 | PostgreSQL-Konfiguration |
| **Redis** | 4 | Message-Bus-Konfiguration |
| **Monitoring** | 5 | Grafana/Prometheus-Konfiguration |
| **Services** | 5 | Service-Ports und URLs |
| **Trading** | 4 | Trading-Modus und API-Keys |
| **System** | 5 | Logging, Runtime, Python-Umgebung |
| **Deprecated** | 8 | Alte Naming-Konvention (vor ADR-035) |

---

## 📊 Risk Engine

| Variable | Kategorie | Default | Min | Max | Format | Pflicht | Beschreibung | Betroffene Services |
|----------|-----------|---------|-----|-----|--------|---------|--------------|---------------------|
| `MAX_POSITION_PCT` | Risk | `0.10` | `0.01` | `0.25` | Dezimal | ✅ | Maximale Positionsgröße (10% des Kapitals) | cdb_risk |
| `MAX_DAILY_DRAWDOWN_PCT` | Risk | `0.05` | `0.01` | `0.20` | Dezimal | ✅ | Maximaler Tagesverlust (5%) - Trading-Stopp bei Überschreitung | cdb_risk |
| `MAX_TOTAL_EXPOSURE_PCT` | Risk | `0.30` | `0.10` | `1.00` | Dezimal | ✅ | Maximales Gesamt-Exposure (30% des Kapitals) | cdb_risk |
| `CIRCUIT_BREAKER_THRESHOLD_PCT` | Risk | `0.10` | `0.05` | `0.30` | Dezimal | ✅ | Emergency Stop bei Gesamt-Verlust (10%) | cdb_risk |
| `MAX_SLIPPAGE_PCT` | Risk | `0.02` | `0.001` | `0.05` | Dezimal | ✅ | Maximale Slippage-Toleranz (2%) | cdb_risk, cdb_execution |
| `STOP_LOSS_PCT` | Risk | `0.02` | `0.005` | `0.10` | Dezimal | ✅ | Stop-Loss pro Trade (2%) | cdb_risk, cdb_execution |
| `MAX_SPREAD_MULTIPLIER` | Risk | `5.0` | `2.0` | `10.0` | Float | ✅ | Spread-Multiplikator (5x normal = Anomalie) | cdb_risk |
| `DATA_STALE_TIMEOUT_SEC` | Risk | `60` | `10` | `120` | Integer | ✅ | Timeout für Marktdaten (60s) - Trading pausiert bei Überschreitung | cdb_ws, cdb_risk |
| `ACCOUNT_EQUITY` | Risk | `100000.0` | `1000.0` | `∞` | Float | ✅ | Startkapital (USD) für Paper-Trading | cdb_risk, cdb_execution |

**Wichtig:**
- **Dezimal-Konvention (ADR-035):** Prozentangaben als Dezimalwerte (`0.10` = 10%, **nicht** `10.0`)
- **Suffix `_PCT`:** Kennzeichnet Prozent-Variablen
- **Layer-Priorisierung:** Daily Drawdown (Layer 1) → Spread/Slippage (Layer 2) → Data Staleness (Layer 3) → Exposure (Layer 4) → Position Size (Layer 5) → Stop-Loss (Layer 6)

---

## 🗄️ PostgreSQL (Database)

| Variable | Kategorie | Default | Format | Pflicht | Beschreibung | Betroffene Services |
|----------|-----------|---------|--------|---------|--------------|---------------------|
| `POSTGRES_HOST` | DB | `cdb_postgres` | String | ✅ | PostgreSQL-Hostname (Docker-Container-Name) | Alle Services |
| `POSTGRES_PORT` | DB | `5432` | Integer | ✅ | PostgreSQL-Port | Alle Services |
| `POSTGRES_USER` | DB | `claire_user` | String | ✅ | PostgreSQL-Benutzername (kanonisch ohne `database_`-Präfix) | Alle Services |
| `POSTGRES_PASSWORD` | DB | `<secret>` | String | ✅ | PostgreSQL-Passwort (**niemals committen!**) | Alle Services |
| `POSTGRES_DB` | DB | `claire_de_binaire` | String | ✅ | Datenbank-Name (kanonisch, unveränderlich) | Alle Services |
| `DATABASE_URL` | DB | `postgresql://claire_user:<password>@cdb_postgres:5432/claire_de_binaire` | String | ❌ | Connection-String (optional, wird aus Einzelvariablen konstruiert) | Alle Services |

**Sicherheit:**
- `POSTGRES_PASSWORD` **NIEMALS** in `.env.example` committen
- `.env` ist in `.gitignore` und **MUSS** lokal bleiben
- Für Production: Secrets über Kubernetes Secrets oder HashiCorp Vault

**Kanonische Regel:**
- DB-Name **MUSS** exakt `claire_de_binaire` sein (ohne Präfixe/Suffixe)
- User-Name **SOLLTE** `claire_user` sein (kanonische Konvention)

---

## 🔴 Redis (Message Bus)

| Variable | Kategorie | Default | Format | Pflicht | Beschreibung | Betroffene Services |
|----------|-----------|---------|--------|---------|--------------|---------------------|
| `REDIS_HOST` | Redis | `cdb_redis` | String | ✅ | Redis-Hostname (Docker-Container-Name, **nicht** `redis`!) | Alle Services |
| `REDIS_PORT` | Redis | `6379` | Integer | ✅ | Redis-Port | Alle Services |
| `REDIS_PASSWORD` | Redis | `<secret>` | String | ✅ | Redis-Passwort (**requirepass**-Flag in docker-compose) | Alle Services |
| `REDIS_DB` | Redis | `0` | Integer | ❌ | Redis-Datenbank-Index (Default: 0) | Optional |

**Kritisch:**
- `REDIS_HOST` **MUSS** `cdb_redis` sein (nicht `redis` oder `localhost`)
- Redis-Auth ist **Pflicht** (`--requirepass` in docker-compose.yml)
- Fehlende/falsche `REDIS_HOST` führt zu Service-Crashes (Connection Refused)

**Event-Topics (über Redis Pub/Sub):**
- `market_data` (cdb_ws → cdb_core)
- `signals` (cdb_core → cdb_risk)
- `orders` (cdb_risk → cdb_execution)
- `order_results` (cdb_execution → cdb_postgres, Grafana)
- `alerts` (cdb_risk → Grafana, Logging)

---

## 📊 Monitoring (Grafana/Prometheus)

| Variable | Kategorie | Default | Format | Pflicht | Beschreibung | Betroffene Services |
|----------|-----------|---------|--------|---------|--------------|---------------------|
| `GRAFANA_PASSWORD` | Monitoring | `admin` | String | ✅ | Grafana-Admin-Passwort (⚠️ **ändern vor Production!**) | cdb_grafana |
| `GF_SECURITY_ADMIN_USER` | Monitoring | `admin` | String | ❌ | Grafana-Admin-Username (Alternative zu `GRAFANA_PASSWORD`) | cdb_grafana |
| `GF_SECURITY_ADMIN_PASSWORD` | Monitoring | `admin` | String | ❌ | Grafana-Admin-Passwort (Alternative zu `GRAFANA_PASSWORD`) | cdb_grafana |
| `GF_USERS_ALLOW_SIGN_UP` | Monitoring | `false` | Boolean | ❌ | Grafana-User-Registrierung deaktiviert | cdb_grafana |
| `PROM_PORT` | Monitoring | `19090` | Integer | ❌ | Prometheus Host-Port (gemappt auf Container-Port 9090) | cdb_prometheus |

**Hinweis:**
- `GRAFANA_PASSWORD` ist ein Alias für `GF_SECURITY_ADMIN_PASSWORD` (wird von docker-compose.yml als ENV-Variable gesetzt)
- Production: Starke Passwörter verwenden + HTTPS + Auth-Provider (OAuth/LDAP)

---

## 🚀 Services (Ports & URLs)

| Variable | Kategorie | Default | Format | Pflicht | Beschreibung | Betroffene Services |
|----------|-----------|---------|--------|---------|--------------|---------------------|
| `WS_PORT` | Services | `8000` | Integer | ✅ | WebSocket-Screener Port | cdb_ws |
| `SIGNAL_PORT` | Services | `8001` | Integer | ✅ | Signal Engine Port | cdb_core |
| `RISK_PORT` | Services | `8002` | Integer | ✅ | Risk Manager Port | cdb_risk |
| `EXEC_PORT` | Services | `8003` | Integer | ✅ | Execution Service Port | cdb_execution |
| `GRAFANA_PORT` | Services | `3000` | Integer | ✅ | Grafana Dashboard Port | cdb_grafana |

**Hinweis:**
- Ports sind in docker-compose.yml hardcoded (`8000:8000`, etc.)
- ENV-Variablen werden innerhalb der Container genutzt (Flask/FastAPI App-Config)

---

## 💱 Trading (API-Keys & Modus)

| Variable | Kategorie | Default | Format | Pflicht | Beschreibung | Betroffene Services |
|----------|-----------|---------|--------|---------|--------------|---------------------|
| `TRADING_MODE` | Trading | `paper` | String | ✅ | Trading-Modus: `paper` (Simulation) oder `live` (MEXC Testnet/Mainnet) | cdb_execution |
| `MEXC_API_KEY` | Trading | `<required>` | String | ⚠️ | MEXC-API-Key (**NUR für Live-Trading**, in `.env.example` auskommentiert) | cdb_execution |
| `MEXC_API_SECRET` | Trading | `<required>` | String | ⚠️ | MEXC-API-Secret (**NUR für Live-Trading**, in `.env.example` auskommentiert) | cdb_execution |
| `INITIAL_CAPITAL` | Trading | `100000.0` | Float | ✅ | Startkapital (USD) für Paper-Trading (Alias für `ACCOUNT_EQUITY`) | cdb_execution, cdb_risk |

**Paper-Trading (N1-Phase):**
- `TRADING_MODE=paper` → Keine API-Keys erforderlich
- `MEXC_API_KEY/SECRET` bleiben auskommentiert

**Live-Trading (zukünftig):**
- `TRADING_MODE=live` → API-Keys **Pflicht**
- Keys niemals in `.env.example` committen
- Secrets über externe Secret-Manager (Kubernetes Secrets, Vault)

---

## 🖥️ System (Logging & Runtime)

| Variable | Kategorie | Default | Format | Pflicht | Beschreibung | Betroffene Services |
|----------|-----------|---------|--------|---------|--------------|---------------------|
| `LOG_LEVEL` | System | `INFO` | String | ✅ | Logging-Level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Alle Services |
| `USE_SYSTEM_PYTHON` | System | `true` | Boolean | ❌ | Verwendet global installiertes Python (nicht lokal im Projektordner) | Python-Runtime |
| `PYTHON_HOME` | System | `/usr/bin/python3` | String | ❌ | Python-Installation-Pfad (für System-Python) | Python-Runtime |
| `SYSTEM_PYTHON_PATH` | System | `/usr/lib/python3.x` | String | ❌ | Python-Library-Pfad (für System-Python) | Python-Runtime |
| `RETENTION_DAYS` | System | `14` | Integer | ❌ | Log-/Daten-Retention (14 Tage) | cdb_postgres, Loki |

**Logging-Konvention:**
- **Structured Logging** (JSON-Format bevorzugt)
- **NIEMALS** `print()` verwenden → Nur `logger.info()`, `logger.error()`, etc.
- Level-Empfehlungen:
  - `DEBUG`: Entwicklung, lokale Tests
  - `INFO`: Production-Default
  - `WARNING`: Deployment-Probleme
  - `ERROR`: Service-Crashes

---

## ⚠️ Deprecated (Alte Konvention vor ADR-035)

Diese Variablen wurden durch die **Dezimal-Konvention (ADR-035)** abgelöst und sollten **NICHT** mehr verwendet werden:

| Variable (ALT) | Variable (NEU) | Grund | Status |
|----------------|----------------|-------|--------|
| `MAX_DAILY_DRAWDOWN=5.0` | `MAX_DAILY_DRAWDOWN_PCT=0.05` | Prozent vs. Dezimal | ❌ Deprecated |
| `MAX_POSITION_SIZE=10.0` | `MAX_POSITION_PCT=0.10` | Prozent vs. Dezimal | ❌ Deprecated |
| `MAX_TOTAL_EXPOSURE=50.0` | `MAX_TOTAL_EXPOSURE_PCT=0.30` | Prozent vs. Dezimal (Wert geändert!) | ❌ Deprecated |
| `SIGNAL_THRESHOLD=3.0` | *(keine Alternative)* | Service-spezifisch, nicht dokumentiert | ⚠️ Unclear |
| `MIN_VOLUME=100000` | *(keine Alternative)* | Service-spezifisch, nicht dokumentiert | ⚠️ Unclear |

**Kritisch:**
- `MAX_TOTAL_EXPOSURE=50.0` (alt) vs. `MAX_TOTAL_EXPOSURE_PCT=0.30` (neu) → **Wert-Änderung von 50% auf 30%!**
- Code **MUSS** auf neue Variablen migriert werden (Breaking Change)

**Migrations-Hinweis:**
Siehe **ADR-035** in `backoffice/docs/DECISION_LOG.md` für Details zur ENV-Naming-Konvention-Änderung.

---

## 📋 Vollständige Tabelle (alphabetisch)

| Variable | Kategorie | Default | Pflicht | Range | Format | Beschreibung | Betroffene Services |
|----------|-----------|---------|---------|-------|--------|--------------|---------------------|
| `ACCOUNT_EQUITY` | Risk | `100000.0` | ✅ | `1000.0` - `∞` | Float | Startkapital (USD) für Paper-Trading | cdb_risk, cdb_execution |
| `CIRCUIT_BREAKER_THRESHOLD_PCT` | Risk | `0.10` | ✅ | `0.05` - `0.30` | Dezimal | Emergency Stop bei Gesamt-Verlust (10%) | cdb_risk |
| `DATABASE_URL` | DB | `postgresql://...` | ❌ | - | String | PostgreSQL Connection-String (optional) | Alle Services |
| `DATA_STALE_TIMEOUT_SEC` | Risk | `60` | ✅ | `10` - `120` | Integer | Timeout für Marktdaten (60s) | cdb_ws, cdb_risk |
| `EXEC_PORT` | Services | `8003` | ✅ | - | Integer | Execution Service Port | cdb_execution |
| `GF_SECURITY_ADMIN_PASSWORD` | Monitoring | `admin` | ❌ | - | String | Grafana-Admin-Passwort | cdb_grafana |
| `GF_SECURITY_ADMIN_USER` | Monitoring | `admin` | ❌ | - | String | Grafana-Admin-Username | cdb_grafana |
| `GF_USERS_ALLOW_SIGN_UP` | Monitoring | `false` | ❌ | - | Boolean | Grafana-User-Registrierung | cdb_grafana |
| `GRAFANA_PASSWORD` | Monitoring | `admin` | ✅ | - | String | Grafana-Admin-Passwort | cdb_grafana |
| `GRAFANA_PORT` | Services | `3000` | ✅ | - | Integer | Grafana Dashboard Port | cdb_grafana |
| `INITIAL_CAPITAL` | Trading | `100000.0` | ✅ | `1000.0` - `∞` | Float | Startkapital (Alias für `ACCOUNT_EQUITY`) | cdb_execution, cdb_risk |
| `LOG_LEVEL` | System | `INFO` | ✅ | - | String | Logging-Level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | Alle Services |
| `MAX_DAILY_DRAWDOWN_PCT` | Risk | `0.05` | ✅ | `0.01` - `0.20` | Dezimal | Maximaler Tagesverlust (5%) | cdb_risk |
| `MAX_POSITION_PCT` | Risk | `0.10` | ✅ | `0.01` - `0.25` | Dezimal | Maximale Positionsgröße (10%) | cdb_risk |
| `MAX_SLIPPAGE_PCT` | Risk | `0.02` | ✅ | `0.001` - `0.05` | Dezimal | Maximale Slippage-Toleranz (2%) | cdb_risk, cdb_execution |
| `MAX_SPREAD_MULTIPLIER` | Risk | `5.0` | ✅ | `2.0` - `10.0` | Float | Spread-Multiplikator (5x = Anomalie) | cdb_risk |
| `MAX_TOTAL_EXPOSURE_PCT` | Risk | `0.30` | ✅ | `0.10` - `1.00` | Dezimal | Maximales Gesamt-Exposure (30%) | cdb_risk |
| `MEXC_API_KEY` | Trading | `<required>` | ⚠️ | - | String | MEXC-API-Key (nur für Live-Trading) | cdb_execution |
| `MEXC_API_SECRET` | Trading | `<required>` | ⚠️ | - | String | MEXC-API-Secret (nur für Live-Trading) | cdb_execution |
| `POSTGRES_DB` | DB | `claire_de_binaire` | ✅ | - | String | PostgreSQL Datenbank-Name (kanonisch) | Alle Services |
| `POSTGRES_HOST` | DB | `cdb_postgres` | ✅ | - | String | PostgreSQL-Hostname | Alle Services |
| `POSTGRES_PASSWORD` | DB | `<secret>` | ✅ | - | String | PostgreSQL-Passwort (**niemals committen!**) | Alle Services |
| `POSTGRES_PORT` | DB | `5432` | ✅ | - | Integer | PostgreSQL-Port | Alle Services |
| `POSTGRES_USER` | DB | `claire_user` | ✅ | - | String | PostgreSQL-Benutzername | Alle Services |
| `PROM_PORT` | Monitoring | `19090` | ❌ | - | Integer | Prometheus Host-Port | cdb_prometheus |
| `PYTHON_HOME` | System | `/usr/bin/python3` | ❌ | - | String | Python-Installation-Pfad | Python-Runtime |
| `REDIS_DB` | Redis | `0` | ❌ | `0` - `15` | Integer | Redis-Datenbank-Index | Optional |
| `REDIS_HOST` | Redis | `cdb_redis` | ✅ | - | String | Redis-Hostname (**nicht** `redis`!) | Alle Services |
| `REDIS_PASSWORD` | Redis | `<secret>` | ✅ | - | String | Redis-Passwort | Alle Services |
| `REDIS_PORT` | Redis | `6379` | ✅ | - | Integer | Redis-Port | Alle Services |
| `RETENTION_DAYS` | System | `14` | ❌ | - | Integer | Log-/Daten-Retention (Tage) | cdb_postgres, Loki |
| `RISK_PORT` | Services | `8002` | ✅ | - | Integer | Risk Manager Port | cdb_risk |
| `SIGNAL_PORT` | Services | `8001` | ✅ | - | Integer | Signal Engine Port | cdb_core |
| `STOP_LOSS_PCT` | Risk | `0.02` | ✅ | `0.005` - `0.10` | Dezimal | Stop-Loss pro Trade (2%) | cdb_risk, cdb_execution |
| `SYSTEM_PYTHON_PATH` | System | `/usr/lib/python3.x` | ❌ | - | String | Python-Library-Pfad | Python-Runtime |
| `TRADING_MODE` | Trading | `paper` | ✅ | - | String | Trading-Modus: `paper` oder `live` | cdb_execution |
| `USE_SYSTEM_PYTHON` | System | `true` | ❌ | - | Boolean | Verwendet global installiertes Python | Python-Runtime |
| `WS_PORT` | Services | `8000` | ✅ | - | Integer | WebSocket-Screener Port | cdb_ws |

---

## 🔍 Kritische Findings & Konflikte

### 1. Naming-Konflikt (behoben durch ADR-035)

**Problem (vor ADR-035):**
- `MAX_DAILY_DRAWDOWN=5.0` wurde als **500%** interpretiert → Risk-Limits unwirksam
- Alte Konvention: Prozent als Integer (`5.0`, `10.0`, `50.0`)
- Neue Konvention: Prozent als Dezimal (`0.05`, `0.10`, `0.30`)

**Lösung (ADR-035):**
- Suffix `_PCT` für Prozent-Variablen
- Dezimal-Format (0.05 = 5%)
- Alle Risk-Parameter migriert

### 2. Exposure-Wert-Änderung

**Problem:**
- `MAX_TOTAL_EXPOSURE=50.0` (alt, 50%) vs. `MAX_TOTAL_EXPOSURE_PCT=0.30` (neu, 30%)
- **Wert wurde von 50% auf 30% geändert!**

**Impact:**
- Conservative Risk-Policy in N1-Phase
- Kann später angepasst werden (Config-Change, kein Code-Change)

### 3. Fehlende Variablen (in `.env.example` ergänzt)

**Vorher fehlend:**
- `STOP_LOSS_PCT`
- `MAX_SPREAD_MULTIPLIER`
- `DATA_STALE_TIMEOUT_SEC`

**Status:** ✅ In `.env.example` ergänzt (2025-11-19)

### 4. Redis-Host-Name (kritisch!)

**Problem:**
- Services crashten initial mit `REDIS_HOST=redis` (Default)
- Container-Name ist `cdb_redis` (nicht `redis`)

**Lösung:**
- `.env.example` korrigiert: `REDIS_HOST=cdb_redis`
- **Pflicht:** ENV-Variable **MUSS** gesetzt sein (sonst Connection Refused)

---

## ✅ Best Practices

### Secrets-Management

**DO:**
- ✅ `.env` in `.gitignore` (niemals committen)
- ✅ `.env.example` mit Platzhaltern (`<secret>`, `<required>`)
- ✅ Production: Kubernetes Secrets / HashiCorp Vault
- ✅ Rotation: `.env` aktualisieren + `docker compose restart`

**DON'T:**
- ❌ Echte Passwörter in `.env.example` committen
- ❌ API-Keys im Code hardcoden
- ❌ Secrets in Git-History (auch nach Löschen sichtbar!)

### ENV-Validierung

**Service-Start:**
```python
import os
import sys

# Pflicht-Variablen prüfen
REQUIRED_VARS = [
    "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD",
    "POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "MAX_POSITION_PCT", "MAX_DAILY_DRAWDOWN_PCT"
]

missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
if missing:
    print(f"ERROR: Missing ENV variables: {missing}")
    sys.exit(1)
```

**Range-Checks:**
```python
def validate_risk_params():
    max_pos = float(os.getenv("MAX_POSITION_PCT", "0.10"))
    if not (0.01 <= max_pos <= 0.25):
        logger.warning(f"MAX_POSITION_PCT out of range: {max_pos}, using default 0.10")
        max_pos = 0.10
    return max_pos
```

---

## 📚 Referenzen

### Architektur-Dokumente
- **ADR-035:** ENV-Naming-Konvention (Dezimal-Format) → `backoffice/docs/DECISION_LOG.md`
- **ADR-036:** Secrets-Management-Policy → `backoffice/docs/DECISION_LOG.md`
- **N1-Architektur:** System-Übersicht → `backoffice/docs/architecture/N1_ARCHITEKTUR.md`
- **Risk-Engine-Logik:** Risk-Parameter-Details → `backoffice/docs/knowledge/output.md`

### Konfigurationsdateien
- **`.env.example`** – ENV-Template (committed)
- **`.env`** – Lokale Konfiguration (gitignored, **NIEMALS** committen)
- **`docker-compose.yml`** – Container-Definitionen mit ENV-Mappings
- **`pytest.ini`** – Test-Konfiguration (nutzt Mocks statt echte ENV)

### Service-Code
- **`services/cdb_risk/service.py`** – Risk-Engine (nutzt ENV-Parameter)
- **`services/cdb_core/service.py`** – Signal-Engine
- **`services/cdb_execution/service.py`** – Execution-Service (nutzt `TRADING_MODE`)

---

## 🎯 Nächste Schritte

### Sofort
1. **Validierung:** Alle Services starten mit `.env.example` als Basis
2. **Tests:** ENV-Parameter in Unit-Tests prüfen (Mocks für Secrets)
3. **Dokumentation:** Diesen Katalog bei ENV-Änderungen aktualisieren

### Mittelfristig
4. **Secrets-Rotation:** Policy für regelmäßige Secret-Rotation definieren
5. **Production-Config:** Kubernetes Secrets oder Vault-Integration
6. **Monitoring:** ENV-Parameter-Änderungen in Audit-Log tracken

---

**Erstellt von:** Claude Code (claire-architect)
**Letzte Änderung:** 2025-11-21
**Version:** 1.0
**Status:** ✅ Kanonische Referenz
