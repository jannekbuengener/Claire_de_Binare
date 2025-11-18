# ENV-Index - Environment-Variablen

**Erstellt von**: software-jochen
**Datum**: 2025-11-16
**Scope**: ENV-Namen aus ` - Kopie.env`, docker-compose.yml, Service-Configs
**⚠️ WICHTIG**: Dieses Dokument enthält NUR ENV-Namen und Bedeutungen, NIEMALS reale Werte/Secrets!

## Kategorien

- **Secret**: Passwörter, API-Keys, Tokens (darf NIEMALS committed werden)
- **Config**: Konfigurationswerte (Ports, Limits, Schwellwerte)
- **Feature-Flag**: Boolean-Flags für Features
- **Infra**: Infrastruktur-Verbindungsparameter (Hosts, Ports, DB-Namen)

## DATABASE (PostgreSQL)

| Name | Kategorie | Bedeutung | Scope | Fundstelle |
|------|-----------|-----------|-------|------------|
| `POSTGRES_DB` | Infra | Datenbank-Name (Default: `claire_de_binare`) | Global | ` - Kopie.env`, docker-compose.yml |
| `POSTGRES_USER` | Infra | PostgreSQL-Benutzername | Global | ` - Kopie.env`, docker-compose.yml |
| `POSTGRES_PASSWORD` | Secret | PostgreSQL-Passwort | Global | ` - Kopie.env`, docker-compose.yml |
| `DATABASE_URL` | Infra | Vollständige PostgreSQL-Connection-String | Global | ` - Kopie.env` |

**Hinweis**: `POSTGRES_DB` laut Kommentar in ` - Kopie.env` kanonisch **ohne** `database_`-Präfix.

## MESSAGE BUS (Redis)

| Name | Kategorie | Bedeutung | Scope | Fundstelle |
|------|-----------|-----------|-------|------------|
| `REDIS_HOST` | Infra | Redis-Hostname (Default: `cdb_redis`) | Global | ` - Kopie.env`, docker-compose.yml |
| `REDIS_PORT` | Infra | Redis-Port (Default: `6379`) | Global | ` - Kopie.env`, docker-compose.yml |
| `REDIS_PASSWORD` | Secret | Redis-Passwort (⚠️ **requirepass** in docker-compose.yml) | Global | ` - Kopie.env`, docker-compose.yml |
| `REDIS_DB` | Infra | Redis-Datenbank-Index (Default: `0`) | Signal-Gen | docker-compose.yml (cdb_signal_gen) |

**Sicherheit**: docker-compose.yml nutzt `--requirepass` Flag → Redis-Auth ist **Pflicht**!

## SERVICE PORTS

| Name | Kategorie | Bedeutung | Scope | Fundstelle |
|------|-----------|-----------|-------|------------|
| `WS_PORT` | Config | WebSocket-Screener Port (Default: `8000`) | cdb_ws | ` - Kopie.env` |
| `SIGNAL_PORT` | Config | Signal Engine Port (Default: `8001`) | cdb_core | ` - Kopie.env` |
| `RISK_PORT` | Config | Risk Manager Port (Default: `8002`) | cdb_risk | ` - Kopie.env` |
| `EXEC_PORT` | Config | Execution Service Port (Default: `8003`) | cdb_execution | ` - Kopie.env` |

**Hinweis**: Ports in docker-compose.yml sind hardcoded (`8000:8000`, `8001:8001`, etc.). ENV-Variablen werden möglicherweise nur innerhalb der Container genutzt.

## RISK MANAGEMENT

| Name | Kategorie | Bedeutung | Scope | Fundstelle |
|------|-----------|-----------|-------|------------|
| `MAX_DAILY_DRAWDOWN` | Config | Maximaler Tagesverlust (Default: `5.0`%) | Risk Manager | ` - Kopie.env` |
| `MAX_POSITION_SIZE` | Config | Maximale Positionsgröße (Default: `10.0`%) | Risk Manager | ` - Kopie.env` |
| `MAX_TOTAL_EXPOSURE` | Config | Maximales Gesamt-Exposure (Default: `50.0`%) | Risk Manager | ` - Kopie.env` |
| `INITIAL_CAPITAL` | Config | Startkapital (Default: `1000`) | Risk Manager | ` - Kopie.env` |

**Vergleich mit output.md**: In `sandbox/output.md` sind Risk-Parameter mit anderem Naming dokumentiert:
- `MAX_POSITION_PCT` (Dezimal: `0.10`) vs. `MAX_POSITION_SIZE` (Prozent: `10.0`)
- `MAX_EXPOSURE_PCT` (Dezimal: `0.50`) vs. `MAX_TOTAL_EXPOSURE` (Prozent: `50.0`)
- `MAX_DAILY_DRAWDOWN_PCT` (Dezimal: `0.05`) vs. `MAX_DAILY_DRAWDOWN` (Prozent: `5.0`)

