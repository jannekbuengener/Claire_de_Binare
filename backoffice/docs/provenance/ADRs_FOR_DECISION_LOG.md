# ADRs für DECISION_LOG.md - Claire de Binare-Migration

**Erstellt**: 2025-11-16
**Anzahl**: 3 neue ADRs
**Einfügen in**: `backoffice/docs/DECISION_LOG.md` (Claire de Binare-Repo)

---

## ADR-035: ENV-Naming-Konvention für Risk-Parameter (Dezimal-Format)

**Datum**: 2025-11-16
**Status**: ✅ Akzeptiert
**Verantwortlicher**: jannekbuengener (via Pipeline 4 - Multi-Agenten-System)

### Kontext

Vor der Migration existierte eine inkonsistente ENV-Naming-Konvention für Risk-Parameter:
- `MAX_DAILY_DRAWDOWN=5.0` (Bedeutung unklar: 5% oder 500%?)
- `MAX_POSITION_SIZE=10.0` (10% oder 1000%?)
- `MAX_TOTAL_EXPOSURE=50.0` (50% oder 5000%?)

**Problem**: Service-Code interpretierte diese Werte als Ganzzahlen, nicht als Prozentangaben:
```python
# FALSCH - liest 5.0 als 500%:
max_dd = float(os.getenv("MAX_DAILY_DRAWDOWN"))  # 5.0 → wird als 500% behandelt!
if daily_loss > max_dd:  # Daily loss 6% > 5.0? NEIN → Limit unwirksam!
```

**Konsequenz**: Risk-Limits waren faktisch unwirksam, da sie um Faktor 100 zu hoch interpretiert wurden.

### Entscheidung

Alle Prozent-Angaben in ENV-Variablen nutzen **Dezimal-Format** (0.05 = 5%) und Suffix `_PCT`.

**Neue Konvention**:
```bash
# Alte Namen (ENTFERNT):
# MAX_DAILY_DRAWDOWN=5.0
# MAX_POSITION_SIZE=10.0
# MAX_TOTAL_EXPOSURE=50.0

# Neue Namen (Dezimal-Format):
MAX_DAILY_DRAWDOWN_PCT=0.05    # 5%
MAX_POSITION_PCT=0.10          # 10%
MAX_EXPOSURE_PCT=0.50          # 50%
STOP_LOSS_PCT=0.02             # 2%
MAX_SLIPPAGE_PCT=0.01          # 1%

# Ausnahmen (keine Prozente):
MAX_SPREAD_MULTIPLIER=5.0      # 5x (Faktor, kein Prozent)
DATA_STALE_TIMEOUT_SEC=30      # 30 Sekunden
```

**Code-Änderung** (Service-Side):
```python
# KORREKT - liest 0.05 als 5%:
max_dd_pct = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT"))  # 0.05 → 5%
if daily_loss_pct > max_dd_pct:  # Daily loss 6% > 5%? JA → Limit greift!
    halt_trading()
```

### Konsequenzen

**Positiv**:
- ✅ Eindeutige Interpretation (0.05 = 5%, nicht 500%)
- ✅ Konsistent mit Python float-Arithmetik (0.05 * portfolio_value)
- ✅ Alle Risk-Parameter mit `_PCT` Suffix (Typ-Safety durch Naming)
- ✅ Min/Max-Werte in Dezimal-Format dokumentiert (z.B. Min: 0.01, Max: 0.20 für Drawdown)

**Negativ**:
- ⚠️ **Breaking Change**: Alte ENV-Namen (`MAX_DAILY_DRAWDOWN`) nicht mehr gültig
- ⚠️ Code-Änderungen in allen Services erforderlich (config.py, risk_manager)
- ⚠️ Bestehende .env-Dateien müssen aktualisiert werden

**Migration-Aufwand**:
- .env.template: Alle ENV-Namen aktualisiert ✅
- Service-Code: `os.getenv("MAX_DAILY_DRAWDOWN")` → `os.getenv("MAX_DAILY_DRAWDOWN_PCT")`
- Tests: Risk-Parameter-Tests an neue Werte anpassen (5.0 → 0.05)

### Betroffene ENV-Variablen

