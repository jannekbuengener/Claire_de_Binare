# Pre-Migration Checklist - Claire de Binare (HISTORISCH)

**Erstellt**: 2025-11-16
**Migration durchgeführt**: 2025-11-16
**Status**: ✅ **ABGESCHLOSSEN**

> **Historischer Kontext**: Diese Checkliste dokumentiert die Pre-Migration-Tasks für die Cleanroom-Migration vom 2025-11-16. Alle Tasks wurden erfolgreich abgeschlossen. Dieses Dokument dient als Template für zukünftige Migrationen.

---

## Übersicht

Diese Checkliste beschreibt die 4 CRITICAL Pre-Migration-Tasks, die vor der Cleanroom-Migration durchgeführt wurden. Alle Aufgaben wurden erfolgreich abgeschlossen.

---

## Voraussetzungen

- [ ] PowerShell 5.1 oder höher installiert
- [ ] Docker & Docker Compose verfügbar
- [ ] Git installiert (für History-Check)
- [ ] Backup des aktuellen Zustands erstellt

---

## TASK 0: Backup erstellen (5 Min)

### Manuelle Schritte

```powershell
# Backup-Ordner erstellen
mkdir sandbox\backups -ErrorAction SilentlyContinue

# Kritische Dateien sichern
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item " - Kopie.env" "sandbox\backups\.env.backup_$timestamp"
Copy-Item "docker-compose.yml" "sandbox\backups\docker-compose.yml.backup_$timestamp"
```

### Validierung

- [ ] Backup-Dateien existieren in `sandbox\backups\`
- [ ] Timestamp im Dateinamen korrekt

---

## TASK 1: SR-001 - Secrets bereinigen (15 Min)

**Risiko**: 🔴 CRITICAL - Exposed Secrets in Git
**Betroffene Datei**: ` - Kopie.env`

### Ziel

Alle echten Passwörter, API-Keys und Tokens aus ` - Kopie.env` entfernen und Datei zu `.env.template` umbenennen.

### Automatisiert (empfohlen)

```powershell
cd sandbox
.\pre_migration_tasks.ps1
```

### Manuell (Alternative)

```powershell
# 1. Datei öffnen
code " - Kopie.env"

# 2. Folgende Zeilen anpassen (Secrets durch Platzhalter ersetzen):
# ALT:
POSTGRES_PASSWORD=Jannek8$
POSTGRES_USER=claire
DATABASE_URL=postgresql://claire:Jannek8$@cdb_postgres:5432/claire_de_binare
GRAFANA_PASSWORD=Jannek2025!

# NEU:
POSTGRES_PASSWORD=<SET_IN_ENV>
POSTGRES_USER=<SET_IN_ENV>
DATABASE_URL=postgresql://<USER>:<PASSWORD>@cdb_postgres:5432/claire_de_binare
GRAFANA_PASSWORD=<SET_IN_ENV>

# 3. Datei umbenennen
Move-Item " - Kopie.env" ".env.template" -Force
```

### Validierung

- [ ] Datei `.env.template` existiert
- [ ] Datei ` - Kopie.env` existiert NICHT mehr
- [ ] Keine echten Passwörter in `.env.template` (Suche nach "Jannek", "8$", "2025!")
- [ ] Alle Secrets nutzen `<SET_IN_ENV>` Platzhalter
- [ ] `.env` ist in `.gitignore` eingetragen

**Check-Befehl**:
```powershell
.\pre_migration_validation.ps1
```

**Git-History-Check** (WICHTIG):
```powershell
# Prüfe, ob Secrets jemals committed wurden
git log --all -S "Jannek8" --oneline

