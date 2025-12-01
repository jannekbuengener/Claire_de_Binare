# Claire de Binare Migration Manifest - Claire de Binare (HISTORISCH)

**Erstellt**: 2025-11-16
**Migration durchgeführt**: 2025-11-16
**Status**: ✅ **MIGRATION ABGESCHLOSSEN**

> **Historischer Kontext**: Dieses Manifest dokumentiert die erfolgreich durchgeführte Migration vom Backup-Repo in das Claire de Binare-Repository (2025-11-16). Das Dokument dient als Template für zukünftige Repository-Migrationen.

---

## Übersicht

Dieses Manifest definierte präzise, welche Dateien aus dem Backup-Repo (`claire_de_binare - Kopie`) ins Claire de Binare-Repo übertragen wurden.

**Ziel (erreicht)**: Sauberes, kanonisches System ohne Legacy-Ballast, Secrets oder Inkonsistenzen.

---

## Migration-Strategie

### ✅ Was migriert wird

- **Kanonische Dokumentation** (aus sandbox/)
- **Bereinigte Konfiguration** (.env.template, docker-compose.yml)
- **Service-Code** (nur validierte, getestete Services)
- **Infra-Templates** (wiederverwendbare Patterns)
- **ADRs** (Architektur-Entscheidungen)

### ❌ Was NICHT migriert wird

- **Alte ENV-Dateien** (` - Kopie.env` - enthielt Secrets)
- **Legacy-Services** (cdb_signal_gen)
- **Duplikate** (`Dockerfile - Kopie`, alte Compose-Files)
- **Backup/Temp-Files**
- **Git-History** (frisches Repo, saubere History)

---

## Datei-Transfer-Matrix

### 1. Kanonische Dokumentation (sandbox/ → backoffice/docs/)

| Source (Backup-Repo) | Target (Claire de Binare-Repo) | Aktion |
|----------------------|-------------------------|--------|
| `sandbox/canonical_schema.yaml` | `backoffice/docs/canonical_schema.yaml` | COPY |
| `sandbox/canonical_model_overview.md` | `backoffice/docs/canonical_model_overview.md` | COPY |
| `sandbox/canonical_readiness_report.md` | `backoffice/docs/canonical_readiness_report.md` | COPY |
| `sandbox/output.md` | `backoffice/docs/SYSTEM_REFERENCE.md` | RENAME + COPY |
| `sandbox/infra_knowledge.md` | `backoffice/docs/infra_knowledge.md` | COPY |
| `sandbox/file_index.md` | `backoffice/docs/file_index.md` | COPY |
| `sandbox/env_index.md` | `backoffice/docs/env_index.md` | COPY |

**Total**: 7 Dateien

---

### 2. Infra-Templates (sandbox/ → backoffice/templates/)

| Source (Backup-Repo) | Target (Claire de Binare-Repo) | Aktion |
|----------------------|-------------------------|--------|
| `sandbox/infra_templates.md` | `backoffice/templates/infra_templates.md` | COPY |
| `sandbox/project_template.md` | `backoffice/templates/project_template.md` | COPY |
| `sandbox/.env.template` | `backoffice/templates/.env.template` | COPY |

**Total**: 3 Dateien

---

### 3. Konfiguration (Root → Root)

| Source (Backup-Repo) | Target (Claire de Binare-Repo) | Aktion |
|----------------------|-------------------------|--------|
| `.env.template` | `.env.template` | COPY (bereinigte Version) |
| `docker-compose.yml` | `docker-compose.yml` | COPY + REVIEW (cdb_signal_gen entfernt) |
| `prometheus.yml` | `prometheus.yml` | COPY |
| `.gitignore` | `.gitignore` | COPY + VERIFY (.env enthalten) |

**Total**: 4 Dateien

---

### 4. Service-Code (backoffice/services/ → backoffice/services/)

**Nur validierte Services mit Tests und Health-Checks**:

| Service | Source | Target | Bedingung |
|---------|--------|--------|-----------|
| **Signal Engine** | `backoffice/services/signal_engine/` | `backoffice/services/signal_engine/` | ✅ COPY (wenn Tests vorhanden) |
| **Risk Manager** | `backoffice/services/risk_manager/` | `backoffice/services/risk_manager/` | ✅ COPY (wenn Tests vorhanden) |
| **Execution Service** | `backoffice/services/execution_service/` | `backoffice/services/execution_service/` | ✅ COPY (wenn Tests vorhanden) |

**Screeners** (bestehende Implementierung):

