# Password Contract Remediation - User Actions Required

## Status: CRITICAL - Stack Will Fail Until Fixed

Die env-vars.yml Datei wurde gelöscht und Docker Secrets wurden in den Compose-Dateien wiederhergestellt.
Der Stack wird NICHT starten, bis Sie die folgenden Aktionen durchführen.

---

## Aktion 1: Windows Umgebungsvariablen bereinigen

**Problem**: POSTGRES_PASSWORD und REDIS_PASSWORD in OS-Umgebung konfligieren mit *_PASSWORD_FILE

**Erforderliche Schritte**:

1. Windows-Taste drücken → "Umgebungsvariablen" eingeben → "Umgebungsvariablen für dieses Konto bearbeiten"

2. **LÖSCHEN** Sie diese Variablen aus "Benutzervariablen":
   - `POSTGRES_PASSWORD`
   - `REDIS_PASSWORD`

3. **BEHALTEN** Sie diese Variablen (diese sind erlaubt, da keine Passwörter):
   - `POSTGRES_USER`
   - `POSTGRES_DB`
   - `REDIS_PORT`
   - Alle anderen nicht-sensitiven Konfigurationsvariablen

4. PowerShell neu starten (damit Änderungen wirksam werden)

---

## Aktion 2: Postgres Secret-Datei reparieren

**Problem**: `../.cdb_local/.secrets/postgres_password` ist leer (0 bytes)

**Erforderliche Schritte**:

1. Öffnen Sie die Datei:
   ```
   ../.cdb_local/.secrets/postgres_password
   ```

2. Fügen Sie das tatsächliche Postgres-Passwort ein
   - **NUR das Passwort** (keine Leerzeichen, kein Zeilenumbruch)
   - Beispiel: Datei sollte nur "mein_passwort" enthalten, nichts sonst

3. Speichern Sie die Datei

---

## Aktion 3: Stack neu starten

**Nach** Abschluss von Aktion 1 und 2:

```powershell
# Stack herunterfahren
docker-compose down

# Stack mit Logging-Overlay hochfahren
docker-compose -f infrastructure/compose/base.yml -f infrastructure/compose/logging.yml up -d

# 60 Sekunden warten
Start-Sleep -Seconds 60

# Service-Status prüfen
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## Verifikation: Nachweis der Compliance

**Schritt 1: Postgres Umgebung prüfen** (sollte NUR *_FILE zeigen, KEIN Klartext-Passwort):
```powershell
docker inspect cdb_postgres --format '{{json .Config.Env}}' | ConvertFrom-Json | Select-String PASSWORD
```

**Erwartetes Ergebnis**:
```
POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
```
**KEIN** `POSTGRES_PASSWORD=...` darf erscheinen!

---

**Schritt 2: Redis Umgebung prüfen** (sollte KEINE *_PASSWORD Variablen zeigen):
```powershell
docker inspect cdb_redis --format '{{json .Config.Env}}' | ConvertFrom-Json | Select-String PASSWORD
```

**Erwartetes Ergebnis**: Keine Ausgabe oder nur Redis-interne Variablen

---

**Schritt 3: Logs auf "both are set" Fehler prüfen**:
```powershell
docker logs cdb_postgres --tail 30 | Select-String "both"
```

**Erwartetes Ergebnis**: Keine Ausgabe (kein Fehler)

---

**Schritt 4: Secret-Dateien in Containern prüfen**:
```powershell
# Postgres
docker exec cdb_postgres sh -c "ls -la /run/secrets/ && wc -c /run/secrets/postgres_password"

# Redis
docker exec cdb_redis sh -c "ls -la /run/secrets/ && wc -c /run/secrets/redis_password"
```

**Erwartetes Ergebnis**:
- postgres_password: Dateigröße > 0 bytes
- redis_password: Dateigröße = 24 bytes (bereits korrekt)

---

## Secret-Datei Status (vor Ihren Änderungen)

**Workspace-Level** (`../.cdb_local/.secrets/`):
- ✅ `redis_password` - FILE (24 bytes) - **GUT**
- ❌ `postgres_password` - FILE (0 bytes) - **LEER - MUSS GEFÜLLT WERDEN**
- ❌ `grafana_password` - DIRECTORY - nicht verwendet
- ❌ `mexc_api_key` - DIRECTORY - nicht verwendet
- ❌ `mexc_api_secret` - DIRECTORY - nicht verwendet

**Projekt-Level** (`./.secrets/`):
- Alle DIRECTORIES - nicht verwendet, werden ignoriert

---

## Durchgeführte Änderungen (automatisch)

1. ✅ `infrastructure/compose/env-vars.yml` gelöscht (Richtlinienverstoß)
2. ✅ `docker-compose.base.yml` - `secrets: - postgres_password` wiederhergestellt
3. ✅ `docker-compose.base.yml` - `POSTGRES_PASSWORD_FILE` wiederhergestellt
4. ✅ `docker-compose.base.yml` - Secret-Pfade auf Workspace-Level aktualisiert
5. ✅ `infrastructure/compose/base.yml` - `secrets: - postgres_password` wiederhergestellt
6. ✅ `infrastructure/compose/base.yml` - `POSTGRES_PASSWORD_FILE` wiederhergestellt
7. ✅ `infrastructure/compose/base.yml` - Secret-Pfade auf Workspace-Level aktualisiert

---

## Nächste Schritte (nach erfolgreicher Verifikation)

Sobald der Passwort-Vertrag sauber ist und der Stack stabil läuft:

- ✅ Criteria A-G Vervollständigung kann fortgesetzt werden:
  - Criterion B: Port-Bindings aktualisieren (dev.yml)
  - Criterion A: Rollback-Scripts erstellen
  - Criterion F: DR-Scripts erstellen
  - Criterion G: Utility-Scripts erstellen
  - Criteria D & E: Dokumentation erstellen

---

## Bei Problemen

Falls nach Durchführung aller Aktionen immer noch Fehler auftreten:

1. Prüfen Sie die Container-Logs:
   ```powershell
   docker logs cdb_postgres --tail 50
   docker logs cdb_redis --tail 50
   ```

2. Prüfen Sie, ob die Secret-Dateien korrekt gemountet sind:
   ```powershell
   docker exec cdb_postgres ls -la /run/secrets/
   ```

3. Stellen Sie sicher, dass die PowerShell-Sitzung nach Änderung der Umgebungsvariablen neu gestartet wurde