# Sollte leer sein! Falls nicht: Git-History-Bereinigung erforderlich
```

---

## TASK 2: SR-002 - ENV-Naming normalisieren (20 Min)

**Risiko**: 🔴 CRITICAL - ENV-Naming-Konflikt führt zu unwirksamen Risk-Limits
**Betroffene Dateien**: `.env.template`, Service-Code (später)

### Ziel

ENV-Variablen auf **Dezimal-Konvention** umstellen:
- `MAX_DAILY_DRAWDOWN=5.0` → `MAX_DAILY_DRAWDOWN_PCT=0.05` (5%)
- `MAX_POSITION_SIZE=10.0` → `MAX_POSITION_PCT=0.10` (10%)
- `MAX_TOTAL_EXPOSURE=50.0` → `MAX_EXPOSURE_PCT=0.50` (50%)

### Schritte

#### 1. .env.template aktualisieren

```powershell
# Automatisch (empfohlen):
.\pre_migration_tasks.ps1

# ODER manuell in .env.template bearbeiten:
```

**Alte Werte** (ENTFERNEN):
```bash
MAX_DAILY_DRAWDOWN=5.0
MAX_POSITION_SIZE=10.0
MAX_TOTAL_EXPOSURE=50.0
```

**Neue Werte** (ERSETZEN):
```bash
# ============================================================================
# RISK MANAGEMENT (Dezimal-Konvention: 0.05 = 5%)
# ============================================================================
# Daily Drawdown Limit (Min: 0.01, Max: 0.20, Default: 0.05)
MAX_DAILY_DRAWDOWN_PCT=0.05

# Position Size Limit (Min: 0.01, Max: 0.25, Default: 0.10)
MAX_POSITION_PCT=0.10

# Total Portfolio Exposure (Min: 0.10, Max: 1.00, Default: 0.50)
MAX_EXPOSURE_PCT=0.50

# Per-Trade Stop Loss (Min: 0.005, Max: 0.10, Default: 0.02)
STOP_LOSS_PCT=0.02

# Market Anomaly: Max Slippage (Min: 0.001, Max: 0.05, Default: 0.01)
MAX_SLIPPAGE_PCT=0.01

# Market Anomaly: Max Spread Multiplier (Min: 2.0, Max: 10.0, Default: 5.0)
MAX_SPREAD_MULTIPLIER=5.0

# Data Staleness Timeout in Seconds (Min: 10, Max: 120, Default: 30)
DATA_STALE_TIMEOUT_SEC=30
```

#### 2. Service-Code aktualisieren (wenn vorhanden)

**Betroffene Services**: `cdb_core`, `cdb_risk`, `cdb_execution`

**Beispiel-Änderung** (in `config.py` oder `service.py`):

```python
# ALT (FALSCH - liest 5.0 als 500%!):
max_dd = float(os.getenv("MAX_DAILY_DRAWDOWN"))

# NEU (KORREKT - liest 0.05 als 5%):
max_dd = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT"))
```

### Validierung

- [ ] Alle 7 Risk-Parameter in `.env.template` vorhanden:
  - `MAX_DAILY_DRAWDOWN_PCT`
  - `MAX_POSITION_PCT`
  - `MAX_EXPOSURE_PCT`
  - `STOP_LOSS_PCT`
  - `MAX_SLIPPAGE_PCT`
  - `MAX_SPREAD_MULTIPLIER`
  - `DATA_STALE_TIMEOUT_SEC`
- [ ] Alte ENV-Namen (`MAX_DAILY_DRAWDOWN=5.0` etc.) NICHT mehr vorhanden
- [ ] Dezimal-Werte korrekt (0.05 für 5%, nicht 5.0)
- [ ] Kommentare mit Min/Max/Defaults vorhanden

**Check-Befehl**:
```powershell
# Prüfe auf alte Konvention
Select-String -Path .env.template -Pattern "MAX_DAILY_DRAWDOWN="
# Sollte nur MAX_DAILY_DRAWDOWN_PCT finden, nicht MAX_DAILY_DRAWDOWN=
```

---

## TASK 3: SR-003 - MEXC-API-ENV ergänzen (5 Min)

**Risiko**: 🔴 CRITICAL - System nicht funktionsfähig ohne MEXC-API-Credentials
**Betroffene Datei**: `.env.template`

### Ziel

Sicherstellen, dass `MEXC_API_KEY` und `MEXC_API_SECRET` in `.env.template` vorhanden sind.

### Schritte

```powershell
# Automatisch (empfohlen):
.\pre_migration_tasks.ps1