| Service | Source | Target | Bedingung |
|---------|--------|--------|-----------|
| **WS Screener** | `mexc_top5_ws.py` | `mexc_top5_ws.py` | ✅ COPY |
| **REST Screener** | `mexc_top_movers.py` | `mexc_top_movers.py` | ✅ COPY |
| **Dockerfile** | `Dockerfile` | `Dockerfile` | ✅ COPY (ohne ` - Kopie` Suffix) |

**Total**: Bis zu 6 Services (abhängig von Test-Abdeckung)

---

### 5. Tests (tests/ → tests/)

| Source | Target | Bedingung |
|--------|--------|-----------|
| `tests/conftest.py` | `tests/conftest.py` | ✅ COPY |
| `tests/unit/test_smoke_repo.py` | `tests/unit/test_smoke_repo.py` | ✅ COPY |
| `tests/integration/test_compose_smoke.py` | `tests/integration/test_compose_smoke.py` | ✅ COPY |

**Total**: 3 Dateien (Basis-Setup)

---

### 6. Backoffice-Dokumentation (bestehend, zu aktualisieren)

Diese Dateien existieren bereits im Claire de Binare-Repo und müssen **aktualisiert** werden:

| Datei | Aktion | Details |
|-------|--------|---------|
| `backoffice/docs/DECISION_LOG.md` | **UPDATE** | 3 neue ADRs hinzufügen (siehe unten) |
| `backoffice/docs/ARCHITEKTUR.md` | **REVIEW** | Konsistenz mit canonical_schema.yaml prüfen |
| `backoffice/PROJECT_STATUS.md` | **UPDATE** | Phase auf "Post-Migration" setzen |

---

### 7. Zusätzliche Dokumentation (sandbox/ → backoffice/docs/)

| Source | Target | Zweck |
|--------|--------|-------|
| `sandbox/PIPELINE_COMPLETE_SUMMARY.md` | `backoffice/docs/PIPELINE_COMPLETE_SUMMARY.md` | Migration-Historie |
| `sandbox/PRE_MIGRATION_EXECUTION_REPORT.md` | `backoffice/docs/PRE_MIGRATION_EXECUTION_REPORT.md` | Pre-Migration-Nachweis |

**Total**: 2 Dateien (optional, für Nachvollziehbarkeit)

---

## ADRs für DECISION_LOG.md

Die folgenden 3 ADRs müssen ins `backoffice/docs/DECISION_LOG.md` eingefügt werden:

### ADR-035: ENV-Naming-Konvention (Dezimal-Format)

```markdown
## ADR-035: ENV-Naming-Konvention für Risk-Parameter (Dezimal-Format)

**Datum**: 2025-11-16
**Status**: ✅ Akzeptiert
**Kontext**: Inkonsistente ENV-Naming führte zu unwirksamen Risk-Limits (5.0 wurde als 500% interpretiert)
**Entscheidung**: Alle Prozent-Angaben in ENV-Variablen nutzen Dezimal-Format (0.05 = 5%) und Suffix `_PCT`
**Konsequenzen**:
- ✅ Eindeutige Interpretation (0.05 = 5%, nicht 500%)
- ✅ Konsistent mit Python float-Arithmetik
- ✅ Alle Risk-Parameter mit `_PCT` Suffix (außer `MAX_SPREAD_MULTIPLIER`, `DATA_STALE_TIMEOUT_SEC`)
- ⚠️ Breaking Change: Alte ENV-Namen (`MAX_DAILY_DRAWDOWN`) nicht mehr gültig
**Betroffene ENV-Variablen**:
- `MAX_DAILY_DRAWDOWN_PCT=0.05` (5%, Min: 0.01, Max: 0.20)
- `MAX_POSITION_PCT=0.10` (10%, Min: 0.01, Max: 0.25)
- `MAX_EXPOSURE_PCT=0.50` (50%, Min: 0.10, Max: 1.00)
- `STOP_LOSS_PCT=0.02` (2%, Min: 0.005, Max: 0.10)
- `MAX_SLIPPAGE_PCT=0.01` (1%, Min: 0.001, Max: 0.05)
**Verantwortlich**: Pipeline 4 - Multi-Agenten-System
**Referenz**: Pre-Migration Task SR-002, canonical_schema.yaml
```

---

### ADR-036: Secrets-Management-Policy