| Alte Variable | Neue Variable | Default | Min | Max |
|---------------|---------------|---------|-----|-----|
| `MAX_DAILY_DRAWDOWN=5.0` | `MAX_DAILY_DRAWDOWN_PCT=0.05` | 0.05 (5%) | 0.01 | 0.20 |
| `MAX_POSITION_SIZE=10.0` | `MAX_POSITION_PCT=0.10` | 0.10 (10%) | 0.01 | 0.25 |
| `MAX_TOTAL_EXPOSURE=50.0` | `MAX_EXPOSURE_PCT=0.50` | 0.50 (50%) | 0.10 | 1.00 |
| *(neu)* | `STOP_LOSS_PCT=0.02` | 0.02 (2%) | 0.005 | 0.10 |
| *(neu)* | `MAX_SLIPPAGE_PCT=0.01` | 0.01 (1%) | 0.001 | 0.05 |
| *(neu)* | `MAX_SPREAD_MULTIPLIER=5.0` | 5.0 (5x) | 2.0 | 10.0 |
| *(neu)* | `DATA_STALE_TIMEOUT_SEC=30` | 30 (30s) | 10 | 120 |

### Referenzen

- **Pre-Migration Task**: SR-002 (ENV-Naming normalisieren)
- **Canonical Schema**: `backoffice/docs/canonical_schema.yaml` → Sektion `env_variables`
- **Security-Risk**: SR-002 in `infra_conflicts.md`
- **Pipeline**: Pipeline 4 - Kanonische Systemrekonstruktion

---

## ADR-036: Secrets-Management-Policy (Never Commit Secrets)

**Datum**: 2025-11-16
**Status**: ✅ Akzeptiert
**Verantwortlicher**: jannekbuengener (via Pipeline 4 - Multi-Agenten-System)

### Kontext

Vor der Migration wurden Secrets im Klartext in ` - Kopie.env` committed:
```bash
# ` - Kopie.env` (FALSCH - Secrets committed!):
POSTGRES_PASSWORD=Jannek8$
GRAFANA_PASSWORD=Jannek2025!
DATABASE_URL=postgresql://claire:Jannek8$@cdb_postgres:5432/claire_de_binare
```

**Probleme**:
1. **Security-Risk SR-001**: Exposed Secrets im Git-Repo (öffentlich oder intern sichtbar)
2. **Git-History**: Secrets bleiben in Git-History, selbst nach Löschen der Datei
3. **Rotation unmöglich**: Passwort-Wechsel erfordert Git-History-Bereinigung
4. **Compliance**: Verstößt gegen Security-Best-Practices (OWASP, CIS Benchmarks)

### Entscheidung

**Strikte Trennung** zwischen `.env.template` (committed) und `.env` (gitignored, lokal):

1. **`.env.template`** (committed im Git-Repo):
   - Enthält ALLE ENV-Variablen-Namen
   - Secrets als Platzhalter: `<SET_IN_ENV>`
   - Dokumentation (Kommentare): Bedeutung, Min/Max, Defaults
   - Versioniert, Teil des Repos

2. **`.env`** (lokal, NIEMALS committed):
   - Kopie von `.env.template`
   - Platzhalter durch echte Secrets ersetzt
   - In `.gitignore` eingetragen
   - Nur auf lokalem System / Production-Servern

### Konsequenzen

**Positiv**:
- ✅ Keine Secrets im Git-Repo (weder aktuell noch in History)
- ✅ Neue Setups einfach: `cp .env.template .env` → Platzhalter ersetzen
- ✅ Rotation: Nur lokale `.env` ändern + Container-Restart (kein Git-Commit nötig)
- ✅ Dokumentation: `.env.template` zeigt ALLE benötigten Variablen
- ✅ Compliance: Erfüllt Security-Best-Practices

**Negativ**:
- ⚠️ Manuelle Arbeit: Platzhalter müssen lokal ersetzt werden
- ⚠️ Secret-Management: Keine automatische Distribution (z.B. via Vault, AWS Secrets Manager)
- ⚠️ Backup: Lokale `.env` muss separat gesichert werden (außerhalb Git)

### Umsetzung

#### .env.template (Beispiel-Struktur)

