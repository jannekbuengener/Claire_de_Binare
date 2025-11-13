# Archiviert: DOCKER_QUICKSTART.md (Stand 2025-01-11)

> Hinweis: Dieses Dokument wurde am 2025-11-01 durch
> `../ops/RUNBOOK_DOCKER_OPERATIONS.md` und das Root-`README.md`
> abgelöst. Inhalte bleiben unverändert zur historischen Referenz erhalten.

## 🚀 Claire de Binaire - Docker Quick Start

## ⚡ TL;DR - Sofort starten

```bash
## 0. Gordon-Freigabe über MCP bestätigen lassen
## (Ticket/Session-Notiz mit Freigabe-ID bereithalten)

## 1. API-Keys eintragen
notepad .env

## 2. Alle Container starten
docker compose up -d

## 3. Logs checken
docker compose logs -f bot_ws

## 4. Services prüfen (nur innerhalb der freigegebenen Maßnahme)
docker compose ps
```

---

## ❗ Gordon-Freigabe Pflicht

- Vor **jedem** Docker-Befehl (up/down/stop/restart/build/prune) ist Gordon über das MCP-Toolkit zu konsultieren.
- Freigabe-ID und Zeitpunkt müssen im laufenden Session-Memo festgehalten werden.
- Ohne dokumentierte Freigabe sind ausschließlich Lesezugriffe (`docker ps`, `docker logs`) zulässig.

---

## 📋 Voraussetzungen

- ✅ Docker Desktop installiert & läuft
- ✅ 4GB RAM frei
- ✅ MEXC API-Keys (READ + TRADE Rechte)

---

## 🔧 Setup (Erstmaliges Starten)

### Schritt 1: API-Keys konfigurieren

Öffne `.env` und trage ein:

```env
MEXC_API_KEY=dein_api_key
MEXC_API_SECRET=dein_api_secret

## Optional: Postgres-Passwort ändern
POSTGRES_PASSWORD=dein_sicheres_passwort
```

### Schritt 2: Container starten

```bash
## Nur Infrastruktur (Redis, Postgres, Monitoring)
docker compose up -d redis postgres prometheus grafana

## + Screener
docker compose up -d bot_ws bot_rest

## Oder alles auf einmal:
docker compose up -d
```

### Schritt 3: Warten bis alle Ready

```bash
## Health-Check
docker compose ps

## Sollte zeigen:
## cdb_redis      Up (healthy)
## cdb_postgres   Up (healthy)
## cdb_ws         Up (healthy)
## cdb_rest       Up (healthy)
## ...
```

---

## 🌐 Zugriff auf Services

| Service | URL | Login |
|---------|-----|-------|
| **WebSocket Screener** | [http://localhost:8000/health](http://localhost:8000/health) | - |
| **REST Screener** | [http://localhost:8080/health](http://localhost:8080/health) | - |
| **Grafana** | [http://localhost:3000](http://localhost:3000) | admin / admin123 |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | - |
| **Redis** | localhost:6379 | (kein Passwort) |
| **PostgreSQL** | localhost:5432 | cdb_user / (siehe .env) |

---

## 📊 Monitoring

### Logs anzeigen

```bash
## Alle Services
docker compose logs -f

## Nur Screener
docker compose logs -f bot_ws bot_rest

## Nur ein Service
docker logs -f cdb_ws
```

### Container-Status

```bash
## Übersicht
docker compose ps

## Detailliert
docker stats

## Health-Checks
docker inspect cdb_redis | grep -A5 Health
```

---

## 🛠️ Häufige Befehle

### Container neustarten

```bash
## Einzelner Service
docker compose restart bot_ws

## Alle
docker compose restart
```

### Container stoppen

```bash
## Alle stoppen
docker compose stop

## Alle stoppen + entfernen
docker compose down

## + Volumes löschen (⚠️ DATEN WEG!)
docker compose down -v
```

### Services aktualisieren

```bash
## Nach Code-Änderung neu bauen
docker compose build bot_ws

## Neu bauen + starten
docker compose up -d --build bot_ws
```

---

## 🔄 MVP-Services aktivieren

**Hinweis**: Signal/Risk/Execution sind noch nicht implementiert!

Wenn Code bereit:

```bash
## Profile "dev" aktivieren
docker compose --profile dev up -d

## Oder einzeln
docker compose up -d signal_engine
```

---

## 🐛 Troubleshooting

### Container startet nicht

```bash
## Logs prüfen
docker compose logs bot_ws

## Häufige Probleme:
## - API-Keys falsch → .env prüfen
## - Port belegt → anderer Service?
## - Build-Fehler → docker compose build bot_ws
```

### Redis-Verbindung fehlgeschlagen

```bash
## Redis läuft?
docker compose ps redis

## Testen
docker exec cdb_redis redis-cli ping
## Sollte: PONG
```

### Postgres-Connection-Error

```bash
## Postgres ready?
docker compose logs postgres | grep "ready to accept"

## Verbindung testen
docker exec cdb_postgres pg_isready -U cdb_user
```

### "No space left"

```bash
## Volumes aufräumen
docker system prune -a --volumes

## ⚠️ Löscht ALLE ungenutzten Container/Images/Volumes!
```

---

## 💾 Backup-Strategie

### Volumes sichern

```bash
## PostgreSQL Backup
docker exec cdb_postgres pg_dump -U cdb_user claire_de_binare > backup_$(date +%Y%m%d).sql

## Redis Backup
docker exec cdb_redis redis-cli SAVE
## Datei liegt in Volume: redis_data/dump.rdb
```

### Volumes-Pfad finden

```bash
docker volume inspect claire_de_binare_postgres_data

## Ausgabe zeigt "Mountpoint": C:\ProgramData\Docker\volumes\...
```

### Manuelles Backup (Windows)

```powershell
## Volumes nach Backup-Ordner kopieren
$backupDir = "C:\Backups\claire_de_binare_$(Get-Date -Format 'yyyyMMdd')"
New-Item -ItemType Directory -Path $backupDir

## PostgreSQL Volume
docker run --rm -v claire_de_binare_postgres_data:/data -v ${backupDir}:/backup alpine tar czf /backup/postgres.tar.gz /data
```

---

## 🎯 Nächste Schritte

1. **Screener laufen lassen** (24h testen)
2. **Monitoring checken** (Grafana Dashboards)
3. **Signal-Engine entwickeln** (siehe backoffice/docs/SERVICE_TEMPLATE.md)

---

## 📚 Weitere Doku

- Architektur: `backoffice/docs/ARCHITEKTUR.md`
- Service-Template: `backoffice/docs/SERVICE_TEMPLATE.md`
- Troubleshooting: `backoffice/docs/TROUBLESHOOTING.md`
- Projekt-Status: `backoffice/PROJECT_STATUS.md`

---

**Fertig! Bei Problemen siehe backoffice/docs/TROUBLESHOOTING.md** 🚀