**⚠️ KONFLIKT ERKANNT**: Namenskonvention und Format-Unterschied (Dezimal vs. Prozent)!

## SIGNAL ENGINE

| Name | Kategorie | Bedeutung | Scope | Fundstelle |
|------|-----------|-----------|-------|------------|
| `SIGNAL_THRESHOLD` | Config | Momentum-Signal-Schwellwert (Default: `3.0`%) | Signal Engine | ` - Kopie.env` |
| `MIN_VOLUME` | Config | Minimales Handelsvolumen (Default: `100000`) | Signal Engine | ` - Kopie.env` |

## MONITORING (Prometheus/Grafana)

| Name | Kategorie | Bedeutung | Scope | Fundstelle |
|------|-----------|-----------|-------|------------|
| `GF_SECURITY_ADMIN_USER` | Infra | Grafana-Admin-Username (Default: `admin`) | Grafana | docker-compose.yml |
| `GF_SECURITY_ADMIN_PASSWORD` | Secret | Grafana-Admin-Passwort | Grafana | docker-compose.yml |
| `GF_USERS_ALLOW_SIGN_UP` | Feature-Flag | Grafana-User-Registrierung (Default: `false`) | Grafana | docker-compose.yml |
| `GRAFANA_PASSWORD` | Secret | Alias für `GF_SECURITY_ADMIN_PASSWORD`? | Grafana | ` - Kopie.env` referenziert |

**⚠️ UNKLAR**: Ist `GRAFANA_PASSWORD` identisch mit `GF_SECURITY_ADMIN_PASSWORD` oder separate Variable?

## Fehlende ENV-Variablen (aus output.md)

Folgende ENV-Variablen sind in `sandbox/output.md` dokumentiert, aber **nicht** in ` - Kopie.env` oder docker-compose.yml gefunden:

| Name | Dokumentiert in | Fehlt in |
|------|----------------|----------|
| `STOP_LOSS_PCT` | output.md | ` - Kopie.env` |
| `MAX_SLIPPAGE_PCT` | output.md | ` - Kopie.env` |
| `MAX_SPREAD_MULTIPLIER` | output.md | ` - Kopie.env` |
| `DATA_STALE_TIMEOUT_SEC` | output.md | ` - Kopie.env` |
| `MEXC_API_KEY`, `MEXC_API_SECRET` | output.md (als Pflicht markiert) | ` - Kopie.env` (nur Kommentar in Zeile 50+?) |

**⚠️ LÜCKE ERKANNT**: Risk-Parameter aus Architektur-Doku fehlen im ENV-Template!

## Zusammenfassung

### Nach Kategorie

| Kategorie | Anzahl | Beispiele |
|-----------|--------|-----------|
| Secret | 5 | `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `GRAFANA_PASSWORD`, `MEXC_API_KEY/SECRET` |
| Infra | 8 | `POSTGRES_DB`, `REDIS_HOST`, `DATABASE_URL`, Ports |
| Config | 7 | Risk-Parameter, Signal-Threshold, Volume |
| Feature-Flag | 1 | `GF_USERS_ALLOW_SIGN_UP` |
| **TOTAL** | **21** | |

### Nach Scope

| Scope | Anzahl |
|-------|--------|
| Global (alle Services) | 6 |
| Service-spezifisch | 15 |

### Kritische Findings

1. **Naming-Konflikt**: Risk-Parameter mit unterschiedlichen Namen in ` - Kopie.env` (`MAX_DAILY_DRAWDOWN`) vs. output.md (`MAX_DAILY_DRAWDOWN_PCT`)
2. **Format-Konflikt**: Prozent vs. Dezimal (`5.0` vs. `0.05`)
3. **Fehlende Variablen**: `STOP_LOSS_PCT`, `MAX_SLIPPAGE_PCT`, `MAX_SPREAD_MULTIPLIER`, `DATA_STALE_TIMEOUT_SEC` fehlen in ` - Kopie.env`
4. **Duplikat-Verdacht**: `GRAFANA_PASSWORD` vs. `GF_SECURITY_ADMIN_PASSWORD`
5. **Secrets in ENV**: ` - Kopie.env` enthält aktuell echte Werte (z.B. `POSTGRES_PASSWORD=Jannek8$`) → **MUSS bereinigt werden**!

## Empfehlungen (für agata-van-data & devops-infrastructure-architect)

1. **Vereinheitlichen**: ENV-Präfix `CDB_*` für alle projekt-spezifischen Variablen (siehe DevOps-Anmerkungen in audit_log.md)
2. **Komplettieren**: Fehlende Risk-Parameter in ` - Kopie.env` ergänzen
3. **Bereinigen**: Echte Secrets durch Platzhalter ersetzen (z.B. `<SET_IN_ENV>`, `<REQUIRED>`)
4. **Dokumentieren**: Namenskonvention (Suffix `_PCT` für Prozent-Dezimal, ohne Suffix für Prozent-Integer?)