```bash
# ============================================================================
# DATABASE (PostgreSQL)
# ============================================================================
POSTGRES_DB=claire_de_binare
POSTGRES_USER=<SET_IN_ENV>           # Username für PostgreSQL (z.B. "claire")
POSTGRES_PASSWORD=<SET_IN_ENV>       # Starkes Passwort (min. 16 Zeichen)
DATABASE_URL=postgresql://<USER>:<PASSWORD>@cdb_postgres:5432/claire_de_binare

# ============================================================================
# MESSAGE BUS (Redis)
# ============================================================================
REDIS_HOST=cdb_redis
REDIS_PORT=6379
REDIS_PASSWORD=<SET_IN_ENV>          # Starkes Passwort (min. 16 Zeichen)

# ============================================================================
# MEXC API (CRITICAL - System nicht funktionsfähig ohne!)
# ============================================================================
MEXC_API_KEY=<SET_IN_ENV>            # API-Key aus MEXC-Account
MEXC_API_SECRET=<SET_IN_ENV>         # API-Secret aus MEXC-Account
```

#### .gitignore (Eintrag sicherstellen)

```bash
# Environment
.env
.env.local
*.env
# Exclude all .env files in docker directories
docker/**/.env
# But include .env.example templates
!docker/**/.env.example
!.env.template
```

#### Setup-Prozess (neue Deployments)

```bash
# 1. .env.template kopieren
cp .env.template .env

# 2. .env öffnen und Platzhalter ersetzen
nano .env  # oder code .env

# 3. Secrets eintragen (manuell oder via Secret-Manager)
# POSTGRES_PASSWORD=<starkes-passwort-generieren>
# REDIS_PASSWORD=<starkes-passwort-generieren>
# MEXC_API_KEY=<aus-mexc-account>
# ...

# 4. Validieren: .env nicht in git status
git status | grep -q "\.env" && echo "FEHLER: .env in Git!" || echo "OK"
```

#### Optional: Pre-Commit-Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached --name-only | grep -q "^\.env$"; then
  echo "❌ ERROR: .env darf nicht committed werden!"
  echo "Nur .env.template sollte versioniert sein."
  exit 1
fi
```

### Betroffene Secrets

| Secret | ENV-Variable | Verwendung |
|--------|--------------|------------|
| PostgreSQL User | `POSTGRES_USER` | Datenbank-Zugriff |
| PostgreSQL Password | `POSTGRES_PASSWORD` | Datenbank-Auth |
| Redis Password | `REDIS_PASSWORD` | Message-Bus-Auth |
| Grafana Admin Password | `GRAFANA_PASSWORD` | Monitoring-UI-Zugriff |
| MEXC API Key | `MEXC_API_KEY` | Exchange-API-Zugriff |
| MEXC API Secret | `MEXC_API_SECRET` | Exchange-API-Signierung |

### Referenzen

- **Pre-Migration Task**: SR-001 (Secrets bereinigen)
- **Security-Risk**: SR-001 in `infra_conflicts.md` (Exposed Secrets in ` - Kopie.env`)
- **Pipeline**: Pipeline 4 - Kanonische Systemrekonstruktion

---

## ADR-037: Legacy-Service cdb_signal_gen entfernt

**Datum**: 2025-11-16
**Status**: ✅ Akzeptiert
**Verantwortlicher**: jannekbuengener (via Pipeline 4 - Multi-Agenten-System)

### Kontext

Service `cdb_signal_gen` war in `docker-compose.yml` definiert:
```yaml
cdb_signal_gen:
  build:
    context: .
    dockerfile: Dockerfile.signal_gen  # ← Diese Datei fehlt!
  container_name: cdb_signal_gen
  restart: unless-stopped
  environment:
    REDIS_HOST: cdb_redis
    REDIS_PORT: 6379
    REDIS_PASSWORD: ${REDIS_PASSWORD}
  depends_on:
    - cdb_redis
  networks:
    - cdb_network
