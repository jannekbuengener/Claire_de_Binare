# Quick Reference Guide – Claire de Binaire Agents
**Version**: 1.0 | **Datum**: 2025-01-11
**Zweck**: Schnellzugriff für häufige Agent-Anfragen

---

## 🚀 Häufigste Anfragen (Top 10)

| # | Frage | Antwort (Dokument + Zeilen) |
|---|-------|------------------------------|
| 1 | "Wie deploye ich das System neu?" | `cdb_redis.md` (Zeilen 1–200: Server-Setup, 201–250: Testing) + `README.md` (Quick Start) + `../ops/RUNBOOK_DOCKER_OPERATIONS.md` |
| 2 | "Welche Port-Mappings gelten?" | Siehe Tabelle unten + `cdb_ws.md`, `cdb_signal.md` |
| 3 | "Wie funktioniert die Signal Engine?" | `cdb_signal.md` (vollständig) + `backoffice/docs/reports/SIGNAL_ENGINE_COMPLETE.md` |
| 4 | "Wie sichere ich Daten?" | `cdb_redis.md` (Zeilen 123–180: Backup-Strategie) + `BACKUP_ANLEITUNG.md` |
| 5 | "Wie integriere ich Monitoring?" | `cdb_prometheus.md` (vollständig) + `prometheus.yml` (Repo-Root) |
| 6 | "Wie migriere ich zu Kubernetes?" | `cdb_kubernetes.md` (595 Zeilen, vollständig) |
| 7 | "Was ist der WebSocket-Symbol-Limit?" | 200 Symbole/Connection (Auto-Chunking in `cdb_ws.md` Zeilen 50–80) |
| 8 | "Welche ENV-Variablen brauche ich?" | `cdb_redis.md` (Zeilen 15–45: Secrets-Management) + `.env.example` |
| 9 | "Kann ich ML integrieren?" | `cdb_advisor.md` (vollständig) – **NUR Research-Phase, NICHT produktionsreif** |
| 10 | "Wie troubleshoote ich Redis?" | `cdb_redis.md` (Zeilen 210–240: Troubleshooting-Sektion) |

---

## 📊 Port-Mapping-Tabelle

| Service | Port | Endpoints | Health-Check | Source |
|---------|------|-----------|--------------|--------|
| **WebSocket Screener** | 8000 | `/health`, `/top5` | GET `/health` → `{"status":"ok"}` | `cdb_ws.md` |
| **Signal Engine** | 8001 | `/health`, `/status`, `/metrics` | GET `/health` → `{"status":"running"}` | `cdb_signal.md` |
| **Risk Manager** | 8002 | `/health`, `/status`, `/metrics` | GET `/health` → `{"status":"ok"}` | Inferred |
| **Execution Service** | 8003 | `/health`, `/status`, `/metrics` | GET `/health` → `{"status":"ok"}` | Inferred |
| **PostgreSQL** | 5432 | – | `pg_isready` | `cdb_redis.md` |
| **Redis** | 6379 | – | `redis-cli PING` → `PONG` | `cdb_redis.md` |
| **Prometheus** | 9090 | `/targets`, `/graph` | GET `/targets` → Targets UP | `cdb_prometheus.md` |
| **Grafana** | 3000 | `/login`, `/dashboards` | GET `/api/health` → `{"status":"ok"}` | Inferred |

---

## 🔑 ENV-Variablen-Checkliste

### Pflicht-Variablen (MUST HAVE):
```bash
## MEXC API (ohne Withdraw-Rechte!)
MEXC_API_KEY=<key>
MEXC_API_SECRET=<secret>

## Redis
REDIS_HOST=redis           # Docker: cdb_redis, K8s: redis
REDIS_PORT=6379
REDIS_PASSWORD=<secret>

## PostgreSQL
POSTGRES_HOST=postgres     # Docker: cdb_postgres, K8s: postgres
POSTGRES_PORT=5432
POSTGRES_DB=claire_de_binare  # ACHTUNG: Ohne Accent!
POSTGRES_USER=cdb_user
POSTGRES_PASSWORD=<secret>

## WebPush (optional für Alerts)
WEBPUSH_VAPID_PUBLIC_KEY=<key>
WEBPUSH_VAPID_PRIVATE_KEY=<secret>
WEBPUSH_VAPID_SUBJECT=mailto:your@email.com
```

### Signal-Engine-Spezifisch:
```bash
SIGNAL_PORT=8001
SIGNAL_THRESHOLD_PCT=3.0       # 3% Preisänderung
SIGNAL_LOOKBACK_MIN=15         # 15-Minuten-Fenster
SIGNAL_MIN_VOLUME=100000       # Mindestvolumen
```

**Quelle**: `cdb_redis.md` (Zeilen 15–45) + `cdb_signal.md` (Zeilen 30–50)

---

## 🔍 Troubleshooting-Cheatsheet

### Problem: "Container restartet ständig"
1. **Check Logs**: `docker logs <container_id>`
2. **Häufige Ursachen**:
   - Redis nicht erreichbar → Prüfe `REDIS_HOST` ENV-Variable
   - Postgres-Connection fehlgeschlagen → Prüfe `POSTGRES_DB`-Namen (ohne Accent!)
   - Port-Kollision → `netstat -ano | findstr :<PORT>`