# ODER manuell in .env.template ergänzen:
```

**Zu ergänzender Block** (falls nicht vorhanden):
```bash
# ============================================================================
# MEXC API (CRITICAL - System nicht funktionsfähig ohne!)
# ============================================================================
MEXC_API_KEY=<SET_IN_ENV>
MEXC_API_SECRET=<SET_IN_ENV>
```

### Validierung

- [ ] `MEXC_API_KEY=<SET_IN_ENV>` in `.env.template`
- [ ] `MEXC_API_SECRET=<SET_IN_ENV>` in `.env.template`
- [ ] Kommentar "CRITICAL - System nicht funktionsfähig ohne!" vorhanden

**Check-Befehl**:
```powershell
Select-String -Path .env.template -Pattern "MEXC_API"
# Sollte 2 Zeilen finden (KEY und SECRET)
```

---

## TASK 4: cdb_signal_gen entfernen (10 Min)

**Risiko**: 🟠 HIGH - Service blockiert Deployment (Dockerfile.signal_gen fehlt)
**Betroffene Datei**: `docker-compose.yml`

### Ziel

Service `cdb_signal_gen` aus `docker-compose.yml` entfernen (auskommentieren), da `Dockerfile.signal_gen` fehlt und Service wahrscheinlich Legacy ist.

### Schritte

```powershell
# Automatisch (empfohlen):
.\pre_migration_tasks.ps1

# ODER manuell in docker-compose.yml:
```

**Service-Block auskommentieren** (Zeilen 263-277):
```yaml
  # ============================================================
  # LEGACY SERVICE (entfernt - Dockerfile.signal_gen fehlt)
  # ============================================================
  # cdb_signal_gen:
  #   build:
  #     context: .
  #     dockerfile: Dockerfile.signal_gen
  #   container_name: cdb_signal_gen
  #   restart: unless-stopped
  #   environment:
  #     REDIS_HOST: cdb_redis
  #     REDIS_PORT: 6379
  #     REDIS_PASSWORD: ${REDIS_PASSWORD}
  #     REDIS_DB: 0
  #   depends_on:
  #     - cdb_redis
  #   networks:
  #     - cdb_network
```

### Validierung

- [ ] Service `cdb_signal_gen` auskommentiert oder entfernt
- [ ] `docker-compose.yml` Syntax valide

**Check-Befehl**:
```powershell
# Syntax-Check
docker compose config --quiet

# Sollte KEINEN Fehler werfen (Exit Code 0)
# Falls Fehler: Compose-Syntax kaputt
```

---

## FINALE VALIDIERUNG (10 Min)

Nach Abschluss aller Tasks:

### 1. Automatisierte Validierung

```powershell
cd sandbox
.\pre_migration_validation.ps1
```

**Erwartetes Ergebnis**:
```
✅ ALLE CHECKS BESTANDEN
Status: ✅ GO für Cleanroom-Migration
```

### 2. Manuelle Checks

- [ ] `.env.template` existiert (` - Kopie.env` NICHT mehr)
- [ ] Keine Secrets in `.env.template` (alles `<SET_IN_ENV>`)
- [ ] 7 Risk-Parameter mit Dezimal-Konvention vorhanden
- [ ] MEXC-API-Keys in Template
- [ ] `cdb_signal_gen` auskommentiert
- [ ] `docker compose config --quiet` → kein Fehler

### 3. Git-Status prüfen

```powershell
git status
```

**Erwartete Änderungen**:
- ` - Kopie.env` → deleted
- `.env.template` → modified or new
- `docker-compose.yml` → modified

**WICHTIG**: `.env` sollte NICHT in `git status` erscheinen (ist in .gitignore)!

---

## Nächste Schritte (NACH erfolgreicher Validierung)

### 1. Echte .env erstellen

```powershell
# Template kopieren
Copy-Item .env.template .env

