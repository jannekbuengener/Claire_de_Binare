# Infra-Konflikte - Redundanzen, Widersprüche & Lücken

**Erstellt von**: agata-van-data
**Datum**: 2025-11-16
**Quellen**: file_index.md, env_index.md, infra_knowledge.md

## Kategorien

- **Port-Konflikt**: Unterschiedliche Ports für denselben Service
- **ENV-Konflikt**: Widersprüchliche ENV-Namen oder -Werte
- **File-Redundanz**: Duplikate oder ähnliche Files
- **Legacy**: Files ohne offensichtliche Nutzung
- **Unklar**: Widersprüchliche oder unvollständige Informationen
- **Security-Gap**: Fehlende Security-Maßnahmen

## 1. ENV-Naming & Format-Konflikt (KRITISCH!)

**Kategorie**: ENV-Konflikt
**Betroffene Files**: ` - Kopie.env`, `sandbox/output.md` (Architektur-Referenz)

### Beschreibung

Risk-Parameter haben unterschiedliche Namen und Formate in verschiedenen Quellen:

| Parameter | ` - Kopie.env` | output.md | Format Konflikt |
|-----------|----------------|-----------|-----------------|
| Daily Drawdown | `MAX_DAILY_DRAWDOWN=5.0` | `MAX_DAILY_DRAWDOWN_PCT=0.05` | Prozent (5.0) vs. Dezimal (0.05) |
| Position Size | `MAX_POSITION_SIZE=10.0` | `MAX_POSITION_PCT=0.10` | Prozent (10.0) vs. Dezimal (0.10) |
| Exposure | `MAX_TOTAL_EXPOSURE=50.0` | `MAX_EXPOSURE_PCT=0.50` | Prozent (50.0) vs. Dezimal (0.50) |

### Auswirkung

- Code, der `MAX_DAILY_DRAWDOWN_PCT` erwartet, wird nicht funktionieren mit ` - Kopie.env`
- Verwechslungsgefahr: 5.0% als Dezimal interpretiert = 500% Drawdown-Limit!
- Unterschiedliche Services könnten unterschiedliche Konventionen nutzen → **Inkonsistente Risk-Checks**

### Empfehlung

**Option A (Dezimal-Konvention)**:
- Alle ENV auf `*_PCT` umbenennen
- Werte als Dezimal (0.05 für 5%)
- Vorteile: Konsistent mit output.md, weniger Ambiguität
- Nachteil: ` - Kopie.env` muss komplett überarbeitet werden

**Option B (Prozent-Konvention)**:
- Alle ENV **ohne** `_PCT`-Suffix
- Werte als Prozent (5.0 für 5%)
- Vorteile: Lesbarere ENV-Datei (5.0 statt 0.05)
- Nachteil: output.md muss überarbeitet werden

**Präferenz**: **Option A** (Dezimal) → Best Practice in Trading-Code, weniger Fehleranfälligkeit

## 2. Fehlende ENV-Variablen

**Kategorie**: ENV-Konflikt / Lücke
**Betroffene Files**: ` - Kopie.env`, `sandbox/output.md`

### Beschreibung

Folgende ENV-Variablen sind in `output.md` dokumentiert, aber **fehlen** in ` - Kopie.env`:

| ENV-Variable | Dokumentiert in | Default (laut output.md) | Bedeutung |
|--------------|-----------------|--------------------------|-----------|
| `STOP_LOSS_PCT` | output.md | 0.02 (2%) | Stop-Loss pro Trade |
| `MAX_SLIPPAGE_PCT` | output.md | 0.01 (1%) | Marktanomalien-Schwellwert |
| `MAX_SPREAD_MULTIPLIER` | output.md | 5.0 | Spread-Multiplikator |
| `DATA_STALE_TIMEOUT_SEC` | output.md | 30 | Datenstille-Timeout (Sekunden) |
| `MEXC_API_KEY`, `MEXC_API_SECRET` | output.md (Pflicht) | — | MEXC-API-Credentials |

### Auswirkung

- Risk Manager wird diese Variablen nicht finden → **Startup-Fehler** oder **unerwartete Defaults**
- `MEXC_API_KEY/SECRET` fehlen komplett → **Screener kann nicht funktionieren**