3. **Fix**: Siehe `cdb_redis.md` (Zeilen 210–240)

### Problem: "Keine Signale generiert"
1. **Check WebSocket**: `curl http://localhost:8000/health` → Sollte `{"status":"ok"}` sein
2. **Check Signal Engine**: `curl http://localhost:8001/status` → Prüfe `signals_generated`
3. **Check Redis**: `docker exec -it cdb_redis redis-cli PING` → Sollte `PONG` antworten
4. **Check Market Data Flow**:
   ```bash
   docker exec -it cdb_redis redis-cli
   > SUBSCRIBE market_data
   # Sollte Events sehen
   ```

### Problem: "Prometheus zeigt keine Metriken"
1. **Check Targets**: `http://localhost:9090/targets` → Alle UP?
2. **Check Service Endpoints**: `curl http://localhost:8001/metrics` → Sollte Prometheus-Format liefern
3. **Check Scrape Config**: `prometheus.yml` → `targets: ['signal_engine:8001']` korrekt?

**Quelle**: `cdb_prometheus.md` + `cdb_redis.md` (Troubleshooting-Sektion)

---

## 📚 Dokumentations-Hierarchie

### Tier 1: Operativ (täglich benötigt)
1. `README.md` – Quick Start & Ablauf ohne Vorkenntnisse
2. `../ops/RUNBOOK_DOCKER_OPERATIONS.md` – Compose-/Docker-Befehle
3. `backoffice/docs/research/QUICK_REFERENCE_AGENTS.md` – Dieses Dokument

### Tier 2: Technisch (Entwicklung/Debugging)
4. `backoffice/docs/research/cdb_redis.md` – Deployment-Guide
5. `backoffice/docs/research/cdb_signal.md` – Signal Engine Deep Dive
6. `backoffice/docs/research/cdb_ws.md` – WebSocket Screener Details
7. `backoffice/docs/research/cdb_prometheus.md` – Monitoring-Integration
8. `ARCHITEKTUR.md` – System-Design (High-Level)
9. `DEVELOPMENT.md` – Coding-Standards

### Tier 3: Strategisch (Planung/Roadmap)
10. `backoffice/docs/research/cdb_kubernetes.md` – K8s-Migration-Blueprint
11. `backoffice/docs/research/cdb_advisor.md` – ML-Integration-Research
12. `PROJECT_STATUS.md` – Aktuelle Phase
13. `DECISION_LOG.md` – ADRs (Architecture Decision Records)

### Tier 4: Research/Archiv
14. `backoffice/docs/research/KNOWLEDGE_BASE_INTEGRATION_2025-01-11.md` – Gap-Analyse
15. `backoffice/audits/` – Audit-Reports
16. `archive/` – Veraltete Dokumente

---

## 🔐 Security-Checkliste

### Vor jedem Deployment:
- [ ] MEXC API Keys OHNE Withdraw-Rechte
- [ ] `.env` nicht in Git committed (`.gitignore` prüfen)
- [ ] Redis-Passwort gesetzt (`requirepass` in Config)
- [ ] Container laufen als non-root (UID 1000)
- [ ] Keine Secrets in Logs (Prüfe `logging_config.json`)
- [ ] Backup-Skript funktioniert (`daily_backup.ps1` testen)

### Risk-Management-Limits (immer aktiv):
- ✅ **Tagesverlust-Limit**: ≥5% → Circuit-Breaker
- ✅ **Position Size**: Max. 10% per Trade
- ✅ **Max. Exposure**: 50% Gesamtkapital
- ✅ **Stop-Loss**: 2% per Trade

**Quelle**: `cdb_redis.md` (Security-Sektion) + `ARCHITEKTUR.md` (Risk Management)

---

## 🧪 Testing-Workflows

### Pre-Deployment-Tests (MUST):
1. **Container Health**:
   ```bash
   docker ps --filter "name=claire" --format "{{.Names}}: {{.Status}}"
   # Alle sollten "healthy" sein
   ```

2. **Redis Connectivity**:
   ```bash
   docker exec -it cdb_redis redis-cli PING
   # Erwartung: PONG
   ```

3. **Postgres Connectivity**:
   ```bash
   docker exec -it cdb_postgres psql -U cdb_user -d claire_de_binare -c "SELECT 1;"
   # Erwartung: 1 row
   ```

4. **Service Health Checks**:
   ```bash
   curl http://localhost:8000/health  # WebSocket
   curl http://localhost:8001/health  # Signal Engine
   curl http://localhost:8002/health  # Risk Manager (falls aktiv)
   ```

5. **Event Flow**:
   ```bash
   # In einem Terminal:
   docker exec -it cdb_redis redis-cli
   > SUBSCRIBE market_data

   # Sollte innerhalb 60s Events zeigen
   ```

**Quelle**: `cdb_redis.md` (Zeilen 201–230: Testing-Sektion)

