# Runbook – Docker Compose Operationen

## 🚀 Zweck
Zentrale Referenz für wiederkehrende Docker- und Compose-Befehle im Claire de
Binaire Stack. Ersetzt die verstreuten Quick-Start-Dokumente im Repository und
fasst Start, Validierung, Tests und Störungen zusammen.

## ✅ Vorbedingungen
- Docker Desktop läuft (Status: Running)
- `.env` mit Secrets befüllt, validiert via `check_env.ps1`
- Gordon-Freigabe für Write-Operationen dokumentiert (ADR-017)

## ▶️ Start & Health-Checks

```powershell
# Container starten
pwsh backoffice/automation/check_env.ps1
docker compose pull
docker compose up -d

# Status & Health
docker compose ps
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## 🔍 Schnelltest (Paper-Trading)

```powershell
# Market-Data-Event simulieren
$event = '{"symbol":"BTC_USDT","price":50000,"volume":1000000,"timestamp":1736600000,"pct_change":5.0}'
docker exec cdb_redis redis-cli PUBLISH market_data $event

# Ergebnisse prüfen
docker exec cdb_postgres psql -U claire -d claire_de_binare -c "SELECT * FROM signals ORDER BY timestamp DESC LIMIT 3;"
```

## ♻️ Neustart & Wartung

```powershell
# Einzelne Services neustarten (Signal & Risk)
docker compose restart signal_engine risk_manager

# Kompletten Stack neu starten
docker compose down
Start-Sleep -Seconds 5
docker compose up -d
```

## 🛠️ Troubleshooting

| Symptom                         | Befehl / Maßnahme                                              |
|---------------------------------|----------------------------------------------------------------|
| Container „unhealthy“           | `docker compose logs <service>` → Fehler analysieren           |
| Redis nicht erreichbar          | `docker exec cdb_redis redis-cli ping`                         |
| Postgres Login schlägt fehl     | `docker exec cdb_postgres pg_isready -U claire`                |
| Compose-Konfiguration prüfen    | `docker compose config --quiet`                               |
| Ports belegt                    | `Get-NetTCPConnection | Where-Object LocalPort -in 8000,8080` |

## 🧾 Nacharbeiten
- Ergebnisse in Session-Memo festhalten
- Bei Änderungen an Compose/ENV: `DECISION_LOG.md` prüfen/ergänzen
- Bei dauerhaften Anpassungen Root-`README.md` aktualisieren

## 🔗 Referenzen
- `README.md` (Quick Start für Operatoren)
- `README_GUIDE.md` (Dokumentationsstandard)
- `backoffice/docs/END_TO_END_TEST_GUIDE.md`
- `backoffice/docs/EXECUTION_DEBUG_CHECKLIST.md`
