# 🚀 QUICK START - Nach Docker Neuinstallation

> **Hinweis:** Dieses Dokument enthält einen historischen Snapshot aus dem Docker-Reinstall 2025-12-31.  
> **Aktuelle Backup-Location:** `F:\Claire_Backups`  
> **Aktuelle Restore-Front-Door:** `make restore` (→ `infrastructure/scripts/restore_all.ps1`)

---

## ⚡ Restore — Kanonischer Einstieg

### 1. Docker verifizieren
```powershell
docker --version
docker compose version
```
✅ Sollte funktionieren nach Neuinstallation

### 2. Verfügbare Backups anzeigen
```powershell
make restore
# → listet Archive in F:\Claire_Backups
```

### 3. Restore mit konkretem Backup-Namen ausführen
```powershell
powershell.exe -ExecutionPolicy Bypass -File infrastructure/scripts/restore_all.ps1 -BackupName cdb_backup_YYYYMMDD_HHMMSS
# → Backup-Name aus Schritt 2 einsetzen
```
⏱️ Dauer: ~2-3 Minuten

### 4. Stack starten
```powershell
make docker-up
```
⏱️ Dauer: ~30-60 Sekunden

### 5. Restore verifizieren

```powershell
# Redis — Schlüsselanzahl prüfen (> 0 erwartet)
docker exec cdb_redis redis-cli DBSIZE

# Postgres — Tabellen prüfen
docker exec cdb_postgres psql -U postgres -c "\dt" 2>&1 | Select-String "public"
```

> `make backup-health` prüft die Frische des letzten Backups, nicht den Restore-Erfolg. Backup-Frischecheck separat ausführen wenn gewünscht.

---

## ✅ Erfolgs-Checks

1. **Docker läuft:**
   ```powershell
   docker ps
   ```
   Sollte zeigen: grafana, redis, signal, ws, risk, execution, db_writer, paper_runner

2. **Grafana erreichbar** (wird via Repo-Provisioning geladen, nicht Teil des Restore-Scopes):
   - http://localhost:3000
   - Login: admin / (siehe Secrets)

3. **Redis Daten:**
   ```powershell
   docker exec cdb_redis redis-cli DBSIZE
   ```
   Sollte > 0 sein

4. **Container Health:**
   ```powershell
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```
   Gesunde Container sollten "healthy" zeigen

---

## 🚨 Wenn Probleme auftreten

### Problem: Container crashen
**Check Logs:**
```powershell
docker compose logs cdb_postgres
docker compose logs cdb_execution
```

**Häufige Ursache:** Falsche Pfade in `.env` oder fehlende Secrets — Logs prüfen.

### Problem: Postgres startet nicht
**Container ID prüfen:**
```powershell
docker ps -a | grep postgres
```

**Mount-Fehler?**
- Compose-Konfiguration auf absolute Host-Pfade prüfen
- Volume-Namen sollten ausreichen (keine Host-Mounts für schema.sql nötig)

### Problem: Grafana zeigt keine Dashboards
**Restore nochmal:** `make restore` erneut ausführen oder manuell aus `F:\Claire_Backups` wiederherstellen.

---

## 📊 Was wird wiederhergestellt (aktueller Canon)

| Component | Methode | Status |
|-----------|---------|--------|
| PostgreSQL | SQL dump (pg_dumpall → restore) | ✅ Aktiver Restore-Scope |
| Redis | dump.rdb | ✅ Aktiver Restore-Scope |
| SurrealDB | Optional, wenn aktiv | ◻️ Wenn vorhanden |

> **Historischer Scope (2025-12-31-Snapshot):** Frühere Backups enthielten Grafana-Volumes (109MB), Prometheus (2.0MB), Claude Memory (2.9KB), Loki (671B) — kein Teil des aktuellen `make backup`/`make restore`-Scopes.

---

## 🔧 Historische Referenz: Manuelle Volume-Commands (2025-12-31-Snapshot)

> Diese Befehle stammen aus dem Docker-Reinstall-Event vom 2025-12-31 und referenzieren den damaligen Backup-Pfad.  
> **Aktuelle Front Door:** `make restore` (→ `infrastructure/scripts/restore_all.ps1`)

Hintergrund-Befehle für direktes Volume-Restore falls `make restore` nicht verfügbar ist — Backup-Pfad muss auf aktuelles Archiv in `F:\Claire_Backups` angepasst werden.

---

## 🎯 Erwartete Endstate

**Laufende Container (docker ps):**
```
cdb_grafana      - healthy
cdb_redis        - healthy  
cdb_postgres     - healthy
cdb_prometheus   - healthy
cdb_loki         - healthy
cdb_promtail     - running
cdb_signal       - healthy
cdb_ws           - healthy
cdb_risk         - healthy
cdb_execution    - running/healthy
cdb_db_writer    - running/healthy
cdb_paper_runner - running/healthy
```

**Services erreichbar:**
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Signal: http://localhost:8005/health
- WS: http://localhost:8000/health
- Risk: http://localhost:8002/health

---

**Gesamt-Dauer für komplettes Restore:** ~5 Minuten  
**Kanonischer Einstieg:** `make restore` (Backup-Liste), dann `restore_all.ps1 -BackupName <name>`  
**Hintergrund-Referenz:** `RESTORE_GUIDE.md` (historischer 2025-12-31-Snapshot)