### 7-Day Stability Test (optional, für Produktions-Rollout):
- Siehe `backoffice/docs/7D_PAPER_TRADING_TEST.md`
- Siehe `backoffice/docs/7D_TEST_DAILY_CHECKLIST.md`

---

## 📦 Backup & Recovery Quick-Commands

### Manuelles Backup (sofort):
```powershell
cd C:\Users\janne\Documents\claire_de_binare
.\daily_backup.ps1
```

### Scheduled Backup (täglich 3:00 Uhr):
```powershell
.\setup_backup_task.ps1
```

### Recovery (bei Datenverlust):
```bash
## 1. Stop Container
docker compose down

## 2. Restore Postgres
docker exec -i cdb_postgres psql -U cdb_user -d claire_de_binare < backup_YYYY-MM-DD/postgres_dump.sql

## 3. Restore Redis (optional, bei persistenten Daten)
docker cp backup_YYYY-MM-DD/redis_dump.rdb cdb_redis:/data/dump.rdb

## 4. Restart
docker compose up -d

## 5. Verify
curl http://localhost:8000/health
curl http://localhost:8001/health
```

**Quelle**: `cdb_redis.md` (Zeilen 123–180) + `BACKUP_ANLEITUNG.md`

---

## 🤖 ML-Integration-Status

**WICHTIG**: ML-Advisor ist **NICHT** produktionsreif!

| Aspekt | Status |
|--------|--------|
| Research-Phase | ✅ Abgeschlossen (`cdb_advisor.md`) |
| Prototyping | ❌ Nicht gestartet |
| Shadow Mode | ❌ Nicht implementiert |
| Go/No-Go-Decision | ⏳ Ausstehend |

### Wenn ML-Integration geplant:
1. **Lese `cdb_advisor.md` vollständig** (448 Zeilen)
2. **Prüfe Governance-Framework** (Section 4.4)
3. **Erstelle ADR-018** für Go/No-Go-Entscheidung
4. **Plane Shadow-Mode-Phase** (2–4 Wochen)

**Quelle**: `backoffice/docs/research/cdb_advisor.md`

---

## 🎯 Empfohlene Lesereihenfolge für neue Agenten

### Tag 1: System-Überblick
1. `README.md` (Repo-Root)
2. `backoffice/docs/QUICK_DASHBOARD_GUIDE.md`
3. `ARCHITEKTUR.md`
4. `PROJECT_STATUS.md`

### Tag 2: Deployment & Operations
5. `../ops/RUNBOOK_DOCKER_OPERATIONS.md`
6. `backoffice/docs/research/cdb_redis.md`
7. `BACKUP_ANLEITUNG.md`

### Tag 3: Service-Vertiefung
8. `backoffice/docs/research/cdb_ws.md`
9. `backoffice/docs/research/cdb_signal.md`
10. `DEVELOPMENT.md`

### Tag 4: Monitoring & Advanced Topics
11. `backoffice/docs/research/cdb_prometheus.md`
12. `backoffice/docs/research/cdb_kubernetes.md` (optional)
13. `backoffice/docs/research/cdb_advisor.md` (optional, Future-Roadmap)

---

## 📞 Eskalations-Pfade

| Problem | Erste Anlaufstelle | Dokument |
|---------|-------------------|----------|
| Container startet nicht | `cdb_redis.md` (Troubleshooting) | Zeilen 210–240 |
| Keine Market Data | `cdb_ws.md` (Health-Check) | Zeilen 80–120 |
| Keine Signale generiert | `cdb_signal.md` (Status-Endpoint) | Zeilen 100–130 |
| Prometheus-Fehler | `cdb_prometheus.md` (Targets) | Zeilen 50–100 |
| Backup fehlgeschlagen | `BACKUP_ANLEITUNG.md` | Vollständig |
| DB-Schema-Inkonsistenz | `DATABASE_SCHEMA.sql` + Migration | `backoffice/docs/` |

---

## ✅ Completion-Kriterien für typische Tasks

### "System deployen":
- [ ] `.env` konfiguriert (alle PFLICHT-Variablen gesetzt)
- [ ] `docker compose up -d` erfolgreich
- [ ] Alle Container "healthy" (`docker ps`)
- [ ] Health-Checks grün (Ports 8000, 8001, 8002)
- [ ] Redis Pub/Sub zeigt `market_data`-Events
- [ ] Backup-Task geplant (`setup_backup_task.ps1`)

### "Service debuggen":
- [ ] Logs geprüft (`docker logs <service>`)
- [ ] Health-Endpoint geprüft (`curl /health`)
- [ ] ENV-Variablen validiert (`docker exec <service> env | grep REDIS`)
- [ ] Dependency-Chain geprüft (Redis → Postgres → Services)

### "Monitoring aktivieren":
- [ ] `prometheus.yml` konfiguriert
- [ ] Service-Endpoints `/metrics` liefern Daten
- [ ] Prometheus-Targets UP (`http://localhost:9090/targets`)
- [ ] Grafana-Dashboard importiert

---

**Ende des Dokuments** | Letzte Aktualisierung: 2025-01-11 | Bei Problemen: Siehe `KNOWLEDGE_BASE_INTEGRATION_2025-01-11.md`