```markdown
## ADR-036: Secrets-Management-Policy (Never Commit Secrets)

**Datum**: 2025-11-16
**Status**: ✅ Akzeptiert
**Kontext**: Exposed Secrets in ` - Kopie.env` (POSTGRES_PASSWORD, GRAFANA_PASSWORD im Klartext committed)
**Entscheidung**: Strikte Trennung zwischen `.env.template` (committed) und `.env` (gitignored, lokal)
**Konsequenzen**:
- ✅ `.env.template` enthält ALLE ENV-Keys, aber nur Platzhalter (`<SET_IN_ENV>`) für Secrets
- ✅ `.env` wird NIE committed (in .gitignore)
- ✅ Alle Secrets (Passwörter, API-Keys, Tokens) nur lokal in `.env`
- ✅ Neue Setups: `.env.template` → `.env` kopieren, dann Platzhalter ersetzen
- ⚠️ Rotation: Manuelle Änderung in `.env` + Container-Restart
**Betroffene Secrets**:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `GRAFANA_PASSWORD`
- `MEXC_API_KEY`, `MEXC_API_SECRET`
**Git-Hook** (empfohlen):
```bash
# .git/hooks/pre-commit
if git diff --cached --name-only | grep -q "^\.env$"; then
  echo "ERROR: .env darf nicht committed werden!"
  exit 1
fi
```
**Verantwortlich**: Pipeline 4 - Multi-Agenten-System
**Referenz**: Pre-Migration Task SR-001, Security-Risk SR-001
```

---

### ADR-037: Legacy-Service cdb_signal_gen entfernt

```markdown
## ADR-037: Legacy-Service cdb_signal_gen entfernt

**Datum**: 2025-11-16
**Status**: ✅ Akzeptiert
**Kontext**: Service `cdb_signal_gen` in docker-compose.yml definiert, aber `Dockerfile.signal_gen` fehlt → Deployment blockiert
**Entscheidung**: Service aus docker-compose.yml entfernen, da wahrscheinlich Legacy (cdb_core übernimmt Rolle)
**Konsequenzen**:
- ✅ docker-compose.yml valide (`docker compose config --quiet` ohne Fehler)
- ✅ Signal-Generierung erfolgt durch `cdb_core` (Signal Engine)
- ⚠️ Falls Service doch benötigt: Dockerfile.signal_gen erstellen oder Funktion in cdb_core migrieren
**Alternative nicht gewählt**: Dockerfile.signal_gen neu erstellen (Grund: cdb_core existiert bereits)
**Verantwortlich**: Pipeline 4 - Multi-Agenten-System
**Referenz**: Pre-Migration Task 4, infra_conflicts.md SR-006
```

---

## Migration-Execution-Plan

### Phase 1: Vorbereitung (Claire de Binare-Repo)

```bash
# 1. Neues Repo initialisieren (falls noch nicht geschehen)
git init claire_de_binare_clean
cd claire_de_binare_clean

# 2. Verzeichnisstruktur erstellen
mkdir -p backoffice/docs
mkdir -p backoffice/templates
mkdir -p backoffice/services
mkdir -p tests/unit
mkdir -p tests/integration
```

---

### Phase 2: Datei-Transfer (Backup → Claire de Binare)

**Automatisiert** (empfohlen):

```powershell
# Script wird erstellt: sandbox/Claire de Binare_migration_script.ps1
.\Claire de Binare_migration_script.ps1 -SourceRepo "C:\...\claire_de_binare - Kopie" -TargetRepo "C:\...\claire_de_binare_clean"
```

**Manuell** (Alternative):

```powershell
# Kanonische Docs
Copy-Item "sandbox/canonical_*.yaml" "$TargetRepo/backoffice/docs/"
Copy-Item "sandbox/canonical_*.md" "$TargetRepo/backoffice/docs/"
Copy-Item "sandbox/output.md" "$TargetRepo/backoffice/docs/SYSTEM_REFERENCE.md"

# Templates
Copy-Item "sandbox/infra_templates.md" "$TargetRepo/backoffice/templates/"
Copy-Item "sandbox/project_template.md" "$TargetRepo/backoffice/templates/"

# Konfiguration
Copy-Item ".env.template" "$TargetRepo/.env.template"
Copy-Item "docker-compose.yml" "$TargetRepo/docker-compose.yml"
Copy-Item "prometheus.yml" "$TargetRepo/prometheus.yml"
Copy-Item ".gitignore" "$TargetRepo/.gitignore"

# Services (nur wenn validiert)
Copy-Item -Recurse "backoffice/services/signal_engine" "$TargetRepo/backoffice/services/" -ErrorAction SilentlyContinue
Copy-Item -Recurse "backoffice/services/risk_manager" "$TargetRepo/backoffice/services/" -ErrorAction SilentlyContinue
Copy-Item -Recurse "backoffice/services/execution_service" "$TargetRepo/backoffice/services/" -ErrorAction SilentlyContinue

# Screeners
Copy-Item "mexc_top5_ws.py" "$TargetRepo/"
Copy-Item "mexc_top_movers.py" "$TargetRepo/"
Copy-Item "Dockerfile" "$TargetRepo/"

# Tests
Copy-Item "tests/conftest.py" "$TargetRepo/tests/"
Copy-Item -Recurse "tests/unit" "$TargetRepo/tests/"
Copy-Item -Recurse "tests/integration" "$TargetRepo/tests/"
```