### Empfehlung

Ergänze in ` - Kopie.env`:
```env
# ============================================================================
# RISK MANAGEMENT (Erweitert)
# ============================================================================
STOP_LOSS_PCT=0.02
MAX_SLIPPAGE_PCT=0.01
MAX_SPREAD_MULTIPLIER=5.0
DATA_STALE_TIMEOUT_SEC=30

# ============================================================================
# MEXC API (Secrets - NIEMALS committen!)
# ============================================================================
MEXC_API_KEY=<SET_IN_ENV>
MEXC_API_SECRET=<SET_IN_ENV>
```

## 3. File-Duplikate (Legacy-Verdacht)

**Kategorie**: File-Redundanz
**Betroffene Files**: `Dockerfile - Kopie`, `Dockerfile - Kopie.test`

### Beschreibung

| Original | Duplikat | Nutzung |
|----------|----------|---------|
| `Dockerfile` | `Dockerfile - Kopie` | Kein Service in docker-compose.yml nutzt das Duplikat |
| `Dockerfile.test` | `Dockerfile - Kopie.test` | Kein Service in docker-compose.yml nutzt das Duplikat |

### Empfehlung

- **Prüfen**: Diff zwischen Original und Duplikat (`diff Dockerfile "Dockerfile - Kopie"`)
- **Falls identisch**: Duplikat löschen
- **Falls unterschiedlich**: Zweck klären, ggf. umbenennen (z.B. `Dockerfile.legacy`)

## 4. compose.yml vs. docker-compose.yml

**Kategorie**: File-Redundanz / Unklar
**Betroffene Files**: `compose.yml`, `docker-compose.yml`

### Beschreibung

Beide Dateien existieren im Root-Verzeichnis. Moderne Docker-Compose-Versionen bevorzugen `compose.yml`, ältere nutzen `docker-compose.yml`.

### Empfehlung

- **Prüfen**: Sind beide identisch? (`diff compose.yml docker-compose.yml`)
- **Falls identisch**: Eine Datei entfernen (bevorzugt `compose.yml` behalten, da moderner Standard)
- **Falls unterschiedlich**: Klären, welche aktiv genutzt wird, die andere als `.bak` markieren

## 5. Fehlende Datei: Dockerfile.signal_gen

**Kategorie**: Legacy / Unklar
**Betroffene Files**: `docker-compose.yml` (Service `cdb_signal_gen`)

### Beschreibung

`docker-compose.yml` referenziert `Dockerfile.signal_gen` im Service `cdb_signal_gen`, aber die Datei existiert **nicht** im File-Index.

### Auswirkung

- `docker compose build` wird für `cdb_signal_gen` **fehlschlagen**
- Service kann nicht gestartet werden

### Empfehlung

**Option A (Legacy-Service)**:
- Service `cdb_signal_gen` aus docker-compose.yml entfernen (auskommentieren)
- Begründung: Möglicherweise ersetzt durch `cdb_core` (Signal Engine)

**Option B (Fehlendes File)**:
- `Dockerfile.signal_gen` wiederherstellen aus Git-Historie
- Prüfen, ob Service noch benötigt wird

**Präferenz**: **Option A** → Service erscheint redundant zu `cdb_core`

## 6. Security-Hardening-Inkonsistenz

**Kategorie**: Security-Gap
**Betroffene Files**: docker-compose.yml (Services)

### Beschreibung (siehe infra_knowledge.md für Details)

| Service-Gruppe | Hardening-Status | Betroffene Services |
|----------------|------------------|---------------------|
| **MVP-Services** | ✅ Fast vollständig | `cdb_ws`, `cdb_core`, `cdb_risk`, `cdb_execution` |
| **cdb_rest** | ⚠️ Teilweise | `no-new-privileges`, `cap_drop`, `tmpfs` → aber **kein `read_only`** |
| **Infra-Services** | ❌ Kein Hardening | `cdb_redis`, `cdb_postgres`, `cdb_prometheus`, `cdb_grafana` |
| **cdb_signal_gen** | ❌ Kein Hardening | — |

### Spezifische Lücken

#### cdb_rest: Fehlendes read_only

