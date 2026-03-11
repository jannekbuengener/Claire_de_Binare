# Agent: repo_cartographer
# Scan Date: 2025-12-28
# Scope: Code/Services im Working Repo

---

## Facts (verifiziert)

### Core Module (`core/`)
| Modul | Dateien | Zweck |
|-------|---------|-------|
| `core/clients/mexc.py` | 1 | MEXC Exchange API Client |
| `core/indicators/` | 5 | Technische Indikatoren (base, trend, momentum, volatility, composite) |
| `core/safety/kill_switch.py` | 1 | Emergency Stop Mechanismus |
| `core/utils/` | 6 | clock, rate_limiter, redis_client, postgres_client, uuid_gen, seed |
| `core/domain/` | 3 | event.py, models.py, secrets.py |
| `core/config/` | 2 | trading_mode.py, feature_flags.py |
| `core/auth.py` | 1 | Authentication |
| `core/secrets.py` | 1 | Secret Management |

### Services (`services/`)
| Service | Dateien | Hauptdatei | LOC (geschaetzt) |
|---------|---------|------------|------------------|
| signal | 6 | service.py | ~300 |
| risk | 11 | service.py | ~500 |
| execution | 11 | service.py | ~400 |
| db_writer | 2 | db_writer.py | ~550 |
| ws | 1 | service.py | ~200 |
| allocation | 3 | service.py | 378 |
| regime | 4 | service.py | 213 |
| market | 2 | service.py | 82 |

### Tools (`tools/`)
| Tool | Dateien | Zweck |
|------|---------|-------|
| paper_trading | 3 | Automated Paper Trading Runner (service.py, email_alerter.py, Dockerfile) |
| replay | 2 | Event Replay Tool |
| research | 1 | portfolio_manager.py |
| Utilities | 3 | link_check.py, provenance_hash.py, validate_mcp_config.py |

### Dockerfiles (9 total)
- services/signal/Dockerfile
- services/risk/Dockerfile
- services/execution/Dockerfile
- services/db_writer/Dockerfile
- services/ws/Dockerfile
- services/allocation/Dockerfile
- services/regime/Dockerfile
- services/market/Dockerfile
- tools/paper_trading/Dockerfile

---

## Assumptions (zu validieren)

1. **Signal Service Pattern**: Alle Services folgen dem Pattern `config.py`, `models.py`, `service.py`
   - Ausnahme: db_writer nutzt `db_writer.py` statt `service.py`

2. **LOC Estimates**: Basierend auf Dateianzahl und Glob-Ergebnissen, nicht exakt verifiziert

3. **Feature Flags**: `core/config/feature_flags.py` existiert, aber Nutzung unklar

---

## Gaps (identifiziert)

1. **PSM Service**: In CLAUDE.md erwaehnt (Port 8001), aber kein Verzeichnis unter `services/psm/`
   - **Klarstellung**: PSM Logik ist Teil des Paper Trading Runners, nicht separater Service

2. **Market Service**: Code existiert (`services/market/`), aber Status unklar
   - Compose sagt "not implemented"
   - Code-Dateien: service.py, email_alerter.py vorhanden

3. **Kein dedizierter Signal Service Port**: CLAUDE.md sagt Port 8001, dev.yml sagt Port 8005
   - **RESOLVED**: Signal Service laeuft auf Port 8005 (gemaess dev.yml)

---

## Source Pointers

- `D:\Dev\Workspaces\Repos\Claire_de_Binare\core\`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\services\`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\tools\`