```

**Probleme**:
1. **Dockerfile.signal_gen fehlt** → `docker compose up` schlägt fehl
2. **Keine Service-Implementierung** gefunden (kein Code in `backoffice/services/`)
3. **Funktions-Überschneidung**: Service `cdb_core` (Signal Engine) übernimmt bereits Signal-Generierung

**Hypothese**: `cdb_signal_gen` ist Legacy aus früherer Entwicklungsphase, wurde durch `cdb_core` abgelöst.

### Entscheidung

Service `cdb_signal_gen` aus `docker-compose.yml` entfernen (auskommentieren).

**Begründung**:
- `cdb_core` (Signal Engine) ist vollständig implementiert und übernimmt Signal-Generierung
- Dockerfile fehlt → Service nicht deploybar
- Keine Business-Logik identifiziert, die verloren ginge

**Alternative nicht gewählt**: Dockerfile.signal_gen neu erstellen
- **Grund**: Würde doppelte Signal-Generierung bedeuten (cdb_core + cdb_signal_gen)
- **Aufwand**: Unklar, welche Logik der Service haben sollte

### Konsequenzen

**Positiv**:
- ✅ `docker compose config --quiet` → kein Fehler mehr
- ✅ `docker compose up -d` → erfolgreich (alle Services starten)
- ✅ Keine funktionale Einbuße (cdb_core übernimmt Rolle)
- ✅ Klarere Service-Landschaft (weniger verwirrende Legacy-Reste)

**Negativ**:
- ⚠️ Falls Service doch benötigt: Dockerfile.signal_gen muss erstellt werden ODER Funktion in cdb_core migrieren
- ⚠️ Unklarheit über ursprüngliche Absicht (Doku fehlt)

**Risiko-Bewertung**: 🟢 LOW
- Signal-Generierung funktioniert via cdb_core
- Kein Business-Impact identifiziert

### Rollback-Plan

Falls sich herausstellt, dass Service doch benötigt wird:

**Option 1**: Dockerfile.signal_gen erstellen
```dockerfile
# Dockerfile.signal_gen (hypothetisch)
FROM python:3.11-slim
WORKDIR /app
COPY signal_generator.py .
COPY requirements.txt .
RUN pip install -r requirements.txt
CMD ["python", "signal_generator.py"]
```

**Option 2**: Funktion in cdb_core integrieren
- Legacy-Code reviewen
- Logik in cdb_core/service.py einbauen
- Tests ergänzen

### Betroffene Dateien

| Datei | Änderung |
|-------|----------|
| `docker-compose.yml` | Service-Block `cdb_signal_gen` entfernt/auskommentiert |
| `Dockerfile.signal_gen` | Fehlt (war nie vorhanden) |

### Signal-Generierung nach Entfernung

**Aktuelle Implementierung** (via cdb_core):
```
market_data (cdb_ws/cdb_rest)
    ↓
cdb_core (Signal Engine)
    → Momentum-Strategie
    → SIGNAL_THRESHOLD=3.0
    → MIN_VOLUME=100000
    ↓
signals (Redis Topic)
    ↓
cdb_risk (Risk Manager)
```

### Referenzen

- **Pre-Migration Task**: Task 4 (cdb_signal_gen entfernen)
- **Security-Risk**: SR-006 in `infra_conflicts.md` (cdb_signal_gen ohne Health-Check & fehlende Dockerfile)
- **Canonical Schema**: `backoffice/docs/canonical_schema.yaml` → Sektion `services` (cdb_signal_gen nicht enthalten)
- **Pipeline**: Pipeline 4 - Kanonische Systemrekonstruktion

---

## Einfüge-Anleitung

1. **Datei öffnen**: `backoffice/docs/DECISION_LOG.md` (im Claire de Binare-Repo)

2. **Letzte ADR-Nummer finden**: Suche nach höchster ADR-XXX (z.B. ADR-034)

3. **ADRs einfügen**: Am Ende der Datei (oder in chronologischer Reihenfolge):
   - ADR-035 (ENV-Naming-Konvention)
   - ADR-036 (Secrets-Management-Policy)
   - ADR-037 (cdb_signal_gen entfernt)

4. **Commit**:
   ```bash
   git add backoffice/docs/DECISION_LOG.md
   git commit -m "docs: add ADR-035, ADR-036, ADR-037 (post-migration)"
   ```

---

**Status**: ✅ Bereit zum Einfügen
**Anzahl ADRs**: 3
**Gesamtlänge**: ~600 Zeilen Markdown