# .env öffnen und ALLE <SET_IN_ENV> durch echte Werte ersetzen
code .env
```

**Zu ersetzende Platzhalter**:
- `POSTGRES_USER` → z.B. `claire`
- `POSTGRES_PASSWORD` → starkes Passwort generieren
- `REDIS_PASSWORD` → starkes Passwort generieren
- `GRAFANA_PASSWORD` → starkes Passwort generieren
- `MEXC_API_KEY` → aus MEXC-Account
- `MEXC_API_SECRET` → aus MEXC-Account

### 2. System starten

```powershell
# Services starten
docker compose up -d

# Logs verfolgen
docker compose logs -f

# Nach 30 Sekunden: Health-Checks prüfen
docker compose ps
```

**Erwartete Status**: Alle Services `healthy`

### 3. Smoke-Test

```powershell
# Health-Endpoints einzeln prüfen
curl http://localhost:8000/health  # cdb_ws
curl http://localhost:8001/health  # cdb_core
curl http://localhost:8002/health  # cdb_risk
curl http://localhost:8003/health  # cdb_execution

# Event-Flow testen (manuell Event publishen)
docker exec cdb_redis redis-cli -a <REDIS_PASSWORD> PUBLISH market_data '{"symbol":"BTC_USDT","price":50000}'

# Logs prüfen: Signal → Risk → Execution
docker compose logs cdb_core cdb_risk cdb_execution
```

### 4. Cleanroom-Migration starten

Siehe `PIPELINE_COMPLETE_SUMMARY.md` → Abschnitt "Cleanroom-Migration-Ablauf"

---

## Troubleshooting

### Problem: "Secrets noch in .env.template gefunden"

**Lösung**:
```powershell
# Suche nach Secrets
Select-String -Path .env.template -Pattern "Jannek|8\$|2025!"

# Manuell ersetzen durch <SET_IN_ENV>
```

### Problem: "docker compose config" wirft Fehler

**Häufige Ursachen**:
- YAML-Syntax (Einrückung falsch)
- ENV-Variablen nicht gesetzt (fehlende `${VAR:?...}`)

**Debug**:
```powershell
# Detaillierte Fehlermeldung
docker compose config

# Einzelne Services testen
docker compose config --services
```

### Problem: "Git-History enthält Secrets"

**CRITICAL**: Falls `git log --all -S "Jannek8"` Commits findet:

⚠️ **NIEMALS in Haupt-Repo mergen!**

**Lösungen**:
1. **Cleanroom-Ansatz** (empfohlen): Nur bereinigte Dateien ins neue Repo kopieren
2. **Git-Filter-Branch** (advanced): Git-History bereinigen (siehe Git-Doku)
3. **Neues Repo** (safe): Alten Repo archivieren, neues Repo mit sauberer History starten

---

## Checkliste - Zusammenfassung

- [ ] **TASK 0**: Backup erstellt
- [ ] **TASK 1**: SR-001 - Secrets bereinigt (` - Kopie.env` → `.env.template`)
- [ ] **TASK 2**: SR-002 - ENV-Naming normalisiert (Dezimal-Konvention)
- [ ] **TASK 3**: SR-003 - MEXC-API-ENV ergänzt
- [ ] **TASK 4**: cdb_signal_gen entfernt
- [ ] **Validierung**: `.\pre_migration_validation.ps1` → ✅ PASS
- [ ] **Git-Check**: Keine Secrets in History
- [ ] **Compose-Check**: `docker compose config --quiet` → kein Fehler

**Status nach Abschluss**: ✅ **GO für Cleanroom-Migration**

---

**Geschätzter Gesamt-Aufwand**: 65 Minuten
**Risiko-Level nach Abschluss**: 🟢 LOW

Viel Erfolg! 🚀