---

### Phase 3: DECISION_LOG.md aktualisieren

```powershell
# Im Claire de Binare-Repo
code backoffice/docs/DECISION_LOG.md
```

**Zu ergänzen**:
1. ADR-035 (ENV-Naming-Konvention)
2. ADR-036 (Secrets-Management-Policy)
3. ADR-037 (cdb_signal_gen entfernt)

(Vollständiger Text siehe oben)

---

### Phase 4: Validierung (Claire de Binare-Repo)

```bash
# 1. Git-Status prüfen
git status
# Erwartung: Nur neue/modifizierte Dateien, KEINE .env

# 2. docker-compose Syntax
docker compose config --quiet
# Sollte OHNE Fehler durchlaufen

# 3. .env erstellen (lokal)
cp .env.template .env
# Platzhalter ersetzen

# 4. System starten
docker compose up -d

# 5. Health-Checks (nach 30 Sekunden)
docker compose ps
# Erwartung: Alle Services "healthy"

# 6. Tests ausführen
pytest -v
# Erwartung: Alle Tests bestehen

# 7. Smoke-Test
# market_data → signals → orders → order_results
docker exec cdb_redis redis-cli -a $REDIS_PASSWORD PUBLISH market_data '{"symbol":"BTC_USDT","price":50000,"volume":1000000,"timestamp":'$(date +%s)',"pct_change":5.0}'
docker compose logs cdb_core cdb_risk cdb_execution
```

---

### Phase 5: Initial Commit (Claire de Binare-Repo)

```bash
# 1. Staging
git add .

# 2. Finale Überprüfung
git diff --cached --name-only | grep -q "^\.env$"
# Sollte nichts finden (Exit Code 1)

# 3. Commit
git commit -m "$(cat <<'EOF'
feat: initial Claire de Binare migration - canonical system v1.0

Migrated from backup repo after 4-pipeline canonicalization:
- Pipeline 1: Document transfer & audit
- Pipeline 2: Knowledge extraction (skipped, covered by Pipeline 3)
- Pipeline 3: File/infra cleanup & inventory
- Pipeline 4: Canonical system reconstruction

Changes:
- ENV-Naming: Dezimal-Konvention (MAX_DAILY_DRAWDOWN_PCT=0.05)
- Secrets: Stripped from templates, .env gitignored
- Services: cdb_signal_gen removed (legacy, Dockerfile missing)
- Docs: 7 canonical docs added (canonical_schema.yaml, etc.)
- ADRs: 3 new (ADR-035, ADR-036, ADR-037)

Status: ✅ GO for production (Risk-Level: LOW)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# 4. Tag erstellen
git tag -a v1.0-Claire de Binare -m "Claire de Binare baseline after 4-pipeline migration"
```

---

## Erfolgskriterien

### ✅ Migration erfolgreich, wenn:

1. **Alle kritischen Dateien** übertragen (siehe Matrix oben)
2. **docker compose config --quiet** → kein Fehler
3. **docker compose up -d** → alle Services healthy
4. **pytest** → alle Tests bestehen
5. **Keine Secrets** in Git-Log (`git log --all -S "Jannek8" --oneline` → leer)
6. **3 ADRs** in DECISION_LOG.md eingefügt
7. **.env.template** im Root mit allen Platzhaltern
8. **Smoke-Test** erfolgreich (Event-Flow funktioniert)

### ⚠️ Rollback erforderlich, wenn:

1. Health-Checks fehlschlagen
2. Secrets im Git-Log gefunden
3. Tests nicht bestehen
4. docker-compose.yml Syntax-Fehler

---

## Geschätzte Zeiten

| Phase | Aufwand |
|-------|---------|
| Vorbereitung | 15 Min |
| Datei-Transfer | 30 Min (automatisiert) / 60 Min (manuell) |
| DECISION_LOG aktualisieren | 15 Min |
| Validierung | 30 Min |
| Initial Commit | 10 Min |
| **GESAMT** | **1h 40min** (automatisiert) / **2h 10min** (manuell) |

---

## Zusammenfassung

**Datei-Transfer**:
- 7 kanonische Docs
- 3 Templates
- 4 Config-Files
- Bis zu 6 Services
- 3 Test-Files
- 3 ADRs

**Total**: ~20 Dateien + 3 ADRs

**Status**: ✅ Bereit für Execution
**Nächster Schritt**: Migration-Script ausführen oder manuell durchführen

---

**Viel Erfolg bei der Claire de Binare-Migration!** 🚀
