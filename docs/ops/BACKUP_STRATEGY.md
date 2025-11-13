1x pro Monat)

### Monatlich (manuell):
- [ ] Vollständige Disaster-Recovery-Übung
- [ ] Backup-Strategie reviewen
- [ ] Speicherplatz prüfen
- [ ] Cloud-Backup verifizieren

### Vor Major-Changes:
- [ ] Manueller Snapshot
- [ ] Git-Commit mit Tag
- [ ] Container-Status dokumentieren
- [ ] Rollback-Plan bereit

---

## 📊 Monitoring

### Backup-Erfolg prüfen

```powershell
# Letztes Backup checken
$lastBackup = Get-ChildItem "C:\Backups\claire_de_binare" -Directory | Sort-Object CreationTime -Descending | Select-Object -First 1
Write-Host "Letztes Backup: $($lastBackup.Name)"
Write-Host "Größe: $((Get-ChildItem $lastBackup.FullName -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB) MB"

## Erwartete Dateien
$expectedFiles = @("postgres_*.sql", "redis_*.rdb", "docker-compose.yml")
foreach ($pattern in $expectedFiles) {
    $found = Get-ChildItem "$($lastBackup.FullName)\$pattern" -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "✅ $pattern gefunden"
    } else {
        Write-Host "❌ $pattern FEHLT!"
    }
}
```

### Alert bei Backup-Fehler

In `operations/backup/daily_backup_full.ps1` ergänzen:

```powershell
## Am Ende des Scripts
$logFile = "C:\Backups\claire_de_binare\backup_log.txt"
if ($?) {
    "[$(Get-Date)] ✅ Backup erfolgreich" | Out-File -Append $logFile
} else {
    "[$(Get-Date)] ❌ Backup FEHLGESCHLAGEN!" | Out-File -Append $logFile
    # Optional: E-Mail/Telegram-Alert senden
}
```

---

## 🎯 Best Practices

### ✅ DO:
- Backups automatisieren
- Wiederherstellung regelmäßig testen
- .env verschlüsselt speichern
- 3-2-1-Regel: 3 Kopien, 2 verschiedene Medien, 1 offsite
- Alte Backups automatisch löschen (Speicherplatz!)

### ❌ DON'T:
- Backups im selben Docker-Volume speichern
- .env unverschlüsselt in Cloud
- Nur auf einem Medium sichern
- Wiederherstellung nie testen
- Backups ohne Monitoring

---

## 🚨 Notfall-Kontakte

```
Bei Backup-Problemen:
1. backoffice/docs/TROUBLESHOOTING.md
2. Docker-Logs: docker compose logs
3. Projekt-Status: backoffice/PROJECT_STATUS.md
```

---

## 📝 Änderungshistorie

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2025-01-11 | Initiale Backup-Strategie erstellt | System |
| - | - | - |

---

**Review-Termin**: 2025-02-11
**Verantwortlich**: Projektleitung
**Status**: ✅ Aktiv
1x Monat)

### Vor größeren Änderungen:
- [ ] Git-Commit mit Snapshot
- [ ] Manuelles DB-Backup
- [ ] Container-Status dokumentieren

### Nach Disaster:
- [ ] Backup-Restore testen
- [ ] Alle Services hochfahren
- [ ] Health-Checks prüfen

---

## 🔄 Restore-Test (monatlich)

```bash
## 1. Test-Umgebung
docker compose -f docker-compose.test.yml up -d

## 2. Backup einspielen
cat latest_backup.sql | docker exec -i test_postgres psql -U cdb_user -d claire_de_binare

## 3. Verifizieren
docker exec test_postgres psql -U cdb_user -d claire_de_binare -c "SELECT COUNT(*) FROM trades;"

## 4. Aufräumen
docker compose -f docker-compose.test.yml down -v
```

---

## 📝 Hinweise

### Was NICHT gesichert wird:
- ❌ Docker Images (neu pullen)
- ❌ Node_modules / Build-Artefakte (neu bauen)
- ❌ Temporäre Dateien
- ❌ Cache-Daten

### Backup-Größe (geschätzt):
- PostgreSQL: ~10-50 MB (abhängig von Trade-Historie)
- Redis: ~1-5 MB (Message-Queue)
- Logs: ~10-100 MB/Tag
- **Gesamt**: ~50-200 MB/Tag

### Retention:
- **Täglich**: 30 Tage
- **Wöchentlich**: 12 Wochen
- **Monatlich**: 12 Monate

---

## 🚨 Notfall-Kontakte

**Bei Datenverlust**:
1. Docker Desktop stoppen
2. Volumes NICHT löschen
3. Backup-Restore starten

**Support**:
- Docker Logs: `docker compose logs`
- Volume-Pfad: `docker volume inspect <name>`
- Backup-Status: `ls -lh C:\Backups\claire_de_binare`

---

**Status**: Backup-Strategie etabliert ✅
**Nächster Schritt**: Ersten Backup-Run testen