- Alle anderen MVP-Services haben `read_only: true`, cdb_rest **nicht**
- **Grund unklar**: Läuft als periodischer Job, sollte ebenfalls read-only sein können

#### Infra-Services: Keine Security-Flags

- Redis, Postgres, Prometheus, Grafana nutzen Standard-Images **ohne** Hardening
- **Risiko**:
  - Container-Breakout möglich
  - Privilege Escalation via Kernel-Exploits
  - Uneingeschränkter Zugriff auf Host-Ressourcen (bei Volume-Escape)

### Empfehlung

1. **cdb_rest**: `read_only: true` hinzufügen (testen, ob kompatibel)
2. **Infra-Services**: Security-Flags ergänzen:
   ```yaml
   security_opt:
     - no-new-privileges:true
   cap_drop:
     - ALL
   ```
   - **Ausnahme**: Redis/Postgres könnten `cap_add` für spezifische Capabilities benötigen (testen!)
3. **cdb_signal_gen**: Hardening hinzufügen **oder** Service entfernen (siehe Konflikt #5)

## 7. Port-ENV-Mismatch

**Kategorie**: ENV-Konflikt / Unklar
**Betroffene Files**: docker-compose.yml, ` - Kopie.env`

### Beschreibung

ENV-Variablen `WS_PORT`, `SIGNAL_PORT`, `RISK_PORT`, `EXEC_PORT` existieren in ` - Kopie.env`, aber docker-compose.yml hat **hardcoded Ports**:

| ENV-Variable | ENV-Wert | docker-compose.yml |
|--------------|----------|--------------------|
| `WS_PORT` | 8000 | `8000:8000` (hardcoded) |
| `SIGNAL_PORT` | 8001 | `8001:8001` (hardcoded) |
| `RISK_PORT` | 8002 | `8002:8002` (hardcoded) |
| `EXEC_PORT` | 8003 | `8003:8003` (hardcoded) |

### Auswirkung

- ENV-Variablen werden **nicht** von docker-compose.yml genutzt
- Änderungen in `.env` haben **keine Wirkung** auf Port-Mappings
- ENV könnte **innerhalb der Container** genutzt werden (z.B. für Binding-Address), aber unklar

### Empfehlung

**Option A (ENV nutzen)**:
```yaml
ports:
  - "${WS_PORT}:${WS_PORT}"
```
- Vorteil: Flexible Port-Konfiguration
- Nachteil: Port-Änderung erfordert Anpassung in mehreren Services (wenn Host/Container unterschiedlich)

**Option B (ENV entfernen)**:
- `WS_PORT`, `SIGNAL_PORT`, etc. aus ` - Kopie.env` löschen
- Ports bleiben hardcoded in docker-compose.yml
- Vorteil: Weniger Verwirrung
- **Präferenz**: **Option B** (Einfachheit, da MVP)

## 8. query_service: Test ohne Service-Definition

**Kategorie**: Unklar
**Betroffene Files**: `backoffice/services/query_service/test_service.py`, docker-compose.yml

### Beschreibung

- Test-Datei existiert für `query_service`
- **Kein** Service `query_service` in docker-compose.yml definiert

### Mögliche Szenarien

1. **In Entwicklung**: Service noch nicht in Compose integriert
2. **Legacy**: Service wurde entfernt, Test nicht
3. **Anderer Stack**: Service läuft außerhalb von Docker Compose

### Empfehlung

- Klären: Ist `query_service` geplant oder Legacy?
- Falls geplant: Service in docker-compose.yml hinzufügen
- Falls Legacy: Test-Datei entfernen oder in `backoffice/services/query_service.bak/` verschieben

## 9. Secrets in ENV-Datei (KRITISCH!)

**Kategorie**: Security-Gap
**Betroffene Files**: ` - Kopie.env`

### Beschreibung

` - Kopie.env` enthält **echte Secrets**:
```env
POSTGRES_PASSWORD=Jannek8$  # ⚠️ ECHTES PASSWORT
```

### Auswirkung

- Falls `.env` versehentlich committed wird: **Secrets geleakt**
- Auch in Backup-Repo ist dies ein **Sicherheitsrisiko**

### Empfehlung

**Sofort**:
- Alle echten Secrets in ` - Kopie.env` durch Platzhalter ersetzen:
  ```env
  POSTGRES_PASSWORD=<SET_IN_ENV>
  REDIS_PASSWORD=<SET_IN_ENV>
  GRAFANA_PASSWORD=<SET_IN_ENV>
  MEXC_API_KEY=<SET_IN_ENV>
  MEXC_API_SECRET=<SET_IN_ENV>
  ```
- Datei umbenennen zu `.env.template` (klarere Intention)
- Echte `.env` in `.gitignore` sicherstellen

## 10. GRAFANA_PASSWORD vs. GF_SECURITY_ADMIN_PASSWORD

**Kategorie**: ENV-Konflikt / Duplikat-Verdacht
**Betroffene Files**: ` - Kopie.env`, docker-compose.yml

### Beschreibung

- ` - Kopie.env` (Zeile 50+, nicht in Auszug sichtbar): Wahrscheinlich `GRAFANA_PASSWORD`
- docker-compose.yml: `GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:?...}`

### Klärung erforderlich

- Sind beide **identisch** (Alias)?
- Falls ja: Dokumentieren in env_index.md
- Falls nein: Zweck klären

### Empfehlung

- ENV-Mapping prüfen
- Falls Alias: Umbenennen auf `GF_SECURITY_ADMIN_PASSWORD` für Klarheit
- Falls unterschiedlich: Beschreibung ergänzen

## Zusammenfassung nach Priorität

### 🔴 KRITISCH (Blocker)

| Nr. | Konflikt | Betroffene Files | Aktion erforderlich |
|-----|----------|------------------|---------------------|
| 1 | ENV-Naming & Format-Konflikt | ` - Kopie.env`, output.md | Vereinheitlichen auf Dezimal-Konvention (`*_PCT`) |
| 2 | Fehlende ENV-Variablen | ` - Kopie.env` | `STOP_LOSS_PCT`, `MEXC_API_KEY/SECRET` ergänzen |
| 5 | Fehlende Datei: Dockerfile.signal_gen | docker-compose.yml | Service entfernen oder Dockerfile wiederherstellen |
| 9 | Secrets in ENV-Datei | ` - Kopie.env` | Secrets durch Platzhalter ersetzen, umbenennen zu `.env.template` |

### 🟡 HOCH (Wichtig, aber nicht blockierend)

| Nr. | Konflikt | Betroffene Files | Aktion empfohlen |
|-----|----------|------------------|------------------|
| 6 | Security-Hardening-Inkonsistenz | docker-compose.yml | `read_only` für cdb_rest, Security-Flags für Infra-Services |

### 🟢 MITTEL (Nice-to-have)

| Nr. | Konflikt | Betroffene Files | Aktion empfohlen |
|-----|----------|------------------|------------------|
| 3 | File-Duplikate | `Dockerfile - Kopie` | Diff prüfen, ggf. löschen |
| 4 | compose.yml vs. docker-compose.yml | compose.yml | Diff prüfen, eine Datei entfernen |
| 7 | Port-ENV-Mismatch | ` - Kopie.env`, docker-compose.yml | ENV entfernen oder nutzen |
| 8 | query_service: Test ohne Service | test_service.py | Klären: Entwicklung oder Legacy? |
| 10 | GRAFANA_PASSWORD Duplikat | ` - Kopie.env` | ENV-Mapping dokumentieren |

---

## Security- und Risk-Bewertung

**Auditor**: claire-risk-engine-guardian
**Datum**: 2025-11-16
**Scope**: Read-only Security-Audit auf Infra-/Env-Ebene

### Risk-Level Kategorisierung

- **CRITICAL**: Unmittelbare Sicherheitslücke oder Risk-Management-Versagen
- **HIGH**: Erhebliches Risiko, sollte vor Production behoben werden
- **MEDIUM**: Best-Practice-Verletzung, mittelfristiges Risiko
- **LOW**: Verbesserungspotenzial, kein akutes Risiko

---

### 🔴 CRITICAL-Level Risks

#### SR-001: Exposed Secrets in ENV-Template

**Kategorie**: Secret-Leakage
**Betroffene Datei**: ` - Kopie.env`
**Beschreibung**:
- ENV-Datei enthält **echte Passwörter** (`POSTGRES_PASSWORD=Jannek8$`)
- Falls versehentlich committed: **Vollständiger Datenbankzugriff** kompromittiert
- Backup-Repo ist ebenfalls exponiert → **Secrets bereits verbreitet**

**Empfohlene Maßnahmen**:
1. **Sofort**: Alle Secrets in ` - Kopie.env` durch `<SET_IN_ENV>` ersetzen
2. Datei umbenennen zu `.env.template`
3. Echte `.env` in `.gitignore` verifizieren
4. **Passwort-Rotation**: `POSTGRES_PASSWORD` ändern (falls ENV jemals committed wurde)
5. Git-Historie scannen: `git log --all -S "Jannek8" --oneline` → Falls gefunden: **Historie säubern** (BFG, git-filter-repo)

**Risk-Impact**: 🔴🔴🔴🔴🔴 (5/5) - Datenverlust, unbefugter Zugriff, System-Kompromittierung möglich

---

#### SR-002: ENV-Naming-Konflikt führt zu fehlerhaften Risk-Limits

**Kategorie**: Risk-Management-Failure
**Betroffene Files**: ` - Kopie.env` (Prozent-Werte) vs. output.md / Code (Dezimal-Erwartung)
**Beschreibung**:
- `MAX_DAILY_DRAWDOWN=5.0` in ENV könnte als **Dezimal 5.0 = 500%** interpretiert werden
- Falls Risk Manager Dezimalwerte erwartet (`0.05` für 5%): **Risk-Checks werden deaktiviert**
- Beispiel: Daily Drawdown Limit von 5% wird zu 500% → **Kein Trading-Stopp** bei Verlust

**Szenario**:
```python
# Risk Manager Code (erwartet Dezimal)
if current_drawdown_pct > float(os.getenv("MAX_DAILY_DRAWDOWN")):
    halt_trading()

# ENV hat: MAX_DAILY_DRAWDOWN=5.0
# current_drawdown_pct = 0.08 (8% Verlust)
# Check: 0.08 > 5.0? → FALSE → Kein Halt! ❌
```

**Empfohlene Maßnahmen**:
1. **Code-Audit**: Alle Risk-Parameter-Lesezugriffe prüfen (erwartetes Format?)
2. **Vereinheitlichen**: Entweder **alle** ENV auf Dezimal (`MAX_DAILY_DRAWDOWN_PCT=0.05`) **oder** Code anpassen
3. **Unit-Tests**: Risk-Limit-Parsing mit ENV-Werten testen
4. **Validierung beim Startup**: Range-Checks (`0.01 <= MAX_DAILY_DRAWDOWN_PCT <= 0.20` für Dezimal)

**Risk-Impact**: 🔴🔴🔴🔴⚪ (4/5) - Risk-Limits unwirksam, unkontrollierte Verluste möglich

---

#### SR-003: Fehlende MEXC-API-Credentials

**Kategorie**: Operational-Failure
**Betroffene Files**: ` - Kopie.env` (fehlt komplett)
**Beschreibung**:
- `MEXC_API_KEY`, `MEXC_API_SECRET` fehlen in ENV-Template
- Screener-Services (`cdb_ws`, `cdb_rest`) können **keine Marktdaten** abrufen
- Kein Marktdaten → Kein Signal → Kein Trading

**Empfohlene Maßnahmen**:
1. ENV-Template ergänzen:
   ```env
   MEXC_API_KEY=<SET_IN_ENV>
   MEXC_API_SECRET=<SET_IN_ENV>
   ```
2. Startup-Validierung: Services crashen mit `Exit 1`, falls ENV fehlt
3. Dokumentation: `.env.template` mit Hinweis auf MEXC-API-Registrierung

**Risk-Impact**: 🔴🔴🔴⚪⚪ (3/5) - System nicht funktionsfähig, aber kein direkter Datenverlust

---

### 🟠 HIGH-Level Risks

#### SR-004: Infrastruktur-Services ohne Security-Hardening

**Kategorie**: Container-Security
**Betroffene Services**: `cdb_redis`, `cdb_postgres`, `cdb_prometheus`, `cdb_grafana`
**Beschreibung**:
- Keine `no-new-privileges`, `cap_drop: ALL`, `tmpfs`, `read_only`
- Bei Container-Escape via Kernel-Exploit: **Uneingeschränkter Host-Zugriff** möglich
- Besonders kritisch: **Redis** (enthält alle Event-Daten, Passwörter im Memory)

**Angriffs-Szenario**:
1. Angreifer exploited CVE in Redis 7-alpine
2. Container-Breakout → Root-Zugriff auf Host
3. Zugriff auf **alle** Volumes (postgres_data, redis_data) → **Vollständige Datenbank-Exfiltration**

**Empfohlene Maßnahmen**:
1. Security-Flags hinzufügen:
   ```yaml
   security_opt:
     - no-new-privileges:true
   cap_drop:
     - ALL
   cap_add:  # Falls benötigt, minimalistisch
     - CHOWN  # Nur für Postgres/Redis Daten-Ownership
   ```
2. **Testen**: Services nach Hardening starten, Health-Checks prüfen
3. Falls Inkompatibilität: Spezifische Capabilities dokumentieren

**Risk-Impact**: 🟠🟠🟠🟠⚪ (4/5) - Host-Kompromittierung möglich, Datenverlust wahrscheinlich

---

#### SR-005: cdb_rest ohne read-only Filesystem

**Kategorie**: Container-Security
**Betroffene Services**: `cdb_rest`
**Beschreibung**:
- Alle anderen MVP-Services haben `read_only: true`, cdb_rest **nicht**
- Bei Exploit: Angreifer kann **Malware persistieren** im Container-FS
- Beispiel: Backdoor-Script in `/tmp` schreiben → Überlebt Container-Restart? (Nein, aber während Runtime aktiv)

**Empfohlene Maßnahmen**:
1. `read_only: true` hinzufügen
2. Falls Service schreibbare Verzeichnisse benötigt: `tmpfs` für `/app/cache` o.Ä.
3. Testen: Periodic Loop (`python app.py; sleep 300`) mit read-only FS

**Risk-Impact**: 🟠🟠🟠⚪⚪ (3/5) - Runtime-Kompromittierung, begrenzte Persistenz

---

#### SR-006: cdb_signal_gen ohne Health-Check & Hardening

**Kategorie**: Monitoring-Gap & Security
**Betroffene Services**: `cdb_signal_gen`
**Beschreibung**:
- Kein Health-Check → **Service-Ausfall unbemerkt**
- Keine Security-Flags → Container-Escape-Risiko
- **Dockerfile.signal_gen fehlt** → Service kann nicht gebaut werden (siehe SR-007)

**Empfohlene Maßnahmen**:
1. Klären: Ist Service noch benötigt? (Vermutlich Legacy, da `cdb_core` existiert)
2. Falls benötigt:
   - Health-Check hinzufügen (z.B. Redis-Verbindungs-Test)
   - Security-Flags ergänzen
   - Dockerfile.signal_gen wiederherstellen
3. **Präferenz**: Service aus docker-compose.yml entfernen (auskommentieren)

**Risk-Impact**: 🟠🟠⚪⚪⚪ (2/5) - Monitoring-Lücke, aber Service möglicherweise Legacy

---

### 🟡 MEDIUM-Level Risks

#### SR-007: Fehlende Risk-Parameter in ENV

**Kategorie**: Risk-Management-Incompleteness
**Betroffene Files**: ` - Kopie.env` (fehlt: `STOP_LOSS_PCT`, `MAX_SLIPPAGE_PCT`, `MAX_SPREAD_MULTIPLIER`, `DATA_STALE_TIMEOUT_SEC`)
**Beschreibung**:
- Dokumentierte Risk-Parameter in output.md fehlen in ENV-Template
- Risk Manager wird auf **Hardcoded Defaults** zurückfallen → **Intransparente Konfiguration**

**Empfohlene Maßnahmen**:
1. ENV-Template komplettieren (siehe infra_conflicts.md #2)
2. Dokumentation: Welche Defaults gelten, wenn ENV fehlt?
3. Startup-Warnung: Log-Message bei fehlenden ENV mit Fallback-Werten

**Risk-Impact**: 🟡🟡⚪⚪⚪ (2/5) - Konfigurationsfehler möglich, aber durch Defaults abgefangen

---

#### SR-008: Development-Mounts in Production-Setup

**Kategorie**: Deployment-Antipattern
**Betroffene Services**: `cdb_core`, `cdb_risk`, `cdb_execution`
**Beschreibung**:
- Source-Code als Volume gemountet (`./backoffice/services/signal_engine:/app`)
- **Code-Änderungen ohne Rebuild** möglich → **Versionskontrolle umgangen**
- Bei Produktions-Deployment: Unerwartete Code-Änderungen, fehlende Abhängigkeiten

**Empfohlene Maßnahmen**:
1. **Development**: Aktuelles Setup beibehalten (praktisch für Tests)
2. **Production**: Volume-Mounts entfernen, Code in Image einbrennen
3. docker-compose.override.yml nutzen:
   - `docker-compose.yml`: Production-Setup (kein Volume-Mount)
   - `docker-compose.override.yml`: Development-Setup (mit Volume-Mount)

**Risk-Impact**: 🟡🟡🟡⚪⚪ (3/5) - Deployment-Risiko, aber aktuell MVP-Phase

---

### 🟢 LOW-Level Risks

#### SR-009: Hardcoded Prometheus Host-Port

**Kategorie**: Network-Flexibility
**Betroffene Services**: `cdb_prometheus`
**Beschreibung**:
- Host-Port `19090` statt Standard `9090`
- Grund unklar (Port-Konflikt-Vermeidung?)
- Bei Multi-Deployment (mehrere Instanzen): Port-Kollisionen möglich

**Empfohlene Maßnahmen**:
- ENV-basiertes Mapping: `${PROMETHEUS_PORT:-19090}:9090`
- Dokumentation: Warum 19090? (z.B. "Vermeidung Konflikt mit lokalem Prometheus")

**Risk-Impact**: 🟢⚪⚪⚪⚪ (1/5) - Nur Flexibilitäts-Einschränkung

---

### Zusammenfassung: Risk-Matrix

| Risk-ID | Kategorie | Level | Muss behoben vor Production? |
|---------|-----------|-------|------------------------------|
| SR-001 | Secret-Leakage | 🔴 CRITICAL | ✅ JA (sofort) |
| SR-002 | Risk-Management-Failure | 🔴 CRITICAL | ✅ JA |
| SR-003 | Operational-Failure | 🔴 CRITICAL | ✅ JA |
| SR-004 | Container-Security | 🟠 HIGH | ✅ JA |
| SR-005 | Container-Security | 🟠 HIGH | ✅ JA |
| SR-006 | Monitoring-Gap & Security | 🟠 HIGH | ⚠️ Falls Service benötigt |
| SR-007 | Risk-Management-Incompleteness | 🟡 MEDIUM | ⚠️ Empfohlen |
| SR-008 | Deployment-Antipattern | 🟡 MEDIUM | ❌ Akzeptabel für MVP |
| SR-009 | Network-Flexibility | 🟢 LOW | ❌ Optional |

### Empfohlene Reihenfolge der Behebung

1. **Sofort** (Pre-Commit):
   - SR-001: Secrets aus ENV entfernen
   - SR-003: MEXC-API-ENV ergänzen

2. **Vor nächstem Deploy** (Pre-Production):
   - SR-002: ENV-Naming-Konflikt auflösen
   - SR-004: Infra-Services härten
   - SR-005: cdb_rest read-only

3. **Mittelfristig** (Post-MVP):
   - SR-007: ENV komplettieren
   - SR-006: cdb_signal_gen entfernen/reparieren

4. **Optional** (Nice-to-have):
   - SR-008: Production-Compose erstellen
   - SR-009: Port-ENV einführen

### Verweise auf bestehende Dokumentation

Falls im Haupt-Repo ein **Security-Risk-Register** existiert (z.B. in `backoffice/docs/SECURITY_RISK_REGISTER.md`), sollten diese SR-IDs dort übernommen werden.

Siehe auch:
- `sandbox/output.md` (Architektur-Referenz, Risk-Parameter-Dokumentation)
- `sandbox/audit_log.md` (Security-Anmerkungen aus Pipeline 1)
- `backoffice/docs/Risikomanagement-Logik.md` (Risk-Engine-Logik)
